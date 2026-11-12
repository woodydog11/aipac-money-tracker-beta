-- AIPAC Money Tracker: auditable finance foundation. Run only in a dedicated project.
create table if not exists public.organizations (
 id bigint generated always as identity primary key,
 fec_committee_id text not null unique,
 name text not null,
 organization_type text not null check (organization_type in ('pac','super_pac','other')),
 relationship_class text not null default 'unverified' check (relationship_class in ('direct','documented_network','comparison','unverified')),
 evidence_url text,
 created_at timestamptz not null default now()
);
create table if not exists public.candidates (
 fec_candidate_id text primary key,
 name text not null,
 party text,
 state text,
 office text,
 district text,
 bioguide_id text,
 updated_at timestamptz not null default now()
);
create table if not exists public.fec_filings (
 filing_id text primary key,
 committee_id text,
 report_type text,
 filed_at timestamptz,
 source_url text not null,
 amended_filing_id text,
 ingested_at timestamptz not null default now()
);
create table if not exists public.financial_transactions (
 id bigint generated always as identity primary key,
 source_system text not null default 'fec',
 source_record_id text not null,
 source_sub_id text not null default '',
 fec_committee_id text not null references public.organizations(fec_committee_id),
 fec_candidate_id text references public.candidates(fec_candidate_id),
 filing_id text references public.fec_filings(filing_id),
 election_cycle integer not null,
 transaction_date date,
 amount numeric(16,2) not null,
 category text not null check (category in ('direct_pac','earmarked_conduit','independent_support','independent_oppose','refund','transfer','other')),
 direction text not null default 'outgoing' check (direction in ('incoming','outgoing')),
 memo text,
 source_url text not null,
 is_superseded boolean not null default false,
 reconciliation_status text not null default 'pending' check (reconciliation_status in ('pending','verified','excluded')),
 raw_payload jsonb not null default '{}'::jsonb,
 ingested_at timestamptz not null default now(),
 unique(source_system,source_record_id,source_sub_id)
);
create index if not exists financial_transactions_candidate_cycle_idx on public.financial_transactions(fec_candidate_id,election_cycle,category);
create index if not exists financial_transactions_committee_cycle_idx on public.financial_transactions(fec_committee_id,election_cycle);
create table if not exists public.organization_relationships (
 id bigint generated always as identity primary key,
 source_committee_id text not null references public.organizations(fec_committee_id),
 target_committee_id text not null references public.organizations(fec_committee_id),
 relationship_type text not null,
 evidence_url text not null,
 effective_from date,
 effective_to date,
 review_status text not null default 'pending' check (review_status in ('pending','verified','rejected')),
 unique(source_committee_id,target_committee_id,relationship_type,evidence_url)
);
create table if not exists public.congressional_votes (
 id bigint generated always as identity primary key,
 chamber text not null check (chamber in ('house','senate')),
 congress integer not null,
 session integer,
 roll_call_number integer not null,
 vote_date date,
 question text,
 result text,
 bill_id text,
 source_url text not null,
 unique(chamber,congress,session,roll_call_number)
);
create table if not exists public.member_votes (
 vote_id bigint not null references public.congressional_votes(id) on delete cascade,
 bioguide_id text not null,
 position text not null,
 primary key(vote_id,bioguide_id)
);
create table if not exists public.ingestion_runs (
 id bigint generated always as identity primary key,
 source text not null,
 started_at timestamptz not null default now(),
 completed_at timestamptz,
 status text not null default 'running',
 rows_seen integer not null default 0,
 rows_written integer not null default 0,
 error_message text
);
-- RLS: public clients can read only verified records. All writes require privileged server-side credentials.
alter table public.organizations enable row level security;
alter table public.candidates enable row level security;
alter table public.fec_filings enable row level security;
alter table public.financial_transactions enable row level security;
alter table public.organization_relationships enable row level security;
alter table public.congressional_votes enable row level security;
alter table public.member_votes enable row level security;
alter table public.ingestion_runs enable row level security;
create policy "Public read organizations" on public.organizations for select to anon, authenticated using (relationship_class <> 'unverified');
create policy "Public read candidates" on public.candidates for select to anon, authenticated using (true);
create policy "Public read verified transactions" on public.financial_transactions for select to anon, authenticated using (reconciliation_status = 'verified' and not is_superseded);
create policy "Public read filings" on public.fec_filings for select to anon, authenticated using (true);
create policy "Public read verified relationships" on public.organization_relationships for select to anon, authenticated using (review_status = 'verified');
create policy "Public read votes" on public.congressional_votes for select to anon, authenticated using (true);
create policy "Public read member votes" on public.member_votes for select to anon, authenticated using (true);
-- The ingestion_runs table remains private to administrators.
insert into public.organizations(fec_committee_id,name,organization_type,relationship_class,evidence_url) values
('C00797670','AIPAC PAC','pac','direct','https://www.fec.gov/data/committee/C00797670/'),
('C00799031','United Democracy Project','super_pac','direct','https://www.fec.gov/data/committee/C00799031/')
on conflict(fec_committee_id) do update set name=excluded.name,organization_type=excluded.organization_type,relationship_class=excluded.relationship_class,evidence_url=excluded.evidence_url;
