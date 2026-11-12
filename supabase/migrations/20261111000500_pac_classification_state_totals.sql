update public.financial_transactions set category='other'
where fec_committee_id='C00797670' and reconciliation_status='pending'
and upper(coalesce(raw_payload->>'disbursement_description','')) like 'VOID%';
update public.financial_transactions set category='direct_pac'
where fec_committee_id='C00797670' and reconciliation_status='pending'
and upper(trim(coalesce(raw_payload->>'disbursement_description','')))='CONTRIBUTION TO COMMITTEE';
create or replace view public.verified_state_spending with (security_invoker=true) as
select t.election_cycle,c.state,t.category,t.fec_committee_id,
count(*)::integer as transaction_count,sum(t.amount) as amount
from public.financial_transactions t join public.candidates c on c.fec_candidate_id=t.fec_candidate_id
where t.reconciliation_status='verified' and not t.is_superseded and c.state ~ '^[A-Z]{2}$'
group by t.election_cycle,c.state,t.category,t.fec_committee_id;
grant select on public.verified_state_spending to anon,authenticated;
