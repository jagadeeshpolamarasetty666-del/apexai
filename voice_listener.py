import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import re
import sys
import threading
import time
import requests
import pyttsx3
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from PyQt6.QtWidgets import QApplication
from siri_hud import SiriOrbWidget, signals

try:
    import pythoncom
except ImportError:
    pythoncom = None

SAMPLE_RATE = 16000
WAKE_PATTERNS = [r"\bbro\b", r"\bhey bro\b", r"\byo bro\b"]

is_cancelled = threading.Event()
active_request_adapter = {"session": None}

def on_cancel_signal():
    print("\n🛑 Cancel clicked on HUD.")
    is_cancelled.set()
    s = active_request_adapter.get("session")
    if s:
        try:
            s.close()
        except Exception:
            pass

signals.cancel_requested.connect(on_cancel_signal)

def speak(text: str):
    """Speaks short responses and manages Windows SAPI/COM lifecycle."""
    if is_cancelled.is_set():
        return
    trimmed = text.strip()
    if len(trimmed) > 220:
        trimmed = trimmed[:220] + "..."

    print(f"\n🔊 Apex: {trimmed}")
    signals.show_hud.emit("Apex Speaking...")
    signals.update_text.emit(trimmed)

    if pythoncom:
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 190)
        engine.say(trimmed)
        engine.runAndWait()
        engine.stop()
        del engine
    except Exception as e:
        print(f"TTS Audio Output Error: {e}")
    finally:
        # Give audio driver time to flush buffers
        time.sleep(0.35)

print("Loading Whisper tiny.en...")
whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")

default_device = sd.query_devices(kind="input")
print(f"🎤 Active Microphone: {default_device['name']}")

def normalize_audio(audio: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(audio))
    if peak > 0.001:
        return audio / peak * 0.95
    return audio

def transcribe_audio(audio_array: np.ndarray) -> str:
    if len(audio_array) == 0:
        return ""
    norm = normalize_audio(audio_array)
    segments, _ = whisper_model.transcribe(
        norm,
        beam_size=1,
        language="en",
        condition_on_previous_text=False
    )
    return " ".join([seg.text for seg in segments]).strip().lower()

def clean_command(text: str) -> str:
    cleaned = text
    for pat in WAKE_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def record_user_command(duration: float = 4.5) -> str:
    """Records voice command buffer safely."""
    try:
        rec = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocking=True
        )
        return transcribe_audio(rec.flatten())
    except Exception as e:
        print(f"Recording buffer error: {e}")
        sd.stop()
        return ""

def execute_apex_command(command: str) -> bool:
    """Sends command to FastAPI backend. Returns True if successfully handled."""
    if is_cancelled.is_set():
        return False

    signals.show_hud.emit("Processing Command...")
    signals.update_text.emit(f"'{command}'")

    session = requests.Session()
    active_request_adapter["session"] = session

    try:
        res = session.post(
            "http://127.0.0.1:8000/api/chat",
            json={"message": command},
            timeout=15
        ).json()

        if is_cancelled.is_set():
            return False

        reply_type = res.get("type")

        if reply_type == "action_proposal":
            action = res.get("pending_action", {})
            action_id = action.get("action_id")
            tool_name = action.get("tool_name", "action")

            signals.show_hud.emit("Executing Action...")
            signals.update_text.emit(f"Running {tool_name}...")

            if is_cancelled.is_set():
                return False

            appr = session.post(
                "http://127.0.0.1:8000/api/approve",
                json={"action_id": action_id, "approved": True},
                timeout=15
            ).json()

            if is_cancelled.is_set():
                return False

            tool_result = appr.get("result", "")
            if tool_result:
                speak(f"{tool_result}")
            else:
                speak(f"Done bro, {tool_name} executed.")
            return True

        elif reply_type == "auto_executed":
            if not is_cancelled.is_set():
                speak(f"{res.get('result', 'Task complete.')}")
            return True
        else:
            if not is_cancelled.is_set():
                speak(res.get("reply", "Task finished, bro."))
            return True

    except requests.exceptions.RequestException:
        if is_cancelled.is_set():
            print("Action aborted by user.")
        else:
            speak("Apex backend is offline.")
        return False
    finally:
        session.close()
        active_request_adapter["session"] = None

def voice_daemon_loop():
    if pythoncom:
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass

    print("\n" + "=" * 55)
    print("🚀 Apex Continuous Voice Daemon Active")
    print("👉 Say 'bro' or 'hey bro' to initiate conversation.")
    print("👉 Continue speaking follow-ups naturally without wake words!")
    print("=" * 55 + "\n")

    WINDOW_SEC = 2.0

    while True:
        try:
            is_cancelled.clear()

            # STANDBY LISTENING (Wake word detection)
            rec = sd.rec(
                int(WINDOW_SEC * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocking=True
            )
            audio = rec.flatten()

            if np.max(np.abs(audio)) < 0.0015:
                continue

            detected_text = transcribe_audio(audio)
            is_wake = any(re.search(pat, detected_text, re.IGNORECASE) for pat in WAKE_PATTERNS)

            if is_wake:
                print(f"\n⚡ Wake word triggered: '{detected_text}'")
                signals.show_hud.emit("Hey Bro, Listening...")
                signals.update_text.emit("Yes bro? What's up?")
                speak("Yes bro?")

                # CONTINUOUS DIALOGUE LOOP
                while True:
                    if is_cancelled.is_set():
                        break

                    signals.show_hud.emit("Listening...")
                    signals.update_text.emit("Listening for your command...")

                    cmd_text = record_user_command(duration=4.5)
                    cmd_text = clean_command(cmd_text)

                    if is_cancelled.is_set():
                        break

                    if cmd_text and len(cmd_text) > 2:
                        print(f"🎯 Recognized Command: '{cmd_text}'")
                        success = execute_apex_command(cmd_text)
                        if not success or is_cancelled.is_set():
                            break

                        # Prompt for follow-up command
                        signals.show_hud.emit("Listening for follow-up...")
                        signals.update_text.emit("Anything else, bro?")
                        time.sleep(0.4)
                    else:
                        # User stopped speaking, return to standby
                        print("💤 Conversation timed out. Returning to standby.")
                        signals.update_text.emit("Going to standby...")
                        time.sleep(0.8)
                        signals.hide_hud.emit()
                        break

        except Exception as e:
            print(f"Loop cycle recovered: {e}")
            time.sleep(0.3)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    orb = SiriOrbWidget()

    worker = threading.Thread(target=voice_daemon_loop, daemon=True)
    worker.start()

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\n👋 Apex voice listener stopped.")
        sys.exit(0)