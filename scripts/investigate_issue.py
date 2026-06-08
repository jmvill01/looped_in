#!/usr/bin/env python3
"""
investigate_issue.py — Multi-agent issue investigation orchestrator.

Triggered by the issue-investigation GitHub Actions workflow whenever a new
issue is opened in the looped_in repository.  Four AI agents collaborate to
diagnose the reported defect:

  1. issues-investigator  — triages the issue and routes to specialist(s)
  2. powertrain-specialist — expert on powertrain.py (BUG-2, BUG-3)
  3. brakes-specialist     — expert on brakes.py (BUG-4)
  4. park-brake-specialist — expert on park_brake.py (BUG-1)

The full conversation is posted as a single Markdown comment on the issue.

Environment variables (set by the workflow):
  GITHUB_TOKEN       — token with issues:write and contents:read
  GITHUB_REPOSITORY  — owner/repo
  ISSUE_NUMBER       — integer issue number
  ISSUE_TITLE        — title of the newly opened issue
  ISSUE_BODY         — body text of the newly opened issue
"""

import os
import sys
import json
import textwrap
import requests
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]
ISSUE_NUMBER = os.environ["ISSUE_NUMBER"]
ISSUE_TITLE = os.environ["ISSUE_TITLE"]
ISSUE_BODY = os.environ.get("ISSUE_BODY", "")

REPO_ROOT = Path(__file__).parent.parent

MODELS_API_URL = "https://models.inference.ai.azure.com/chat/completions"
GITHUB_API_BASE = "https://api.github.com"
MODEL = "gpt-4o-mini"
MAX_TOKENS = 350

# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------

def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _load_issues_summary() -> str:
    """Return a compact summary of issues.json for the investigator."""
    data = json.loads(_read("issues.json"))
    lines = [f"Project: {data['project']}  SW: {data['software_version']}",
             ""]
    for issue in data.get("issues", []):
        lines.append(
            f"[{issue['id']}] {issue['title']}\n"
            f"  Component: {issue['component']} | Severity: {issue['severity']} | Status: {issue['status']}\n"
            f"  {issue['description'][:200]}{'…' if len(issue['description']) > 200 else ''}"
        )
        lines.append("")
    return "\n".join(lines)


def _load_controller(filename: str) -> str:
    return _read(f"simulation/controllers/{filename}")

# ---------------------------------------------------------------------------
# Agent system prompts
# ---------------------------------------------------------------------------

INVESTIGATOR_SYSTEM = textwrap.dedent("""\
    You are the VDCS Issues Investigator for the looped_in repository.
    You triage new defect reports by:
      1. Matching symptoms to the known issue database.
      2. Identifying which controller(s) are likely involved.
      3. Formulating one or two targeted questions for each relevant specialist.
    Be brief and clear — keep your opening triage under 120 words.
    End your message with a JSON block on its own line in this exact format:
      {"consult": ["powertrain", "brakes", "park_brake"]}
    Include only the specialists that are relevant; omit any that are not.

    Known issue database:
    {issues_summary}
""")

POWERTRAIN_SYSTEM = textwrap.dedent("""\
    You are the Powertrain Controller Specialist for the looped_in VDCS project.
    You know the full source of simulation/controllers/powertrain.py, shown below.
    Answer the investigator's question concisely (under 120 words).
    Map symptoms directly to BUG-2 (inverted upshift operator) or BUG-3
    (ROLLING_RESISTANCE_COEFF = 1.3 instead of 0.013).  Quote exact variable
    or line references.

    Source:
    {source}
""")

BRAKES_SYSTEM = textwrap.dedent("""\
    You are the Hydraulic Brakes Controller Specialist for the looped_in VDCS project.
    You know the full source of simulation/controllers/brakes.py, shown below.
    Answer the investigator's question concisely (under 120 words).
    Map symptoms directly to BUG-4 (inverted error sign in compute_brake_force).
    Quote exact variable or line references.

    Source:
    {source}
""")

PARK_BRAKE_SYSTEM = textwrap.dedent("""\
    You are the Electronic Park Brake Controller Specialist for the looped_in VDCS project.
    You know the full source of simulation/controllers/park_brake.py, shown below.
    Answer the investigator's question concisely (under 120 words).
    Map symptoms directly to BUG-1 (torque halved instead of zeroed in release()).
    Quote exact variable or line references.

    Source:
    {source}
""")

SYNTHESIS_SYSTEM = textwrap.dedent("""\
    You are the VDCS Issues Investigator writing your final diagnosis.
    Given the specialist responses, produce a concise summary (under 150 words) that:
      - Names the root cause(s) and which bug ID(s) apply.
      - States the exact file and line/constant to fix.
      - Suggests the one-line code change needed.
    Use plain language; avoid restating the symptoms at length.
""")

# ---------------------------------------------------------------------------
# AI call helper
# ---------------------------------------------------------------------------

def call_model(system: str, user: str) -> str:
    """Call GitHub Models API and return the assistant reply text."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.2,
    }
    resp = requests.post(
        MODELS_API_URL,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

# ---------------------------------------------------------------------------
# GitHub comment helper
# ---------------------------------------------------------------------------

def post_comment(body: str) -> None:
    """Post a comment on the issue."""
    url = f"{GITHUB_API_BASE}/repos/{REPO}/issues/{ISSUE_NUMBER}/comments"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"body": body},
        timeout=30,
    )
    resp.raise_for_status()

# ---------------------------------------------------------------------------
# Specialist dispatch
# ---------------------------------------------------------------------------

SPECIALIST_CONFIGS = {
    "powertrain": {
        "label": "🔧 Powertrain Specialist (`@powertrain-specialist`)",
        "system_template": POWERTRAIN_SYSTEM,
        "source_file": "powertrain.py",
    },
    "brakes": {
        "label": "🛑 Brakes Specialist (`@brakes-specialist`)",
        "system_template": BRAKES_SYSTEM,
        "source_file": "brakes.py",
    },
    "park_brake": {
        "label": "🅿️ Park Brake Specialist (`@park-brake-specialist`)",
        "system_template": PARK_BRAKE_SYSTEM,
        "source_file": "park_brake.py",
    },
}


def _extract_consult_list(triage_text: str) -> list[str]:
    """Extract the JSON consult list from the investigator's response."""
    import re
    match = re.search(r'\{[^}]*"consult"\s*:\s*\[[^\]]*\][^}]*\}', triage_text)
    if not match:
        # Default: consult all specialists if parsing fails
        return list(SPECIALIST_CONFIGS.keys())
    try:
        data = json.loads(match.group())
        return [s for s in data.get("consult", []) if s in SPECIALIST_CONFIGS]
    except json.JSONDecodeError:
        return list(SPECIALIST_CONFIGS.keys())


def _strip_json_block(text: str) -> str:
    """Remove the trailing JSON routing block from the investigator's message."""
    import re
    return re.sub(r'\{[^}]*"consult"\s*:\s*\[[^\]]*\][^}]*\}', "", text).strip()

# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Investigating issue #{ISSUE_NUMBER}: {ISSUE_TITLE}")

    # Load context
    issues_summary = _load_issues_summary()

    # --- Step 1: Investigator triage ---
    investigator_system = INVESTIGATOR_SYSTEM.format(issues_summary=issues_summary)
    user_report = (
        f"New issue reported:\n\n"
        f"**Title:** {ISSUE_TITLE}\n\n"
        f"**Description:**\n{ISSUE_BODY or '(no body provided)'}"
    )
    print("Calling issues investigator…")
    triage_response = call_model(investigator_system, user_report)
    consult_list = _extract_consult_list(triage_response)
    triage_clean = _strip_json_block(triage_response)
    print(f"Routing to specialists: {consult_list}")

    # --- Step 2: Specialist consultations ---
    specialist_responses: dict[str, str] = {}
    for specialist_key in consult_list:
        cfg = SPECIALIST_CONFIGS[specialist_key]
        source_code = _load_controller(cfg["source_file"])
        system = cfg["system_template"].format(source=source_code)
        question = (
            f"The issues investigator is looking into: '{ISSUE_TITLE}'.\n\n"
            f"Investigator's analysis so far:\n{triage_clean}\n\n"
            f"Please provide your specialist assessment relevant to your controller."
        )
        print(f"Calling {specialist_key} specialist…")
        specialist_responses[specialist_key] = call_model(system, question)

    # --- Step 3: Synthesis ---
    context_for_synthesis = (
        f"Issue: {ISSUE_TITLE}\n\n"
        f"Investigator triage:\n{triage_clean}\n\n"
    )
    for key, reply in specialist_responses.items():
        label = SPECIALIST_CONFIGS[key]["label"]
        context_for_synthesis += f"{label} response:\n{reply}\n\n"

    print("Calling investigator for synthesis…")
    synthesis = call_model(SYNTHESIS_SYSTEM, context_for_synthesis)

    # --- Step 4: Build and post comment ---
    separator = "\n\n---\n\n"
    comment_parts = [
        "## 🤖 AI Investigation — VDCS Root-Cause Analysis\n",
        f"### 🔍 Issues Investigator (`@issues-investigator`)\n\n{triage_clean}",
    ]

    for key, reply in specialist_responses.items():
        label = SPECIALIST_CONFIGS[key]["label"]
        comment_parts.append(f"### {label}\n\n{reply}")

    comment_parts.append(f"### ✅ Investigator Synthesis\n\n{synthesis}")
    comment_parts.append(
        "_This analysis was generated automatically by the VDCS multi-agent "
        "investigation system. Always validate findings against the source code "
        "before applying fixes._"
    )

    comment_body = separator.join(comment_parts)
    print("Posting investigation comment…")
    post_comment(comment_body)
    print("Done.")


if __name__ == "__main__":
    main()
