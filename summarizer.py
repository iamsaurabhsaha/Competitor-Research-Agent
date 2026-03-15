import anthropic
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def summarize_file(input_path, output_path):
    # Read the input file
    with open(input_path, 'r') as f:
        content = f.read()

    print(f"Summarizing {input_path}...")

    # Send to Claude with a system prompt and the file content
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="You are a concise summarizer. Always respond with a summary in 3-5 bullet points.",
        messages=[
            {"role": "user", "content": f"Summarize this:\n\n{content}"}
        ]
    )

    summary = message.content[0].text

    # Log token usage
    print(f"  Tokens used — input: {message.usage.input_tokens}, output: {message.usage.output_tokens}")

    # Write the summary to output file
    with open(output_path, 'w') as f:
        f.write(summary)

    print(f"  Summary saved to {output_path}")
    print(f"\n--- SUMMARY: {os.path.basename(input_path)} ---")
    print(summary)
    print()

def summarize_folder(input_folder, output_folder):
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Get all .txt files in the input folder
    files = [f for f in os.listdir(input_folder) if f.endswith('.txt')]

    print(f"Found {len(files)} files to summarize.\n")

    total_input_tokens = 0
    total_output_tokens = 0

    for filename in files:
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, f"summary_{filename}")
        summarize_file(input_path, output_path)

    print(f"\nDone! All summaries saved to {output_folder}")

# Run it
summarize_folder("texts", "summaries")
