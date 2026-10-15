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
         User Speech
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
```
## Tech Stack & PrerequisitesOS:
OS: Windows 10 / 11 (64-bit)
Python: 3.10 to 3.12
GPU: NVIDIA GPU with 6GB+ VRAM recommended (CUDA-enabled)
Core Libraries:
faster-whisper — Fast local ASR engine
sounddevice & numpy — Low-latency audio capture
fastapi & uvicorn — Backend REST API
PyQt6 — Frameless desktop HUD
pycaw & comtypes — Windows Core Audio WASAPI integration
screen-brightness-control — Display backlight control
pyttsx3 — Offline text-to-speech
## Installation & Setup
1. Clone the Repository
PowerShell
git clone https://github.com/<your-username>/apex-ai.git
cd apex-ai
2. Set Up Virtual Environment
PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
3. Install Dependencies
PowerShell
pip install -r requirements.txt
4. Configure LM Studio (Local Inference)
Download and install LM Studio.
Search and download: Qwen2.5-7B-Instruct-GGUF (Choose Q4_K_M).
Navigate to the Local Server tab (<->):
GPU Offload: ON (CUDA, device 0)
Limit Model Offload to Dedicated GPU: ON
Offload KV Cache to GPU: ON
Context Length: 4096 or 8192
Model Loading Guardrails: Relaxed (or Custom 6 GB)
Start the server on port 1234.

## Running Apex
Open two separate PowerShell terminals:

Terminal 1: Start Backend Server
PowerShell
.\venv\Scripts\python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8000
Terminal 2: Launch Voice Listener & HUD
PowerShell
.\venv\Scripts\python.exe voice_listener.py
 ##Usage & Voice CommandsActivate
 Apex by saying "Hey bro" or "Bro". After the initial prompt, continue issuing commands naturally:
 CategoryExample Voice CommandsBrowser & Apps
 "Open YouTube", "Open Edge", "Launch VS Code", "Open Calculator"System Volume"Increase volume", "Decrease volume", "Set volume to 40 percent", "Mute"Display Brightness"Increase brightness", "Decrease brightness", "Set brightness to 70 percent"General Q&A"What is RAM?", "Explain binary search in two sentences"Cancel / ExitClick the ✕ button on the floating HUD or stay silent for 4 seconds to enter standby.
 Project StructurePlaintextapex-ai/
├── server/
│   └── main.py           # FastAPI application, tool schemas, and Win32 handlers
├── siri_hud.py           # PyQt6 translucent floating overlay widget
├── voice_listener.py     # Continuous audio capture, Whisper ASR, and dialogue loop
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
 LicenseThis project is licensed under the MIT License.
---

### Push the Fix to GitHub

Run this in your PowerShell terminal:

```powershell
git add README.md
git commit -m "fix: close architecture code fence and restore markdown layout"
git push origin main
