#  Apex AI — Local Desktop Voice Assistant

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![GUI](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Model](https://img.shields.io/badge/LLM-Qwen%202.5%207B-orange.svg)](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**Apex** is a low-latency, fully offline desktop voice assistant built specifically for Windows automation. Powered by a local **Qwen 2.5 7B** model and **OpenAI Whisper**, Apex provides hands-free system controls, multi-turn conversational follow-ups, and native OS integrations—with zero external API calls or cloud dependencies.

---

##  Key Highlights

* **100% Offline & Private:** All inference runs on-device via LM Studio (CUDA-accelerated) and local Whisper models.
* **Continuous Multi-Turn Dialogue:** Speak naturally without repeating the wake word (`"Hey bro"`) between successive commands.
* **Native Windows Automation:** Direct control over applications, URLs, system master volume, and laptop display backlight.
* **Floating HUD Interface:** A sleek, glassmorphic Siri-inspired overlay built with PyQt6, featuring non-blocking signal handling and manual cancellation.
* **Hardware-Optimized:** Tuned specifically for mid-tier laptop GPUs (e.g., NVIDIA GeForce RTX 3050 6GB) using Q4_K_M GGUF quantization.

---

##  System Architecture

```text
       🎤 User Speech
             │
             ▼
   [faster-whisper (tiny.en)]  ──> Real-time Local Transcription
             │
             ▼
    [voice_listener.py]       ──> Wake Detection & Continuous Loop
             │
      (HTTP POST /api/chat)
             │
             ▼
    [FastAPI Server :8000]    ──> Orchestration & Action Dispatcher
             │
    (OpenAI-Compatible API)
             │
             ▼
    [LM Studio / Qwen 2.5 7B] ──> GPU-Accelerated Function Calling
             │
             ▼
    ┌──────────────────────── Native Windows Actions ────────────────────────┐
    │  • os.startfile() / Webbrowser   ──> Apps & URLs                       │
    │  • pycaw & user32 keybd_event    ──> Hardware Master Volume & Mute     │
    │  • screen-brightness-control     ──> Laptop Backlight via WMI          │
    └────────────────────────────────────────────────────────────────────────┘
             │
             ▼
      [PyQt6 Siri HUD]         ──> Real-time Visual State & Audio Feedback
