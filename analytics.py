"""
analytics.py
Pure functions that take raw GitHub API data (as returned by github_client)
and compute the analytics metrics. No network calls here — this module is
fully unit-testable and is the "data science" heart of the project.
"""

import pandas as pd


def commits_to_df(commits: list) -> pd.DataFrame:
    rows = []
    for c in commits:
        commit = c.get("commit", {})
        author = commit.get("author", {}) or {}
        rows.append({
            "sha": c.get("sha"),
            "author_login": (c.get("author") or {}).get("login"),
            "author_name": author.get("name"),
            "date": author.get("date"),
            "message": commit.get("message", "").split("\n")[0],
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def pulls_to_df(pulls: list) -> pd.DataFrame:
    rows = []
    for p in pulls:
        rows.append({
            "number": p.get("number"),
            "title": p.get("title"),
            "user": (p.get("user") or {}).get("login"),
            "state": p.get("state"),
            "created_at": p.get("created_at"),
            "closed_at": p.get("closed_at"),
            "merged_at": p.get("merged_at"),
        })
    df = pd.DataFrame(rows)
    for col in ["created_at", "closed_at", "merged_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


def issues_to_df(issues: list) -> pd.DataFrame:
    # Exclude items that are actually PRs (GitHub's /issues includes them)
    rows = []
    for i in issues:
        if "pull_request" in i:
            continue
        rows.append({
            "number": i.get("number"),
            "title": i.get("title"),
            "user": (i.get("user") or {}).get("login"),
            "state": i.get("state"),
            "created_at": i.get("created_at"),
            "closed_at": i.get("closed_at"),
            "labels": [l.get("name") for l in i.get("labels", [])],
        })
    df = pd.DataFrame(rows)
    for col in ["created_at", "closed_at"]:
        if col in df.columns and not df.empty:
            df[col] = pd.to_datetime(df[col])
    return df


def commit_frequency(commits_df: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    """Commits grouped by time period (default weekly).
    freq accepts 'D' (day), 'W' (week), or 'M' (month) as shorthand;
    internally 'M' is mapped to pandas' 'ME' (month-end) alias."""
    freq = {"M": "ME"}.get(freq, freq)
    if commits_df.empty:
        return pd.DataFrame(columns=["period", "commit_count"])
    grouped = (
        commits_df.set_index("date")
        .resample(freq)
        .size()
        .reset_index(name="commit_count")
        .rename(columns={"date": "period"})
    )
    return grouped


def contributor_concentration(commits_df: pd.DataFrame) -> pd.DataFrame:
    """% of total commits made by each contributor, sorted descending."""
    if commits_df.empty:
        return pd.DataFrame(columns=["author", "commits", "pct_of_total"])
    counts = commits_df["author_login"].fillna("(unknown)").value_counts().reset_index()
    counts.columns = ["author", "commits"]
    total = counts["commits"].sum()
    counts["pct_of_total"] = (counts["commits"] / total * 100).round(2)
    return counts


def bus_factor(concentration_df: pd.DataFrame, threshold_pct: float = 50.0) -> int:
    """Smallest number of top contributors whose combined commits reach
    threshold_pct of all commits. A bus factor of 1 or 2 signals the
    project is risky if a couple of contributors leave."""
    if concentration_df.empty:
        return 0
    cumulative = concentration_df["pct_of_total"].cumsum()
    hit = cumulative[cumulative >= threshold_pct]
    if hit.empty:
        return len(concentration_df)
    return int(hit.index[0]) + 1


def pr_merge_times(pulls_df: pd.DataFrame) -> pd.DataFrame:
    """Time-to-merge (in hours) for merged PRs."""
    if pulls_df.empty:
        return pd.DataFrame(columns=["number", "merge_time_hours"])
    merged = pulls_df.dropna(subset=["merged_at"]).copy()
    if merged.empty:
        return pd.DataFrame(columns=["number", "merge_time_hours"])
    merged["merge_time_hours"] = (
        (merged["merged_at"] - merged["created_at"]).dt.total_seconds() / 3600
    ).round(2)
    return merged[["number", "title", "created_at", "merged_at", "merge_time_hours"]]


def issue_resolution_times(issues_df: pd.DataFrame) -> pd.DataFrame:
    """Time-to-close (in hours) for closed issues."""
    if issues_df.empty:
        return pd.DataFrame(columns=["number", "resolution_time_hours"])
    closed = issues_df.dropna(subset=["closed_at"]).copy()
    if closed.empty:
        return pd.DataFrame(columns=["number", "resolution_time_hours"])
    closed["resolution_time_hours"] = (
        (closed["closed_at"] - closed["created_at"]).dt.total_seconds() / 3600
    ).round(2)
    return closed[["number", "title", "created_at", "closed_at", "resolution_time_hours"]]


def summary_stats(commits_df, pulls_df, issues_df) -> dict:
    """One-shot dict of headline numbers for the dashboard's top cards."""
    concentration = contributor_concentration(commits_df)
    merge_times = pr_merge_times(pulls_df)
    resolution_times = issue_resolution_times(issues_df)

    return {
        "total_commits": len(commits_df),
        "unique_contributors": commits_df["author_login"].nunique() if not commits_df.empty else 0,
        "bus_factor": bus_factor(concentration),
        "total_prs": len(pulls_df),
        "merged_prs": pulls_df["merged_at"].notna().sum() if not pulls_df.empty else 0,
        "median_merge_hours": round(merge_times["merge_time_hours"].median(), 1) if not merge_times.empty else None,
        "total_issues": len(issues_df),
        "closed_issues": (issues_df["state"] == "closed").sum() if not issues_df.empty else 0,
        "median_resolution_hours": round(resolution_times["resolution_time_hours"].median(), 1) if not resolution_times.empty else None,
    }
