"""FEC API importer: candidate identity discovery and independent expenditures.
Requires FEC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
Records remain pending until independently reconciled; nothing unverified is public.
"""
import os, sys, time, requests
from supabase import create_client

FEC_BASE='https://api.open.fec.gov/v1'
COMMITTEES=('C00797670','C00799031')

def pages(endpoint, params):
    key=os.environ['FEC_API_KEY']
    page=1
    while True:
        response=requests.get(FEC_BASE+endpoint,params={**params,'api_key':key,'per_page':100,'page':page},timeout=40)
        response.raise_for_status()
        data=response.json()
        yield from data.get('results',[])
        pages_count=data.get('pagination',{}).get('pages',page)
        if page>=pages_count:break
        page+=1
        time.sleep(0.25)

def upsert_chunks(db,table,records,chunk=100):
    for i in range(0,len(records),chunk):
        db.table(table).upsert(records[i:i+chunk]).execute()

def ingest_candidates(db,cycle):
    records=[]
    for item in pages('/candidates/',{'election_year':cycle,'is_active_candidate':'true'}):
        cid=item.get('candidate_id')
        if cid:
            records.append({'fec_candidate_id':cid,'name':item.get('name') or cid,'party':item.get('party_full') or item.get('party'),'state':item.get('state'),'office':item.get('office_full') or item.get('office'),'district':item.get('district')})
    upsert_chunks(db,'candidates',records)
    return len(records)

def ingest_udp_expenditures(db,cycle):
    # API independent expenditure rows; candidate identities must be present before insert.
    records=[]
    for item in pages('/schedules/schedule_e/',{'committee_id':'C00799031','cycle':cycle}):
        candidate_id=item.get('candidate_id')
        transaction_id=item.get('transaction_id')
        support=item.get('support_oppose_indicator')
        amount=item.get('expenditure_amount')
        if not (candidate_id and transaction_id and support in ('S','O') and amount is not None):continue
        # Do not publish without a source filing link and reconciliation.
        image=item.get('image_number')
        if not image:continue
        records.append({'source_record_id':str(image),'source_sub_id':str(transaction_id),'fec_committee_id':'C00799031','fec_candidate_id':candidate_id,'election_cycle':cycle,'transaction_date':item.get('expenditure_date'),'amount':amount,'category':'independent_support' if support=='S' else 'independent_oppose','source_url':f'https://docquery.fec.gov/cgi-bin/fecimg/?{image}','raw_payload':item,'reconciliation_status':'pending'})
        if len(records)>=100:
            upsert_chunks(db,'financial_transactions',records)
            records=[]
    upsert_chunks(db,'financial_transactions',records)

def main():
    missing=[k for k in ('FEC_API_KEY','SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY') if not os.getenv(k)]
    if missing:sys.exit('Missing server-side secrets: '+', '.join(missing))
    db=create_client(os.environ['SUPABASE_URL'],os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    cycle=int(os.getenv('ELECTION_CYCLE','2026'))
    print('Importing candidate identities for',cycle)
    print('Candidates:',ingest_candidates(db,cycle))
    print('Importing UDP independent expenditures as PENDING records')
    ingest_udp_expenditures(db,cycle)
    print('Import complete. Records are not public until reconciled and marked verified.')

if __name__=='__main__':main()
