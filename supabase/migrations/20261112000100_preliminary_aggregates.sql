-- Preliminary read-only aggregates. Not audited, not candidate receipts.
-- The existing verified-only views and transaction RLS policies remain unchanged.
create or replace function public.preliminary_candidate_spending(p_cycle integer)
returns table(fec_candidate_id text,name text,party text,state text,category text,amount numeric,transaction_count bigint)
language sql stable security definer set search_path=public as $$
 select t.fec_candidate_id,c.name,c.party,c.state,t.category,sum(t.amount),count(*)
 from public.financial_transactions t join public.candidates c on c.fec_candidate_id=t.fec_candidate_id
 where t.election_cycle=p_cycle and t.fec_committee_id in ('C00797670','C00799031')
 and t.reconciliation_status='pending' and not t.is_superseded
 and t.category in ('direct_pac','earmarked_conduit','independent_support','independent_oppose')
 and upper(coalesce(t.raw_payload->>'disbursement_description','')) not like 'VOID%'
 group by t.fec_candidate_id,c.name,c.party,c.state,t.category
 order by sum(t.amount) desc $$;
create or replace function public.preliminary_state_spending(p_cycle integer)
returns table(state text,category text,amount numeric,transaction_count bigint)
language sql stable security definer set search_path=public as $$
 select c.state,t.category,sum(t.amount),count(*)
 from public.financial_transactions t join public.candidates c on c.fec_candidate_id=t.fec_candidate_id
 where t.election_cycle=p_cycle and t.fec_committee_id in ('C00797670','C00799031')
 and t.reconciliation_status='pending' and not t.is_superseded
 and t.category in ('direct_pac','earmarked_conduit','independent_support','independent_oppose')
 and upper(coalesce(t.raw_payload->>'disbursement_description','')) not like 'VOID%'
 and c.state ~ '^[A-Z]{2}$'
 group by c.state,t.category $$;
revoke all on function public.preliminary_candidate_spending(integer) from public;
revoke all on function public.preliminary_state_spending(integer) from public;
grant execute on function public.preliminary_candidate_spending(integer) to anon,authenticated;
grant execute on function public.preliminary_state_spending(integer) to anon,authenticated;
