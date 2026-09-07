import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

now = datetime.now(timezone.utc)
start = now - timedelta(days=365)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
    }
  }
}
"""

payload = {
    "query": query,
    "variables": {
        "login": os.environ["PROFILE_USER"],
        "from": start.isoformat(),
        "to": now.isoformat(),
    },
}

request = Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "Content-Type": "application/json",
        "User-Agent": "profile-activity",
    },
)

with urlopen(request, timeout=60) as response:
    result = json.load(response)

if result.get("errors"):
    raise RuntimeError(json.dumps(result["errors"]))

user = result.get("data", {}).get("user")
if not user:
    raise RuntimeError("GitHub user not found")

data = user["contributionsCollection"]
values = [
    data["totalPullRequestReviewContributions"],
    data["totalIssueContributions"],
    data["totalPullRequestContributions"],
    data["totalCommitContributions"],
]
total = sum(values)
shares = [value / total if total else 0 for value in values]

cx, cy = 300, 185
directions = [(0, -115), (175, 0), (0, 115), (-175, 0)]
points = [
    (cx + dx * share, cy + dy * share)
    for (dx, dy), share in zip(directions, shares)
]
polygon = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)

labels = [
    ("Code review", 300, 32),
    ("Issues", 530, 178),
    ("Pull requests", 300, 327),
    ("Commits", 70, 178),
]

parts = [
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'width="600" height="400" viewBox="0 0 600 400" '
    'role="img" aria-labelledby="title description">',
    '<title id="title">GitHub activity</title>',
    '<desc id="description">Contribution distribution over the '
    'last 365 days. Each axis shows its share of the four categories.</desc>',
    '<rect width="600" height="400" rx="12" fill="#222a32"/>',
    '<g stroke="#56616e" stroke-width="1">',
    '<path d="M125 185H475 M300 70V300"/>',
    '</g>',
    f'<polygon points="{polygon}" fill="#93c5fd" '
    'fill-opacity=".18" stroke="#93c5fd" stroke-width="2"/>',
]

for x, y in points:
    parts.append(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" '
        'fill="#93c5fd" stroke="#dbeafe" stroke-width="1.5"/>'
    )

for (label, x, y), value, share in zip(labels, values, shares):
    parts.append(
        f'<text x="{x}" y="{y}" text-anchor="middle" '
        'font-family="Segoe UI,Arial,sans-serif" font-size="15" '
        f'fill="#b8c4d2">{label}</text>'
    )
    parts.append(
        f'<text x="{x}" y="{y + 21}" text-anchor="middle" '
        'font-family="Segoe UI,Arial,sans-serif" font-size="13" '
        f'fill="#93c5fd">{value:,} · {share:.1%}</text>'
    )

footer = (
    f"Last 365 days · Updated {now:%Y-%m-%d} UTC"
    if total
    else f"No contributions found · Updated {now:%Y-%m-%d} UTC"
)
parts.append(
    '<text x="300" y="382" text-anchor="middle" '
    'font-family="Segoe UI,Arial,sans-serif" font-size="12" '
    f'fill="#94a3b8">{footer}</text></svg>'
)

Path("assets").mkdir(exist_ok=True)
Path("assets/activity.svg").write_text("\n".join(parts), encoding="utf-8")
