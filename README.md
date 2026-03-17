# Competitor Research Agent

### The Problem: Competitive Intelligence is Slow, Expensive, and Generic

Every product manager, founder, and strategist needs to understand their competitive landscape. But the current options are frustrating:

**The Manual Researcher:** You spend hours Googling, switching between tabs, reading articles, and copy-pasting notes into a doc. By the time you're done, you've lost half a day — and the output is inconsistent because you researched each competitor differently, on different days, with different depth.

**The Expensive SaaS Tool:** You pay for a competitive intelligence platform. It's slick, but it covers only the companies and metrics *they* decided matter. You can't ask it about brand trust, international expansion strategy, or any custom dimension that's specific to your context. And it's locked behind a $300/month subscription.

**The LLM Chat User:** You ask ChatGPT or Claude to "research my competitors." It gives you a confident-sounding answer based on training data — which may be months old, occasionally hallucinated, and missing the nuance that actually matters to your decision.

### Enter the Competitor Research Agent

This agent does what a good research analyst does: it goes to the live web, reads real pages, and takes structured notes on your specific questions. But unlike a fully autonomous agent, it pauses at two key moments — to let you approve the competitor list before research begins, and to show you a quality-scored summary before generating the report. If you're not satisfied, you can send it back to research more.

You stay in control. The agent does the work.

---

## What It Does

**1. You name the company. The agent identifies who the real competitors are.**
No pre-defined list needed. The agent searches the web, determines who the key players are in the competitive landscape, and decides how many are worth researching — on its own.

**2. You optionally define what angles matter to you.**
By default the agent covers features, target audience, pricing, and key differentiators. But you can layer on your own research angles — brand trust, sustainability positioning, international expansion, technology stack, customer support quality, or anything else specific to your situation.

**3. You approve the competitor list before research begins.**
After the initial search, the agent pauses and shows you the competitors it found. You can add any it missed, remove any that aren't relevant, then press Enter to proceed. Research only starts on the list you confirmed.

**4. It researches every approved competitor — no early stopping.**
The agent works through your approved list one competitor at a time: search → extract → save note. It never skips a competitor based on an internal quality score. If you approved 8, it researches all 8.

**5. It scores its own output after every save.**
A built-in quality checker makes a separate API call to score research completeness from 0–100 after each competitor is saved. The score is displayed as research progresses so you can see quality building in real time.

**6. You review before the report is generated.**
Before creating the Word document, the agent shows a clean summary of all findings with the final quality score. You choose what happens next:
- **yes** — generate the Word document
- **no** — exit without generating
- **[any feedback]** — send the agent back to research more (e.g. "go deeper on Stripe pricing"). It runs additional iterations beyond the original limit, then shows the summary again.

**7. It delivers a formatted Word document.**
The final output is a `.docx` file with:
- A **competitive landscape overview table** — all competitors across all aspects in one grid
- **Individual profile tables per competitor** — one row per aspect with detailed findings
- Ready to open in Word, Google Docs, or Pages

---

## How It Works

The agent uses the **ReAct pattern** — Reason, Act, Observe, Repeat:

```
You enter a company name (+ optional custom research aspects)
                    ↓
Agent searches: "Who are the key competitors to [company]?"
                    ↓
  ⏸  GATE 1 — You review the competitor list
     Add any missing, remove any irrelevant, press Enter to approve
                    ↓
          For each approved competitor:
          → Search for detailed information
          → Extract content from the most relevant page
          → Save a structured note immediately
          → Quality score updated (displayed, not used to stop)
                    ↓
     All approved competitors researched
                    ↓
  ⏸  GATE 2 — You review findings + quality score
     yes → generate Word doc
     no  → exit
     [feedback] → agent researches more, Gate 2 shows again
                    ↓
   Final report saved as a timestamped .docx file
```

**Four tools the agent uses:**

| Tool | What it does |
|---|---|
| `search_web` | DuckDuckGo search — returns titles, URLs, and snippets |
| `extract_page_content` | Reads and extracts text from a web page (prefers Wikipedia, official sites) |
| `propose_competitor_list` | Pauses the agent to show the identified competitor list for user approval (Gate 1) |
| `save_note` | Saves structured JSON findings per competitor — feeds directly into the Word doc tables |

The **quality checker** is a separate Claude API call that scores completeness 0–100 after each competitor is saved. The score is shown at Gate 2 alongside a warning if it falls below the threshold — giving you the information to decide whether to approve the report or request more research.

---

## Approval Gates

The agent pauses at two points to keep you in control of the research.

**Gate 1 — Competitor List Review**
After the initial search, the agent proposes the competitor list before doing any research. You can edit it interactively:

```
============================================================
  [APPROVAL GATE 1] Agent identified these competitors:

    1. Disney+
    2. HBO Max
    3. Apple TV+
    4. Amazon Prime Video
    5. Peacock

  Commands: press Enter to approve | 'add [name]' | 'remove [name]'
============================================================

  Your decision: add Paramount+
  Added: Paramount+

  Your decision:               ← press Enter to approve

  [gate 1] Approved. Proceeding to research all 6 competitors.
```

**Gate 2 — Research Review Before Report**
After all competitors are researched, the agent shows a clean summary with the quality score before generating any file:

```
============================================================
  [APPROVAL GATE 2] Research complete. Here's what was found:

  Disney+ — Subscription streaming service...
    • Key Features: Disney, Pixar, Marvel, Star Wars libraries...
    • Target Audience: Families, franchise fans...
    ...

  Quality score: 91/100  ⚠ Below threshold (95) — some aspects may be incomplete

  Options:
    yes        -> generate Word document
    no         -> exit without generating
    [feedback] -> request more research (e.g. 'go deeper on Hulu pricing')
============================================================

  Your decision: go deeper on Hulu pricing
  [gate 2] Resuming research (10 additional iterations)...
```

If you give feedback, the agent runs up to 10 additional iterations to address it, then Gate 2 appears again with an updated quality score. This repeats until you type `yes` or `no`.

---

## Context Window Management

Long research runs can accumulate thousands of tokens of conversation history. Without management, the agent would eventually hit Claude's context limit and fail mid-run. This agent uses **three strategies in parallel** to prevent that:

**Strategy 1 — Conversation Summarization**
Every 8 iterations, the full conversation history is compressed into a concise bullet-point summary by a separate Claude call. The summary replaces the raw history, keeping the active context small while preserving all meaningful progress.

**Strategy 2 — Selective Tool Result Archiving**
Tool results (web page content, search results) are the biggest contributors to context bloat. Only the **last 3 tool results** are kept in active memory. Older results are automatically archived to `context_archive.jsonl` on disk — not lost, just moved out of the active window.

**Strategy 3 — Scratchpad Injection**
Instead of relying on Claude to "remember" context from earlier in the conversation, the agent maintains an explicit scratchpad — a live JSON snapshot of the current research state (which competitors have been saved, which aspects are required, how many are done). This scratchpad is injected into every single Claude call so the agent always knows exactly where it is, regardless of how much history was trimmed.

| Strategy | What it solves | When it runs |
|---|---|---|
| Summarization | Conversation history growing too long | Every 8 iterations |
| Tool result archiving | Page content flooding the context | Every iteration |
| Scratchpad injection | Agent losing track of progress | Every iteration |

Together these let the agent run reliably for 40+ iterations without hitting context limits.

---

## Example Run

```
=== COMPETITOR RESEARCH AGENT ===

Enter the company to research competitors for: Netflix
Would you like to add custom research aspects? yes
  Aspect 1: Brand trust and perception
  Aspect 2: International content strategy
  Aspect 3: [Enter to stop]

Max iterations: 40 | Quality scoring: enabled (informational only)

--- Iteration 1 ---  [search_web] top competitors to Netflix streaming 2024

============================================================
  [APPROVAL GATE 1] Agent identified these competitors:

    1. Disney+
    2. HBO Max
    3. Apple TV+
    4. Amazon Prime Video
    5. Peacock

  Commands: press Enter to approve | 'add [name]' | 'remove [name]'
============================================================

  Your decision: add Paramount+
  Added: Paramount+
  Your decision:

  [gate 1] Approved. Proceeding to research all 6 competitors.

--- Iteration 3 ---   [search_web] Disney+ features pricing audience 2024
--- Iteration 4 ---   [extract_page] en.wikipedia.org/wiki/Disney+
--- Iteration 5 ---   [save_note] Disney+
  [quality check] Notes saved: 1 of 6 | Score: 18/100
--- Iteration 6 ---   [search_web] HBO Max features pricing audience 2024
...
--- Iteration 22 ---  [save_note] Paramount+
  [quality check] Notes saved: 6 of 6 | Score: 94/100
  [complete] All 6 approved competitors researched.

============================================================
  [APPROVAL GATE 2] Research complete. Here's what was found:

  Disney+ — Subscription streaming, Disney/Pixar/Marvel/Star Wars
    • Key Features: 4K HDR, offline downloads, GroupWatch...
    • Target Audience: Families, franchise fans, ages 6-45...
  ...

  Quality score: 94/100  Below threshold (95) — some aspects may be incomplete

  Options:
    yes        -> generate Word document
    no         -> exit without generating
    [feedback] -> request more research
============================================================

  Your decision: yes

=== AGENT FINISHED in 23 iterations ===
  [report] Saved to report_Netflix_20260316_143022.docx
```

---

## Output Format

Each competitor gets a structured table:

**Disney+**
*Type: Subscription video streaming service — Disney, Pixar, Marvel, Star Wars content*

| Aspect | Details |
|---|---|
| **Key Features & Offerings** | Disney, Pixar, Marvel, Star Wars, and National Geographic libraries; Disney+ Hotstar in Asia; GroupWatch for co-viewing; downloads for offline viewing; up to 4K HDR streaming |
| **Target Audience** | Families with children; Marvel and Star Wars fans; Disney nostalgia audience; ages 6–45 skewing younger than Netflix |
| **Fee / Pricing Structure** | Ad-supported: $7.99/mo; Ad-free: $13.99/mo; Bundle with Hulu + ESPN+: $24.99/mo |
| **Key Differentiator vs Netflix** | Exclusive ownership of Disney/Marvel/Star Wars IP — content Netflix can never license; stronger family and franchise positioning |
| **Brand Trust** | Extremely high — Disney brand carries 100 years of trust; family-safe reputation |
| **International Content Strategy** | Disney+ Hotstar dominates India and Southeast Asia; local language content investments growing |

Plus an overview table summarizing all competitors side by side.

---

## Setup

**Requirements:**
- Python 3.11+
- Anthropic API key — get one at `console.anthropic.com` (~$5 in credits covers 30–100 full research runs)

**Install dependencies:**
```bash
pip install anthropic python-dotenv requests beautifulsoup4 ddgs python-docx
```

**Add your API key:**
```bash
echo "ANTHROPIC_API_KEY=your-key-here" > .env
```

---

## Run It

```bash
python3 competitor_research_agent.py
```

You will be prompted for:

1. **Company name** — any company (`Netflix`, `Airbnb`, `Shopify`, `Notion`, `eBay`)
2. **Custom aspects** — optional; press Enter to skip and use defaults

That's it. The agent handles everything else.

**Output:** A timestamped `report_COMPANY_DATE.docx` saved in the same folder.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI reasoning | Anthropic Claude (claude-sonnet-4-6) via Messages API |
| AI coding assistant | Anthropic Claude (claude-sonnet-4-6) |
| Web search | DuckDuckGo via `ddgs` — no account or API key required |
| Page extraction | `requests` + `BeautifulSoup4` |
| Report generation | `python-docx` — formatted Word document |
| Config | `python-dotenv` — API key never hardcoded |

---

## Cost

Each full research run costs approximately **$0.05–$0.20** in Anthropic API credits depending on the number of competitors found and pages read. The quality checker adds a small number of additional calls per note saved.

At Anthropic's current pricing, **$5 in credits = 25–100 full research runs.**

---

## Privacy & Security

- Your Anthropic API key is stored in `.env` — gitignored, never committed
- Web searches use DuckDuckGo — no account, no tracking, no API key required
- No data is sent anywhere except Anthropic's API (for reasoning) and the public web pages being read
- The `.docx` report is saved locally on your machine — never uploaded anywhere
- Anthropic does receive the web page text extracted during research — review their data retention policy at `anthropic.com/privacy` if this is relevant to your use case

---

## Disclaimer

This software is provided as-is, without warranty of any kind. It is a research tool, not a professional intelligence service. Research quality depends on what is publicly available on the web at the time of the run. Web search results and page content can be incomplete, outdated, or occasionally inaccurate — always verify critical findings before making business decisions. Each user is responsible for their own Anthropic API usage and costs.