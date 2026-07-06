-- 刷新 PostgREST schema cache
-- 在 Supabase Dashboard → SQL Editor 中执行
NOTIFY pgrst, 'reload schema';
