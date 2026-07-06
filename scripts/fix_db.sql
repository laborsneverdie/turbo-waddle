-- 用 DO 块安全地删除已有策略再重建
DO $$
BEGIN
    -- 删除 user_profiles 策略
    IF EXISTS (SELECT 1 FROM pg_policies WHERE policyname = '允许匿名插入用户资料' AND tablename = 'user_profiles') THEN
        DROP POLICY "允许匿名插入用户资料" ON public.user_profiles;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_policies WHERE policyname = '允许匿名读取用户资料' AND tablename = 'user_profiles') THEN
        DROP POLICY "允许匿名读取用户资料" ON public.user_profiles;
    END IF;

    -- 删除 job_recommendations 策略
    IF EXISTS (SELECT 1 FROM pg_policies WHERE policyname = '允许匿名插入推荐' AND tablename = 'job_recommendations') THEN
        DROP POLICY "允许匿名插入推荐" ON public.job_recommendations;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_policies WHERE policyname = '允许匿名读取推荐' AND tablename = 'job_recommendations') THEN
        DROP POLICY "允许匿名读取推荐" ON public.job_recommendations;
    END IF;
END $$;

-- 重新创建策略
CREATE POLICY "允许匿名插入用户资料" ON public.user_profiles FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "允许匿名读取用户资料" ON public.user_profiles FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "允许匿名插入推荐" ON public.job_recommendations FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "允许匿名读取推荐" ON public.job_recommendations FOR SELECT TO anon, authenticated USING (true);
