const { Pool } = require('pg');

const pool = new Pool({
  connectionString: 'postgresql://postgres:2L01Q10R523@db.clihwbzomhctkxooldbz.supabase.co:5432/postgres',
  ssl: { rejectUnauthorized: false },
});

async function test() {
  try {
    const r1 = await pool.query('SELECT NOW() as now');
    console.log('连接成功！服务器时间:', r1.rows[0].now);

    const r2 = await pool.query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'");
    console.log('public schema 表:', JSON.stringify(r2.rows, null, 2));

    const r3 = await pool.query('SELECT COUNT(*) as count FROM public.user_profiles');
    console.log('user_profiles 记录数:', r3.rows[0].count);

    const r4 = await pool.query('SELECT COUNT(*) as count FROM public.job_recommendations');
    console.log('job_recommendations 记录数:', r4.rows[0].count);

    console.log('\n所有测试通过！');
  } catch (e) {
    console.error('连接失败:', e.message);
  } finally {
    pool.end();
  }
}

test();
