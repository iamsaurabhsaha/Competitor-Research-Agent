import anthropic
import os
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- METHOD 1: JSON Mode ---
# Tell Claude in the system prompt to always respond in JSON
# Then parse it with json.loads()

def screen_job(job_description):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""You are a job screener for a senior Product Manager named Saurabh.

His profile:
- 10+ years PM experience in ecommerce and retail
- Strong data and analytics background
- Experience with AI/ML products
- Looking for Sr PM roles, $150K+ salary

You must respond ONLY in valid JSON with exactly these fields:
{
  "score": <number 1-10>,
  "fit": <"strong" | "moderate" | "weak">,
  "reason": <one sentence why>,
  "apply": <true | false>,
  "missing": <what skills or experience he lacks, or "none">
}

No other text. JSON only.""",
        messages=[
            {"role": "user", "content": f"Screen this job:\n\n{job_description}"}
        ]
    )

    raw = response.content[0].text

    # Strip code block markers if Claude added them
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    # Parse the JSON response
    result = json.loads(raw)
    return result


# --- METHOD 2: Validate the output ---
# Make sure every field is there before using it

def safe_screen_job(job_description):
    result = screen_job(job_description)

    # Validate required fields exist
    required_fields = ["score", "fit", "reason", "apply", "missing"]
    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing field in Claude response: {field}")

    # Validate types
    if not isinstance(result["score"], int):
        raise ValueError("Score must be an integer")
    if result["fit"] not in ["strong", "moderate", "weak"]:
        raise ValueError("Fit must be strong, moderate, or weak")

    return result


# --- TEST IT on 3 different jobs ---

jobs = [
    """
    Senior Product Manager - AI/ML Platform
    Company: Google, Seattle WA
    Salary: $180,000 - $220,000
    Requirements: 7+ years PM experience, experience with ML products,
    strong data analysis skills, experience with large scale platforms.
    """,
    """
    Junior Product Manager - Mobile Apps
    Company: Small Startup, Remote
    Salary: $80,000 - $95,000
    Requirements: 1-2 years PM experience, mobile app experience preferred,
    passion for technology.
    """,
    """
    Senior Product Manager - Ecommerce
    Company: eBay, San Jose CA
    Salary: $160,000 - $190,000
    Requirements: 5+ years PM experience in ecommerce, experience with
    seller/buyer platforms, data-driven decision making, cross-functional leadership.
    """
]

print("=== JOB SCREENER RESULTS ===\n")

for i, job in enumerate(jobs, 1):
    print(f"Job {i}:")
    print(job.strip())
    result = safe_screen_job(job)
    print(f"Score: {result['score']}/10")
    print(f"Fit: {result['fit'].upper()}")
    print(f"Reason: {result['reason']}")
    print(f"Apply: {'YES' if result['apply'] else 'NO'}")
    print(f"Missing: {result['missing']}")
    print("-" * 50 + "\n")
