import pandas as pd
from openai import OpenAI
import json
from tqdm import tqdm
import re

import os
os.environ["OPENAI_API_KEY"] = "<OPENAI_API_KEY>"

# Initialize OpenAI client
client = OpenAI()

# Load transcripts CSV
df = pd.read_csv("data/transcripts.csv")

def process_transcript(transcript_id, customer_id, call_date, transcript):
    prompt = f"""
You are given a customer call transcript from Home Depot call center.

The customer will make one or more request. Your job is to identify distict customer requests and corresponding policies applied to their requests.

Transcript:
\"\"\"
{transcript}
\"\"\"

1. Summarize the entire transcript comprehensively.
2. Identify distinct policies headings (such as promotions, delivery, payment, etc) that appear in the transcript.
3. With each policy heading, identify the policy detail based on customer request.
4. Remove any customer identifiable information.
5. Please highlight any related action in lieu to the policy.
6. Generate Two additional questions that are similar to original user request for the same policy (Do no paraphrase, Generate a unique question, that would apply to the same policy)

Output strictly as a JSON array where each entry has:
- customer_id
- call_date
- transcript_id
- summary
- policy_applied
- policy_details
- action_taken
- user_request_1
- user_request_2
- user_request_3

If there are more than one user request, output as separate JSON within list.

Return ONLY the JSON array, no markdown formatting or code blocks. KEEP JSON FLAT
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that extracts structured JSON from transcripts. Return only valid JSON without any markdown formatting."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3
    )

    json_text = response.choices[0].message.content
    
    # Clean up the response - remove markdown code blocks if present
    json_text = re.sub(r'^```json\s*', '', json_text.strip())
    json_text = re.sub(r'\s*```$', '', json_text.strip())
    
    try:
        data = json.loads(json_text)
    except Exception as e:
        print("Failed to parse JSON:", e)
        print("Raw output:", json_text)
        data = []
    
    for entry in data:
        entry["transcript_id"] = transcript_id
        entry["customer_id"] = customer_id
        entry["call_date"] = call_date
    return data

all_entries = []
for _, row in tqdm(df.iterrows(), total=len(df)):
    entries = process_transcript(row["transcript_id"], row["customer_id"], row["call_date"], row["transcript"])
    all_entries.extend(entries)

# Save to JSON file
with open("data/transcripts_policies.json", "w") as f:
    json.dump(all_entries, f, indent=2)
