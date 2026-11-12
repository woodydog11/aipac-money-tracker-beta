-- Auditable read-only views. Apply to dedicated Supabase project.
create or replace view public.transaction_reconciliation_audit with (security_invoker = true) as
select t.id,t.fec_committee_id,t.fec_candidate_id,t.election_cycle,t.category,t.amount,t.transaction_date,t.source_record_id,t.source_sub_id,
 t.raw_payload->>'sub_id' as fec_sub_id,
 t.raw_payload->>'amendment_indicator' as amendment_indicator,
 t.reconciliation_status,t.is_superseded,t.source_url,
 case
 when t.raw_payload->>'amendment_indicator' = 'A' then 'amended_filing_review'
 when t.raw_payload->>'amendment_indicator' not in ('N','A') then 'unknown_amendment_status'
 when t.raw_payload->>'sub_id' is null then 'missing_fec_sub_id'
 when t.fec_candidate_id is null then 'missing_candidate'
 when t.source_url is null then 'missing_source'
 else 'initial_checks_passed'
 end as audit_flag
from public.financial_transactions t;
create or replace view public.verified_candidate_spending with (security_invoker = true) as
select t.election_cycle,t.fec_candidate_id,c.name,c.party,c.state,c.office,t.fec_committee_id,t.category,
count(*)::integer as transaction_count,sum(t.amount) as amount
from public.financial_transactions t
join public.candidates c on c.fec_candidate_id=t.fec_candidate_id
where t.reconciliation_status='verified' and not t.is_superseded
group by t.election_cycle,t.fec_candidate_id,c.name,c.party,c.state,c.office,t.fec_committee_id,t.category;
revoke all on public.transaction_reconciliation_audit from anon,authenticated;
grant select on public.verified_candidate_spending to anon,authenticated;
