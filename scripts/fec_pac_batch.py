"""Resumable AIPAC PAC Schedule B ingestion, with bounded pages per run.

Stages raw Schedule B transactions without making any per-recipient FEC lookups.
Existing rows are not overwritten; financial review decisions are preserved.
Checkpoint is advanced only after each page's records have been persisted.
"""
import os
import time
from fec_ingest import Database, fec_get

SOURCE = "aipac_pac_schedule_b"
COMMITTEE = "C00797670"
MAX_PAGES = max(1, min(int(os.getenv("MAX_PAGES", "3")), 10))


def main():
    required = ("FEC_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit("Missing secrets: " + ", ".join(missing))
    cycle = int(os.getenv("ELECTION_CYCLE", "2026"))
    db = Database()
    db.check()
    checkpoint_response = db.session.get(
        db.url + "/fec_import_checkpoints",
        params={"source": "eq." + SOURCE, "election_cycle": "eq." + str(cycle), "select": "*"},
        timeout=30,
    )
    checkpoint_response.raise_for_status()
    entries = checkpoint_response.json()
    checkpoint = entries[0] if entries else {
        "source": SOURCE, "election_cycle": cycle, "cursor": {},
        "pages_completed": 0, "rows_seen": 0, "rows_staged": 0, "completed": False
    }
    if checkpoint["completed"]:
        print("Import already complete for this cycle; no action required.", flush=True)
        return
    cursor = checkpoint.get("cursor") or {}
    seen = set()
    for page_number in range(MAX_PAGES):
        params = {"committee_id": COMMITTEE, "cycle": cycle, "per_page": 100, **cursor}
        payload = fec_get("/schedules/schedule_b/", params)
        rows = payload.get("results", [])
        if not rows:
            finished = True
            next_cursor = cursor
        else:
            next_cursor = payload.get("pagination", {}).get("last_indexes") or {}
            finished = not bool(next_cursor)
            marker = tuple(sorted((str(k), str(v)) for k, v in next_cursor.items()))
            if not finished and (next_cursor == cursor or marker in seen):
                raise RuntimeError("Repeated FEC cursor; checkpoint was not advanced")
            seen.add(marker)
        records = []
        for item in rows:
            image = item.get("image_number")
            transaction = item.get("transaction_id")
            amount = item.get("disbursement_amount")
            if not (image and transaction and amount is not None):
                continue
            description = str(item.get("disbursement_description") or "").upper()
            category = "earmarked_conduit" if description.startswith("EARMARK") else "other"
            records.append({
                "source_system": "fec",
                "source_record_id": str(image),
                "source_sub_id": str(transaction),
                "fec_committee_id": COMMITTEE,
                "election_cycle": cycle,
                "transaction_date": item.get("disbursement_date"),
                "amount": amount,
                "category": category,
                "source_url": f"https://docquery.fec.gov/cgi-bin/fecimg/?{image}",
                "raw_payload": item,
            })
        if records:
            # Ignore duplicates instead of updating records that have already been reviewed.
            response = db.session.post(
                db.url + "/financial_transactions",
                params={"on_conflict": "source_system,source_record_id,source_sub_id"},
                headers={"Prefer": "resolution=ignore-duplicates,return=minimal"},
                json=records,
                timeout=60,
            )
            if not response.ok:
                raise RuntimeError(f"Transaction staging failed: HTTP {response.status_code}")
        checkpoint["pages_completed"] += 1
        checkpoint["rows_seen"] += len(rows)
        checkpoint["rows_staged"] += len(records)
        checkpoint["cursor"] = next_cursor
        checkpoint["completed"] = finished
        checkpoint["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        db.upsert("fec_import_checkpoints", [checkpoint], "source,election_cycle")
        print(f"Page {checkpoint['pages_completed']}: {len(rows)} fetched, {len(records)} eligible, checkpoint saved", flush=True)
        cursor = next_cursor
        if finished:
            print("Reached end of FEC Schedule B results.", flush=True)
            break
    print(f"Batch finished. pages={checkpoint['pages_completed']} rows_seen={checkpoint['rows_seen']} complete={checkpoint['completed']}", flush=True)


if __name__ == "__main__":
    main()
