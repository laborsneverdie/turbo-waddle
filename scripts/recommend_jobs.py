"""
岗位推荐脚本（每8小时由 GitHub Actions 触发）
使用 Supabase REST API，不依赖数据库直连，避免端口 5432 不可达问题

流程：
  1. 通过 REST API 读取所有用户资料
  2. 调用智谱 GLM-4-Flash 根据用户画像生成 3 条推荐岗位（含详细说明）
  3. 通过 REST API 写入 job_recommendations 表
  4. 生成 docx 岗位推荐报告
  5. 通过 PushPlus 推送微信通知
"""

import os
import sys
import json
import traceback
from datetime import datetime
import requests
from openai import OpenAI
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

# ============ 初始化客户端 ============
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # service_role key（绕过 RLS）
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_APL_KEY")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN")

# 输出目录（GitHub Actions 中为仓库根目录）
OUTPUT_DIR = os.environ.get("GITHUB_WORKSPACE", os.path.dirname(os.path.abspath(__file__)) + "/..")
OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)
REPORT_DIR = os.path.join(OUTPUT_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

print("=" * 50)
print("[环境检查]")
print(f"  SUPABASE_URL 已设置: {bool(SUPABASE_URL)}")
print(f"  SUPABASE_KEY 已设置: {bool(SUPABASE_KEY)}")
print(f"  ZHIPU_API_KEY 已设置: {bool(ZHIPU_API_KEY)}")
print(f"  PUSHPLUS_TOKEN 已设置: {bool(PUSHPLUS_TOKEN)}")
print(f"  报告输出目录: {REPORT_DIR}")
print("=" * 50)

if not SUPABASE_URL:
    print("[错误] 缺少环境变量 SUPABASE_URL，请在 GitHub Secrets 中添加")
    sys.exit(1)
if not SUPABASE_KEY:
    print("[错误] 缺少环境变量 SUPABASE_KEY，请在 GitHub Secrets 中添加")
    sys.exit(1)
if not ZHIPU_API_KEY:
    print("[错误] 缺少环境变量 ZHIPU_API_KEY，请在 GitHub Secrets 中添加")
    sys.exit(1)

# 智谱 GLM 兼容 OpenAI SDK，只需替换 base_url 和 api_key
ai_client = OpenAI(
    api_key=ZHIPU_API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
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


# ============ 调用 DeepSeek 生成推荐（含详细说明）============
def generate_recommendations(user: dict) -> list[dict]:
    prompt = f"""
你是一名资深猎头，请根据以下求职者画像，推荐 3 个最匹配的岗位。
返回严格的 JSON 数组，每个元素包含以下字段：

- job_title：岗位名称
- company：推荐公司名称（虚构但合理的真实风格公司名）
- enterprise_type：企业类型，只能是 "国企"、"私企"、"外企" 之一
- match_score：匹配度（0-100 的整数）
- detail_link：详情链接（可虚构 https 开头的 url）
- salary_range：薪资范围（如 "15k-25k/月"）
- responsibilities：岗位职责（3-5 条，用换行符分隔）
- requirements：任职要求（3-5 条，用换行符分隔）
- benefits：福利待遇（3-4 条，用换行符分隔）
- development：职业发展前景（1-2 句话描述）
- work_location：具体工作地点

求职者画像：
- 城市：{user.get('city')}
- 学历：{user.get('degree')}
- 工作经验：{user.get('experience')}
- 求职方向：{user.get('field')}
- 权威证书：{user.get('certifications') or '无'}

要求：
1. 岗位必须与求职方向高度相关
2. 薪资范围要符合该城市和岗位的市场水平
3. 任职要求要匹配求职者的学历和经验
4. 只返回 JSON 数组，不要任何额外文字
"""
    resp = ai_client.chat.completions.create(
        model="glm-4-flash",
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


# ============ 生成 docx 岗位推荐报告 ============
def generate_docx_report(user: dict, jobs: list[dict]) -> str:
    """生成 docx 格式的岗位推荐报告，返回文件路径"""
    doc = Document()

    # ---- 设置默认字体 ----
    style = doc.styles['Normal']
    font = style.font
    font.name = '微软雅黑'
    font.size = Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    # ---- 标题 ----
    title = doc.add_heading('智能岗位推荐报告', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x25, 0x63, 0xeb)

    # 日期
    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_run = date_para.add_run(
        f'生成日期：{datetime.now().strftime("%Y年%m月%d日 %H:%M")}'
    )
    date_run.font.size = Pt(10)
    date_run.font.color.rgb = RGBColor(0x6b, 0x72, 0x80)

    doc.add_paragraph()  # 空行

    # ---- 求职者信息 ----
    doc.add_heading('一、求职者信息', level=1)
    info_table = doc.add_table(rows=3, cols=4, style='Light Shading Accent 1')
    info_table.alignment = WD_TABLE_ALIGNMENT.CENTER

    info_data = [
        ['城市', user.get('city', '—'), '学历', user.get('degree', '—')],
        ['工作经验', user.get('experience', '—'), '求职方向', user.get('field', '—')],
        ['权威证书', user.get('certifications') or '无', '邮箱', user.get('email') or '未提供'],
    ]
    for row_idx, row_data in enumerate(info_data):
        for col_idx, val in enumerate(row_data):
            cell = info_table.cell(row_idx, col_idx)
            cell.text = val
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(10)
                    if col_idx % 2 == 0:  # 标签列加粗
                        run.bold = True
                        run.font.color.rgb = RGBColor(0x1e, 0x40, 0xaf)

    doc.add_paragraph()  # 空行

    # ---- 推荐岗位详情 ----
    doc.add_heading('二、推荐岗位详情', level=1)

    type_colors = {
        "国企": RGBColor(0xdc, 0x26, 0x26),
        "私企": RGBColor(0x25, 0x63, 0xeb),
        "外企": RGBColor(0x16, 0xa3, 0x4a),
    }

    for idx, job in enumerate(jobs, 1):
        # 岗位标题
        heading = doc.add_heading(f'{idx}. {job["job_title"]}', level=2)

        # 基本信息（表格）
        basic_table = doc.add_table(rows=2, cols=4, style='Light List Accent 1')
        basic_data = [
            ['公司名称', job.get('company', '—'), '企业类型', job.get('enterprise_type', '—')],
            ['匹配度', f'{job.get("match_score", 0)}%', '薪资范围', job.get('salary_range', '面议')],
        ]
        for row_idx, row_data in enumerate(basic_data):
            for col_idx, val in enumerate(row_data):
                cell = basic_table.cell(row_idx, col_idx)
                cell.text = val
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(10)
                        if col_idx % 2 == 0:
                            run.bold = True

        # 工作地点
        if job.get('work_location'):
            loc_para = doc.add_paragraph()
            loc_label = loc_para.add_run('工作地点：')
            loc_label.bold = True
            loc_label.font.size = Pt(10)
            loc_val = loc_para.add_run(job['work_location'])
            loc_val.font.size = Pt(10)

        # 岗位职责
        doc.add_heading('岗位职责', level=3)
        responsibilities = job.get('responsibilities', '')
        if isinstance(responsibilities, str):
            resp_list = [r.strip() for r in responsibilities.split('\n') if r.strip()]
        else:
            resp_list = responsibilities
        for item in resp_list:
            p = doc.add_paragraph(item, style='List Bullet')
            for run in p.runs:
                run.font.size = Pt(10)

        # 任职要求
        doc.add_heading('任职要求', level=3)
        requirements = job.get('requirements', '')
        if isinstance(requirements, str):
            req_list = [r.strip() for r in requirements.split('\n') if r.strip()]
        else:
            req_list = requirements
        for item in req_list:
            p = doc.add_paragraph(item, style='List Bullet')
            for run in p.runs:
                run.font.size = Pt(10)

        # 福利待遇
        doc.add_heading('福利待遇', level=3)
        benefits = job.get('benefits', '')
        if isinstance(benefits, str):
            ben_list = [r.strip() for r in benefits.split('\n') if r.strip()]
        else:
            ben_list = benefits
        for item in ben_list:
            p = doc.add_paragraph(item, style='List Bullet')
            for run in p.runs:
                run.font.size = Pt(10)

        # 职业发展前景
        doc.add_heading('职业发展前景', level=3)
        dev_para = doc.add_paragraph(job.get('development', '暂无信息'))
        for run in dev_para.runs:
            run.font.size = Pt(10)

        # 详情链接
        link_para = doc.add_paragraph()
        link_label = link_para.add_run('详情链接：')
        link_label.bold = True
        link_label.font.size = Pt(10)
        link_val = link_para.add_run(job.get('detail_link', ''))
        link_val.font.size = Pt(10)
        link_val.font.color.rgb = RGBColor(0x25, 0x63, 0xeb)

        # 分隔线（除最后一个外）
        if idx < len(jobs):
            sep = doc.add_paragraph()
            sep_run = sep.add_run('—' * 40)
            sep_run.font.color.rgb = RGBColor(0xd1, 0xd5, 0xdb)
            sep.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ---- 页脚 ----
    doc.add_paragraph()
    footer_para = doc.add_paragraph()
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer_para.add_run('本报告由智能岗位推荐系统自动生成 | Powered by 智谱 GLM-4-Flash')
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(0x9c, 0xa3, 0xaf)

    # ---- 保存文件 ----
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    user_id = user.get('id', 'unknown')
    filename = f"岗位推荐报告_用户{user_id}_{timestamp}.docx"
    filepath = os.path.join(REPORT_DIR, filename)
    doc.save(filepath)
    print(f"[报告] 已生成: {filepath}")
    return filepath


# ============ 上传报告到 Supabase Storage ============
STORAGE_BUCKET = "reports"  # 需要在 Supabase 创建名为 reports 的公开 bucket


def upload_to_storage(filepath: str) -> str | None:
    """上传 docx 到 Supabase Storage，返回公开下载链接；失败则返回 None"""
    filename = os.path.basename(filepath)
    try:
        with open(filepath, "rb") as f:
            file_data = f.read()
        upload_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        resp = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{filename}",
            headers=upload_headers,
            data=file_data,
            timeout=60,
        )
        if resp.status_code in (200, 201):
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{filename}"
            print(f"[Storage] 上传成功，公开链接: {public_url}")
            return public_url
        else:
            print(f"[Storage] 上传失败 HTTP {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"[Storage] 上传异常: {e}")
        return None


# ============ PushPlus 微信推送 ============
def push_wechat(user: dict, jobs: list[dict], download_url: str | None = None):
    if not PUSHPLUS_TOKEN:
        return
    title = f"岗位推荐：{user.get('field', '求职方向')}"
    # 使用 Markdown 模板，内容包含完整岗位详情 + 下载链接
    md_lines = [
        f"## 📋 岗位推荐报告",
        f"",
        f"**求职者信息**",
        f"- 城市：{user.get('city', '—')}",
        f"- 学历：{user.get('degree', '—')}",
        f"- 工作经验：{user.get('experience', '—')}",
        f"- 求职方向：{user.get('field', '—')}",
        f"",
        f"---",
        f"",
    ]
    for i, j in enumerate(jobs, 1):
        md_lines.append(f"### {i}. {j['job_title']}")
        md_lines.append(f"")
        md_lines.append(f"| 项目 | 详情 |")
        md_lines.append(f"|------|------|")
        md_lines.append(f"| 公司 | {j.get('company', '—')}（{j.get('enterprise_type', '—')}）|")
        md_lines.append(f"| 匹配度 | **{j.get('match_score', 0)}%** |")
        md_lines.append(f"| 薪资 | {j.get('salary_range', '面议')} |")
        if j.get('work_location'):
            md_lines.append(f"| 地点 | {j['work_location']} |")
        md_lines.append(f"")
        md_lines.append(f"---")
        md_lines.append(f"")
    # 下载链接
    if download_url:
        md_lines.append(f"📥 **[点击下载完整岗位推荐报告（docx）]({download_url})**")
        md_lines.append(f"")
        md_lines.append(f"> 报告包含每个岗位的详细职责、任职要求、福利待遇、职业发展前景")
    else:
        md_lines.append(f"> 完整岗位推荐报告（docx）已生成，请前往 GitHub Actions 下载")
    content = "\n".join(md_lines)
    try:
        resp = requests.post(
            "http://www.pushplus.plus/send",
            json={
                "token": PUSHPLUS_TOKEN,
                "title": title,
                "content": content,
                "template": "markdown",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            print(f"[PushPlus] 推送成功")
        else:
            print(f"[PushPlus] 推送返回 HTTP {resp.status_code}: {resp.text}")
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
        generated_reports = []

        for u in users:
            try:
                jobs = generate_recommendations(u)
                saved = save_recommendations(u["id"], jobs)
                report_path = generate_docx_report(u, saved)
                generated_reports.append(report_path)
                # 上传到 Supabase Storage 获取公开下载链接
                download_url = upload_to_storage(report_path)
                # 推送微信/邮箱，包含下载链接
                push_wechat(u, saved, download_url)
                print(f"[主流程] 用户 {u['id']} 推荐了 {len(saved)} 个岗位，报告已生成并推送")
                success_count += 1
            except Exception as e:
                print(f"[主流程] 用户 {u.get('id')} 处理失败: {e}")
                traceback.print_exc()
                fail_count += 1

        print(f"[主流程] 完成！成功 {success_count} 个，失败 {fail_count} 个")
        print(f"[报告] 共生成 {len(generated_reports)} 份 docx 报告:")
        for r in generated_reports:
            print(f"  - {r}")

    except Exception as e:
        print(f"[主流程] 致命错误: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
