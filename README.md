# Competitor Research Agent

### The Problem: Competitive Intelligence is Slow, Expensive, and Generic

Every product manager, founder, and strategist needs to understand their competitive landscape. But the current options are frustrating:

**The Manual Researcher:** You spend hours Googling, switching between tabs, reading articles, and copy-pasting notes into a doc. By the time you're done, you've lost half a day — and the output is inconsistent because you researched each competitor differently, on different days, with different depth.

**The Expensive SaaS Tool:** You pay for a competitive intelligence platform. It's slick, but it covers only the companies and metrics *they* decided matter. You can't ask it about brand trust, international expansion strategy, or any custom dimension that's specific to your context. And it's locked behind a $300/month subscription.

**The LLM Chat User:** You ask ChatGPT or Claude to "research my competitors." It gives you a confident-sounding answer based on training data — which may be months old, occasionally hallucinated, and missing the nuance that actually matters to your decision.

### Enter the Competitor Research Agent

This agent does what a good research analyst does: it goes to the live web, reads real pages, takes structured notes on your specific questions, scores the quality of its own work, and stops only when the research is thorough enough. The output is a formatted Word document — ready to share with your team, drop into a deck, or use as a briefing doc.

You define what matters. The agent does the work.

---

## What It Does

**1. You name the company. The agent identifies who the real competitors are.**
No pre-defined list needed. The agent searches the web, determines who the key players are in the competitive landscape, and decides how many are worth researching — on its own.

**2. You optionally define what angles matter to you.**
By default the agent covers features, target audience, pricing, and key differentiators. But you can layer on your own research angles — brand trust, sustainability positioning, international expansion, technology stack, customer support quality, or anything else specific to your situation.

**3. It researches one competitor at a time, saving structured notes as it goes.**
After fully researching each competitor, it saves a structured note with every aspect covered. Partial results are never lost — even if the agent stops early, everything found so far is preserved and written to the report.

**4. It scores its own output after every save.**
A built-in quality checker makes a separate call to score research completeness from 0–100 after each competitor is saved. When the score hits 95 or above, the agent stops immediately — no wasted iterations, no over-researching.

**5. It delivers a formatted Word document.**
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
          For each competitor:
          → Search for detailed information
          → Extract content from the most relevant page
          → Save a structured note immediately
          → Quality check: is this research complete enough?
                    ↓
   Quality score ≥ 95 → stop early, write report
   Quality score < 95 → continue to next competitor
                    ↓
   Final report saved as a timestamped .docx file
```

**Three tools the agent uses:**

| Tool | What it does |
|---|---|
| `search_web` | DuckDuckGo search — returns titles, URLs, and snippets |
| `extract_page_content` | Reads and extracts text from a web page (prefers Wikipedia, official sites) |
| `save_note` | Saves structured JSON findings per competitor — feeds directly into the Word doc tables |

The **quality checker** is a separate Claude API call that reviews all saved notes and scores completeness 0–100 proportionally across competitors and aspects. This prevents the agent from over-researching or stopping too early.

---

## Example Run

```
=== COMPETITOR RESEARCH AGENT ===

Enter the company to research competitors for: Netflix
Would you like to add custom research aspects? yes
  Aspect 1: Brand trust and perception
  Aspect 2: International content strategy
  Aspect 3: [Enter to stop]

Research aspects: Key Features & Offerings, Target Audience,
Fee / Pricing Structure, Key Differentiator vs Netflix,
Brand trust and perception, International content strategy

--- Iteration 1 ---  [search_web] top competitors to Netflix streaming 2024
--- Iteration 2 ---  [extract_page] Wikipedia: Disney+
--- Iteration 3 ---  [save_note] Disney+
  [quality check] Notes: 1 | Score: 17/100
--- Iteration 4 ---  [search_web] HBO Max features pricing audience
--- Iteration 5 ---  [extract_page] Wikipedia: Max (HBO)
--- Iteration 6 ---  [save_note] Max (HBO)
  [quality check] Notes: 2 | Score: 35/100
...
--- Iteration 19 ---  [save_note] Apple TV+
  [quality check] Notes: 5 | Score: 96/100
  [quality check] Quality threshold reached! Writing report.

=== AGENT FINISHED in 20 iterations ===
  [report] Saved to report_Netflix_20260315_143022.docx
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
python3 ebay_competitor_agent.py
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

---

*Built as part of a 5-phase AI builder learning roadmap — from Claude power user to multi-agent systems engineer.*
