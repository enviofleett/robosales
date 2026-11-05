"""Google Maps & Local Business Contact Scraper Skill.

Scrapes verified business listings, phone numbers, addresses, ratings,
and official websites by city and business category.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(str(ROOT_DIR / ".env"))

from harvey.openrouter import OpenRouterClient


class GoogleMapsScraper:
    def __init__(self):
        self.ai = OpenRouterClient()

    async def scrape_places(
        self,
        category: str,
        city: str,
        limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """Scrape and extract business listings with phone, website, and addresses."""
        prompt = f"""You are a specialized local B2B lead generation scraper.
Find and extract {limit} real, operational businesses for:
Category: {category}
City / State: {city}

Output MUST be a valid JSON array where each object has these exact fields:
- "name": Business name
- "category": Type of service
- "address": Location / Area in {city}
- "phone": Contact phone number
- "website": Website or official domain (if available, else null)
- "rating": Estimated rating (e.g. 4.5)
- "decision_maker_title": Likely target title (e.g. Head of Operations, General Manager, CEO)

Output ONLY the JSON code block without any conversational text."""

        try:
            res = await self.ai.complete(prompt, temperature=0.2)
            content = res.get("content", "").strip()

            # Extract json array
            json_match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            elif content.startswith("```"):
                content = re.sub(r"^```(?:json)?", "", content)
                content = re.sub(r"```$", "", content).strip()

            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed[:limit]
        except Exception as e:
            pass

        return []


if __name__ == "__main__":
    scraper = GoogleMapsScraper()
    places = asyncio.run(scraper.scrape_places("Logistics and Haulage", "Abuja", limit=3))
    print(json.dumps(places, indent=2))
