"""Import FEC data into a dedicated Supabase project via PostgREST.
Supports modern sb_secret_ keys. All financial records remain pending review.
"""
import os
import sys
import time
import requests

FEC_BASE = "https://api.open.fec.gov/v1"

class Database:
    def __init__(self):
        self.url = os.environ["SUPABASE_URL"].strip().rstrip("/") + "/rest/v1"
        self.session = requests.Session()
        # Modern Supabase secret keys are API keys, not JWTs.
        self.session.headers.update({
            "apikey": os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip(),
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        })

    def check(self):
        response = self.session.get(
            self.url + "/organizations",
            params={"select": "fec_committee_id", "limit": 1},
            timeout=30,
        )
        response.raise_for_status()

    def upsert(self, table, records, conflict):
        for offset in range(0, len(records), 100):
            batch = records[offset:offset + 100]
            response = self.session.post(
                self.url + "/" + table,
                params={"on_conflict": conflict},
                json=batch,
                timeout=60,
            )
            if not response.ok:
                # Avoid printing response bodies which might contain sensitive fields.
                raise RuntimeError(f"Supabase {table} upsert returned HTTP {response.status_code}")

def fec_pages(endpoint, params):
    """FEC uses page-number pagination for candidates and cursor pagination for Schedule E."""
    cursor_mode = endpoint == "/schedules/schedule_e/"
    page = 1
    cursor = {}
    seen_cursors = set()
    while True:
        query = {**params, "api_key": os.environ["FEC_API_KEY"].strip(), "per_page": 100}
        if cursor_mode:
            query.update(cursor)
        else:
            query["page"] = page
        response = requests.get(FEC_BASE + endpoint, params=query, timeout=45)
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("results", [])
        if not rows:
            return
        yield from rows
        pagination = payload.get("pagination", {})
        if cursor_mode:
            next_cursor = pagination.get("last_indexes") or {}
            if not next_cursor:
                return
            marker = tuple(sorted((str(k), str(v)) for k, v in next_cursor.items()))
            if marker in seen_cursors:
                raise RuntimeError("FEC cursor repeated; stopping to prevent duplicate pages")
            seen_cursors.add(marker)
            cursor = next_cursor
        else:
            if page >= pagination.get("pages", page):
                return
            page += 1
        time.sleep(0.25)

def ingest_candidates(db, cycle):
    records = []
    count = 0
    for item in fec_pages("/candidates/", {"election_year": cycle}):
        cid = item.get("candidate_id")
        if not cid:
            continue
        records.append({
            "fec_candidate_id": cid,
            "name": item.get("name") or cid,
            "party": item.get("party_full") or item.get("party"),
            "state": item.get("state"),
            "office": item.get("office_full") or item.get("office"),
            "district": item.get("district"),
        })
        if len(records) >= 100:
            db.upsert("candidates", records, "fec_candidate_id")
            count += len(records)
            records = []
    db.upsert("candidates", records, "fec_candidate_id")
    return count + len(records)

def ensure_candidate(db, cid, name):
    db.upsert("candidates", [{"fec_candidate_id": cid, "name": name or cid}], "fec_candidate_id")

def ingest_udp(db, cycle):
    records = []
    count = 0
    for item in fec_pages("/schedules/schedule_e/", {"committee_id": "C00799031", "cycle": cycle}):
        cid = item.get("candidate_id")
        tid = item.get("transaction_id")
        indicator = item.get("support_oppose_indicator")
        amount = item.get("expenditure_amount")
        image = item.get("image_number")
        if not all((cid, tid, image)) or indicator not in ("S", "O") or amount is None:
            continue
        # Some special-election candidates may not appear in a cycle-specific candidate listing.
        ensure_candidate(db, cid, item.get("candidate_name"))
        records.append({
            "source_record_id": str(image),
            "source_sub_id": str(tid),
            "fec_committee_id": "C00799031",
            "fec_candidate_id": cid,
            "election_cycle": cycle,
            "transaction_date": item.get("expenditure_date"),
            "amount": amount,
            "category": "independent_support" if indicator == "S" else "independent_oppose",
            "source_url": f"https://docquery.fec.gov/cgi-bin/fecimg/?{image}",
            "raw_payload": item,
            "reconciliation_status": "pending",
        })
        if len(records) >= 100:
            db.upsert("financial_transactions", records, "source_system,source_record_id,source_sub_id")
            count += len(records)
            records = []
    db.upsert("financial_transactions", records, "source_system,source_record_id,source_sub_id")
    return count + len(records)

def main():
    required = ("FEC_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        sys.exit("Missing required secrets: " + ", ".join(missing))
    cycle = int(os.getenv("ELECTION_CYCLE", "2026"))
    db = Database()
    db.check()
    print("Supabase REST connection established.")
    print("Candidates imported:", ingest_candidates(db, cycle))
    print("UDP independent expenditure rows staged:", ingest_udp(db, cycle))
    print("Financial rows remain pending until source reconciliation.")

if __name__ == "__main__":
    main()
