import os

import requests
from dotenv import load_dotenv

from utils import band_for_months, load_records, months_since, save_records

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDS_PATH = os.path.join(SCRIPT_DIR, "..", "data", "records.json")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
ALERT_RECIPIENTS = ["obowen@vccp.com"]
FROM_ADDRESS = "CMO Carousel <onboarding@resend.dev>"

ALERT_BANDS = {"amber", "red"}
BAND_LABEL = {"amber": "Prime window", "red": "Past prime"}


def find_new_alerts(records):
    """Mutates each record's alerted_bands in place, returns only the newly-crossed ones."""
    new_alerts = []
    for r in records:
        months = months_since(r.get("start_date"))
        band = band_for_months(months)
        alerted = r.setdefault("alerted_bands", [])
        if band in ALERT_BANDS and band not in alerted:
            new_alerts.append({**r, "months_since_start": months, "band": band})
            alerted.append(band)
    return new_alerts


def build_email_html(alerts):
    rows = ""
    for a in alerts:
        rows += (
            "<tr>"
            f"<td>{a.get('person_name') or 'Unknown'}</td>"
            f"<td>{a.get('new_company') or '-'}</td>"
            f"<td>{a.get('sector_guess') or '-'}</td>"
            f"<td>{a['months_since_start']} months</td>"
            f"<td>{BAND_LABEL[a['band']]}</td>"
            f"<td>{a.get('current_incumbent_agency') or '-'}</td>"
            "</tr>"
        )
    return f"""
    <h2>CMO Carousel &ndash; new trigger alerts</h2>
    <p>{len(alerts)} account(s) just entered the pitching window:</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
      <tr><th>Person</th><th>Company</th><th>Sector</th><th>Months since start</th><th>Status</th><th>Agency</th></tr>
      {rows}
    </table>
    """


def send_email(html):
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": FROM_ADDRESS,
            "to": ALERT_RECIPIENTS,
            "subject": "CMO Carousel: new trigger alerts",
            "html": html,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    records = load_records(RECORDS_PATH)
    new_alerts = find_new_alerts(records)

    if not new_alerts:
        print("No new alerts today.")
        return

    result = send_email(build_email_html(new_alerts))
    print(f"Sent alert email for {len(new_alerts)} record(s). Resend id: {result.get('id')}")

    save_records(RECORDS_PATH, records)


if __name__ == "__main__":
    main()
