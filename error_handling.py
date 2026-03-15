import anthropic
import os
import json
import time
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# --- LOGGING SETUP ---
# This creates a log file that records every API call
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("api_calls.log"),  # saves to file
        logging.StreamHandler()                 # also prints to terminal
    ]
)
log = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# --- RETRY LOGIC ---
# If a call fails, wait and try again up to max_retries times

def call_claude_with_retry(system_prompt, user_message, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            log.info(f"API call attempt {attempt} of {max_retries}")
            start_time = time.time()

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )

            latency = round(time.time() - start_time, 2)
            log.info(f"Success | Latency: {latency}s | Input tokens: {response.usage.input_tokens} | Output tokens: {response.usage.output_tokens}")

            return response.content[0].text

        except anthropic.RateLimitError:
            wait_time = 2 ** attempt  # exponential backoff: 2s, 4s, 8s
            log.warning(f"Rate limit hit. Waiting {wait_time}s before retry...")
            time.sleep(wait_time)

        except anthropic.APIError as e:
            log.error(f"API error on attempt {attempt}: {e}")
            if attempt == max_retries:
                raise

    raise Exception("All retries failed")


# --- OUTPUT VALIDATION WITH RETRY ---
# If Claude returns bad JSON, ask it to fix it

def get_valid_json(system_prompt, user_message, max_retries=3):
    raw = call_claude_with_retry(system_prompt, user_message)

    for attempt in range(1, max_retries + 1):
        try:
            # Strip code block markers if present
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            result = json.loads(cleaned)
            log.info("JSON parsed successfully")
            return result

        except json.JSONDecodeError:
            log.warning(f"Invalid JSON on attempt {attempt}. Asking Claude to fix it...")
            # Ask Claude to correct its own output
            raw = call_claude_with_retry(
                system_prompt,
                f"Your previous response was not valid JSON. Please return ONLY valid JSON, no other text.\n\nYour previous response was:\n{raw}"
            )

    raise ValueError("Could not get valid JSON after retries")


# --- TEST IT ---

system_prompt = """You are a job screener for a senior Product Manager named Saurabh.
His profile: 10+ years PM experience, ecommerce, AI/ML products, $150K+ salary target.
Respond ONLY in valid JSON with fields: score (1-10), fit (strong/moderate/weak), reason, apply (true/false)."""

job = """
Senior Product Manager - Growth
Company: Amazon, Seattle WA
Salary: $170,000 - $200,000
Requirements: 6+ years PM experience, growth metrics, experimentation, data-driven.
"""

print("Testing error handling and retry logic...\n")

result = get_valid_json(system_prompt, job)

print("\n=== RESULT ===")
print(f"Score: {result['score']}/10")
print(f"Fit: {result['fit'].upper()}")
print(f"Reason: {result['reason']}")
print(f"Apply: {'YES' if result['apply'] else 'NO'}")
print("\nCheck api_calls.log to see the full log of what happened.")
