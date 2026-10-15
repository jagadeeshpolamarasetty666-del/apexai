import json
import os
import requests

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_ID = "qwen/qwen3-4b"

# 1. Define a sandboxed action tool
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_local_folder",
            "description": "Creates a new folder inside the user's workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {
                        "type": "string",
                        "description": "Name of the folder to create",
                    }
                },
                "required": ["folder_name"],
            },
        },
    }
]


def execute_tool(name: str, arguments: dict):
    """Safe execution sandbox"""
    if name == "create_local_folder":
        folder_name = arguments.get("folder_name")
        sandbox_path = os.path.join(os.getcwd(), "sandbox", folder_name)
        os.makedirs(sandbox_path, exist_ok=True)
        return (
            f"Success: Folder '{folder_name}' created safely in sandbox directory."
        )
    return "Error: Tool not recognized or unauthorized."


# 2. Ask the model to perform an action
payload = {
    "model": MODEL_ID,
    "messages": [
        {
            "role": "system",
            "content": "You are Apex AI, a desktop assistant. When a user asks you to create a folder, invoke the create_local_folder tool.",
        },
        {"role": "user", "content": "Please create a folder named 'JavaPractice'"},
    ],
    "tools": TOOLS,
    "tool_choice": "auto",
    "temperature": 0.0,
}

print("Querying local model for action plan...")
response = requests.post(LM_STUDIO_URL, json=payload).json()
choice = response["choices"][0]["message"]

if "tool_calls" in choice and choice["tool_calls"]:
    call = choice["tool_calls"][0]
    func_name = call["function"]["name"]
    func_args = json.loads(call["function"]["arguments"])
    print(f"\n[AI PROPOSED ACTION]")
    print(f"Tool: {func_name}")
    print(f"Arguments: {func_args}")

    # Simulated user approval gate
    approval = input("\nApprove action execution? (y/n): ")
    if approval.lower() == "y":
        result = execute_tool(func_name, func_args)
        print(f"[ACTION RESULT]: {result}")
    else:
        print("[ACTION ABORTED BY USER]")
else:
    print("\nModel replied conversationally without calling a tool:")
    print(choice.get("content"))