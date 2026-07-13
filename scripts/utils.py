from __future__ import annotations

import csv
import json
import re
from datetime import date

SUFFIXES = [" plc", " ltd", " limited", " inc", " llc", " corp", " corporation", " group", " co"]


def normalize_company(name: str | None) -> str:
    if not name:
        return ""
    n = name.lower().strip()
    n = re.sub(r"[.,]", "", n)
    for suffix in SUFFIXES:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return n


def record_key(person_name: str | None, new_company: str | None) -> str:
    return f"{(person_name or '').lower().strip()}|{normalize_company(new_company)}"


def load_records(path: str) -> list[dict]:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_records(path: str, records: list[dict]) -> None:
    records_sorted = sorted(records, key=lambda r: (r.get("new_company") or "", r.get("person_name") or ""))
    with open(path, "w") as f:
        json.dump(records_sorted, f, indent=2, sort_keys=False)
        f.write("\n")


def already_seen(url: str, records: list[dict]) -> bool:
    for r in records:
        if url in r.get("source_urls", []):
            return True
    return False


def merge_record_into_list(records: list[dict], key: str, extracted: dict, source_url: str) -> list[dict]:
    # A key of "|" means neither person_name nor new_company was extracted -
    # never merge on that, or unrelated vague articles would collide into one record.
    for r in records:
        if key != "|" and record_key(r.get("person_name"), r.get("new_company")) == key:
            if source_url not in r.get("source_urls", []):
                r.setdefault("source_urls", []).append(source_url)
            # Fill in any fields that were missing before, without overwriting known values.
            for field in ("new_title", "old_company", "new_company", "start_date", "country_guess"):
                if not r.get(field) and extracted.get(field):
                    r[field] = extracted[field]
            return records

    new_record = {
        "person_name": extracted.get("person_name"),
        "new_title": extracted.get("new_title"),
        "old_company": extracted.get("old_company"),
        "new_company": extracted.get("new_company"),
        "start_date": extracted.get("start_date"),
        "sector_guess": extracted.get("sector_guess"),
        "country_guess": extracted.get("country_guess"),
        "source_urls": [source_url],
    }
    records.append(new_record)
    return records


UNMAPPED_LABEL = "Unknown - needs mapping"


def load_agency_mapping(path: str) -> dict:
    """Returns {normalized_company_name: incumbent_agency}."""
    mapping = {}
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                agency = (row.get("incumbent_agency") or "").strip()
                if agency:
                    mapping[normalize_company(row.get("company_name"))] = agency
    except FileNotFoundError:
        pass
    return mapping


def enrich_with_agency(records: list[dict], mapping: dict) -> list[dict]:
    for r in records:
        r["current_incumbent_agency"] = mapping.get(
            normalize_company(r.get("new_company")), UNMAPPED_LABEL
        )
    return records


def months_since(start_date_str: str | None) -> int | None:
    if not start_date_str:
        return None
    try:
        start = date.fromisoformat(start_date_str)
    except ValueError:
        return None
    today = date.today()
    months = (today.year - start.year) * 12 + (today.month - start.month)
    if today.day < start.day:
        months -= 1
    return max(months, 0)


def band_for_months(months: int | None) -> str:
    if months is None:
        return "unknown"
    if months < 6:
        return "green"
    if months <= 12:
        return "amber"
    return "red"


BAND_SCORE_LABEL = {"green": "Low", "amber": "Med", "red": "High", "unknown": "Unknown"}


def vulnerability_percent(months: int | None) -> int | None:
    if months is None:
        return None
    return int(min(100, round(months / 15 * 100)))


def guess_domain(company_name: str | None) -> str | None:
    """Best-effort .com domain guess from a company name, for logo lookups.

    Works for simple single-word names (Unilever -> unilever.com) but not
    multi-word or abbreviated real names (Procter & Gamble) - correct those
    via a 'domain' column in agency_mapping.csv rather than here.
    """
    if not company_name:
        return None
    slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
    return f"{slug}.com" if slug else None


def load_domain_overrides(path: str) -> dict:
    """Returns {normalized_company_name: domain} from an optional 'domain' column."""
    overrides = {}
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                domain = (row.get("domain") or "").strip()
                if domain:
                    overrides[normalize_company(row.get("company_name"))] = domain
    except FileNotFoundError:
        pass
    return overrides


def initials_for(name: str | None) -> str:
    if not name:
        return "?"
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()
