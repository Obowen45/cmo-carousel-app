import os

import feedparser

from extract import extract
from rss_sources import EDITIONS, SECTORS, TRADE_PRESS_FEEDS, build_rss_url
from utils import already_seen, load_records, merge_record_into_list, record_key, save_records

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDS_PATH = os.path.join(SCRIPT_DIR, "..", "data", "records.json")


def process_feed(url, records):
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"Skipping feed (failed to fetch): {url} ({e})")
        return records

    for entry in feed.entries:
        if already_seen(entry.link, records):
            print(f"Skipping already-seen: {entry.title}")
            continue

        extracted = extract(entry.title, entry.get("summary", ""))
        if not extracted.get("is_relevant"):
            continue

        key = record_key(extracted.get("person_name"), extracted.get("new_company"))
        records = merge_record_into_list(records, key, extracted, entry.link)
        print(f"Added/updated: {extracted.get('person_name')} -> {extracted.get('new_company')}")

    return records


def main():
    records = load_records(RECORDS_PATH)
    print(f"Loaded {len(records)} existing records.")

    for sector, queries in SECTORS.items():
        for query in queries:
            for edition in EDITIONS:
                records = process_feed(build_rss_url(query, edition), records)

    for name, url in TRADE_PRESS_FEEDS.items():
        print(f"Checking {name}...")
        records = process_feed(url, records)

    save_records(RECORDS_PATH, records)
    print(f"Saved {len(records)} total records to {RECORDS_PATH}")


if __name__ == "__main__":
    main()
