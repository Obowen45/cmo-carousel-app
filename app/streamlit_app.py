import io
import json
import math
import os
import sys
import tempfile
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(SCRIPT_DIR, "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from utils import (  # noqa: E402
    BAND_SCORE_LABEL,
    UNMAPPED_LABEL,
    band_for_months,
    enrich_with_agency,
    guess_domain,
    initials_for,
    load_agency_mapping,
    load_domain_overrides,
    load_records,
    months_since,
    normalize_company,
    vulnerability_percent,
)

RECORDS_PATH = os.path.join(SCRIPT_DIR, "..", "data", "records.json")
MAPPING_PATH = os.path.join(SCRIPT_DIR, "..", "data", "agency_mapping.csv")

BAND_COLOR = {"green": "#22c55e", "amber": "#f5a623", "red": "#ef4444", "unknown": "#8b93a1"}
CARDS_PER_PAGE = 4

st.set_page_config(page_title="CMO Carousel | VCCP New Business Hub", layout="wide")


def get_secret(name):
    try:
        value = st.secrets[name]
    except (KeyError, FileNotFoundError):
        return None
    if isinstance(value, str):
        # Strip whitespace and any non-ASCII characters (e.g. smart quotes
        # introduced by copy-pasting into a web form) that would otherwise
        # crash the underlying HTTP request with a UnicodeEncodeError.
        value = value.strip().encode("ascii", "ignore").decode("ascii")
    return value or None


def fetch_private_file(path_in_repo):
    """Fetch a file from the private data repo via the GitHub API, if secrets
    are configured (deployed use). Returns None when not configured or on any
    failure, so the caller falls back to reading the local data/ folder
    (local dev use) - a broken secret should degrade gracefully, not crash
    the whole app."""
    token = get_secret("GITHUB_DATA_TOKEN")
    repo = get_secret("GITHUB_DATA_REPO")
    if not token or not repo:
        return None
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/contents/{path_in_repo}",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.raw"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


@st.cache_data(ttl=300)
def load_data():
    records_text = fetch_private_file("data/records.json")
    records = json.loads(records_text) if records_text is not None else load_records(RECORDS_PATH)

    mapping_text = fetch_private_file("data/agency_mapping.csv")
    if mapping_text is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(mapping_text)
            mapping_path = f.name
    else:
        mapping_path = MAPPING_PATH

    mapping = load_agency_mapping(mapping_path)
    domain_overrides = load_domain_overrides(mapping_path)
    if mapping_text is not None:
        os.unlink(mapping_path)

    records = enrich_with_agency(records, mapping)
    for r in records:
        r["domain"] = domain_overrides.get(normalize_company(r.get("new_company"))) or guess_domain(
            r.get("new_company")
        )
    return pd.DataFrame(records)


def favicon_url(domain):
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"


@st.cache_data(ttl=60 * 60 * 24)
def logo_exists(domain):
    # Clearbit's old free logo API (logo.clearbit.com) has been shut down -
    # Google's favicon service is a live, free replacement, at lower resolution.
    if not domain:
        return False
    try:
        resp = requests.get(favicon_url(domain), timeout=3)
        return resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image")
    except requests.RequestException:
        return False


@st.cache_data(ttl=300)
def last_updated_text():
    token = get_secret("GITHUB_DATA_TOKEN")
    repo = get_secret("GITHUB_DATA_REPO")
    if token and repo:
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo}/commits",
                headers={"Authorization": f"token {token}"},
                params={"path": "data/records.json", "per_page": 1},
                timeout=10,
            )
            resp.raise_for_status()
            commits = resp.json()
            if commits:
                commit_date = commits[0]["commit"]["committer"]["date"]
                dt = datetime.strptime(commit_date, "%Y-%m-%dT%H:%M:%SZ")
                return dt.strftime("%b %d, %Y - %H:%M GMT")
            return "never"
        except Exception:
            return "unavailable"

    try:
        ts = os.path.getmtime(RECORDS_PATH)
        return datetime.fromtimestamp(ts).strftime("%b %d, %Y - %H:%M")
    except FileNotFoundError:
        return "never"


st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
.block-container { padding-top: 2rem; }
.app-header h1 {
    font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 0;
}
.app-header h1 .brand { color: #ffc931; }
.app-header h1 .sub { color: #8a8a8a; font-weight: 400; font-size: 1.1rem; }
.app-header p { color: #8a8a8a; margin-top: 0.15rem; }

.cmo-card {
    background: #141414;
    border-radius: 16px;
    padding: 1.25rem 1.25rem 1rem 1.25rem;
    border: 1px solid #2a2a2a;
    height: 100%;
}
.cmo-card-top { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.9rem; }
.cmo-avatar {
    position: relative;
    width: 44px; height: 44px; border-radius: 50%;
    background: #ffc931; color: #000;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.95rem; flex-shrink: 0; overflow: hidden;
}
.cmo-avatar img {
    position: absolute; inset: 0;
    width: 100%; height: 100%; object-fit: contain; background: #fff;
}
.cmo-name { font-weight: 700; font-size: 1.02rem; color: #f5f5f5; line-height: 1.2; letter-spacing: -0.01em; }
.cmo-title { color: #8a8a8a; font-size: 0.85rem; }
.cmo-row { display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 0.5rem; color: #d4d4d4; }
.cmo-row span.label { color: #8a8a8a; }
.score-pill { display: inline-flex; align-items: center; gap: 0.4rem; font-weight: 700; }
.score-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
hr.card-divider { border: none; border-top: 1px solid #2a2a2a; margin: 0.75rem 0; }

.needs-mapping-box { background: #141414; border: 1px solid #2a2a2a; border-radius: 12px; padding: 1rem; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="app-header">
<h1><span class="brand">CMO CAROUSEL</span> <span class="sub">| VCCP New Business Hub</span></h1>
<p>Last updated: {last_updated_text()}</p>
</div>
""",
    unsafe_allow_html=True,
)

df = load_data()

if df.empty:
    st.info("No records yet. Run scripts/fetch_and_extract.py to pull in some data.")
    st.stop()

df["months_since_start"] = df["start_date"].apply(months_since)
df["months_since_start"] = df["months_since_start"].astype(object).where(
    df["months_since_start"].notna(), None
)
df["band"] = df["months_since_start"].apply(band_for_months)
df["score_pct"] = df["months_since_start"].apply(vulnerability_percent)

sectors = st.multiselect(
    "Sector", options=sorted(df["sector_guess"].dropna().unique()), default=None
)
if sectors:
    df = df[df["sector_guess"].isin(sectors)]

df = df.sort_values("months_since_start", ascending=False, na_position="last").reset_index(drop=True)

st.subheader("Active CMO Movements")

if "card_page" not in st.session_state:
    st.session_state.card_page = 0

total_pages = max(1, math.ceil(len(df) / CARDS_PER_PAGE))
st.session_state.card_page = min(st.session_state.card_page, total_pages - 1)

nav_prev, nav_label, nav_next = st.columns([1, 6, 1])
with nav_prev:
    if st.button("←", disabled=st.session_state.card_page == 0):
        st.session_state.card_page -= 1
        st.rerun()
with nav_label:
    st.markdown(
        f"<div style='text-align:center;color:#8b93a1;'>Page {st.session_state.card_page + 1} of {total_pages}</div>",
        unsafe_allow_html=True,
    )
with nav_next:
    if st.button("→", disabled=st.session_state.card_page >= total_pages - 1):
        st.session_state.card_page += 1
        st.rerun()

start = st.session_state.card_page * CARDS_PER_PAGE
page_df = df.iloc[start : start + CARDS_PER_PAGE]

card_cols = st.columns(CARDS_PER_PAGE)
for col, (_, row) in zip(card_cols, page_df.iterrows()):
    color = BAND_COLOR[row["band"]]
    score_text = f"{row['score_pct']}% ({BAND_SCORE_LABEL[row['band']]})" if row["score_pct"] is not None else "Unknown"
    months_text = f"{row['months_since_start']} months ago" if row["months_since_start"] is not None else "unknown"
    domain = row.get("domain")
    initials = initials_for(row.get("person_name"))
    # Checked server-side (logo_exists) so the <img> is only ever included
    # when it's known to work - no reliance on client-side onerror JS, which
    # Streamlit's CSP blocks from firing on inline HTML.
    avatar_html = (
        f"<img src='{favicon_url(domain)}'>" if domain and logo_exists(domain) else initials
    )
    with col:
        st.markdown(
            f"""
<div class="cmo-card">
  <div class="cmo-card-top">
    <div class="cmo-avatar">{avatar_html}</div>
    <div>
      <div class="cmo-name">{row['person_name'] or 'Unknown person'}</div>
      <div class="cmo-title">{row['new_title'] or 'Unknown title'}</div>
    </div>
  </div>
  <div class="cmo-row"><span class="label">Company</span><span>{row['new_company'] or '-'}</span></div>
  <div class="cmo-row"><span class="label">Sector</span><span>{row['sector_guess'] or '-'}</span></div>
  <div class="cmo-row"><span class="label">Appointed</span><span>{months_text}</span></div>
  <hr class="card-divider">
  <div class="cmo-row"><span class="label">Vulnerability</span>
    <span class="score-pill"><span class="score-dot" style="background:{color};"></span>{score_text}</span>
  </div>
  <div class="cmo-row"><span class="label">Agency</span><span>{row['current_incumbent_agency']}</span></div>
</div>
""",
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

table_col, chart_col = st.columns([2, 1])

with table_col:
    display_cols = [
        "person_name", "new_company", "sector_guess", "months_since_start",
        "current_incumbent_agency", "score_pct", "band",
    ]
    styled = df[display_cols].rename(columns={
        "person_name": "Person", "new_company": "Company", "sector_guess": "Sector",
        "months_since_start": "Months Since", "current_incumbent_agency": "Agency",
        "score_pct": "Score %", "band": "Band",
    })

    header_col, export_col = st.columns([3, 1])
    with header_col:
        st.subheader("Vulnerability Alerts")
    with export_col:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            styled.to_excel(writer, index=False, sheet_name="Movements")
        st.download_button(
            "Export to Excel",
            data=excel_buffer.getvalue(),
            file_name=f"cmo_carousel_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.dataframe(styled, width="stretch", hide_index=True)

with chart_col:
    st.subheader("Sector Opportunities")
    sector_counts = df["sector_guess"].value_counts()
    st.bar_chart(sector_counts, color="#ffc931")

unmapped = df[df["current_incumbent_agency"] == UNMAPPED_LABEL]["new_company"].dropna().unique()
if len(unmapped):
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(f"⚠️ {len(unmapped)} companies need an agency mapping"):
        st.write(list(unmapped))
