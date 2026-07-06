-- 深度排查脚本
-- 在 SQL Editor 中执行，把所有结果截图给我

-- 1. 检查 user_profiles 表是否真的存在
SELECT EXISTS (
    SELECT FROM pg_tables 
    WHERE schemaname = 'public' 
      AND tablename = 'user_profiles'
) AS "user_profiles存在";

SELECT EXISTS (
    SELECT FROM pg_tables 
    WHERE schemaname = 'public' 
      AND tablename = 'job_recommendations'
) AS "job_recommendations存在";

-- 2. 检查序列
SELECT sequencename, schema_name 
FROM information_schema.sequences 
WHERE sequencename LIKE '%user_profiles%' OR sequencename LIKE '%job_recommendations%';

-- 3. 检查表的 owner（PostgREST 需要能访问）
SELECT tablename, tableowner, hasindexes, hasrules, hastriggers
FROM pg_tables 
WHERE schemaname = 'public' AND tablename IN ('user_profiles', 'job_recommendations');

-- 4. 检查 anon 角色是否有权限
SELECT grantee, privilege_type, table_name 
FROM information_schema.role_table_grants 
WHERE table_name IN ('user_profiles', 'job_recommendations')
ORDER BY table_name;

-- 5. 检查 public schema 是否在 PostgREST 的搜索路径中
SELECT current_schemas(true);

-- 6. 列出 public 下所有表
SELECT * FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
