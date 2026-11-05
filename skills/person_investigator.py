"""Person & Social Intelligence Investigator Skill.

Combines DuckDuckGo search and OSINT tools to research a target individual
by full name, company, and likely usernames across LinkedIn, Twitter/X, GitHub,
company websites, press releases, and articles.
"""

import asyncio
from typing import Any, Dict, List, Optional
from duckduckgo_search import DDGS


class PersonInvestigator:
    def __init__(self):
        self.ddgs = DDGS()

    def search_person(
        self,
        full_name: str,
        company: Optional[str] = None,
        location: Optional[str] = None,
        max_results: int = 8,
    ) -> List[Dict[str, str]]:
        """Perform targeted Google/DDG searches to discover professional social profiles,
        interviews, articles, and company mentions.
        """
        queries = []
        name_clean = full_name.strip()
        comp_clean = (company or "").strip()
        loc_clean = (location or "").strip()

        # 1. Broad professional presence
        base_query = f'"{name_clean}"'
        if comp_clean:
            base_query += f' "{comp_clean}"'
        if loc_clean:
            base_query += f' "{loc_clean}"'

        queries.append(base_query)
        # 2. LinkedIn targeted
        queries.append(f'site:linkedin.com/in/ "{name_clean}" {comp_clean}'.strip())
        # 3. Twitter/X targeted
        queries.append(f'site:twitter.com OR site:x.com "{name_clean}" {comp_clean}'.strip())
        # 4. News / interviews / articles
        queries.append(f'"{name_clean}" {comp_clean} interview OR speaker OR podcast OR article'.strip())

        seen_urls = set()
        findings = []

        for q in queries:
            try:
                results = self.ddgs.text(q, max_results=max_results)
                for r in results:
                    url = r.get("href", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        findings.append({
                            "title": r.get("title", ""),
                            "snippet": r.get("body", ""),
                            "url": url,
                            "query": q,
                        })
            except Exception as e:
                continue

        return findings

    async def investigate_summary(
        self,
        full_name: str,
        company: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate discovery and produce a structured dossier."""
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, self.search_person, full_name, company, location
        )

        social_links = {
            "linkedin": None,
            "twitter": None,
            "github": None,
            "other": []
        }

        articles_and_mentions = []

        for item in results:
            url = item["url"].lower()
            if "linkedin.com/in/" in url and not social_links["linkedin"]:
                social_links["linkedin"] = item["url"]
            elif ("twitter.com/" in url or "x.com/" in url) and not social_links["twitter"]:
                social_links["twitter"] = item["url"]
            elif "github.com/" in url and not social_links["github"]:
                social_links["github"] = item["url"]
            else:
                articles_and_mentions.append(item)

        return {
            "target": {
                "name": full_name,
                "company": company,
                "location": location,
            },
            "social_profiles": social_links,
            "total_web_matches": len(results),
            "web_mentions": articles_and_mentions[:10],
        }


if __name__ == "__main__":
    import json
    inv = PersonInvestigator()
    dossier = asyncio.run(inv.investigate_summary("Satya Nadella", "Microsoft"))
    print(json.dumps(dossier, indent=2))
