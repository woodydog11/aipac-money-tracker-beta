"""Stage AIPAC PAC Schedule B candidate-committee disbursements for review.
No candidate is inferred from recipient name. Only explicit recipient committee IDs
matched to a verified principal campaign committee are eligible.
Never mark imports verified automatically.
"""
import os
import requests
from fec_ingest import Database, fec_pages

def main():
    for name in ("FEC_API_KEY","SUPABASE_URL","SUPABASE_SERVICE_ROLE_KEY"):
        if not os.getenv(name):
            raise SystemExit("Missing secret: "+name)
    db=Database()
    db.check()
    cycle=int(os.getenv("ELECTION_CYCLE","2026"))
    rows=[]
    scanned=0
    eligible=0
    for item in fec_pages("/schedules/schedule_b/",{"committee_id":"C00797670","cycle":cycle}):
        scanned+=1
        recipient=item.get("recipient_committee_id")
        image=item.get("image_number")
        tid=item.get("transaction_id")
        amount=item.get("disbursement_amount")
        if not (recipient and image and tid and amount is not None):
            continue
        # Resolve recipient committee using FEC principal campaign committee details.
        response=requests.get("https://api.open.fec.gov/v1/committee/"+str(recipient)+"/",
            params={"api_key":os.environ["FEC_API_KEY"].strip()},timeout=40)
        response.raise_for_status()
        committees=response.json().get("results",[])
        if not committees:
            continue
        cm=committees[0]
        if cm.get("designation")!="P":
            continue
        candidate_ids=cm.get("candidate_ids") or []
        if len(candidate_ids)!=1:
            continue
        cid=candidate_ids[0]
        # Obtain a real candidate name rather than overwriting existing names with IDs.\n        candidate_response=requests.get("https://api.open.fec.gov/v1/candidate/"+str(cid)+"/",\n            params={"api_key":os.environ["FEC_API_KEY"].strip()},timeout=40)\n        candidate_response.raise_for_status()\n        candidate_records=candidate_response.json().get("results",[])\n        if not candidate_records:\n            continue\n        candidate=candidate_records[0]\n        db.upsert("candidates",[{"fec_candidate_id":cid,"name":candidate.get("name") or cid,\n            "party":candidate.get("party_full") or candidate.get("party"),\n            "state":candidate.get("state"),"office":candidate.get("office_full") or candidate.get("office"),\n            "district":candidate.get("district")}],"fec_candidate_id")
        rows.append({
            "source_record_id":str(image),
            "source_sub_id":str(tid),
            "fec_committee_id":"C00797670",
            "fec_candidate_id":cid,
            "election_cycle":cycle,
            "transaction_date":item.get("disbursement_date"),
            "amount":amount,
            "category":"direct_pac",
            "source_url":f"https://docquery.fec.gov/cgi-bin/fecimg/?{image}",
            "raw_payload":item,
        })
        eligible+=1
        if len(rows)>=100:
            db.upsert("financial_transactions",rows,"source_system,source_record_id,source_sub_id")
            rows=[]
    db.upsert("financial_transactions",rows,"source_system,source_record_id,source_sub_id")
    print(f"Schedule B scanned: {scanned}; staged candidate-committee disbursements: {eligible}")
    print("Records are PENDING; classification and receiving-committee reconciliation required.")

if __name__=="__main__":
    main()
