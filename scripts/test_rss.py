import feedparser
from rss_sources import SECTORS, EDITIONS, build_rss_url

for sector, queries in SECTORS.items():
    print(f"\n=== {sector} ===")
    seen = 0
    for query in queries:
        for edition in EDITIONS:
            url = build_rss_url(query, edition)
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if seen >= 5:
                    break
                print(f"- {entry.title}")
                seen += 1
            if seen >= 5:
                break
        if seen >= 5:
            break
