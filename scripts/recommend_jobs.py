"""
岗位推荐脚本（每8小时由 GitHub Actions 触发）
流程：
  1. 从 Supabase 读取所有用户资料
  2. 调用 OpenAI 根据用户画像生成 3 条推荐岗位
  3. 写入 Supabase 的 job_recommendations 表
  4. 通过 PushPlus 推送微信通知
"""

import os
import json
import requests
from supabase import create_client, Client
from openai import OpenAI

# ============ 初始化客户端 ============
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY]):
    raise EnvironmentError("缺少必要环境变量：SUPABASE_URL / SUPABASE_KEY / OPENAI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = OpenAI(api_key=OPENAI_API_KEY)


# ============ 读取用户 ============
def fetch_users():
    resp = supabase.table("user_profiles").select("*").execute()
    return resp.data or []


# ============ 调用 OpenAI 生成推荐 ============
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
        model="gpt-4o-mini",
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
    rows = [
        {
            "user_id": user_id,
            "job_title": j["job_title"],
            "company": j["company"],
            "enterprise_type": j["enterprise_type"],
            "match_score": j["match_score"],
            "detail_link": j["detail_link"],
        }
        for j in jobs
    ]
    supabase.table("job_recommendations").insert(rows).execute()
    return rows


# ============ PushPlus 微信推送 ============
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
        requests.post(
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
    users = fetch_users()
    print(f"共读取到 {len(users)} 个用户")
    for u in users:
        try:
            jobs = generate_recommendations(u)
            saved = save_recommendations(u["id"], jobs)
            push_wechat(u, saved)
            print(f"用户 {u['id']} 推荐了 {len(saved)} 个岗位")
        except Exception as e:
            print(f"用户 {u.get('id')} 处理失败：{e}")


if __name__ == "__main__":
    main()
