import os
import json
import uuid
import ctypes
import subprocess
import webbrowser
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

# COM initialization for Windows worker threads
try:
    import pythoncom
except ImportError:
    pythoncom = None

# Audio & Display Hardware Controls
try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
except ImportError:
    AudioUtilities = None

app = FastAPI(title="Apex AI Backend", version="2.3")

LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_ID = "qwen2.5-7b-instruct"

pending_actions: Dict[str, Dict[str, Any]] = {}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_application_or_site",
            "description": "Opens a desktop application, website, or Windows utility (e.g., YouTube, VS Code, Calculator, Settings, Chrome, Edge).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "The name of the app, protocol, or URL to launch (e.g., 'youtube', 'edge', 'calc', 'notepad', 'code', 'https://github.com')."
                    }
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_system_volume",
            "description": "Adjusts Windows master volume. Can increase, decrease, mute, unmute, or set to an exact level (0-100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["increase", "decrease", "set", "mute", "unmute"],
                        "description": "The volume adjustment to perform."
                    },
                    "level": {
                        "type": "integer",
                        "description": "Optional target percentage from 0 to 100 (used when action is 'set')."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_screen_brightness",
            "description": "Adjusts laptop display brightness. Can raise/lower brightness relatively, or set an exact percentage (0-100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["increase", "decrease", "set"],
                        "description": "Whether to increase, decrease, or set exact brightness level."
                    },
                    "level": {
                        "type": "integer",
                        "description": "The exact percentage (0-100) or change amount (default is 15)."
                    }
                },
                "required": ["action"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are Apex, a fast Windows voice assistant.
- Address the user casually as 'bro'.
- Keep all conversational responses strictly 1 to 2 sentences. Never ramble.
- When the user asks to launch an app, visit a site, or change volume/brightness, invoke the matching function immediately.
- Never output markdown formatting or bullet points in voice replies."""

class ChatRequest(BaseModel):
    message: str

class ApproveRequest(BaseModel):
    action_id: str
    approved: bool

def set_volume_windows(action: str, val: Optional[int] = None) -> dict:
    """Adjusts Windows master volume reliably using Win32 API and pycaw."""
    action = action.lower().strip()

    # Hardware Virtual Key Codes
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF

    # 1. Direct hardware stepping via Windows user32 keybd_event
    if action in ["increase", "up", "raise"]:
        steps = max(1, (val // 2) if (val and val > 0) else 4)
        for _ in range(steps):
            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
        return {"output": "Volume increased, bro.", "error": False}

    elif action in ["decrease", "down", "lower"]:
        steps = max(1, (val // 2) if (val and val > 0) else 4)
        for _ in range(steps):
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
        return {"output": "Volume decreased, bro.", "error": False}

    elif action == "mute":
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
        return {"output": "Volume muted, bro.", "error": False}

    elif action == "unmute":
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
        return {"output": "Volume unmuted, bro.", "error": False}

    # 2. Set Exact Percentage (0-100) via Core Audio WASAPI
    elif action == "set" or val is not None:
        target_val = val if val is not None else 50
        target_val = max(0, min(100, target_val))

        if pythoncom:
            try:
                pythoncom.CoInitialize()
            except Exception:
                pass

        try:
            if AudioUtilities is None:
                raise RuntimeError("pycaw library missing")

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(target_val / 100.0, None)
            return {"output": f"Volume set to {target_val} percent, bro.", "error": False}
        except Exception as e:
            return {"output": f"Could not set exact volume: {str(e)}", "error": True}
        finally:
            if pythoncom:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

    return {"output": "Unknown volume action, bro.", "error": True}

def execute_action(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # 1. Master Volume Control
        if name == "adjust_system_volume":
            action = args.get("action", "increase")
            val = args.get("level")
            return set_volume_windows(action, val)

        # 2. Display Brightness Control
        elif name == "adjust_screen_brightness":
            action = args.get("action", "increase")
            val = args.get("level", 15)

            if sbc is None:
                return {"output": "screen_brightness_control library not found.", "error": True}

            try:
                current = sbc.get_brightness(display=0)
                current_val = current[0] if isinstance(current, list) else current

                if action == "set":
                    target_val = max(5, min(100, val))
                elif action == "decrease":
                    target_val = max(5, current_val - val)
                else:  # increase
                    target_val = min(100, current_val + val)

                sbc.set_brightness(target_val)
                return {"output": f"Brightness set to {target_val} percent, bro.", "error": False}
            except Exception as e:
                return {"output": f"Could not adjust brightness: {str(e)}", "error": True}

        # 3. Application & Website Launching
        elif name == "open_application_or_site":
            raw_target = args.get("target", "").strip()
            target = raw_target.lower()

            app_map = {
                "edge": "microsoft-edge:https://www.google.com",
                "msedge": "microsoft-edge:https://www.google.com",
                "microsoft edge": "microsoft-edge:https://www.google.com",
                "chrome": "chrome",
                "google chrome": "chrome",
                "youtube": "https://www.youtube.com",
                "google": "https://www.google.com",
                "github": "https://www.github.com",
                "calc": "calc.exe",
                "calculator": "calc.exe",
                "notepad": "notepad.exe",
                "vscode": "code",
                "code": "code",
                "vs code": "code",
                "spotify": "spotify",
                "settings": "ms-settings:",
                "explorer": "explorer.exe",
                "cmd": "cmd.exe",
                "terminal": "wt.exe",
            }

            resolved = app_map.get(target, raw_target)

            if resolved.startswith("http://") or resolved.startswith("https://"):
                webbrowser.open(resolved, new=2)
                return {"output": f"Opened {resolved} in browser.", "error": False}

            if ":" in resolved and not os.path.exists(resolved):
                os.startfile(resolved)
                return {"output": f"Opened {raw_target}.", "error": False}

            if any(resolved.endswith(tld) for tld in [".com", ".org", ".net", ".in", ".io", ".co"]):
                full_url = f"https://{resolved}"
                webbrowser.open(full_url, new=2)
                return {"output": f"Opened {full_url}.", "error": False}

            try:
                os.startfile(resolved)
                return {"output": f"Launched {raw_target}.", "error": False}
            except Exception:
                subprocess.Popen(f'start "" "{resolved}"', shell=True)
                return {"output": f"Launched {raw_target}.", "error": False}

        return {"output": f"Unknown tool: {name}", "error": True}

    except Exception as ex:
        return {"output": f"Execution error in {name}: {str(ex)}", "error": True}

@app.get("/api/health")
def health():
    return {"status": "online", "model": MODEL_ID}

@app.post("/api/chat")
def chat(req: ChatRequest):
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.message}
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.2,
        "max_tokens": 150
    }

    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=20)
        data = response.json()
        choice = data["choices"][0]["message"]

        if choice.get("tool_calls"):
            tool_call = choice["tool_calls"][0]
            func_name = tool_call["function"]["name"]

            raw_args = tool_call["function"].get("arguments", "{}")
            func_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

            action_id = str(uuid.uuid4())
            pending_actions[action_id] = {
                "tool_name": func_name,
                "tool_args": func_args
            }

            return {
                "type": "action_proposal",
                "pending_action": {
                    "action_id": action_id,
                    "tool_name": func_name,
                    "tool_args": func_args
                }
            }

        reply = choice.get("content", "I'm right here bro.")
        return {"type": "chat_reply", "reply": reply}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"LM Studio connection error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/api/approve")
def approve(req: ApproveRequest):
    if req.action_id not in pending_actions:
        raise HTTPException(status_code=404, detail="Action ID not found.")

    action = pending_actions.pop(req.action_id)
    if not req.approved:
        return {"status": "rejected", "result": "Action cancelled."}

    result = execute_action(action["tool_name"], action["tool_args"])
    return {
        "status": "completed",
        "tool_name": action["tool_name"],
        "result": result.get("output", "Action executed.")
    }