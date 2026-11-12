create table if not exists public.fec_import_checkpoints (
 source text not null,
 election_cycle integer not null,
 cursor jsonb not null default '{}'::jsonb,
 pages_completed integer not null default 0,
 rows_seen bigint not null default 0,
 rows_staged bigint not null default 0,
 completed boolean not null default false,
 updated_at timestamptz not null default now(),
 primary key(source,election_cycle)
);
alter table public.fec_import_checkpoints enable row level security;
revoke all on public.fec_import_checkpoints from anon,authenticated;
