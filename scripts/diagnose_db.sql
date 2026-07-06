-- 诊断脚本：检查 user_profiles 和 job_recommendations 表的位置
-- 在 Supabase Dashboard → SQL Editor 中执行

-- 1. 检查 public schema 下的表
SELECT 'public schema 表' AS info, table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- 2. 检查所有 schema 中是否有 user_profiles
SELECT '所有 schema 中的 user_profiles' AS info, table_schema, table_name 
FROM information_schema.tables 
WHERE table_name = 'user_profiles';

-- 3. 检查所有 schema 中是否有 job_recommendations
SELECT '所有 schema 中的 job_recommendations' AS info, table_schema, table_name 
FROM information_schema.tables 
WHERE table_name = 'job_recommendations';

-- 4. 检查 user_profiles 的列结构
SELECT 'user_profiles 列结构' AS info, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'user_profiles'
ORDER BY ordinal_position;

-- 5. 检查 job_recommendations 的列结构
SELECT 'job_recommendations 列结构' AS info, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'job_recommendations'
ORDER BY ordinal_position;

-- 6. 检查 RLS 状态
SELECT 'RLS 状态' AS info, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename IN ('user_profiles', 'job_recommendations');

-- 7. 检查策略
SELECT '策略列表' AS info, tablename, policyname, cmd 
FROM pg_policies 
WHERE tablename IN ('user_profiles', 'job_recommendations');

-- 8. 检查当前数据库和用户
SELECT '当前环境' AS info, current_database(), current_user, current_schema();
