-- 先删除旧表（如果存在），然后我们通过 Table Editor 重新创建
DROP TABLE IF EXISTS public.job_recommendations CASCADE;
DROP TABLE IF EXISTS public.user_profiles CASCADE;

-- 验证表已删除
SELECT '旧表已删除，请使用 Table Editor 重新创建' AS next_step;
