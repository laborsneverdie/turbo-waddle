-- ============================================
-- 完整修复脚本：解决 PGRST205 错误
-- 在 Supabase Dashboard → SQL Editor 中执行
-- ============================================

-- 第1步：疏通通知队列
SELECT pg_notification_queue_usage();

-- 第2步：授予 anon 和 authenticated 角色对两张表的权限
GRANT ALL ON public.user_profiles TO anon, authenticated;
GRANT ALL ON public.job_recommendations TO anon, authenticated;

-- 第3步：授予使用序列的权限（用于自增 ID）
GRANT USAGE, SELECT ON SEQUENCE user_profiles_id_seq TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE job_recommendations_id_seq TO anon, authenticated;

-- 第4步：刷新 schema cache
NOTIFY pgrst, 'reload schema';

-- 验证结果
SELECT '修复完成！' AS status;
