#!/usr/bin/env python3
"""Submit ONLY explicitly marked BriDigitalCo branches to the allowlisted upstream.

Runs in a trusted scheduled workflow on the fork's default branch. It neither
checks out nor executes code from contribution branches, nor logs its token.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

FORK = "BriDigitalCo/Go-Hybrid"
UPSTREAM = "limitlessprojects/Go-Hybrid"
BASE = "main"
BRANCH_RE = re.compile(r"^submit/[a-z0-9][a-z0-9._-]{2,60}$")
BLOCKED = (".github/", ".env", ".git/", "AGENTS.md", "package-lock.json", "Cargo.lock")
TOKEN = os.getenv("BRI_UPSTREAM_PR_TOKEN", "")


def api(path, payload=None):
    url = "https://api.github.com" + path
    req = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "BriDigitalCo-reviewed-PR-submitter",
        },
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def ready_message(message):
    """Only use explicit, truthful metadata added after the coding review."""
    required = (
        "Upstream-Ready: true",
        "Tests-Verified: true",
        "AI-Assistance: permitted",
        "Payment-Eligibility: verified",
    )
    if not all(row in message.splitlines() for row in required):
        return None
    lines = message.splitlines()
    title = lines[0].strip()
    if not (12 <= len(title) <= 120):
        return None
    tests = next((x[len("Tests-Run: "):] for x in lines if x.startswith("Tests-Run: ")), "")
    if not tests or len(tests) > 400:
        return None
    body_lines = [x for x in lines[1:] if not re.match(
        r"^(Upstream-Ready|Tests-Verified|AI-Assistance|Payment-Eligibility|Tests-Run):", x
    )]
    summary = "\n".join(body_lines).strip() or title
    body = (
        "## Summary\n\n" + summary + "\n\n## Tests reported by contributor\n\n" +
        tests + "\n\nFull upstream CI and maintainer review remain required. " +
        "Submission is not a claim of bounty award or payment."
    )
    return title, body


def run():
    if not TOKEN:
        print("Not configured: repository secret BRI_UPSTREAM_PR_TOKEN is missing.")
        return 0
    branches = []
    for page in range(1, 6):
        results = api(f"/repos/{FORK}/branches?per_page=100&page={page}")
        branches.extend(results)
        if len(results) < 100:
            break
    for entry in branches:
        branch = entry.get("name", "")
        if not BRANCH_RE.fullmatch(branch):
            continue
        query = urllib.parse.urlencode({"state": "all", "head": "BriDigitalCo:" + branch, "per_page": 100})
        existing = api(f"/repos/{UPSTREAM}/pulls?{query}")
        if existing:
            print(f"Already submitted: {branch}; PR #{existing[0]['number']}")
            continue
        ref = urllib.parse.quote(branch, safe="")
        comparison = api(f"/repos/{FORK}/compare/{BASE}...{ref}")
        files = comparison.get("files", [])
        if not (0 < comparison.get("ahead_by", 0) <= 6 and 0 < len(files) <= 8):
            print(f"Skipped {branch}: review scope is outside safe bounds")
            continue
        if any(path.get("filename", "").startswith(BLOCKED) for path in files):
            print(f"Skipped {branch}: sensitive/configuration file change")
            continue
        if sum(f.get("changes", 0) for f in files) > 500:
            print(f"Skipped {branch}: large patch requires manual review")
            continue
        commit = api(f"/repos/{FORK}/commits/{ref}")
        parsed = ready_message(commit["commit"]["message"])
        if not parsed:
            print(f"Skipped {branch}: complete review metadata is missing")
            continue
        title, body = parsed
        payload = {
            "title": title,
            "body": body,
            "head": "BriDigitalCo:" + branch,
            "base": BASE,
            "maintainer_can_modify": True,
        }
        result = api(f"/repos/{UPSTREAM}/pulls", payload)
        print("Created: " + result["html_url"])
        return 0  # At most one external PR per run; avoid flooding maintainers.
    print("No new reviewed branches eligible for submission.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except urllib.error.HTTPError as exc:
        print(f"GitHub API returned HTTP {exc.code}; check repository permissions.", file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Submission paused: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
