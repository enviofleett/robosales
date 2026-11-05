#!/usr/bin/env python3
"""Multi-project launcher for Harvey.

Usage:
    python3 manage_projects.py list
    python3 manage_projects.py run --project <project_name>
    python3 manage_projects.py status --project <project_name>
    python3 manage_projects.py create --project <project_name>
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = BASE_DIR / "projects"
CONFIG_FILE = BASE_DIR / "harvey.yaml"


def list_projects():
    PROJECTS_DIR.mkdir(exist_ok=True)
    profiles = list(PROJECTS_DIR.glob("*.yaml"))
    if not profiles:
        print("No project profiles found in projects/.")
        return
    print("\nConfigured Project Profiles:")
    for p in profiles:
        print(f"  - {p.stem} ({p.name})")
    print()


def switch_project(project_name: str):
    target = PROJECTS_DIR / f"{project_name}.yaml"
    if not target.exists():
        print(f"Error: Project profile '{project_name}' not found at {target}")
        sys.exit(1)
    shutil.copyfile(target, CONFIG_FILE)
    print(f"Active project switched to '{project_name}'.")


def create_project(project_name: str):
    PROJECTS_DIR.mkdir(exist_ok=True)
    target = PROJECTS_DIR / f"{project_name}.yaml"
    if target.exists():
        print(f"Error: Project '{project_name}' already exists.")
        sys.exit(1)
    
    # Template
    template = f"""persona:
  name: "Sales Lead"
  company: "{project_name.capitalize()}"
  role: "Growth & Outreach"
  email: "outreach@{project_name.lower()}.com"
  linkedin: ""
  tone: "sharp, consultative, concise"

product:
  name: "{project_name.capitalize()}"
  description: "Description for {project_name}"
  pricing: "Custom pricing"
  key_benefits:
    - "Value proposition 1"
    - "Value proposition 2"
  objection_responses:
    "too expensive": "We focus on quick ROI..."
  offer:
    primary: "{project_name.capitalize()} Platform"
    entry: "15-minute introductory call"
    goal: "book_call"
    booking_method: "calendar_link"
    booking_url: ""
    meeting_duration: "15 minutes"
    meeting_owner: "Sales Lead"

icp:
  industries:
    - "Technology"
  company_size: "10-200 employees"
  titles:
    - "Founder"
    - "CEO"
    - "Head of Growth"
  geography:
    - "United States"
    - "United Kingdom"
  hiring_signals: []

brain:
  provider: "openrouter"
  model: "meta-llama/llama-3.3-70b-instruct"

channels:
  email:
    enabled: true
    provider: "smtp"
    max_daily_sends: 25
    require_approval: true
    send_to_risky: false
    max_bounce_rate: 0.05
  linkedin:
    enabled: false

usage:
  max_daily_claude_percent: 80
  heartbeat_interval_minutes: 15
  quiet_hours:
    start: "22:00"
    end: "07:00"
    timezone: "America/New_York"

compliance:
  precleared:
    enabled: false
    sender_country: ""
    address_source: "unknown"
"""
    target.write_text(template)
    print(f"Created template profile for '{project_name}' at {target}")


def main():
    parser = argparse.ArgumentParser(description="Harvey Multi-Project Manager")
    subparsers = parser.add_subparsers(dest="action", required=True)

    subparsers.add_parser("list", help="List all project profiles")

    create_parser = subparsers.add_parser("create", help="Create a new project profile")
    create_parser.add_argument("--project", "-p", required=True, help="Name of project")

    switch_parser = subparsers.add_parser("switch", help="Switch active project")
    switch_parser.add_argument("--project", "-p", required=True, help="Name of project")

    status_parser = subparsers.add_parser("status", help="Check status for a project")
    status_parser.add_argument("--project", "-p", required=False, help="Name of project (optional)")

    run_parser = subparsers.add_parser("run", help="Run Harvey heartbeat/agent for a project")
    run_parser.add_argument("--project", "-p", required=False, help="Name of project (optional)")

    discover_parser = subparsers.add_parser("discover", help="Discover companies matching ICP")
    discover_parser.add_argument("--project", "-p", required=False, help="Name of project (optional)")
    discover_parser.add_argument("--city", "-c", required=False, help="Specific city override")
    discover_parser.add_argument("--limit", "-l", type=int, default=10, help="Max companies to discover")

    args = parser.parse_args()

    if args.action == "list":
        list_projects()
    elif args.action == "create":
        create_project(args.project)
    elif args.action == "switch":
        switch_project(args.project)
    elif args.action == "status":
        if args.project:
            switch_project(args.project)
        venv_python = BASE_DIR / ".venv" / "bin" / "python3"
        subprocess.run([str(venv_python), "-m", "harvey", "status"])
    elif args.action == "run":
        if args.project:
            switch_project(args.project)
        venv_python = BASE_DIR / ".venv" / "bin" / "python3"
        cmd = [str(venv_python), "-m", "harvey", "run"]
        subprocess.run(cmd)
    elif args.action == "discover":
        if args.project:
            switch_project(args.project)
        venv_python = BASE_DIR / ".venv" / "bin" / "python3"
        cmd = [str(venv_python), "-m", "harvey", "discover", "--limit", str(args.limit)]
        if args.city:
            cmd.extend(["--city", args.city])
        subprocess.run(cmd)


if __name__ == "__main__":
    main()
