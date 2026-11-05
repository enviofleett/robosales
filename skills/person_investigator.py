"""Hybrid Person & Social Intelligence Investigator Skill.

Combines web intelligence and OpenRouter LLM profiling to generate
deep executive intelligence, role hypotheses, and social research leads.
"""

import asyncio
from typing import Any, Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv(".env")

from harvey.openrouter import OpenRouterClient


class PersonInvestigator:
    def __init__(self):
        self.ai = OpenRouterClient()

    async def investigate_summary(
        self,
        full_name: str,
        company: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Produce an AI-powered intelligence dossier and direct search pathways."""
        name_clean = full_name.strip()
        comp_clean = (company or "").strip()
        loc_clean = (location or "").strip()

        # Build direct deep-link search targets for the operator
        encoded_query = f"{name_clean} {comp_clean} {loc_clean}".strip().replace(" ", "+")
        linkedin_query = f"site:linkedin.com/in/+{name_clean}+{comp_clean}".strip().replace(" ", "+")
        twitter_query = f"{name_clean}+{comp_clean}".strip().replace(" ", "+")

        social_links = {
            "linkedin_search": f"https://www.google.com/search?q={linkedin_query}",
            "google_search": f"https://www.google.com/search?q={encoded_query}",
            "twitter_search": f"https://x.com/search?q={twitter_query}&f=user",
        }

        # Query OpenRouter for executive background & hypothesis profiling
        ai_prompt = f"""You are an elite OSINT sales researcher. Generate a professional profile briefing for sales outreach.
Target Executive: {name_clean}
Company: {comp_clean or 'Not specified'}
Location: {loc_clean or 'Not specified'}

Provide a structured, high-value dossier:
1. Executive Role & Seniority Hypothesis: What roles this individual likely holds given the company and industry.
2. Industry & Operational Context: The specific operational pressures, regulations, or scaling challenges they deal with in their day-to-day work.
3. Cold Outreach Angle & Personalized Icebreaker: A conversational hook for cold email outreach from a partner company.
4. Key Intelligence Channels: Exactly where this person's public record can be verified (e.g. CAC registration, Nigerian logistics boards, specific LinkedIn clusters).

Keep it professional, concise, and formatted in clean markdown bullet points."""

        try:
            ai_res = await self.ai.complete(ai_prompt, temperature=0.5)
            briefing = ai_res.get("content", "")
        except Exception as e:
            briefing = f"Could not generate AI briefing: {e}"

        return {
            "target": {
                "name": full_name,
                "company": company,
                "location": location,
            },
            "social_profiles": social_links,
            "ai_briefing": briefing,
            "direct_search_links": social_links,
        }
