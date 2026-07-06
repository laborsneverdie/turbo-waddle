"""
岗位推荐脚本（每8小时由 GitHub Actions 触发）
流程：
  1. 从 Supabase 读取所有用户资料（PostgreSQL 直连，绕过 PostgREST）
  2. 调用 DeepSeek 根据用户画像生成 3 条推荐岗位
  3. 写入 Supabase 的 job_recommendations 表
  4. 通过 PushPlus 推送微信通知
"""

import os
import sys
import json
import traceback
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI

# ============ 初始化客户端 ============
DATABASE_URL = os.environ.get("DATABASE_URL")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN")

print("=" * 50)
print("[环境检查]")
print(f"  DATABASE_URL 已设置: {bool(DATABASE_URL)}")
print(f"  DEEPSEEK_API_KEY 已设置: {bool(DEEPSEEK_API_KEY)}")
print(f"  PUSHPLUS_TOKEN 已设置: {bool(PUSHPLUS_TOKEN)}")
print("=" * 50)

if not DATABASE_URL:
    print("[错误] 缺少环境变量 DATABASE_URL，请在 GitHub Secrets 中添加")
    sys.exit(1)
if not DEEPSEEK_API_KEY:
    print("[错误] 缺少环境变量 DEEPSEEK_API_KEY，请在 GitHub Secrets 中添加")
    sys.exit(1)

# 连接数据库（Supabase 远程连接需要 SSL）
try:
    print("[数据库] 正在连接...")
    conn = psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=15)
    print("[数据库] 连接成功")
except Exception as e:
    print(f"[数据库] 连接失败: {e}")
    traceback.print_exc()
    sys.exit(1)

ai_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)


# ============ 读取用户 ============
def fetch_users():
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM public.user_profiles ORDER BY created_at DESC")
        return [dict(row) for row in cur.fetchall()]


# ============ 调用 DeepSeek 生成推荐 ============
def generate_recommendations(user: dict) -> list[dict]:
    prompt = f"""
你是一名资深猎头，请根据以下求职者画像，推荐 3 个最匹配的岗位。
返回严格的 JSON 数组，每个元素包含字段：
- job_title：岗位名称
- company：推荐公司名称（虚构但合理）
- enterprise_type：企业类型，只能是 "国企"、"私企"、"外企" 之一
- match_score：匹配度（0-100 的整数）
- detail_link：详情链接（可虚构 https 开头的 url）

求职者画像：
- 城市：{user.get('city')}
- 学历：{user.get('degree')}
- 工作经验：{user.get('experience')}
- 求职方向：{user.get('field')}
- 权威证书：{user.get('certifications') or '无'}

只返回 JSON 数组，不要任何额外文字。
"""
    resp = ai_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    content = resp.choices[0].message.content.strip()
    # 兼容模型偶尔包裹 ```json ... ```
    if content.startswith("```"):
        content = content.strip("`").lstrip("json").strip()
    return json.loads(content)


# ============ 写入 Supabase ============
def save_recommendations(user_id: int, jobs: list[dict]):
    with conn.cursor() as cur:
        for j in jobs:
            cur.execute("""
                INSERT INTO public.job_recommendations (user_id, job_title, company, enterprise_type, match_score, detail_link)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, j["job_title"], j["company"], j["enterprise_type"], j["match_score"], j["detail_link"]))
        conn.commit()
    return jobs


# ============ PushPlus 微信推送 ============
import requests as req_lib
def push_wechat(user: dict, jobs: list[dict]):
    if not PUSHPLUS_TOKEN:
        return
    title = f"岗位推荐：{user.get('field', '求职方向')}"
    lines = [f"城市：{user.get('city')} | 学历：{user.get('degree')}"]
    for i, j in enumerate(jobs, 1):
        lines.append(
            f"{i}. {j['job_title']} @ {j['company']}（{j['enterprise_type']}）"
            f" 匹配度 {j['match_score']}%"
        )
    content = "\n".join(lines)
    try:
        req_lib.post(
            "http://www.pushplus.plus/send",
            json={
                "token": PUSHPLUS_TOKEN,
                "title": title,
                "content": content,
                "template": "txt",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"[PushPlus] 推送失败：{e}")


# ============ 主流程 ============
def main():
    try:
        users = fetch_users()
        print(f"[主流程] 共读取到 {len(users)} 个用户")

        if len(users) == 0:
            print("[主流程] 没有用户数据，任务结束")
            return

        success_count = 0
        fail_count = 0
        for u in users:
            try:
                jobs = generate_recommendations(u)
                saved = save_recommendations(u["id"], jobs)
                push_wechat(u, saved)
                print(f"[主流程] 用户 {u['id']} 推荐了 {len(saved)} 个岗位")
                success_count += 1
            except Exception as e:
                print(f"[主流程] 用户 {u.get('id')} 处理失败: {e}")
                traceback.print_exc()
                fail_count += 1

        print(f"[主流程] 完成！成功 {success_count} 个，失败 {fail_count} 个")
    finally:
        conn.close()
        print("[数据库] 连接已关闭")


if __name__ == "__main__":
    main()
