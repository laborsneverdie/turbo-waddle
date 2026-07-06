-- ============================================
-- Supabase 数据库初始化脚本
-- 在 Supabase Dashboard → SQL Editor 中执行此脚本
-- ============================================

-- 1. 创建 user_profiles 表（用户资料）
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city TEXT NOT NULL,
    degree TEXT NOT NULL,
    experience TEXT NOT NULL,
    field TEXT NOT NULL,
    certifications TEXT,
    email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. 创建 job_recommendations 表（岗位推荐结果）
CREATE TABLE IF NOT EXISTS public.job_recommendations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    job_title TEXT NOT NULL,
    company TEXT NOT NULL,
    enterprise_type TEXT NOT NULL CHECK (enterprise_type IN ('国企', '私企', '外企')),
    match_score INTEGER NOT NULL CHECK (match_score >= 0 AND match_score <= 100),
    detail_link TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. 创建索引
CREATE INDEX IF NOT EXISTS idx_job_recommendations_user_id
    ON public.job_recommendations(user_id);

CREATE INDEX IF NOT EXISTS idx_job_recommendations_created_at
    ON public.job_recommendations(created_at DESC);

-- 4. 启用行级安全 (RLS)
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_recommendations ENABLE ROW LEVEL SECURITY;

-- 5. 配置 RLS 策略（允许匿名访问，适用于本项目）
CREATE POLICY "允许匿名插入用户资料"
    ON public.user_profiles
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "允许匿名读取用户资料"
    ON public.user_profiles
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "允许匿名插入推荐"
    ON public.job_recommendations
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "允许匿名读取推荐"
    ON public.job_recommendations
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- 6. 更新统计信息
ANALYZE public.user_profiles;
ANALYZE public.job_recommendations;

-- 完成
SELECT '数据库初始化完成！' AS message;
