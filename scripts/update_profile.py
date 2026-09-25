#!/usr/bin/env python3
"""Fully dynamic GitHub profile generator.

Pulls 100% of profile data, repository metrics, language distribution,
repository topics, and public activity directly from the GitHub API.
Includes intelligent batching, rate-limit resilience, and zero hardcoded project lists.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

API = "https://api.github.com"
OWNER = (
    os.environ.get("GITHUB_REPOSITORY_OWNER")
    or os.environ.get("PROFILE_USERNAME")
    or "Abhijeetsingh0022"
)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
OUTPUT = WORKSPACE_DIR / "README.md"
CONFIG_PATH = WORKSPACE_DIR / "profile.config.json"
CACHE_PATH = WORKSPACE_DIR / "scripts" / ".cache_data.json"


def api_get(path: str, *, query: dict[str, str] | None = None) -> dict | list:
    url = API + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{OWNER}-dynamic-profile",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def safe_text(value: str | None, fallback: str = "") -> str:
    return html.escape((value or fallback).strip())


def compact_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def age_text(iso: str | None) -> str:
    if not iso:
        return "recently"
    try:
        value = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = dt.datetime.now(dt.timezone.utc) - value
        days = delta.days
        if days <= 0:
            return "today"
        if days == 1:
            return "1 day ago"
        if days < 30:
            return f"{days} days ago"
        months = days // 30
        if months < 12:
            return f"{months} mo{'s' if months != 1 else ''} ago"
        years = months // 12
        return f"{years} yr{'s' if years != 1 else ''} ago"
    except Exception:
        return "recently"


def make_two_column_table(cells: list[str]) -> str:
    """Pairs cells into a valid 2-column HTML table with balanced <tr> tags."""
    if not cells:
        return ""
    rows = []
    for i in range(0, len(cells), 2):
        left = cells[i]
        right = cells[i + 1] if i + 1 < len(cells) else '<td width="50%" valign="top"></td>'
        rows.append(f"<tr>\n{left}\n{right}\n</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cache(user_data: dict, repos_data: list[dict]) -> None:
    try:
        CACHE_PATH.write_text(
            json.dumps({"user": user_data, "repos": repos_data, "cached_at": dt.datetime.now(dt.timezone.utc).isoformat()}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def event_summary(event: dict) -> str:
    typ = event.get("type", "")
    repo = event.get("repo", {}).get("name", "")
    payload = event.get("payload", {})
    if typ == "PushEvent":
        count = len(payload.get("commits", []))
        return f"Pushed {count or 'new'} commit{'s' if count != 1 else ''} to [{repo}](https://github.com/{repo})"
    if typ == "PullRequestEvent":
        action = payload.get("action", "updated")
        return f"{action.capitalize()} a pull request in [{repo}](https://github.com/{repo})"
    if typ == "IssuesEvent":
        action = payload.get("action", "updated")
        return f"{action.capitalize()} an issue in [{repo}](https://github.com/{repo})"
    if typ == "CreateEvent":
        ref_type = payload.get("ref_type", "resource")
        return f"Created {ref_type} in [{repo}](https://github.com/{repo})"
    if typ == "WatchEvent":
        return f"Starred [{repo}](https://github.com/{repo})"
    if typ == "ForkEvent":
        return f"Forked [{repo}](https://github.com/{repo})"
    if typ == "ReleaseEvent":
        return f"Published a release in [{repo}](https://github.com/{repo})"
    return f"Activity in [{repo}](https://github.com/{repo})" if repo else typ.replace("Event", "")


def main() -> None:
    config = load_config()
    cached = load_cache()

    # 1. Fetch user profile from GitHub API
    user: dict = {}
    try:
        user = api_get(f"/users/{urllib.parse.quote(OWNER)}")
    except Exception as exc:
        print(f"[warning] GitHub user API: {exc}. Using fallback cache if available.", file=sys.stderr)
        user = cached.get("user", {})

    # 2. Fetch public repositories
    repos: list[dict] = []
    page = 1
    fetch_success = False
    try:
        while True:
            batch = api_get(
                f"/users/{urllib.parse.quote(OWNER)}/repos",
                query={"per_page": "100", "page": str(page), "sort": "pushed", "direction": "desc"},
            )
            if isinstance(batch, list):
                repos.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
            else:
                break
        fetch_success = True
    except Exception as exc:
        print(f"[warning] GitHub repos API: {exc}. Using fallback cache if available.", file=sys.stderr)

    if not fetch_success or not repos:
        cached_repos = cached.get("repos", [])
        if cached_repos:
            repos = cached_repos
            print(f"[info] Using {len(repos)} cached repositories.", file=sys.stderr)
        else:
            print("[error] No repositories available from API or cache.", file=sys.stderr)
            if OUTPUT.exists():
                print("[info] Keeping existing README.md without modification.", file=sys.stderr)
                return

    # Cache successful data
    if fetch_success and repos and user:
        save_cache(user, repos)

    # Filter out forks, archived repos, and the profile repository itself
    public_repos = [
        r for r in repos
        if not r.get("fork") and not r.get("archived") and r.get("name", "").lower() != OWNER.lower()
    ]

    # 3. Dynamic language calculation & topic aggregation
    # If GITHUB_TOKEN is available, we can fetch exact language bytes; otherwise compute from primary languages.
    language_counts: Counter[str] = Counter()
    aggregated_topics: Counter[str] = Counter()

    for r in public_repos:
        r_name = r.get("name", "")
        if GITHUB_TOKEN:
            try:
                lang_data = api_get(f"/repos/{OWNER}/{r_name}/languages")
                if isinstance(lang_data, dict):
                    language_counts.update({k: int(v) for k, v in lang_data.items()})
            except Exception:
                if r.get("language"):
                    language_counts[r["language"]] += 1000
        else:
            if r.get("language"):
                language_counts[r["language"]] += 1000

        # Collect topics
        topics = r.get("topics") or []
        aggregated_topics.update(topics)

    # 4. Fetch recent public events for dynamic activity feed
    events: list[dict] = []
    try:
        ev_data = api_get(
            f"/users/{urllib.parse.quote(OWNER)}/events/public",
            query={"per_page": "8"},
        )
        if isinstance(ev_data, list):
            events = ev_data
    except Exception:
        events = []

    # Calculate totals
    total_stars = sum(int(r.get("stargazers_count") or r.get("stars", 0)) for r in public_repos)
    total_forks = sum(int(r.get("forks_count") or r.get("forks", 0)) for r in public_repos)
    total_weights = max(sum(language_counts.values()), 1)
    languages_sorted = language_counts.most_common(8)

    # Dynamic user details
    display_name = user.get("name") or OWNER
    bio = user.get("bio") or "AI/ML Engineer & Full-Stack Developer"
    location = user.get("location") or ""
    website = user.get("blog") or ""
    website_url = website if re.match(r"^https?://", website) else (f"https://{website}" if website else "")

    # External contact links (from config or user profile)
    links = config.get("links", {})
    linkedin_url = links.get("linkedin", "")
    email = links.get("email", "")
    github_url = f"https://github.com/{OWNER}"

    # Build Header Badges
    badge_items = []
    if website_url:
        badge_items.append(f'<a href="{safe_text(website_url)}"><img src="https://img.shields.io/badge/Portfolio-111111?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Portfolio" /></a>')
    if linkedin_url:
        badge_items.append(f'<a href="{safe_text(linkedin_url)}"><img src="https://img.shields.io/badge/LinkedIn-111111?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn" /></a>')
    if email:
        badge_items.append(f'<a href="mailto:{safe_text(email)}"><img src="https://img.shields.io/badge/Email-111111?style=for-the-badge&logo=gmail&logoColor=white" alt="Email" /></a>')
    badge_items.append(f'<a href="{safe_text(github_url)}"><img src="https://img.shields.io/badge/GitHub-111111?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" /></a>')
    badges_html = " &nbsp; ".join(badge_items)

    # Build Dynamic Language Distribution Table
    lang_table_rows = []
    for lang, count in languages_sorted:
        pct = (count / total_weights) * 100
        filled_blocks = int(round(pct / 10))
        bar = "█" * filled_blocks + "░" * (10 - filled_blocks)
        lang_table_rows.append(f"| `{safe_text(lang)}` | `{bar}` | {pct:.1f}% |")

    languages_table = (
        "| Language | Distribution | Share |\n|:---|:---:|---:|\n" + "\n".join(lang_table_rows)
        if lang_table_rows
        else "_Language statistics updating automatically._"
    )

    # Dynamic Topics / Ecosystem
    topic_chips = [f"`{safe_text(t)}`" for t, _ in aggregated_topics.most_common(16)]
    topic_cloud = " · ".join(topic_chips) if topic_chips else "`AI/ML` · `FastAPI` · `Python` · `TypeScript` · `Next.js`"

    # Rank repositories dynamically: (Stars * 50) + (Forks * 20) + (Pushed recency)
    def repo_rank(r: dict) -> tuple[int, str]:
        stars = int(r.get("stargazers_count") or r.get("stars", 0))
        forks = int(r.get("forks_count") or r.get("forks", 0))
        pushed = r.get("pushed_at") or r.get("updated_at") or ""
        score = (stars * 50) + (forks * 20)
        return (score, pushed)

    ranked_repos = sorted(public_repos, key=repo_rank, reverse=True)

    # Build Featured Repositories 2-Column Table
    repo_cells = []
    for r in ranked_repos[:6]:
        r_name = safe_text(r["name"])
        r_url = r.get("html_url") or f"https://github.com/{OWNER}/{r_name}"
        raw_desc = r.get("desc") or r.get("description") or "Open-source project on GitHub."
        r_desc = safe_text(raw_desc)
        r_lang = safe_text(r.get("language") or "Code")
        r_stars = compact_number(int(r.get("stargazers_count", r.get("stars", 0))))
        r_forks = compact_number(int(r.get("forks_count", r.get("forks", 0))))
        r_updated = age_text(r.get("pushed_at"))
        r_topics = r.get("topics") or []

        topics_line = ""
        if r_topics:
            topics_html = " ".join(f"<code>{safe_text(t)}</code>" for t in r_topics[:4])
            topics_line = f"<br/>{topics_html}"

        repo_cells.append(
            f'<td width="50%" valign="top">\n\n'
            f'### [{r_name}]({r_url})\n\n'
            f'{r_desc}{topics_line}\n<br/>\n'
            f'<sub>⚙ {r_lang} &nbsp; ⭐ {r_stars} &nbsp; ⑂ {r_forks} &nbsp; · &nbsp; {r_updated}</sub>\n\n'
            f'</td>'
        )

    featured_repos_table = make_two_column_table(repo_cells)

    # Build Dynamic Recent Activity Section
    activity_items = []
    for ev in events[:6]:
        summary = event_summary(ev)
        date_str = ev.get("created_at", "")[:10]
        activity_items.append(f"- {summary} · <sub>`{date_str}`</sub>")

    activity_md = "\n".join(activity_items) if activity_items else "_Recent public commits and actions refresh automatically._"

    # Location indicator
    location_line = f"📍 {safe_text(location)} &nbsp; • &nbsp; " if location else ""

    # Assemble the dynamic README
    readme_content = f'''<div align="center">

# {safe_text(display_name)}

**{safe_text(bio)}**

{location_line}<a href="{safe_text(github_url)}">@{safe_text(OWNER)}</a>

<br/>

{badges_html}

<br/><br/>

<img src="https://komarev.com/ghpvc/?username={safe_text(OWNER)}&style=flat-square&color=111111&label=PROFILE+VIEWS" alt="Profile views" />

</div>

---

### 📊 Live GitHub Snapshot

<div align="center">

| 📦 Public Repositories | ⭐ Total Stars Earned | 🍴 Total Forks | 📅 Tracked Since |
|:---:|:---:|:---:|:---:|
| **{len(public_repos)}** | **{total_stars}** | **{total_forks}** | **{safe_text((user.get('created_at') or '')[:10], '—')}** |

</div>

---

### 🛠️ Dynamic Tech Ecosystem

*Aggregated in real-time from repository language data and topics:*

**Repository Topics & Tags**  
{topic_cloud}

<br/>

**Codebase Language Distribution**  
{languages_table}

---

### 🚀 Featured Repositories

{featured_repos_table}

---

### 📈 GitHub Analytics

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-stats.vercel.app/api?username={safe_text(OWNER)}&show_icons=true&hide_border=true&theme=github_dark&title_color=ffffff&icon_color=ffffff&text_color=999999&bg_color=0d1117" />
  <source media="(prefers-color-scheme: light)" srcset="https://github-readme-stats.vercel.app/api?username={safe_text(OWNER)}&show_icons=true&hide_border=true&theme=default&title_color=111111&icon_color=111111&text_color=555555" />
  <img src="https://github-readme-stats.vercel.app/api?username={safe_text(OWNER)}&show_icons=true&hide_border=true&theme=default&title_color=111111&icon_color=111111&text_color=555555" width="48%" alt="GitHub Stats" />
</picture>
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-stats.vercel.app/api/top-langs/?username={safe_text(OWNER)}&layout=compact&hide_border=true&theme=github_dark&title_color=ffffff&text_color=999999&bg_color=0d1117" />
  <source media="(prefers-color-scheme: light)" srcset="https://github-readme-stats.vercel.app/api/top-langs/?username={safe_text(OWNER)}&layout=compact&hide_border=true&theme=default&title_color=111111&text_color=555555" />
  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username={safe_text(OWNER)}&layout=compact&hide_border=true&theme=default&title_color=111111&text_color=555555" width="40%" alt="Top Languages" />
</picture>

<br/><br/>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://streak-stats.demolab.com?user={safe_text(OWNER)}&theme=dark&hide_border=true&background=0d1117&ring=ffffff&fire=ffffff&currStreakLabel=ffffff" />
  <source media="(prefers-color-scheme: light)" srcset="https://streak-stats.demolab.com?user={safe_text(OWNER)}&theme=default&hide_border=true&ring=111111&fire=111111&currStreakLabel=111111" />
  <img src="https://streak-stats.demolab.com?user={safe_text(OWNER)}&theme=default&hide_border=true&ring=111111&fire=111111&currStreakLabel=111111" width="70%" alt="GitHub Streak" />
</picture>

</div>

---

### 🐍 Contribution Activity

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/github-contribution-grid-snake-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="assets/github-contribution-grid-snake.svg" />
    <img alt="GitHub contribution grid snake" src="assets/github-contribution-grid-snake.svg" />
  </picture>
</p>

---

### ⚡ Recent Public Activity

{activity_md}

---

<div align="center">

**Building · Learning · Shipping**

<a href="https://github.com/{safe_text(OWNER)}?tab=repositories">
  <img src="https://img.shields.io/badge/VIEW%20ALL%20REPOSITORIES-111111?style=for-the-badge&logo=github&logoColor=white" alt="View Repositories" />
</a>{' &nbsp; <a href="' + safe_text(website_url) + '"><img src="https://img.shields.io/badge/EXPLORE%20PORTFOLIO-111111?style=for-the-badge&logoColor=white" alt="Portfolio" /></a>' if website_url else ''}

</div>

<!-- profile-readme:generated -->
'''

    OUTPUT.write_text(readme_content, encoding="utf-8")
    print(f"Successfully generated {OUTPUT} for {OWNER} ({len(public_repos)} public repos detected).")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"GitHub API HTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        sys.exit(1)
