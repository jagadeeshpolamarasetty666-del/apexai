import os
import uuid
import json
import subprocess
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

from server.db import init_db, save_message, get_recent_messages, log_action, get_audit_logs, add_task, get_tasks, toggle_task, delete_task

app = FastAPI(title="Apex AI Local Engine")

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_ID = "qwen/qwen3-4b"
SANDBOX_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sandbox")
os.makedirs(SANDBOX_DIR, exist_ok=True)

pending_actions: Dict[str, Dict[str, Any]] = {}
SAFE_TOOLS = {"list_workspace_files", "read_workspace_file"}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_workspace_files",
            "description": "Lists all files and subdirectories currently present in the sandbox workspace.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_workspace_file",
            "description": "Reads and returns the text content of a file inside the sandbox workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the file to inspect"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_local_folder",
            "description": "Creates a new folder inside the workspace sandbox directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {"type": "string", "description": "Name of the directory to create"},
                },
                "required": ["folder_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_local_file",
            "description": "Creates or writes text into a file inside the workspace sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the file with extension"},
                    "content": {"type": "string", "description": "The file content to write"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_code_script",
            "description": "Executes a Python (.py) or Java (.java) script located in the sandbox and returns its terminal output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File to execute (e.g., solution.py or Main.java)"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_windows_terminal",
            "description": "Opens a native Windows PowerShell terminal window in the workspace directory.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_workspace_in_vscode",
            "description": "Opens Visual Studio Code directly inside the user sandbox directory.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_workspace_in_explorer",
            "description": "Opens the Windows File Explorer directly showing the sandbox folder.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

class ChatRequest(BaseModel):
    message: str

class ApprovalRequest(BaseModel):
    action_id: str
    approved: bool

class TaskCreateRequest(BaseModel):
    title: str

def execute_action(name: str, args: dict) -> Dict[str, Any]:
    if name == "list_workspace_files":
        items = os.listdir(SANDBOX_DIR)
        if not items:
            return {"output": "The workspace directory is currently empty.", "error": False}
        formatted = []
        for item in items:
            path = os.path.join(SANDBOX_DIR, item)
            kind = "[DIR]" if os.path.isdir(path) else "[FILE]"
            formatted.append(f"{kind} {item}")
        return {"output": "\n".join(formatted), "error": False}

    elif name == "read_workspace_file":
        filename = os.path.basename(args.get("filename", ""))
        target = os.path.join(SANDBOX_DIR, filename)
        if not os.path.exists(target):
            return {"output": f"Error: File '{filename}' does not exist in sandbox.", "error": True}
        if os.path.isdir(target):
            return {"output": f"Error: '{filename}' is a directory, not a file.", "error": True}
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            return {"output": f.read(), "error": False}

    elif name == "create_local_folder":
        folder = os.path.basename(args.get("folder_name", ""))
        target = os.path.join(SANDBOX_DIR, folder)
        os.makedirs(target, exist_ok=True)
        return {"output": f"Created folder '{folder}' at sandbox/{folder}", "error": False}

    elif name == "create_local_file":
        filename = os.path.basename(args.get("filename", "notes.txt"))
        content = args.get("content", "")
        target = os.path.join(SANDBOX_DIR, filename)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return {"output": f"Created file '{filename}' with {len(content)} characters.", "error": False}

    elif name == "execute_code_script":
        filename = os.path.basename(args.get("filename", ""))
        target = os.path.join(SANDBOX_DIR, filename)
        if not os.path.exists(target):
            return {"output": f"Error: File '{filename}' not found in sandbox.", "error": True}

        try:
            if filename.endswith(".py"):
                res = subprocess.run(
                    ["python", target],
                    cwd=SANDBOX_DIR,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
            elif filename.endswith(".java"):
                res = subprocess.run(
                    ["java", target],
                    cwd=SANDBOX_DIR,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
            else:
                return {"output": "Error: Only .py and .java scripts are permitted.", "error": True}

            is_error = res.returncode != 0
            raw_output = res.stderr if is_error else res.stdout
            cleaned = raw_output.strip() or ("Script finished with returncode 0" if not is_error else "Unknown script error")
            return {"output": cleaned, "error": is_error, "filename": filename}
        except subprocess.TimeoutExpired:
            return {"output": "Execution timed out (15 second limit exceeded).", "error": True, "filename": filename}
        except Exception as e:
            return {"output": f"Execution failed: {str(e)}", "error": True, "filename": filename}

    elif name == "open_windows_terminal":
        try:
            subprocess.Popen(["powershell.exe", "-NoExit", "-Command", f"Set-Location '{SANDBOX_DIR}'"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            return {"output": "Launched Windows PowerShell console in sandbox workspace.", "error": False}
        except Exception as e:
            return {"output": f"Failed to launch Terminal: {str(e)}", "error": True}

    elif name == "open_workspace_in_vscode":
        try:
            subprocess.Popen(["code", SANDBOX_DIR], shell=True)
            return {"output": "Launched Visual Studio Code in sandbox workspace.", "error": False}
        except Exception as e:
            return {"output": f"Failed to launch VS Code: {str(e)}", "error": True}

    elif name == "open_workspace_in_explorer":
        try:
            subprocess.Popen(["explorer", os.path.normpath(SANDBOX_DIR)])
            return {"output": "Opened Windows File Explorer for sandbox directory.", "error": False}
        except Exception as e:
            return {"output": f"Failed to open File Explorer: {str(e)}", "error": True}

    return {"output": "Error: Unknown action.", "error": True}

def generate_healing_fix(filename: str, error_log: str) -> Dict[str, Any] | None:
    target = os.path.join(SANDBOX_DIR, filename)
    if not os.path.exists(target):
        return None
    with open(target, "r", encoding="utf-8", errors="ignore") as f:
        code_content = f.read()

    prompt = (
        f"The following script '{filename}' failed during execution with an error.\n\n"
        f"### ORIGINAL CODE:\n{code_content}\n\n"
        f"### ERROR LOG:\n{error_log}\n\n"
        "Provide ONLY the corrected, full source code with no markdown formatting, no backticks, and no explanations. Just raw code."
    )
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a code debugger. Output ONLY corrected raw code without backticks or explanations."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
    }
    try:
        res = requests.post(LM_STUDIO_URL, json=payload, timeout=20).json()
        fixed_code = res["choices"][0]["message"].get("content", "").strip()
        # Clean potential markdown backticks if returned
        if fixed_code.startswith("```"):
            fixed_code = "\n".join(fixed_code.split("\n")[1:])
        if fixed_code.endswith("```"):
            fixed_code = "\n".join(fixed_code.split("\n")[:-1])
        return {"filename": filename, "content": fixed_code.strip()}
    except Exception:
        return None

@app.get("/api/history")
def get_history():
    return {"history": get_recent_messages(50)}

@app.get("/api/logs")
def get_logs():
    return {"logs": get_audit_logs(50)}

@app.get("/api/tasks")
def list_tasks():
    return {"tasks": get_tasks()}

@app.post("/api/tasks")
def create_task(req: TaskCreateRequest):
    new_id = add_task(req.title)
    return {"status": "created", "id": new_id, "title": req.title}

@app.post("/api/tasks/{task_id}/toggle")
def toggle_task_status(task_id: int):
    toggle_task(task_id)
    return {"status": "updated"}

@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: int):
    delete_task(task_id)
    return {"status": "deleted"}

@app.post("/api/chat")
def handle_chat(req: ChatRequest):
    save_message("user", req.message)

    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Apex AI, an operating system assistant. Always provide a helpful conversational reply. "
                    "Use tools when requested: open_windows_terminal for terminal/command prompt, "
                    "open_workspace_in_vscode for VS Code, open_workspace_in_explorer for File Explorer, "
                    "or file management tools for files/folders."
                ),
            },
            {"role": "user", "content": req.message},
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.2,
    }

    try:
        res = requests.post(LM_STUDIO_URL, json=payload, timeout=20).json()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="LM Studio timed out.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LM Studio connection error: {str(e)}")

    choice = res["choices"][0]["message"]

    if "tool_calls" in choice and choice["tool_calls"]:
        call = choice["tool_calls"][0]
        tool_name = call["function"]["name"]
        raw_args = call["function"]["arguments"]
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

        if tool_name in SAFE_TOOLS:
            res_obj = execute_action(tool_name, args)
            tool_output = res_obj["output"]
            log_action(tool_name, json.dumps(args), "auto_executed")

            summary_payload = {
                "model": MODEL_ID,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a concise desktop assistant. Provide a direct, helpful summary of the tool output."
                    },
                    {
                        "role": "user",
                        "content": f"The user asked: '{req.message}'.\n\nThe tool '{tool_name}' returned:\n{tool_output}\n\nSummarize this for the user."
                    }
                ],
                "temperature": 0.1,
            }
            try:
                summary_res = requests.post(LM_STUDIO_URL, json
Set-Content -Path "update_app.ps1" -Value @'
$path = "ui/src/App.tsx"
$content = Get-Content $path -Raw$oldBlock = @"
      setActiveAction(null);
      setMessages(prev => [
        ...prev,
        {
          sender: 'apex',
          text: approved ? `Execution result: ${data.result}` : 'Action execution was cancelled.'
        }
      ]);
"@

$newBlock = @"
      if (data.self_healing && data.pending_action) {
        setActiveAction(data.pending_action);
        setMessages(prev => [
          ...prev,
          {
            sender: 'apex',
            text: `${data.result}\n\n⚠️ Self-Healing Engine: A code patch has been generated. Review and approve the patch below:`,
            action: data.pending_action
          }
        ]);
      } else {
        setActiveAction(null);
        setMessages(prev => [
          ...prev,
          {
            sender: 'apex',
            text: approved ? `Execution result: ${data.result}` : 'Action execution was cancelled.'
          }
        ]);
      }
"@

$content =$content.Replace($oldBlock,$newBlock)
Set-Content -Path $path -Value$content -Encoding UTF8
