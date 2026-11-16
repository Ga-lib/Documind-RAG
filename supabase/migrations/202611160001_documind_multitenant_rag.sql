-- DocuMind multi-tenant foundation.
-- Applied to Supabase project tzttshoaktrceinptpex on 2026-11-16.
create extension if not exists vector with schema extensions;

create table if not exists public.documind_documents (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  filename text not null check (char_length(filename) between 1 and 255),
  storage_path text not null unique,
  content_hash text not null,
  status text not null default 'processing' check (status in ('processing','ready','failed')),
  chunks_count integer not null default 0 check (chunks_count >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(owner_id, content_hash),
  unique(owner_id, filename)
);

create table if not exists public.documind_chunks (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  document_id uuid not null references public.documind_documents(id) on delete cascade,
  chunk_index integer not null check (chunk_index >= 0),
  content text not null,
  embedding extensions.vector(384) not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(document_id, chunk_index)
);

create index if not exists documind_documents_owner_created_idx
  on public.documind_documents(owner_id, created_at desc);
create index if not exists documind_chunks_owner_document_idx
  on public.documind_chunks(owner_id, document_id);
create index if not exists documind_chunks_embedding_hnsw_idx
  on public.documind_chunks using hnsw (embedding extensions.vector_cosine_ops);

alter table public.documind_documents enable row level security;
alter table public.documind_chunks enable row level security;

drop policy if exists "Users manage their own DocuMind documents" on public.documind_documents;
create policy "Users manage their own DocuMind documents"
  on public.documind_documents for all to authenticated
  using (owner_id = (select auth.uid()))
  with check (owner_id = (select auth.uid()));

drop policy if exists "Users manage their own DocuMind chunks" on public.documind_chunks;
create policy "Users manage their own DocuMind chunks"
  on public.documind_chunks for all to authenticated
  using (owner_id = (select auth.uid()))
  with check (
    owner_id = (select auth.uid())
    and exists (
      select 1 from public.documind_documents d
      where d.id = document_id and d.owner_id = (select auth.uid())
    )
  );

create or replace function public.match_documind_chunks(
  query_embedding extensions.vector(384),
  match_count integer default 4,
  filter_document_id uuid default null
)
returns table (
  id uuid, document_id uuid, filename text, chunk_index integer,
  content text, similarity double precision
)
language sql stable security invoker
set search_path = public, extensions
as $$
  select c.id, c.document_id, d.filename, c.chunk_index, c.content,
    (1 - (c.embedding <=> query_embedding))::double precision as similarity
  from public.documind_chunks c
  join public.documind_documents d on d.id = c.document_id
  where c.owner_id = (select auth.uid())
    and d.owner_id = (select auth.uid())
    and d.status = 'ready'
    and (filter_document_id is null or c.document_id = filter_document_id)
  order by c.embedding <=> query_embedding
  limit greatest(1, least(match_count, 20));
$$;
revoke all on function public.match_documind_chunks(extensions.vector, integer, uuid) from public;
grant execute on function public.match_documind_chunks(extensions.vector, integer, uuid) to authenticated;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('documind-documents', 'documind-documents', false, 20971520, array['application/pdf'])
on conflict (id) do update set public=false, file_size_limit=excluded.file_size_limit,
  allowed_mime_types=excluded.allowed_mime_types;

drop policy if exists "DocuMind users read their own files" on storage.objects;
create policy "DocuMind users read their own files" on storage.objects
  for select to authenticated using (bucket_id='documind-documents'
  and (storage.foldername(name))[1]=(select auth.uid())::text);
drop policy if exists "DocuMind users upload their own files" on storage.objects;
create policy "DocuMind users upload their own files" on storage.objects
  for insert to authenticated with check (bucket_id='documind-documents'
  and (storage.foldername(name))[1]=(select auth.uid())::text);
drop policy if exists "DocuMind users update their own files" on storage.objects;
create policy "DocuMind users update their own files" on storage.objects
  for update to authenticated using (bucket_id='documind-documents'
  and (storage.foldername(name))[1]=(select auth.uid())::text)
  with check (bucket_id='documind-documents'
  and (storage.foldername(name))[1]=(select auth.uid())::text);
drop policy if exists "DocuMind users delete their own files" on storage.objects;
create policy "DocuMind users delete their own files" on storage.objects
  for delete to authenticated using (bucket_id='documind-documents'
  and (storage.foldername(name))[1]=(select auth.uid())::text);
