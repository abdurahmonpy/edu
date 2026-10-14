-- ============================================================
-- edu platformasi — Supabase sxemasi
-- Supabase Dashboard → SQL Editor → New Query → shu kodni
-- joylashtirib → Run bosing. Qayta ishga tushirish xavfsiz.
-- ============================================================

-- 1) PROFILLAR (auth.users bilan bog'lanadi)
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text not null check (char_length(full_name) between 2 and 120),
  created_at timestamptz not null default now()
);

-- 2) LEADLAR — index.html ro'yxatdan o'tish formasiga (hisobsiz)
create table if not exists public.leads (
  id bigint generated always as identity primary key,
  full_name text not null check (char_length(full_name) between 2 and 120),
  phone text not null check (char_length(phone) between 7 and 20),
  created_at timestamptz not null default now()
);
create index if not exists leads_created_at_idx on public.leads (created_at desc);

-- 3) CHAT XABARLARI — xona bo'yicha (support, ai, jamoa ...)
create table if not exists public.messages (
  id bigint generated always as identity primary key,
  room text not null check (char_length(room) between 1 and 60),
  user_id uuid not null references auth.users (id) on delete cascade,
  author_name text not null check (char_length(author_name) between 1 and 120),
  body text not null check (char_length(body) between 1 and 2000),
  created_at timestamptz not null default now()
);
create index if not exists messages_room_created_idx
  on public.messages (room, created_at desc);

-- 4) DARS PROGRESSI — dars.html (video + uy vazifasi foizi)
create table if not exists public.lesson_progress (
  user_id uuid not null references auth.users (id) on delete cascade,
  lesson text not null check (char_length(lesson) between 1 and 120),
  video_watched boolean not null default false,
  video_percent smallint not null default 0 check (video_percent between 0 and 100),
  hw_percent smallint not null default 0 check (hw_percent between 0 and 100),
  updated_at timestamptz not null default now(),
  primary key (user_id, lesson)
);

-- 5) SHAXSIY LUG'AT — lugat.html so'zlar
create table if not exists public.words (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  en text not null check (char_length(en) between 1 and 200),
  uz text not null check (char_length(uz) between 1 and 200),
  type text not null default 'so''z' check (type in ('so''z', 'ibora')),
  ex text default '' check (char_length(ex) <= 500),
  status text not null default 'new' check (status in ('new', 'learned', 'review')),
  created_at timestamptz not null default now()
);
create index if not exists words_user_idx on public.words (user_id);

-- ============================================================
-- RLS (Row Level Level Security) — himoya qatlami
-- Backend serverda SECRET_KEY ishlatadi (RLS ni chetlab o'tadi),
-- lekin kelajakda anon/publik ochilsa ham ma'lumot yopiq qoladi.
-- ============================================================

alter table public.profiles enable row level security;
alter table public.leads enable row level security;
alter table public.messages enable row level security;
alter table public.lesson_progress enable row level security;
alter table public.words enable row level security;

-- profiles: faqat o'z profili
drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own on public.profiles
  for select using (auth.uid() = id);
drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own on public.profiles
  for insert with check (auth.uid() = id);
drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own on public.profiles
  for update using (auth.uid() = id) with check (auth.uid() = id);

-- leads: autentifikatsiyadan o'tgan foydalanuvchi qo'shishi mumkin
-- (anon kalit bilan ham ishlaydi, chunki server orqali yuboriladi)
drop policy if exists leads_insert on public.leads;
create policy leads_insert on public.leads
  for insert with check (true);
-- Leadlarni o'qish — faqat service/secret kalit orqali (siyosat yo'q).

-- messages: o'z xabari — yozish/chiqarish, xona bo'yicha o'qish
drop policy if exists messages_select_room on public.messages;
create policy messages_select_room on public.messages
  for select using (true);
drop policy if exists messages_insert_own on public.messages;
create policy messages_insert_own on public.messages
  for insert with check (auth.uid() = user_id);
drop policy if exists messages_delete_own on public.messages;
create policy messages_delete_own on public.messages
  for delete using (auth.uid() = user_id);

-- lesson_progress: faqat o'z progressi
drop policy if exists progress_all_own on public.lesson_progress;
create policy progress_all_own on public.lesson_progress
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- words: faqat o'z so'zlari
drop policy if exists words_all_own on public.words;
create policy words_all_own on public.words
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
