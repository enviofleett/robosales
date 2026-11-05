"""Supabase Database Client & ORM layer for Harvey SaaS.

Uses httpx for high-performance async communication with Supabase PostgREST & Auth.
"""

import os
from typing import Any, Dict, List, Optional
import httpx


class SupabaseClient:
    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
    ):
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.rest_url = f"{self.url}/rest/v1"

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def select(
        self,
        table: str,
        filters: Optional[Dict[str, str]] = None,
        select_cols: str = "*",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query rows from a table."""
        params: Dict[str, Any] = {
            "select": select_cols,
            "limit": limit,
        }
        if filters:
            for k, v in filters.items():
                params[k] = v

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(
                f"{self.rest_url}/{table}",
                headers=self.headers,
                params=params,
            )
            if res.status_code >= 400:
                raise RuntimeError(f"Supabase select failed: {res.text}")
            return res.json()

    async def insert(
        self,
        table: str,
        data: Dict[str, Any] | List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Insert one or multiple rows into a table."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{self.rest_url}/{table}",
                headers=self.headers,
                json=data,
            )
            if res.status_code >= 400:
                raise RuntimeError(f"Supabase insert failed: {res.text}")
            return res.json()

    async def update(
        self,
        table: str,
        filters: Dict[str, str],
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Update rows matching filters."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.patch(
                f"{self.rest_url}/{table}",
                headers=self.headers,
                params=filters,
                json=data,
            )
            if res.status_code >= 400:
                raise RuntimeError(f"Supabase update failed: {res.text}")
            return res.json()

    async def delete(
        self,
        table: str,
        filters: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Delete rows matching filters."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.delete(
                f"{self.rest_url}/{table}",
                headers=self.headers,
                params=filters,
            )
            if res.status_code >= 400:
                raise RuntimeError(f"Supabase delete failed: {res.text}")
            return res.json()


# Singleton instance
db = SupabaseClient()
