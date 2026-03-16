import anthropic
import os
import json
import requests
from dotenv import load_dotenv
from ddgs import DDGS
from bs4 import BeautifulSoup

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- TOOLS ---

notes = {}  # simple in-memory scratchpad

def search_web(query):
    print(f"    [search_web] Query: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        return json.dumps([{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results])
    except Exception as e:
        return f"Search failed: {e}"

def extract_page_content(url):
    print(f"    [extract_page] URL: {url}")
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")
        # Get main text, limit to 2000 chars to save tokens
        text = " ".join(soup.get_text().split())[:2000]
        return text
    except Exception as e:
        return f"Could not extract page: {e}"

def save_note(key, value):
    print(f"    [save_note] Key: {key}")
    notes[key] = value
    return f"Note saved under '{key}'"

def get_notes():
    print(f"    [get_notes] Retrieving all notes")
    if not notes:
        return "No notes saved yet."
    return json.dumps(notes, indent=2)

def write_report(filename, content):
    print(f"    [write_report] Writing to {filename}")
    with open(filename, "w") as f:
        f.write(content)
    return f"Report written to {filename}"

# --- TOOL DEFINITIONS FOR CLAUDE ---

tools = [
    {
        "name": "search_web",
        "description": "Search the web using DuckDuckGo. Returns titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "extract_page_content",
        "description": "Extract the text content from a web page URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to extract content from"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "save_note",
        "description": "Save a note to memory with a key and value for later use.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The note label"},
                "value": {"type": "string", "description": "The note content"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "get_notes",
        "description": "Retrieve all saved notes.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_report",
        "description": "Write the final research report to a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The output filename"},
                "content": {"type": "string", "description": "The full report content"}
            },
            "required": ["filename", "content"]
        }
    }
]

# --- TOOL EXECUTOR ---

def run_tool(name, inputs):
    if name == "search_web":
        return search_web(inputs["query"])
    elif name == "extract_page_content":
        return extract_page_content(inputs["url"])
    elif name == "save_note":
        return save_note(inputs["key"], inputs["value"])
    elif name == "get_notes":
        return get_notes()
    elif name == "write_report":
        return write_report(inputs["filename"], inputs["content"])
    else:
        return f"Unknown tool: {name}"

# --- CONTEXT MANAGEMENT: SUMMARIZATION ---
# Every N turns, summarize the conversation to prevent context overflow

def summarize_messages(messages):
    print(f"\n  [context] Summarizing conversation history to save context space...")
    history_text = json.dumps(messages, indent=2)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"Summarize what has been done so far in this agent session. Be concise. Include: what was searched, what was found, what notes were saved, what still needs to be done.\n\nHistory:\n{history_text}"
        }]
    )

    summary = response.content[0].text
    print(f"  [context] History compressed. Summary: {summary[:200]}...")

    # Replace full history with just the summary
    return [{"role": "user", "content": f"Previous work summary:\n{summary}\n\nContinue working on the original goal."}]


# --- AGENTIC LOOP ---

def run_research_agent(goal, max_iterations=30, summarize_every=8):
    print(f"\n=== RESEARCH AGENT STARTED ===")
    print(f"Goal: {goal}\n")

    messages = [{"role": "user", "content": goal}]
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="""You are a research agent. Your job is to research a topic and write a report efficiently.

Follow this process STRICTLY:
1. Do 2-3 searches maximum
2. Extract content from 3-4 pages maximum
3. Save your key findings using save_note
4. After no more than 8 tool calls total, write the final report using write_report to 'research_report.txt'
5. You MUST write the report by iteration 8 — do not keep researching indefinitely

Be concise and efficient. Stop researching and write the report early.""",
            tools=tools,
            messages=messages
        )

        # If Claude is done
        if response.stop_reason == "end_turn":
            print(f"\n=== AGENT FINISHED after {iteration} iterations ===")
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nClaude: {block.text}")
            break

        # Summarize every N iterations to prevent context overflow
        if iteration % summarize_every == 0:
            messages = summarize_messages(messages)

        # If Claude wants to use tools
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

    if iteration >= max_iterations:
        print(f"\n=== AGENT STOPPED: max iterations ({max_iterations}) reached ===")

# --- RUN IT ---
run_research_agent("Research the top 3 competitors to eBay in the secondhand goods marketplace space. For each competitor, find their key features, target audience, and how they differ from eBay. Write a report summarizing your findings.")
