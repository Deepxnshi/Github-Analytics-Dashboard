"""
fetch_data.py
CLI script to fetch a repo's commits, PRs, issues, and contributors
from the GitHub API and cache them as JSON in data/<owner>_<repo>/.

Usage:
    python fetch_data.py --owner facebook --repo react
    python fetch_data.py --owner pallets --repo flask --max-pages 5
"""

import argparse
import json
import os

from github_client import GitHubClient

DATA_DIR = "data"


def save_json(obj, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f)


def main():
    parser = argparse.ArgumentParser(description="Fetch and cache GitHub repo data")
    parser.add_argument("--owner", required=True, help="Repo owner/org, e.g. 'facebook'")
    parser.add_argument("--repo", required=True, help="Repo name, e.g. 'react'")
    parser.add_argument("--max-pages", type=int, default=10, help="Pages to fetch per endpoint (100 items/page)")
    args = parser.parse_args()

    client = GitHubClient()
    repo_dir = os.path.join(DATA_DIR, f"{args.owner}_{args.repo}")

    print(f"Fetching repo info for {args.owner}/{args.repo}...")
    repo_info = client.get_repo(args.owner, args.repo)
    save_json(repo_info, os.path.join(repo_dir, "repo.json"))

    print("Fetching commits...")
    commits = client.get_commits(args.owner, args.repo, max_pages=args.max_pages)
    save_json(commits, os.path.join(repo_dir, "commits.json"))
    print(f"  {len(commits)} commits")

    print("Fetching contributors...")
    contributors = client.get_contributors(args.owner, args.repo)
    save_json(contributors, os.path.join(repo_dir, "contributors.json"))
    print(f"  {len(contributors)} contributors")

    print("Fetching pull requests...")
    pulls = client.get_pull_requests(args.owner, args.repo, max_pages=args.max_pages)
    save_json(pulls, os.path.join(repo_dir, "pulls.json"))
    print(f"  {len(pulls)} pull requests")

    print("Fetching issues...")
    issues = client.get_issues(args.owner, args.repo, max_pages=args.max_pages)
    save_json(issues, os.path.join(repo_dir, "issues.json"))
    print(f"  {len(issues)} issues (includes PRs, filtered later)")

    print(f"\nDone. Cached to {repo_dir}/")


if __name__ == "__main__":
    main()
