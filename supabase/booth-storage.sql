-- PNG Booth — guest photo/GIF/video storage (Supabase Storage)
--
-- The booth page uploads with the public anon key. This bucket lets anyone
-- ADD a file under YYYY-MM-DD/<uuid>.<ext> and read it by its exact URL —
-- nothing else: no listing, no overwriting, no deleting.
-- Safe to re-run.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'booth', 'booth', true,
  52428800, -- 50 MB: a 30 s 1080p booth video is ~15 MB
  array['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/webm', 'video/quicktime']
)
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- Upload only; path shape enforced so random names/folders can't be written.
drop policy if exists "booth: anon can add guest files" on storage.objects;
create policy "booth: anon can add guest files"
  on storage.objects for insert
  to anon
  with check (
    bucket_id = 'booth'
    and name ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(jpg|png|gif|mp4|webm|mov)$'
  );

-- No select/update/delete policies for anon on purpose. Public-bucket file
-- URLs are served without RLS, so guests can still open their own link.

-- Keep-alive: free-plan projects pause after ~7 days without activity, which
-- breaks QR uploads between events. A daily Vercel cron (keepalive/, project
-- conex1/png-booth-keepalive) calls this. Returns only the server time.
create or replace function public.keepalive()
returns timestamptz
language sql
stable
set search_path = ''
as $$ select now() $$;

revoke all on function public.keepalive() from public;
grant execute on function public.keepalive() to anon;
