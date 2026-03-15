import anthropic
import os
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- STEP 1: Define the actual functions your code can run ---

def read_file(path):
    with open(path, 'r') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)
    return f"File written to {path}"

def list_files(directory):
    files = os.listdir(directory)
    return json.dumps(files)

# --- STEP 2: Describe those functions to Claude ---

tools = [
    {
        "name": "read_file",
        "description": "Reads the contents of a file and returns the text",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The file path to read"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Writes content to a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The file path to write to"},
                "content": {"type": "string", "description": "The content to write"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_files",
        "description": "Lists all files in a directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "The directory path to list"}
            },
            "required": ["directory"]
        }
    }
]

# --- STEP 3: The tool executor - runs whatever tool Claude picks ---

def run_tool(tool_name, tool_input):
    print(f"  Running tool: {tool_name} with input: {tool_input}")
    if tool_name == "read_file":
        return read_file(tool_input["path"])
    elif tool_name == "write_file":
        return write_file(tool_input["path"], tool_input["content"])
    elif tool_name == "list_files":
        return list_files(tool_input["directory"])

# --- STEP 4: The agentic loop - keeps going until Claude is done ---

def run_agent(task):
    print(f"\nTask: {task}\n")
    messages = [{"role": "user", "content": task}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        # If Claude is done, print the final answer
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, 'text'):
                    print(f"\nClaude's final answer:\n{block.text}")
            break

        # If Claude wants to use a tool, run it
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })

            messages.append({"role": "user", "content": tool_results})

# --- Run it ---
run_agent("List the files in the texts folder, then read sample.txt and write a one-paragraph summary to summaries/tool_summary.txt")
