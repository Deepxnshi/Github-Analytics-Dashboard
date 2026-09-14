"""
github_client.py
Thin wrapper around the GitHub REST API: handles auth, pagination,
and basic rate-limit awareness. No analytics logic here — just fetching.
"""

import os
import time
import requests

API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        resp = self.session.get(url, params=params)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - int(time.time()), 1)
            print(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp

    def _paginate(self, url: str, params: dict | None = None, max_pages: int = 10) -> list:
        """Fetch all pages up to max_pages (100 items/page = up to 1000 items by default).
        max_pages keeps runtime & API usage reasonable for a student project."""
        params = dict(params or {})
        params["per_page"] = 100
        results = []
        page = 1
        while page <= max_pages:
            params["page"] = page
            resp = self._get(url, params=params)
            batch = resp.json()
            if not batch:
                break
            results.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return results

    def get_repo(self, owner: str, repo: str) -> dict:
        return self._get(f"{API_BASE}/repos/{owner}/{repo}").json()

    def get_commits(self, owner: str, repo: str, max_pages: int = 10) -> list:
        return self._paginate(f"{API_BASE}/repos/{owner}/{repo}/commits", max_pages=max_pages)

    def get_contributors(self, owner: str, repo: str, max_pages: int = 5) -> list:
        return self._paginate(
            f"{API_BASE}/repos/{owner}/{repo}/contributors",
            params={"anon": "false"},
            max_pages=max_pages,
        )

    def get_pull_requests(self, owner: str, repo: str, state: str = "all", max_pages: int = 10) -> list:
        return self._paginate(
            f"{API_BASE}/repos/{owner}/{repo}/pulls",
            params={"state": state, "sort": "created", "direction": "desc"},
            max_pages=max_pages,
        )

    def get_issues(self, owner: str, repo: str, state: str = "all", max_pages: int = 10) -> list:
        # Note: GitHub's /issues endpoint also returns PRs; callers should
        # filter out items that have a "pull_request" key if they want
        # issues only (analytics.py handles this).
        return self._paginate(
            f"{API_BASE}/repos/{owner}/{repo}/issues",
            params={"state": state, "sort": "created", "direction": "desc"},
            max_pages=max_pages,
        )
