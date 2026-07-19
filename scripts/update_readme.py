#!/usr/bin/env python3
"""
update_readme.py
Fetches data from the GitHub API and rewrites four dynamic sections in README.md:
  - working-on       : recent pushes to the user's own repos
  - contributed-to   : recent events in repos owned by others (stars excluded)
  - most-starred     : the user's own public repos sorted by star count
  - recently-starred : repos the user has recently starred
"""

import os
import re
import sys
import requests

USERNAME = "anthonymendez"
README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")
MAX_ITEMS = 5

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def gh_get(url: str, params: dict = None) -> list | dict:
    """Simple GitHub API GET with error handling."""
    response = requests.get(url, headers=HEADERS, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def update_section(content: str, section_name: str, new_body: str) -> str:
    """Replace the content between section comment markers."""
    pattern = (
        rf"(<!--START_SECTION:{re.escape(section_name)}-->)"
        r".*?"
        rf"(<!--END_SECTION:{re.escape(section_name)}-->)"
    )
    replacement = rf"\1\n{new_body}\n\2"
    updated, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        print(f"WARNING: section '{section_name}' markers not found in README.", file=sys.stderr)
    return updated


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def get_working_on() -> list[str]:
    """
    Returns up to MAX_ITEMS bullet points for recent push events
    in repos owned by the user.
    """
    events = gh_get(
        f"https://api.github.com/users/{USERNAME}/events/public",
        params={"per_page": 100},
    )

    lines = []
    seen: set[str] = set()

    for event in events:
        if event.get("type") != "PushEvent":
            continue
        repo_name = event["repo"]["name"]
        owner = repo_name.split("/")[0]
        if owner.lower() != USERNAME.lower():
            continue
        if repo_name in seen:
            continue
        seen.add(repo_name)

        short_name = repo_name.split("/", 1)[1]
        url = f"https://github.com/{repo_name}"
        lines.append(f"- 🔨 Pushed to [**{short_name}**]({url})")
        if len(lines) >= MAX_ITEMS:
            break

    return lines or ["_No recent pushes found._"]


def get_contributed_to() -> list[str]:
    """
    Returns up to MAX_ITEMS bullet points for recent events in repos NOT owned
    by the user. WatchEvent (stars) are excluded — they get their own section.
    """
    events = gh_get(
        f"https://api.github.com/users/{USERNAME}/events/public",
        params={"per_page": 100},
    )

    # WatchEvent intentionally omitted — handled by get_recently_starred()
    EVENT_ICONS = {
        "PushEvent": ("🔨", "pushed to"),
        "PullRequestEvent": ("📬", "opened a PR in"),
        "IssueCommentEvent": ("💬", "commented in"),
        "IssuesEvent": ("🐛", "opened an issue in"),
        "ForkEvent": ("🍴", "forked"),
        "CreateEvent": ("✨", "created a branch in"),
    }

    lines = []
    seen: set[str] = set()

    for event in events:
        event_type = event.get("type", "")
        # Skip stars — they belong in the recently-starred section
        if event_type == "WatchEvent":
            continue
        repo_name = event["repo"]["name"]
        owner = repo_name.split("/")[0]
        if owner.lower() == USERNAME.lower():
            continue
        if repo_name in seen:
            continue

        icon, verb = EVENT_ICONS.get(event_type, ("🔗", "was active in"))
        seen.add(repo_name)

        url = f"https://github.com/{repo_name}"
        lines.append(f"- {icon} {verb.capitalize()} [**{repo_name}**]({url})")
        if len(lines) >= MAX_ITEMS:
            break

    return lines or ["_No recent contributions to other repos found._"]


def get_recently_starred() -> list[str]:
    """
    Returns up to MAX_ITEMS bullet points for repos the user has recently starred,
    using the /users/{username}/starred endpoint (sorted by most recently starred).
    """
    starred = gh_get(
        f"https://api.github.com/users/{USERNAME}/starred",
        params={"per_page": MAX_ITEMS, "sort": "created", "direction": "desc"},
    )

    lines = []
    for repo in starred:
        name = repo["full_name"]
        url = repo["html_url"]
        description = repo.get("description") or ""
        stars = repo.get("stargazers_count", 0)
        desc_part = f" — {description}" if description else ""
        lines.append(f"- ⭐ [**{name}**]({url}) ({stars} ★){desc_part}")

    return lines or ["_No recently starred repos found._"]


def get_most_starred() -> list[str]:
    """
    Returns up to MAX_ITEMS bullet points for the user's own public repos
    sorted by star count (descending).
    """
    repos = gh_get(
        f"https://api.github.com/users/{USERNAME}/repos",
        params={"per_page": 100, "type": "owner", "sort": "updated"},
    )

    repos_sorted = sorted(
        repos,
        key=lambda r: r.get("stargazers_count", 0),
        reverse=True,
    )[:MAX_ITEMS]

    lines = []
    for repo in repos_sorted:
        stars = repo.get("stargazers_count", 0)
        name = repo["name"]
        url = repo["html_url"]
        description = repo.get("description") or ""
        star_badge = f"⭐ {stars}"
        desc_part = f" — {description}" if description else ""
        lines.append(f"- [{star_badge} **{name}**]({url}){desc_part}")

    return lines or ["_No public repos found._"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Fetching data for @{USERNAME} …")

    working_on = get_working_on()
    contributed_to = get_contributed_to()
    most_starred = get_most_starred()
    recently_starred = get_recently_starred()

    print(f"  working-on       : {len(working_on)} item(s)")
    print(f"  contributed-to   : {len(contributed_to)} item(s)")
    print(f"  most-starred     : {len(most_starred)} item(s)")
    print(f"  recently-starred : {len(recently_starred)} item(s)")

    readme_path = os.path.abspath(README_PATH)
    with open(readme_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    content = update_section(content, "working-on",       "\n".join(working_on))
    content = update_section(content, "contributed-to",   "\n".join(contributed_to))
    content = update_section(content, "most-starred",     "\n".join(most_starred))
    content = update_section(content, "recently-starred", "\n".join(recently_starred))

    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    print("README.md updated successfully.")


if __name__ == "__main__":
    main()
