import anthropic
import os
import json
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv
from ddgs import DDGS
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# --- TOOLS ---

def search_web(query, notes):
    print(f"    [search_web] Query: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        return json.dumps([{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results])
    except Exception as e:
        return f"Search failed: {e}"

def extract_page_content(url, notes):
    print(f"    [extract_page] URL: {url}")
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")
        text = " ".join(soup.get_text().split())[:2000]
        return text
    except Exception as e:
        return f"Could not extract page: {e}"

def save_note(competitor_name, competitor_type, aspects_data, notes):
    print(f"    [save_note] Saving note for: {competitor_name}")
    notes[competitor_name] = {
        "type": competitor_type,
        "aspects": aspects_data
    }
    return f"Note saved for '{competitor_name}'"

def propose_competitor_list(competitors, notes):
    competitor_list = list(competitors) if isinstance(competitors, list) else [competitors]

    while True:
        print(f"\n{'='*60}")
        print(f"  [APPROVAL GATE 1] Agent identified these competitors:\n")
        for i, c in enumerate(competitor_list, 1):
            print(f"    {i}. {c}")
        print(f"\n  Commands: press Enter to approve | 'add [name]' | 'remove [name]'")
        print(f"{'='*60}")

        user_input = input("\n  Your decision: ").strip().lower()

        if not user_input:
            print(f"\n  [gate 1] Approved. Proceeding to research {len(competitor_list)} competitors.\n")
            return f"Competitor list approved: {json.dumps(competitor_list)}. Now research each one."
        elif user_input.startswith("add "):
            name = user_input[4:].strip().title()
            competitor_list.append(name)
            print(f"  Added: {name}")
        elif user_input.startswith("remove "):
            name = user_input[7:].strip().lower()
            before = len(competitor_list)
            competitor_list = [c for c in competitor_list if c.lower() != name]
            if len(competitor_list) < before:
                print(f"  Removed: {name.title()}")
            else:
                print(f"  Not found: {name.title()}")
        else:
            print("  Type 'add [name]', 'remove [name]', or press Enter to approve.")


# --- TOOL DEFINITIONS FOR CLAUDE ---

tools = [
    {
        "name": "search_web",
        "description": "Search the web using DuckDuckGo. Returns titles, URLs, and snippets. Use specific queries like '[competitor name] [company] competitor features fees target audience comparison'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A specific search query including the competitor name and what you want to know."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "extract_page_content",
        "description": "Extract the full text content from a web page URL. Prefer Wikipedia, official sites, or comparison articles over social media.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the page to extract content from."
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "propose_competitor_list",
        "description": "After your first search, call this to propose the competitor list to the user for approval before starting research. The user can add or remove competitors. You MUST call this before researching any individual competitor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "competitors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The list of competitor names you identified from your initial search."
                }
            },
            "required": ["competitors"]
        }
    },
    {
        "name": "save_note",
        "description": "Save structured findings about a competitor. Call this once per competitor immediately after researching them. Data must be structured for table output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "competitor_name": {
                    "type": "string",
                    "description": "The name of the competitor (e.g. 'Amazon', 'Netflix')."
                },
                "competitor_type": {
                    "type": "string",
                    "description": "A short one-line description of what type of company this is (e.g. 'Broad horizontal e-commerce marketplace', 'Subscription video streaming platform')."
                },
                "aspects_data": {
                    "type": "object",
                    "description": "A JSON object where each key is an aspect name and each value is the detailed findings for that aspect. Every requested aspect must be a key.",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["competitor_name", "competitor_type", "aspects_data"]
        }
    }
]


# --- TOOL EXECUTOR ---

def run_tool(name, inputs, notes):
    if name == "search_web":
        return search_web(inputs["query"], notes)
    elif name == "extract_page_content":
        return extract_page_content(inputs["url"], notes)
    elif name == "propose_competitor_list":
        return propose_competitor_list(inputs["competitors"], notes)
    elif name == "save_note":
        return save_note(
            inputs["competitor_name"],
            inputs["competitor_type"],
            inputs["aspects_data"],
            notes
        )
    else:
        return f"Unknown tool: {name}"


# --- QUALITY CHECKER ---

def check_quality(notes, aspects):
    if not notes:
        return 0
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": f"""Score the quality of this competitor research from 0-100.
Each competitor must cover these aspects: {', '.join(aspects)}.
Notes collected so far ({len(notes)} competitors):
{json.dumps(notes, indent=2)}

Rules:
- All key competitors covered with all aspects fully addressed = 100
- Missing competitors or incomplete aspects = deduct points proportionally
- Respond with ONLY a number between 0 and 100. Nothing else."""
        }]
    )
    try:
        return int(response.content[0].text.strip())
    except:
        return 0


# =============================================================================
# CONTEXT WINDOW MANAGEMENT — 3 STRATEGIES
# =============================================================================

# --- STRATEGY 1: SUMMARIZATION ---
# Every 3 iterations, compress conversation history into a summary.
# Prevents the message list from growing too large on long runs.

def summarize_history(messages, company, notes):
    print(f"\n  [context] Summarizing conversation history (iteration checkpoint)...")

    # Build a readable version of history for Claude to summarize
    history_text = []
    for m in messages:
        if isinstance(m["content"], str):
            history_text.append(f"{m['role'].upper()}: {m['content']}")
        elif isinstance(m["content"], list):
            for block in m["content"]:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        history_text.append(f"TOOL RESULT: {str(block.get('content', ''))[:300]}")
                elif hasattr(block, "type"):
                    if block.type == "text":
                        history_text.append(f"ASSISTANT: {block.text[:300]}")
                    elif block.type == "tool_use":
                        history_text.append(f"TOOL CALL: {block.name}({json.dumps(block.input)[:200]})")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"""Summarize what this research agent has done so far. Be concise.
Include: which competitors were identified, which have been researched, which are still pending, and any key findings.

History:
{chr(10).join(history_text[-30:])}

Respond in 3-5 bullet points."""
        }]
    )

    summary = response.content[0].text
    print(f"  [context] History compressed. Summary:\n  {summary[:300]}...")

    # Replace full history with summary + current notes state
    compressed = [
        {
            "role": "user",
            "content": f"""Previous session summary:
{summary}

Competitors researched so far: {list(notes.keys()) if notes else 'None yet'}

Continue researching remaining competitors for {company}."""
        }
    ]
    return compressed


# --- STRATEGY 2: SELECTIVE MEMORY ---
# Keep only the last N tool results in active context.
# Older tool results are archived to a file, not lost — just moved out of context.

def trim_tool_results(messages, keep_last=3, archive_file="context_archive.jsonl"):
    tool_result_indices = [
        i for i, m in enumerate(messages)
        if isinstance(m.get("content"), list)
        and any(
            isinstance(b, dict) and b.get("type") == "tool_result"
            for b in m["content"]
        )
    ]

    if len(tool_result_indices) <= keep_last:
        return messages  # nothing to trim

    # Archive older tool results
    to_archive = tool_result_indices[:-keep_last]
    with open(archive_file, "a") as f:
        for idx in to_archive:
            f.write(json.dumps(messages[idx]) + "\n")

    # Remove archived messages from active context
    indices_to_remove = set(to_archive)
    trimmed = [m for i, m in enumerate(messages) if i not in indices_to_remove]

    archived_count = len(to_archive)
    if archived_count > 0:
        print(f"  [context] Archived {archived_count} old tool results. Keeping last {keep_last} in active context.")

    return trimmed


# --- STRATEGY 3: SCRATCHPAD ---
# Agent maintains an explicit short-term memory dict.
# This is injected into every prompt so Claude always knows current state
# without relying on long conversation history.

def build_scratchpad(notes, aspects, company):
    researched = list(notes.keys())
    pending = f"Still researching — waiting for more competitors" if not researched else ""

    scratchpad = {
        "company_being_researched": company,
        "aspects_required": aspects,
        "competitors_researched": researched,
        "competitors_count": len(researched),
        "status": "in_progress" if len(researched) < 3 else "nearing_completion"
    }
    return json.dumps(scratchpad, indent=2)


# =============================================================================
# BUILD WORD DOC WITH TABLES
# =============================================================================

def add_competitor_table(doc, competitor_name, competitor_type, aspects_data):
    doc.add_heading(competitor_name, level=2)

    p = doc.add_paragraph()
    p.add_run("Type: ").bold = True
    p.add_run(competitor_type)
    doc.add_paragraph("")

    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"

    header = table.rows[0].cells
    header[0].text = "Aspect"
    header[1].text = "Details"
    for cell in header:
        for para in cell.paragraphs:
            for run in para.runs:
                run.bold = True

    for aspect, details in aspects_data.items():
        row = table.add_row().cells
        row[0].text = aspect.replace("_", " ").title()
        row[1].text = details

    doc.add_paragraph("")


def add_landscape_table(doc, notes, aspects, company):
    doc.add_heading("Competitive Landscape Overview", level=1)
    doc.add_paragraph(f"Summary comparison of all key competitors to {company}.")
    doc.add_paragraph("")

    col_headers = ["Competitor", "Type"] + [a.replace("_", " ").title() for a in aspects]

    table = doc.add_table(rows=1, cols=len(col_headers))
    table.style = "Light Grid Accent 1"

    header = table.rows[0].cells
    for i, h in enumerate(col_headers):
        header[i].text = h
        for para in header[i].paragraphs:
            for run in para.runs:
                run.bold = True

    for name, data in notes.items():
        row = table.add_row().cells
        row[0].text = name
        row[1].text = data.get("type", "")
        for i, aspect in enumerate(aspects):
            aspect_value = ""
            for key, value in data.get("aspects", {}).items():
                if aspect.lower() in key.lower() or key.lower() in aspect.lower():
                    aspect_value = value[:200] + "..." if len(value) > 200 else value
                    break
            row[2 + i].text = aspect_value

    doc.add_paragraph("")


def show_research_summary_and_confirm(notes, aspects):
    print(f"\n{'='*60}")
    print(f"  [APPROVAL GATE 2] Research complete. Here's what was found:\n")
    for name, data in notes.items():
        print(f"  {name}")
        print(f"  Type: {data.get('type', '')}")
        for aspect, value in data.get("aspects", {}).items():
            short = value.split(".")[0][:120]
            print(f"    • {aspect}: {short}")
        print()
    print(f"{'='*60}")
    decision = input("\n  Generate Word document? (yes/no): ").strip().lower()
    return decision in ("yes", "y")


def save_report(notes, company, aspects):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{company.replace(' ', '_')}_{timestamp}.docx"

    doc = Document()

    doc.add_heading(f"Competitor Research: {company}", 0)
    doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"Research aspects: {', '.join(aspects)}")
    doc.add_paragraph("")

    add_landscape_table(doc, notes, aspects, company)

    doc.add_page_break()
    doc.add_heading("Detailed Competitor Profiles", level=1)

    for name, data in notes.items():
        add_competitor_table(
            doc,
            name,
            data.get("type", ""),
            data.get("aspects", {})
        )

    doc.save(filename)
    print(f"\n  [report] Saved to {filename}")
    return filename


# --- USER INPUT ---

def get_user_inputs():
    print("\n=== COMPETITOR RESEARCH AGENT ===\n")

    company = input("Enter the company to research competitors for: ").strip()
    if not company:
        print("No company entered. Exiting.")
        sys.exit(1)

    default_aspects = [
        "Key Features & Offerings",
        "Target Audience",
        "Fee / Pricing Structure",
        f"Key Differentiator vs {company}"
    ]

    add_aspects = input("\nWould you like to add custom research aspects? (e.g. 'Brand trust', 'International strategy') — type 'yes' or press Enter to skip: ").strip().lower()

    extra_aspects = []
    if add_aspects == "yes":
        print("Enter up to 5 aspects (press Enter on any to stop):\n")
        for i in range(1, 6):
            aspect = input(f"  Aspect {i}: ").strip()
            if not aspect:
                break
            extra_aspects.append(aspect)

    aspects = default_aspects + extra_aspects
    print(f"\nResearch aspects: {aspects}")

    return company, aspects


# --- AGENTIC LOOP ---

def run_agent(company, aspects, max_iterations=30, quality_threshold=95,
              summarize_every=3, keep_tool_results=3):
    notes = {}
    last_note_count = 0
    aspects_str = "\n".join(f"- {a}" for a in aspects)
    goal = f"Identify the key competitors to {company} and research each one covering these aspects:\n{aspects_str}"

    print(f"\nGoal: {goal}")
    print(f"Max iterations: {max_iterations} | Quality threshold: {quality_threshold}")
    print(f"Context: summarize every {summarize_every} iterations | keep last {keep_tool_results} tool results\n")

    messages = [{"role": "user", "content": goal}]
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} of {max_iterations} ---")

        # STRATEGY 1: Summarize every N iterations
        if iteration > 1 and iteration % summarize_every == 0:
            messages = summarize_history(messages, company, notes)

        # STRATEGY 2: Trim old tool results, keep only last N
        messages = trim_tool_results(messages, keep_last=keep_tool_results)

        # Quality check when new note saved
        if len(notes) > last_note_count:
            last_note_count = len(notes)
            quality = check_quality(notes, aspects)
            print(f"\n  [quality check] Notes saved: {len(notes)} competitors | Score: {quality}/100")
            if quality >= quality_threshold:
                print(f"  [quality check] Quality threshold reached! Stopping and writing report.")
                messages.append({
                    "role": "user",
                    "content": f"Quality threshold of {quality_threshold} reached. Stop researching. Output a brief final summary and stop."
                })

        # STRATEGY 3: Inject scratchpad into every Claude call
        scratchpad = build_scratchpad(notes, aspects, company)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=f"""You are a market research agent.

Your goal is to identify and research the key competitors to {company}.

CURRENT STATE (scratchpad — always read this first):
{scratchpad}

RESEARCH PROCESS — FOLLOW EXACTLY IN ORDER:
1. Do ONE broad search to identify the key competitors to {company}
2. Call propose_competitor_list with the competitors you found — WAIT for user approval before proceeding
3. For each approved competitor: search for it, read ONE page, then immediately save a note using save_note
4. Repeat until all approved competitors are researched and saved
5. Output a brief final summary and stop

CRITICAL RULES:
- You MUST call propose_competitor_list after step 1 before researching any individual competitor
- SAVE A NOTE after every single competitor before moving to the next one
- Do NOT read more than 1 page per competitor
- Maximum {max_iterations} iterations total
- When saving notes, populate aspects_data with ALL of these as keys:
{aspects_str}
- Make each aspect value detailed and specific — these go directly into a table in the report""",
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            print(f"\n=== AGENT FINISHED in {iteration} iterations ===")
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n{block.text}")
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input, notes)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })

            messages.append({"role": "user", "content": tool_results})

    if iteration >= max_iterations:
        print(f"\n=== AGENT STOPPED: hit max {max_iterations} iterations ===")

    if notes:
        if show_research_summary_and_confirm(notes, aspects):
            save_report(notes, company, aspects)
        else:
            print("\n  [gate 2] Word document skipped. Research notes are preserved in memory.")

    return notes


# --- MAIN ---

if __name__ == "__main__":
    company, aspects = get_user_inputs()
    run_agent(company, aspects)
