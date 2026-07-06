-- 综合权限修复脚本
-- 在 SQL Editor 中执行

-- 1. 授予所有角色所有权限
GRANT ALL ON public.user_profiles TO anon, authenticated, service_role;
GRANT ALL ON public.job_recommendations TO anon, authenticated, service_role;

-- 2. 授予序列权限（处理可能的序列名）
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

-- 3. 授予 schema 使用权限
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- 4. 确保表对默认角色可见
ALTER TABLE public.user_profiles OWNER TO postgres;
ALTER TABLE public.job_recommendations OWNER TO postgres;

-- 5. 刷新通知队列
SELECT pg_notification_queue_usage();

-- 6. 发送刷新信号（多次）
NOTIFY pgrst, 'reload schema';

-- 7. 等待一下再次刷新
SELECT pg_sleep(2);
NOTIFY pgrst, 'reload schema';

-- 8. 验证权限
SELECT grantee, table_name, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_name IN ('user_profiles', 'job_recommendations')
ORDER BY table_name, grantee;

SELECT '修复完成' AS status;
