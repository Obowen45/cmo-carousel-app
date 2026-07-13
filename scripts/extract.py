import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SCHEMA = {
    "type": "object",
    "properties": {
        "is_relevant": {
            "type": "boolean",
            "description": (
                "True only if this article reports a NEW senior marketing "
                "leadership appointment (CMO, Chief Marketing Officer, "
                "Marketing Director, VP Marketing) at a company in FMCG, "
                "Financial Services, Tech, or Telecoms, in the UK or Europe."
            ),
        },
        "person_name": {"type": ["string", "null"]},
        "new_title": {"type": ["string", "null"]},
        "old_company": {"type": ["string", "null"]},
        "new_company": {"type": ["string", "null"]},
        "start_date": {
            "type": ["string", "null"],
            "description": "ISO date YYYY-MM-DD if explicitly stated or clearly inferable, else null.",
        },
        "sector_guess": {
            "type": "string",
            "enum": ["FMCG", "Financial Services", "Tech", "Telecoms", "Other"],
        },
        "country_guess": {"type": ["string", "null"]},
    },
    "required": ["is_relevant", "sector_guess"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You extract structured facts about executive marketing appointments from "
    "short news snippets for a marketing agency's new-business research team. "
    "Be conservative: if the snippet doesn't clearly describe a new appointment, "
    "set is_relevant to false rather than guessing."
)


def extract(article_title: str, article_summary: str) -> dict:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": f"Headline: {article_title}\n\nSnippet: {article_summary}",
            }
        ],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


if __name__ == "__main__":
    test_cases = [
        ("Unilever names new Chief Marketing Officer", "Unilever has appointed Jane Smith as its new Chief Marketing Officer, joining from Procter & Gamble where she was VP of Marketing. She takes up the role in January."),
        ("J Brrothers appoints Vishal N Sharma as India Head", "Consumer goods firm J Brrothers has appointed Vishal N Sharma as its new India Head, overseeing sales operations across the region."),
        ("WHOOP Appoints Former Nike Marketing Chief As Member Base Passes Three Million", "Fitness tech company WHOOP has named a former Nike marketing executive as its new CMO as the company's user base grows."),
    ]
    for title, summary in test_cases:
        result = extract(title, summary)
        print(f"\nHeadline: {title}")
        print(json.dumps(result, indent=2))
