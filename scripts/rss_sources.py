from urllib.parse import quote_plus

SECTORS = {
    "FMCG": [
        '"chief marketing officer" OR "marketing director" appointed FMCG when:1d',
        '"chief marketing officer" OR "marketing director" appointed "consumer goods" when:1d',
    ],
    "Financial Services": [
        '"chief marketing officer" OR "marketing director" appointed bank OR insurer when:1d',
    ],
    "Tech": [
        '"chief marketing officer" OR "marketing director" appointed tech OR software when:1d',
    ],
    "Telecoms": [
        '"chief marketing officer" OR "marketing director" appointed telecom OR telco when:1d',
    ],
}

EDITIONS = [
    {"hl": "en-GB", "gl": "GB", "ceid": "GB:en"},  # UK edition
    {"hl": "en-US", "gl": "US", "ceid": "US:en"},  # broader English-language coverage
]

# General trade-press feeds, not sector/query-specific - Claude still judges
# relevance and sector per article same as with Google News results. Each is
# fetched in its own try/except in fetch_and_extract.py so a dead feed (The
# Drum and PRWeek block automated RSS access; Marketing Week does too) can't
# take down the rest of the run.
TRADE_PRESS_FEEDS = {
    "Campaign UK": "https://www.campaignlive.co.uk/rss/news",
    "Adweek": "https://www.adweek.com/feed/",
}


def build_rss_url(query: str, edition: dict) -> str:
    q = quote_plus(query)
    return (
        f"https://news.google.com/rss/search?q={q}"
        f"&hl={edition['hl']}&gl={edition['gl']}&ceid={edition['ceid']}"
    )
