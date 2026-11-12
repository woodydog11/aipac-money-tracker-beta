"""Stage AIPAC PAC Schedule B disbursements with paced, cached FEC lookups.

No records are automatically verified. Only FEC-designated principal campaign
committees with exactly one associated candidate are staged.
"""
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests
from fec_ingest import Database, fec_pages

API = "https://api.open.fec.gov/v1"
MIN_REQUEST_INTERVAL = 0.8
MAX_RETRIES = 6

class FecLookup:
    def __init__(self):
        self.session = requests.Session()
        self.last_request = 0.0
        self.committees = {}
        self.candidates = {}

    def fetch(self, endpoint):
        for attempt in range(MAX_RETRIES):
            elapsed = time.monotonic() - self.last_request
            if elapsed < MIN_REQUEST_INTERVAL:
                time.sleep(MIN_REQUEST_INTERVAL - elapsed)
            self.last_request = time.monotonic()
            response = self.session.get(
                API + endpoint,
                params={"api_key": os.environ["FEC_API_KEY"].strip()},
                timeout=40,
            )
            if response.status_code in (429, 500, 502, 503, 504):
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry_after)
                except ValueError:
                    try:
                        delay = (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
                    except (ValueError, TypeError, OverflowError):
                        delay = min(2 ** attempt * 5, 120)
                delay = max(1, min(delay, 180))
                print(f"FEC temporary HTTP {response.status_code}; waiting {delay:.0f}s before retry {attempt+1}/{MAX_RETRIES}", flush=True)
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response.json().get("results", [])
        raise RuntimeError(f"FEC API retries exhausted for {endpoint}; import stopped safely")

    def committee(self, cid):
        if cid not in self.committees:
            results = self.fetch("/committee/" + cid + "/")
            self.committees[cid] = results[0] if results else None
        return self.committees[cid]

    def candidate(self, cid):
        if cid not in self.candidates:
            results = self.fetch("/candidate/" + cid + "/")
            self.candidates[cid] = results[0] if results else None
        return self.candidates[cid]


def main():
    for name in ("FEC_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if not os.getenv(name):
            raise SystemExit("Missing secret: " + name)
    db = Database()
    db.check()
    fec = FecLookup()
    cycle = int(os.getenv("ELECTION_CYCLE", "2026"))
    rows = []
    scanned = eligible = 0
    for item in fec_pages("/schedules/schedule_b/", {"committee_id": "C00797670", "cycle": cycle}):
        scanned += 1
        recipient = item.get("recipient_committee_id")
        image = item.get("image_number")
        tid = item.get("transaction_id")
        amount = item.get("disbursement_amount")
        if not (recipient and image and tid and amount is not None):
            continue
        cm = fec.committee(str(recipient))
        if not cm or cm.get("designation") != "P":
            continue
        candidate_ids = cm.get("candidate_ids") or []
        if len(candidate_ids) != 1:
            continue
        cid = candidate_ids[0]
        candidate = fec.candidate(cid)
        if not candidate:
            continue
        db.upsert("candidates", [{
            "fec_candidate_id": cid,
            "name": candidate.get("name") or cid,
            "party": candidate.get("party_full") or candidate.get("party"),
            "state": candidate.get("state"),
            "office": candidate.get("office_full") or candidate.get("office"),
            "district": candidate.get("district"),
        }], "fec_candidate_id")
        rows.append({
            "source_record_id": str(image),
            "source_sub_id": str(tid),
            "fec_committee_id": "C00797670",
            "fec_candidate_id": cid,
            "election_cycle": cycle,
            "transaction_date": item.get("disbursement_date"),
            "amount": amount,
            "category": "direct_pac",
            "source_url": f"https://docquery.fec.gov/cgi-bin/fecimg/?{image}",
            "raw_payload": item,
        })
        eligible += 1
        if len(rows) >= 100:
            db.upsert("financial_transactions", rows, "source_system,source_record_id,source_sub_id")
            rows = []
    db.upsert("financial_transactions", rows, "source_system,source_record_id,source_sub_id")
    print(f"Schedule B scanned: {scanned}; candidate-committee disbursements staged: {eligible}")
    print(f"Unique committee lookups: {len(fec.committees)}; candidate lookups: {len(fec.candidates)}")
    print("Records remain PENDING until receiving-committee reconciliation.")

if __name__ == "__main__":
    main()
