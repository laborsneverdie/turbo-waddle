"""
岗位推荐脚本（每8小时由 GitHub Actions 触发）
使用 Supabase REST API，不依赖数据库直连，避免端口 5432 不可达问题

流程：
  1. 通过 REST API 读取所有用户资料
  2. 调用 DeepSeek 根据用户画像生成 3 条推荐岗位
  3. 通过 REST API 写入 job_recommendations 表
  4. 通过 PushPlus 推送微信通知
"""

import os
import sys
import json
import traceback
import requests
from openai import OpenAI

# ============ 初始化客户端 ============
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # service_role key（绕过 RLS）
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_APL_KEY")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN")

print("=" * 50)
print("[环境检查]")
print(f"  SUPABASE_URL 已设置: {bool(SUPABASE_URL)}")
print(f"  SUPABASE_KEY 已设置: {bool(SUPABASE_KEY)}")
print(f"  DEEPSEEK_API_KEY 已设置: {bool(DEEPSEEK_API_KEY)}")
print(f"  PUSHPLUS_TOKEN 已设置: {bool(PUSHPLUS_TOKEN)}")
print("=" * 50)

if not SUPABASE_URL:
    print("[错误] 缺少环境变量 SUPABASE_URL，请在 GitHub Secrets 中添加")
    sys.exit(1)
if not SUPABASE_KEY:
    print("[错误] 缺少环境变量 SUPABASE_KEY，请在 GitHub Secrets 中添加")
    sys.exit(1)
if not DEEPSEEK_API_KEY:
    print("[错误] 缺少环境变量 DEEPSEEK_API_KEY，请在 GitHub Secrets 中添加")
    sys.exit(1)

ai_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# Supabase REST API 请求头（使用 service_role key 绕过 RLS）
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


# ============ 读取用户 ============
def fetch_users():
    """通过 REST API 读取所有用户资料"""
    print("[数据库] 正在通过 REST API 读取用户...")
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/user_profiles?order=created_at.desc",
        headers=HEADERS,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"[数据库] 读取失败 HTTP {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    users = resp.json()
    print(f"[数据库] 读取成功，共 {len(users)} 个用户")
    return users


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


# ============ 写入推荐结果 ============
def save_recommendations(user_id: int, jobs: list[dict]):
    """通过 REST API 写入推荐结果"""
    for j in jobs:
        payload = {
            "user_id": user_id,
            "job_title": j["job_title"],
            "company": j["company"],
            "enterprise_type": j["enterprise_type"],
            "match_score": j["match_score"],
            "detail_link": j["detail_link"],
        }
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/job_recommendations",
            headers=HEADERS,
            json=payload,
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            print(f"[数据库] 写入失败 HTTP {resp.status_code}: {resp.text}")
            resp.raise_for_status()
    return jobs


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
    except Exception as e:
        print(f"[主流程] 致命错误: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
