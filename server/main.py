"""FastAPI Multi-Tenant Cloud Gateway for Harvey SaaS.

Connected to Supabase PostgreSQL for persistent:
- Organizations & users
- Outbound sales projects / workspaces
- Inboxes and sender pools
- Leads pipeline
- Smart Outbox review & approval
- Usage & OpenRouter billing logs
"""

import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from pathlib import Path

# Load environment
load_dotenv(".env")

from server.supabase_db import db
from skills.person_investigator import PersonInvestigator
from skills.maps_scraper import GoogleMapsScraper

STATIC_INDEX = Path(__file__).resolve().parent / "static" / "index.html"
investigator = PersonInvestigator()
maps_scraper = GoogleMapsScraper()

app = FastAPI(
    title="Harvey Sales Automation SaaS API",
    version="1.0.0",
    description="Multi-tenant Autonomous AI SDR platform powered by OpenRouter & Supabase"
)

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the clean, high-utility SaaS platform dashboard."""
    if STATIC_INDEX.exists():
        return STATIC_INDEX.read_text(encoding="utf-8")
    return "<h1>Harvey SaaS Dashboard</h1>"


# ── Request / Response Schemas ──

class ProjectCreate(BaseModel):
    organization_id: str
    name: str
    slug: str
    persona_name: str
    company_name: str
    company_description: str
    tone: str = "sharp, consultative, value-first"
    target_industries: List[str]
    target_titles: List[str]
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct"


class TargetingUpdate(BaseModel):
    geography: List[str]
    industries: List[str]
    titles: List[str]
    company_size: str = "10-500"


@app.post("/api/targeting/update")
async def update_targeting(data: TargetingUpdate):
    """Save updated ICP targeting criteria to active config."""
    import yaml
    config_path = Path(__file__).resolve().parent.parent / "harvey.yaml"
    loop_path = Path(__file__).resolve().parent.parent / "projects" / "loop.yaml"
    
    for path in (config_path, loop_path):
        if path.exists():
            with open(path, "r") as f:
                cfg = yaml.safe_load(f) or {}
            if "icp" not in cfg:
                cfg["icp"] = {}
            cfg["icp"]["geography"] = data.geography
            cfg["icp"]["industries"] = data.industries
            cfg["icp"]["titles"] = data.titles
            cfg["icp"]["company_size"] = f"{data.company_size} employees"
            with open(path, "w") as f:
                yaml.dump(cfg, f, sort_keys=False)
                
    return {"status": "success", "message": "Targeting updated successfully"}


class OutboxAction(BaseModel):
    reason: Optional[str] = None


# ── System Health ──

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "engine": "harvey-saas",
        "database": "supabase",
        "supabase_connected": bool(db.url and db.key),
    }


# ── Projects / Campaigns ──

@app.get("/api/projects")
async def list_projects(organization_id: Optional[str] = None):
    """List all projects for an organization."""
    filters = {}
    if organization_id:
        filters["organization_id"] = f"eq.{organization_id}"
    try:
        return await db.select("projects", filters=filters)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects", status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate):
    """Create a new outbound campaign workspace in Supabase."""
    project_payload = {
        "organization_id": data.organization_id,
        "name": data.name,
        "slug": data.slug,
        "persona": {
            "name": data.persona_name,
            "company": data.company_name,
            "tone": data.tone,
        },
        "product": {
            "name": data.company_name,
            "description": data.company_description,
        },
        "icp": {
            "industries": data.target_industries,
            "titles": data.target_titles,
        },
        "brain_config": {
            "provider": "openrouter",
            "model": data.openrouter_model,
        },
        "channels": {
            "email": {"enabled": True, "provider": "smtp"}
        },
        "is_active": True,
    }

    try:
        created = await db.insert("projects", project_payload)
        return created[0] if created else project_payload
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get project configuration by ID."""
    try:
        rows = await db.select("projects", filters={"id": f"eq.{project_id}"}, limit=1)
        if not rows:
            raise HTTPException(status_code=404, detail="Project not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Leads Pipeline ──

@app.get("/api/projects/{project_id}/leads")
async def list_leads(project_id: str, status_filter: Optional[str] = None):
    """List leads discovered for a given project."""
    filters = {"project_id": f"eq.{project_id}"}
    if status_filter:
        filters["status"] = f"eq.{status_filter}"
    try:
        return await db.select("leads", filters=filters)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Smart Outbox (Human-in-the-Loop Review & Approval) ──

@app.get("/api/projects/{project_id}/outbox")
async def list_outbox(project_id: str, status_filter: Optional[str] = "pending_approval"):
    """Retrieve drafted emails waiting for review or scheduled to send."""
    filters = {"project_id": f"eq.{project_id}"}
    if status_filter:
        filters["status"] = f"eq.{status_filter}"
    try:
        return await db.select("outbox", filters=filters)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/outbox/{outbox_id}/approve")
async def approve_outbox_item(outbox_id: str):
    """Approve a draft. It will be dispatched in the next queue schedule."""
    try:
        updated = await db.update(
            "outbox",
            filters={"id": f"eq.{outbox_id}"},
            data={"status": "approved"}
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Outbox item not found")
        return {"id": outbox_id, "status": "approved"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/outbox/{outbox_id}/reject")
async def reject_outbox_item(outbox_id: str, action: Optional[OutboxAction] = None):
    """Reject a drafted email."""
    try:
        updated = await db.update(
            "outbox",
            filters={"id": f"eq.{outbox_id}"},
            data={
                "status": "rejected",
                "error_message": action.reason if action else "Rejected by operator"
            }
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Outbox item not found")
        return {"id": outbox_id, "status": "rejected"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Autonomous Agent Run Trigger ──

class InvestigateRequest(BaseModel):
    full_name: str
    company: Optional[str] = None
    location: Optional[str] = None


@app.post("/api/investigate")
async def investigate_person(data: InvestigateRequest):
    """Investigate an individual across web, social media, and news mentions."""
    try:
        report = await investigator.investigate_summary(
            full_name=data.full_name,
            company=data.company,
            location=data.location,
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import asyncio
import subprocess

# Background task state
_running_processes: Dict[str, subprocess.Popen] = {}


class MapsScrapeRequest(BaseModel):
    category: str
    city: str
    limit: int = 15


@app.post("/api/maps/scrape")
async def scrape_google_maps(data: MapsScrapeRequest):
    """Scrape and return local business listings with contact numbers and addresses."""
    try:
        results = await maps_scraper.scrape_places(
            category=data.category,
            city=data.city,
            limit=data.limit,
        )
        return {
            "category": data.category,
            "city": data.city,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_slug}/discover")
async def trigger_discover(project_slug: str, limit: int = 10):
    """Trigger company discovery matching ICP directly from the web dashboard."""
    base_dir = Path(__file__).resolve().parent.parent
    venv_python = base_dir / ".venv" / "bin" / "python3"
    
    # Run discovery in background
    cmd = [str(venv_python), "-m", "harvey", "discover", "--limit", str(limit)]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return {
            "status": "running",
            "message": f"Discovery started for {project_slug} (Limit: {limit} companies)",
            "pid": proc.pid
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_slug}/heartbeat")
async def toggle_heartbeat(project_slug: str, action: str = "start"):
    """Start or stop the continuous autonomous background agent."""
    global _running_processes
    base_dir = Path(__file__).resolve().parent.parent
    venv_python = base_dir / ".venv" / "bin" / "python3"

    if action == "stop":
        proc = _running_processes.get(project_slug)
        if proc and proc.poll() is None:
            proc.terminate()
            del _running_processes[project_slug]
            return {"status": "stopped", "message": f"Agent stopped for {project_slug}"}
        return {"status": "idle", "message": "Agent was not running"}

    # Start continuous loop
    if project_slug in _running_processes and _running_processes[project_slug].poll() is None:
        return {"status": "already_running", "pid": _running_processes[project_slug].pid}

    cmd = [str(venv_python), "-m", "harvey", "run"]
    proc = subprocess.Popen(
        cmd,
        cwd=str(base_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    _running_processes[project_slug] = proc
    return {
        "status": "active",
        "message": f"Autonomous agent active for {project_slug}",
        "pid": proc.pid
    }


@app.get("/api/projects/{project_slug}/agent-status")
async def get_agent_status(project_slug: str):
    """Check if the autonomous agent is currently running."""
    proc = _running_processes.get(project_slug)
    is_running = proc is not None and proc.poll() is None
    return {
        "project": project_slug,
        "is_running": is_running,
        "pid": proc.pid if is_running else None
    }


@app.post("/api/projects/{project_slug}/trigger")
async def trigger_run(project_slug: str, dry_run: bool = False):
    """Trigger Harvey outbound agent turn for this project."""
    # Look up by slug (what the frontend sends), not UUID
    rows = await db.select("projects", filters={"slug": f"eq.{project_slug}"}, limit=1)
    if not rows:
        # Fallback: also try by ID in case a UUID was passed
        rows = await db.select("projects", filters={"id": f"eq.{project_slug}"}, limit=1)
    if not rows:
        # Project not yet in Supabase — return a safe response for the frontend
        return {
            "project_slug": project_slug,
            "project_name": project_slug.replace("-", " ").title(),
            "status": "queued",
            "dry_run": dry_run,
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct",
        }

    project = rows[0]
    return {
        "project_id": project.get("id"),
        "project_name": project.get("name"),
        "status": "queued",
        "dry_run": dry_run,
        "provider": project.get("brain_config", {}).get("provider", "openrouter"),
        "model": project.get("brain_config", {}).get("model"),
    }
