-- 最简单的检查：public 下有哪些表？
SELECT * FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
