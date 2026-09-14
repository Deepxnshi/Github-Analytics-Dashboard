"""
app.py
Streamlit dashboard for GitHub Repository & Open-Source Contribution Analytics.
Includes a custom visual theme (ink-navy background, serif headings,
monospace data, single brass accent) inline — no separate theme file needed.

Usage:
    streamlit run app.py
"""

import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import (
    commits_to_df,
    pulls_to_df,
    issues_to_df,
    commit_frequency,
    contributor_concentration,
    bus_factor,
    pr_merge_times,
    issue_resolution_times,
    summary_stats,
)
from github_client import GitHubClient

DATA_DIR = "data"

# ---------------------------------------------------------------------------
# Theme: colors, fonts, and CSS injected directly (no separate theme.py)
# ---------------------------------------------------------------------------
INK = "#14171F"
PANEL = "#1B1F2A"
TEXT = "#EDEAE2"
MUTED = "#9099AC"
ACCENT = "#C9A227"
LINE = "rgba(237, 234, 226, 0.10)"

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'JetBrains Mono', monospace;
}}

.stApp {{
    background-color: {INK};
    color: {TEXT};
}}

/* Headings use the serif — this is the one place personality lives */
h1, h2, h3 {{
    font-family: 'Source Serif 4', serif;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: {TEXT};
}}

h1 {{
    font-size: 2.1rem;
    border-bottom: 1px solid {LINE};
    padding-bottom: 0.6rem;
    margin-bottom: 0.3rem;
}}

[data-testid="stCaptionContainer"] {{
    color: {MUTED};
    font-size: 0.85rem;
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background-color: {PANEL};
    border-right: 1px solid {LINE};
}}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] label {{
    color: {TEXT} !important;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
}}

/* Metrics — flatten into a ledger row, remove the boxed-card look */
[data-testid="stMetric"] {{
    background-color: transparent;
    border: none;
    border-left: 1px solid {LINE};
    padding-left: 1rem;
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED};
    font-size: 0.78rem;
    font-weight: 400;
}}
[data-testid="stMetricValue"] {{
    color: {TEXT};
    font-family: 'Source Serif 4', serif;
    font-size: 1.7rem;
}}

/* Tabs — underline indicator instead of the default pill background */
.stTabs [data-baseweb="tab-list"] {{
    gap: 1.5rem;
    border-bottom: 1px solid {LINE};
}}
.stTabs [data-baseweb="tab"] {{
    background-color: transparent;
    color: {MUTED};
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    padding: 0.5rem 0;
}}
.stTabs [aria-selected="true"] {{
    color: {ACCENT} !important;
    border-bottom: 2px solid {ACCENT};
    background-color: transparent !important;
}}

/* Buttons — one deliberate use of the accent */
.stButton > button {{
    background-color: transparent;
    color: {ACCENT};
    border: 1px solid {ACCENT};
    border-radius: 2px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    padding: 0.4rem 1rem;
}}
.stButton > button:hover {{
    background-color: {ACCENT};
    color: {INK};
}}

/* Dataframes / tables */
[data-testid="stDataFrame"] {{
    border: 1px solid {LINE};
}}

/* Radio & select labels */
.stRadio label, .stSelectbox label, .stSlider label {{
    color: {MUTED} !important;
    font-size: 0.8rem;
}}

.block-container {{
    padding-top: 2.5rem;
}}

hr {{
    border-color: {LINE};
}}
</style>
"""


def style_fig(fig):
    """Apply the same ink/serif/brass identity to a Plotly figure."""
    fig.update_layout(
        paper_bgcolor=INK,
        plot_bgcolor=INK,
        font=dict(family="JetBrains Mono, monospace", color=TEXT, size=12),
        title_font=dict(family="Source Serif 4, serif", color=TEXT, size=18),
        colorway=[ACCENT, "#7B8794", "#4F8F7B", "#9099AC"],
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(gridcolor=LINE, zerolinecolor=LINE, color=MUTED),
        yaxis=dict(gridcolor=LINE, zerolinecolor=LINE, color=MUTED),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Repository Analytics", page_icon="◆", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.title("Repository Analytics")
st.caption("Commit activity, contributor concentration, and review velocity, computed directly from the GitHub API")


def list_cached_repos():
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(
        d for d in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, d))
    )


def load_json(repo_key: str, filename: str):
    path = os.path.join(DATA_DIR, repo_key, filename)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


# --- Sidebar: choose or fetch a repo ---
st.sidebar.header("Repository")
cached = list_cached_repos()

mode = st.sidebar.radio("Source", ["Use cached repo", "Fetch new repo"])

repo_key = None

if mode == "Use cached repo":
    if not cached:
        st.sidebar.warning("No cached repos yet. Switch to 'Fetch new repo', "
                            "or run `python fetch_data.py --owner X --repo Y` first.")
    else:
        repo_key = st.sidebar.selectbox("Choose a repo", cached)

else:
    owner = st.sidebar.text_input("Owner/org", value="pallets")
    repo = st.sidebar.text_input("Repo name", value="flask")
    max_pages = st.sidebar.slider("Pages to fetch per endpoint (100 items/page)", 1, 10, 3)
    if st.sidebar.button("Fetch from GitHub", type="primary"):
        with st.spinner(f"Fetching {owner}/{repo} from GitHub API..."):
            client = GitHubClient()
            key = f"{owner}_{repo}"
            repo_dir = os.path.join(DATA_DIR, key)
            os.makedirs(repo_dir, exist_ok=True)

            repo_info = client.get_repo(owner, repo)
            with open(os.path.join(repo_dir, "repo.json"), "w") as f:
                json.dump(repo_info, f)

            commits = client.get_commits(owner, repo, max_pages=max_pages)
            with open(os.path.join(repo_dir, "commits.json"), "w") as f:
                json.dump(commits, f)

            pulls = client.get_pull_requests(owner, repo, max_pages=max_pages)
            with open(os.path.join(repo_dir, "pulls.json"), "w") as f:
                json.dump(pulls, f)

            issues = client.get_issues(owner, repo, max_pages=max_pages)
            with open(os.path.join(repo_dir, "issues.json"), "w") as f:
                json.dump(issues, f)

            repo_key = key
        st.sidebar.success(f"Fetched {owner}/{repo}")

if not repo_key:
    st.info("Choose a cached repo, or fetch a new one from the sidebar to get started.")
    st.stop()

# --- Load & process data ---
repo_info = load_json(repo_key, "repo.json")
commits_raw = load_json(repo_key, "commits.json")
pulls_raw = load_json(repo_key, "pulls.json")
issues_raw = load_json(repo_key, "issues.json")

commits_df = commits_to_df(commits_raw)
pulls_df = pulls_to_df(pulls_raw)
issues_df = issues_to_df(issues_raw)

if repo_info:
    st.subheader(f"{repo_info.get('full_name', repo_key)}")
    st.write(repo_info.get("description") or "")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stars", f"{repo_info.get('stargazers_count', 0):,}")
    c2.metric("Forks", f"{repo_info.get('forks_count', 0):,}")
    c3.metric("Watchers", f"{repo_info.get('watchers_count', 0):,}")
    c4.metric("Open issues", f"{repo_info.get('open_issues_count', 0):,}")

stats = summary_stats(commits_df, pulls_df, issues_df)

st.markdown("#### Headline metrics")
st.caption("From the cached page window fetched for this repo")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Commits fetched", stats["total_commits"])
m2.metric("Contributors", stats["unique_contributors"])
m3.metric("Bus factor", stats["bus_factor"], help="Fewest top contributors covering ≥50% of commits")
m4.metric("Median PR merge time", f"{stats['median_merge_hours']} hrs" if stats["median_merge_hours"] is not None else "—")
m5.metric("Median issue resolution", f"{stats['median_resolution_hours']} hrs" if stats["median_resolution_hours"] is not None else "—")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Commit activity", "Contributors", "Pull requests", "Issues"]
)

with tab1:
    st.subheader("Commit frequency over time")
    freq_choice = st.radio("Group by", ["D", "W", "M"], index=1, horizontal=True,
                            format_func=lambda x: {"D": "Day", "W": "Week", "M": "Month"}[x])
    freq_df = commit_frequency(commits_df, freq=freq_choice)
    if freq_df.empty:
        st.write("No commit data.")
    else:
        fig = px.line(freq_df, x="period", y="commit_count", markers=True,
                       title="Commits over time")
        st.plotly_chart(style_fig(fig), use_container_width=True)

with tab2:
    st.subheader("Contributor concentration")
    conc_df = contributor_concentration(commits_df)
    if conc_df.empty:
        st.write("No contributor data.")
    else:
        top_n = st.slider("Show top N contributors", 3, min(20, len(conc_df)), min(10, len(conc_df)))
        fig = px.bar(conc_df.head(top_n), x="author", y="pct_of_total",
                     title="% of commits by contributor", text="commits")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.caption(
            f"Bus factor: {stats['bus_factor']} — this many top contributors "
            "account for at least half of all commits fetched. A low number means "
            "the project depends heavily on very few people."
        )
        st.dataframe(conc_df, use_container_width=True)

with tab3:
    st.subheader("Pull request merge times")
    merge_df = pr_merge_times(pulls_df)
    if merge_df.empty:
        st.write("No merged PR data.")
    else:
        fig = px.histogram(merge_df, x="merge_time_hours", nbins=30,
                            title="Distribution of PR merge times (hours)")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.dataframe(
            merge_df.sort_values("merge_time_hours", ascending=False).head(20),
            use_container_width=True,
        )

with tab4:
    st.subheader("Issue resolution times")
    res_df = issue_resolution_times(issues_df)
    if res_df.empty:
        st.write("No closed issue data.")
    else:
        fig = px.histogram(res_df, x="resolution_time_hours", nbins=30,
                            title="Distribution of issue resolution times (hours)")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.dataframe(
            res_df.sort_values("resolution_time_hours", ascending=False).head(20),
            use_container_width=True,
        )