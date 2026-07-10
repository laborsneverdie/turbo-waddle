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
import html
import smtplib
import traceback
from urllib.parse import quote
from datetime import datetime
from email.mime.text import MIMEText
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
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")

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
print(f"  SMTP 邮件推送: {'已配置' if all([SMTP_HOST, SMTP_USER, SMTP_PASS]) else '未配置'}")
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


# ============ 多平台真实招聘搜索链接 ============
# 国企官方招聘平台映射（根据岗位名称匹配）
ENTERPRISE_OFFICIAL_LINKS = {
    "国家电网": {"name": "国家电网招聘", "url": "https://zhaopin.sgcc.com.cn/", "icon": "⚡"},
    "南方电网": {"name": "南方电网招聘", "url": "http://www.csg.cn/", "icon": "⚡"},
    "中国移动": {"name": "中国移动招聘", "url": "https://job.10086.cn/", "icon": "📱"},
    "中国联通": {"name": "中国联通招聘", "url": "https://hr.chinaunicom.com/", "icon": "📱"},
    "中国电信": {"name": "中国电信招聘", "url": "https://www.chinatelecom.com.cn/", "icon": "📱"},
    "工商银行": {"name": "工商银行招聘", "url": "https://job.icbc.com.cn/", "icon": "🏦"},
    "建设银行": {"name": "建设银行招聘", "url": "https://job.ccb.com/", "icon": "🏦"},
    "农业银行": {"name": "农业银行招聘", "url": "https://job.abchina.com/", "icon": "🏦"},
    "中国银行": {"name": "中国银行招聘", "url": "https://campus.chinahr.com/pages/boc/", "icon": "🏦"},
    "交通银行": {"name": "交通银行招聘", "url": "https://job.bankcomm.com/", "icon": "🏦"},
    "中石油": {"name": "中石油招聘", "url": "https://zhaopin.cnpc.com.cn/", "icon": "🛢️"},
    "中石化": {"name": "中石化招聘", "url": "http://job.sinopec.com/", "icon": "🛢️"},
    "中国建筑": {"name": "中国建筑招聘", "url": "https://jobs.cscec.com/", "icon": "🏗️"},
    "中铁": {"name": "中国铁路人才招聘", "url": "https://job.crec.cn/", "icon": "🚄"},
    "中交": {"name": "中交集团招聘", "url": "https://job.ccccltd.cn/", "icon": "🚧"},
    "烟草": {"name": "中国烟草招聘", "url": "http://www.tobacco.gov.cn/", "icon": "🚬"},
    "水务": {"name": "水务集团招聘", "url": "https://www.waterchina.com/", "icon": "💧"},
    "城投": {"name": "城投集团招聘", "url": "http://www.citiccapital.com/", "icon": "🏢"},
    "地铁": {"name": "地铁集团招聘", "url": "https://www.chinametro.net/", "icon": "🚇"},
}


def get_enterprise_official_link(job_title: str) -> dict | None:
    """根据岗位名称中的国企单位名，返回对应的官方招聘平台链接"""
    for key, info in ENTERPRISE_OFFICIAL_LINKS.items():
        if key in str(job_title):
            return info
    return None


def build_search_links(keyword: str, city: str, enterprise_type: str = "", job_title: str = "") -> list[dict]:
    """为每个岗位生成多个真实招聘平台的搜索链接"""
    # 简化关键词：去掉国企前缀，只保留岗位关键词
    simple_kw = keyword
    if "-" in simple_kw:
        simple_kw = simple_kw.split("-", 1)[1].strip()
    core_kw = simple_kw
    for suffix in ["工程师", "经理", "主管", "专员", "技术员", "操作员"]:
        if core_kw.endswith(suffix) and len(core_kw) > len(suffix) + 2:
            core_kw = core_kw[:-len(suffix)]
            break
    search_kw = quote(str(core_kw or simple_kw or keyword))
    links = []
    # 综合招聘平台
    links.append({"name": "BOSS直聘", "url": f"https://www.zhipin.com/web/geek/job?query={search_kw}", "icon": "💼"})
    links.append({"name": "智联招聘", "url": f"https://sou.zhaopin.com/?kw={search_kw}", "icon": "🔍"})
    links.append({"name": "猎聘", "url": f"https://www.liepin.com/zhaopin/?key={search_kw}", "icon": "🎯"})
    # 国企官方权威平台（优先推荐）
    if enterprise_type == "国企":
        links.append({"name": "国聘网", "url": f"https://www.iguopin.com/job/list?keywords={search_kw}", "icon": "🏛️"})
        links.append({"name": "国资委央企招聘", "url": "http://www.sasac.gov.cn/n2588035/n2588105/index.html", "icon": "🇨🇳"})
        links.append({"name": "人社部就业", "url": "http://job.mohrss.gov.cn/", "icon": "📋"})
        links.append({"name": "新职业网", "url": f"https://www.ncss.cn/student/jobsearch/fairs.html?keywords={search_kw}", "icon": "🎓"})
        # 企业自有官方招聘平台
        official = get_enterprise_official_link(job_title)
        if official:
            links.append(official)
    return links


# ============ 爬取国聘网真实岗位数据 ============
def _format_salary(min_wage, max_wage):
    """格式化薪资"""
    if not min_wage and not max_wage:
        return "面议"
    if min_wage and max_wage:
        return f"{min_wage}-{max_wage}元/月"
    return f"{min_wage or max_wage}元/月"


def crawl_iguopin(keyword: str, city: str) -> list[dict]:
    """爬取国聘网（国资央企招聘平台）真实岗位数据"""
    try:
        print(f"[爬取] 正在爬取国聘网，关键词: {keyword}")
        url = "https://gp-api.iguopin.com/api/jobs/v1/list"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Device": "pc",
            "Subsite": "cujiuye",
            "Version": "5.0.0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        }
        payload = {
            "page": 1,
            "page_size": 50,
            "keyword": keyword,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.status_code != 200:
            print(f"[爬取] 国聘网API返回 HTTP {resp.status_code}: {resp.text[:200]}")
            return []

        data = resp.json()
        job_list = data.get("data", {}).get("list", [])

        if not job_list:
            print("[爬取] 国聘网未返回岗位数据")
            return []

        # 解析岗位
        jobs = []
        for item in job_list:
            districts = item.get("district_list", [])
            locations = [d.get("area_cn", "") for d in districts if d.get("area_cn")]
            location_str = "、".join(locations) if locations else ""

            company_info = item.get("company_info", {}) or {}
            job = {
                "job_title": item.get("job_name", ""),
                "company": item.get("company_name", ""),
                "enterprise_type": "国企",  # 国聘网的岗位都是国企/央企
                "match_score": 0,  # 由 AI 后续分析
                "detail_link": f"https://www.iguopin.com/job/detail?id={item.get('job_id', '')}",
                "salary_range": _format_salary(item.get("min_wage"), item.get("max_wage")),
                "responsibilities": item.get("contents", ""),
                "requirements": "",
                "benefits": "",
                "development": "",
                "work_location": location_str or city,
                "education": item.get("education_cn", ""),
                "source": "国聘网（真实数据）",
                "company_nature": company_info.get("nature_cn", ""),
                "start_time": item.get("start_time", ""),
                "end_time": item.get("end_time", ""),
            }
            jobs.append(job)

        # 优先筛选用户所在城市的岗位
        city_jobs = [j for j in jobs if city in j["work_location"]]
        if city_jobs:
            jobs = city_jobs
            print(f"[爬取] 筛选{city}岗位后剩余 {len(jobs)} 个")
        else:
            print(f"[爬取] 未找到{city}的岗位，使用全部 {len(jobs)} 个岗位")

        return jobs[:10]
    except Exception as e:
        print(f"[爬取] 国聘网爬取失败: {e}")
        traceback.print_exc()
        return []


# ============ 调用智谱 GLM 生成推荐（含详细说明 + 自检）============
def generate_recommendations(user: dict) -> list[dict]:
    city = user.get('city', '')
    field = user.get('field', '')
    degree = user.get('degree', '')
    experience = user.get('experience', '')
    certs = user.get('certifications') or '无'

    # ---- 第零步：尝试爬取国聘网真实岗位数据 ----
    real_jobs = crawl_iguopin(field, city)
    if len(real_jobs) >= 3:
        # 爬取成功，用真实数据 + AI 分析匹配度
        print(f"[推荐] 使用国聘网真实数据，共 {len(real_jobs)} 个岗位，AI 分析匹配度")
        jobs = _ai_analyze_real_jobs(user, real_jobs[:3])
        # 构造多平台搜索链接
        for j in jobs:
            keyword = j.pop('search_keyword', j.get('job_title', field))
            j['search_links'] = build_search_links(keyword, city, j.get('enterprise_type', '国企'), j.get('job_title', ''))
            if not j.get('detail_link') or 'iguopin' not in j.get('detail_link', ''):
                j['detail_link'] = j['search_links'][0]['url']
            if not j.get('company'):
                j['company'] = j.get('company') or f'点击查看{city}在招公司'
        return jobs
    else:
        print("[推荐] 国聘网数据不足，回退AI生成")

    # ---- 第一轮：生成推荐 ----
    prompt = f"""你是一名资深猎头，精通中国{city}市的就业市场，尤其熟悉国企招聘。请根据以下求职者画像，推荐 3 个最匹配的岗位方向。

【最高原则 — 岗位要求必须真实，禁止反向定制】
岗位的任职要求、薪资、学历等必须基于该岗位在真实招聘市场的【实际要求】，绝不能根据求职者资历反向定制！
- 如果求职者是985硕士，但真实岗位要求是"硕士"，那就写"硕士"，不能写"985硕士"或"211硕士"
- 如果求职者有高级证书，但真实岗位不要求该证书，就不能写进任职要求
- 如果求职者有5年经验，但真实岗位要求3年，就写"3年以上"，不能写"5年以上"
- 薪资必须基于真实市场水平，不能为了匹配求职者而虚高
- match_score 反映求职者条件【超出】岗位要求的程度（超出越多分越高），而不是修改岗位要求来凑分

【严格规则 — 必须遵守】
1. 国企岗位占比：3 个岗位中至少 2 个必须是国企方向（国家电网/南方电网/三大运营商/国有四大行/中石油中石化/中国建筑/中铁/中交/烟草/水务/燃气/城投/地铁等）
2. 禁止虚构公司名称！company 字段固定填空字符串 ""
3. 禁止编造详情链接！detail_link 字段固定填空字符串 ""
4. 薪资范围必须是{city}市该岗位的【真实市场水平】，参考 BOSS直聘/智联招聘的实际数据，不能虚高
5. 任职要求基于真实招聘市场，不得根据求职者资历反向定制（见最高原则）
6. 岗位职责必须真实、具体，符合该岗位的实际工作内容
7. 福利待遇必须是该类企业的常见真实福利
8. match_score 基于求职者条件与【真实岗位要求】的匹配度计算
9. enterprise_type 只能是"国企""私企""外企"之一

【国企岗位专项要求】
A. job_title 格式为"单位简称-岗位名"，如"国家电网-配电运维工程师"
B. 国企薪资参考真实国企薪酬体系：地市级国企基层岗到手月薪通常6k-12k，年终奖2-5万，不能虚高
C. 国企福利包含：编制/六险二金/年终奖/带薪年假/体检等
D. 国企任职要求基于真实国企招聘公告，体现学历层次/专业对口/年龄限制等
E. 国企岗位职责符合该国企主营业务
F. search_keyword 用"单位名+岗位关键词"格式
G. 【信息来源优先级】国企岗位信息必须优先从以下官方权威来源获取：①国聘网(iguopin.com) ②国资委(sasac.gov.cn) ③人社部就业网(job.mohrss.gov.cn) ④新职业网(ncss.cn)。如官方来源找不到匹配岗位，再从企业自有官方招聘平台获取（国家电网人力资源招聘平台、中国铁路人才招聘网、中国烟草总公司人才招聘平台、国有六大行/三大运营商/建筑类央企各自的招聘官网）。最后才考虑BOSS直聘等商业平台。
H. 从官方来源获取的信息仍需经过自检验证真实性，确保薪资/要求/职责与官方招聘公告一致

返回严格的 JSON 数组，每个元素包含：
- job_title：岗位名称（国企带单位简称前缀）
- company：固定填空字符串 ""
- enterprise_type：国企/私企/外企
- match_score：匹配度（0-100 整数，基于求职者超出真实岗位要求的程度）
- detail_link：固定填空字符串 ""
- salary_range：薪资范围（{city}市真实市场水平，不虚高）
- responsibilities：岗位职责（4-5 条，基于真实岗位）
- requirements：任职要求（4-5 条，基于真实招聘市场，不反向定制）
- benefits：福利待遇（3-4 条真实福利）
- development：职业发展前景（1-2 句）
- work_location：{city}市具体区域
- search_keyword：搜索关键词（国企用"单位名+岗位名"）

求职者画像（仅供匹配参考，不写入岗位要求）：
- 城市：{city}
- 学历：{degree}
- 工作经验：{experience}
- 求职方向：{field}
- 权威证书：{certs}

只返回 JSON 数组，不要任何额外文字。"""
    jobs = _call_ai(prompt)

    # ---- 第二轮：通用自检修正 ----
    jobs = _validate_and_fix(user, jobs)

    # ---- 第三轮：国企专项自检 ----
    jobs = _validate_guoqi_jobs(user, jobs)

    # ---- 构造多平台真实招聘搜索链接 ----
    for j in jobs:
        keyword = j.pop('search_keyword', j['job_title'])
        j['search_links'] = build_search_links(keyword, city, j.get('enterprise_type', ''), j.get('job_title', ''))
        j['detail_link'] = j['search_links'][0]['url']  # 默认指向第一个平台
        if not j.get('company'):
            j['company'] = f'点击查看{city}在招公司'

    return jobs


def _ai_analyze_real_jobs(user: dict, real_jobs: list[dict]) -> list[dict]:
    """AI 分析真实爬取岗位的匹配度，补充详细说明（不虚构岗位信息）"""
    prompt = f"""以下是来自国聘网的真实爬取岗位数据。请根据求职者画像，为每个岗位分析匹配度并整理详细说明。

【严格规则】
1. 岗位名称、公司名称、薪资、工作地点、学历要求保持原样，不要修改（这些是真实数据）
2. match_score 基于求职者条件与真实岗位要求的匹配度计算
3. responsibilities 和 requirements 从 contents 字段中提取整理（如果 contents 有内容）
4. 如果 contents 为空，基于岗位名称生成合理的职责和要求
5. benefits 基于国企常见真实福利（编制/六险二金/年终奖等）
6. development 基于该岗位的职业发展前景
7. search_keyword 用岗位名称作为搜索关键词
8. 保留 source 字段为"国聘网（真实数据）"
9. 保留 detail_link 字段不变

求职者画像：
- 城市：{user.get('city')}
- 学历：{user.get('degree')}
- 工作经验：{user.get('experience')}
- 求职方向：{user.get('field')}
- 权威证书：{user.get('certifications') or '无'}

真实岗位数据（JSON）：
{json.dumps(real_jobs, ensure_ascii=False, indent=2)}

返回 JSON 数组，每个元素包含所有原有字段 + match_score + responsibilities + requirements + benefits + development + search_keyword。
只返回 JSON 数组，不要任何额外文字。"""
    try:
        result = _call_ai(prompt)
        print(f"[AI分析] 真实岗位分析完成，共 {len(result)} 个岗位")
        return result
    except Exception as e:
        print(f"[AI分析] 分析失败，使用原始数据: {e}")
        # 如果 AI 分析失败，直接返回原始数据（补充默认值）
        for j in real_jobs:
            j['match_score'] = 75
            j['search_keyword'] = j.get('job_title', '')
            if not j.get('responsibilities'):
                j['responsibilities'] = '详见岗位详情页'
            if not j.get('requirements'):
                j['requirements'] = '详见岗位详情页'
            if not j.get('benefits'):
                j['benefits'] = '编制/六险二金/年终奖'
            if not j.get('development'):
                j['development'] = '国企平台稳定，发展前景良好'
        return real_jobs


def _call_ai(prompt: str) -> any:
    """调用智谱 GLM 并解析 JSON"""
    resp = ai_client.chat.completions.create(
        model="glm-4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    content = resp.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.strip("`").lstrip("json").strip()
    return json.loads(content)


def _validate_and_fix(user: dict, jobs: list[dict]) -> list[dict]:
    """AI 自检环节：审查岗位要求的真实性和准确性，禁止反向定制"""
    check_prompt = f"""你是猎头质量审核员。请逐一审查以下岗位推荐，严格检查并修正：

【最高原则 — 岗位要求必须真实，禁止反向定制】
岗位的任职要求、薪资、学历等必须基于真实招聘市场，绝不能根据求职者资历反向定制！
- 求职者学历是"{user.get('degree')}"，但如果真实岗位要求是"硕士"，requirements 只能写"硕士"，不能写"985硕士"或"211硕士"
- 求职者经验是"{user.get('experience')}"，但如果真实岗位要求3年，就写"3年以上"，不能写求职者的实际年数
- 求职者证书是"{user.get('certifications') or '无'}"，但如果真实岗位不要求该证书，就不能写进 requirements
- 薪资必须基于真实市场水平，不能为了匹配求职者而虚高

【检查项】
1. 反向定制检查：requirements 中是否混入了求职者个人资历（如985/211/具体证书/具体年数）？如果有，改为真实岗位的市场要求。
2. 薪资虚高检查：salary_range 是否高于{user.get('city')}市该岗位的真实市场水平？参考：国企基层6k-12k/月，中级10k-18k/月。虚高的必须下调。
3. 学历虚高检查：requirements 中的学历要求是否高于真实岗位要求？如岗位实际要求本科，不能写硕士。
4. 国企岗位比例：至少 2 个国企方向。不足则将最匹配的私企岗位改为国企。
5. 岗位职责真实性：是否泛泛而谈？必须符合该岗位实际工作。
6. 福利待遇真实性：国企要含编制/六险二金/年终奖。
7. match_score 合理性：基于求职者条件超出真实岗位要求的程度。
8. work_location 为{user.get('city')}市具体区域。
9. company 和 detail_link 为空字符串 ""。
10. search_keyword 保留，国企用"单位名+岗位名"。

求职者画像（仅供匹配参考，不写入岗位要求）：
- 城市：{user.get('city')}
- 学历：{user.get('degree')}
- 工作经验：{user.get('experience')}
- 求职方向：{user.get('field')}
- 权威证书：{user.get('certifications') or '无'}

待审查的推荐结果（JSON）：
{json.dumps(jobs, ensure_ascii=False, indent=2)}

请修正所有问题，返回修正后的完整 JSON 数组（保持原字段结构，包含 search_keyword）。
只返回 JSON 数组，不要任何额外文字。"""
    try:
        fixed = _call_ai(check_prompt)
        print(f"[自检] 通用自检完成，已审查 {len(fixed)} 个岗位")
        return fixed
    except Exception as e:
        print(f"[自检] 通用自检失败，使用原始结果: {e}")
        return jobs


def _validate_guoqi_jobs(user: dict, jobs: list[dict]) -> list[dict]:
    """国企专项自检：专门审查国企岗位的真实性和准确性"""
    guoqi_jobs = [j for j in jobs if j.get('enterprise_type') == '国企']
    if not guoqi_jobs:
        print("[国企自检] 无国企岗位，跳过")
        return jobs

    check_prompt = f"""你是国企招聘专家，熟悉各大国企的真实招聘情况。请逐一审查以下国企岗位推荐，严格检查并修正：

【最高原则 — 岗位要求必须真实，禁止反向定制】
国企岗位的任职要求、薪资、学历等必须基于该国企真实招聘公告，绝不能根据求职者资历反向定制！
- 求职者学历是"{user.get('degree')}"，但如果该国企真实要求是"本科"，requirements 只能写"本科"，不能写"硕士"或"985本科"
- 求职者经验是"{user.get('experience')}"，但如果该国企真实要求3年，就写"3年以上"，不能写求职者的实际年数
- 求职者证书是"{user.get('certifications') or '无'}"，但如果该国企不要求该证书，就不能写进 requirements
- 薪资必须基于该国企真实薪酬水平，不能虚高

【国企专项检查项】
1. 反向定制检查：requirements 中是否混入了求职者个人资历（如985/211/具体证书/具体年数）？如果有，改为该国企真实招聘的市场要求。
2. 单位真实性：job_title 必须包含真实存在的国企单位名。不真实的替换为同行业真实国企。
3. 岗位真实性：岗位必须是该国企真实招聘的岗位类型。
4. 薪资合理性：必须符合该国企在{user.get('city')}市的真实薪酬水平，不能虚高。参考：地市级国企基层岗到手月薪6k-12k，年终奖2-5万。中级岗10k-18k，年终奖3-8万。
5. 学历虚高检查：requirements 中学历要求是否高于该国企真实要求？如岗位实际要求本科，不能写硕士。
6. 福利完整性：必须含编制/六险二金/年终奖/带薪年假等。
7. 职责匹配性：岗位职责符合该国企主营业务。
8. match_score：基于求职者条件超出真实岗位要求的程度。
9. search_keyword：用"单位名+岗位关键词"格式。
10. 【来源权威性】岗位信息是否基于官方权威来源？优先级：①国聘网(iguopin.com) ②国资委(sasac.gov.cn) ③人社部(job.mohrss.gov.cn) ④新职业网(ncss.cn) ⑤企业自有官方招聘平台。如果岗位信息明显不符合官方招聘公告的实际情况，请基于官方来源修正。

待审查的国企岗位（JSON）：
{json.dumps(guoqi_jobs, ensure_ascii=False, indent=2)}

请修正所有问题，返回修正后的完整 JSON 数组（保持原字段结构，包含 search_keyword）。
只返回 JSON 数组，不要任何额外文字。"""
    try:
        fixed_guoqi = _call_ai(check_prompt)
        print(f"[国企自检] 国企专项自检完成，已审查 {len(fixed_guoqi)} 个国企岗位")
        # 用修正后的国企岗位替换原列表中的国企岗位
        fixed_map = {i: fg for i, fg in enumerate(fixed_guoqi)}
        guoqi_idx = 0
        for j in jobs:
            if j.get('enterprise_type') == '国企':
                if guoqi_idx in fixed_map:
                    jobs[jobs.index(j)] = fixed_map[guoqi_idx]
                    guoqi_idx += 1
        return jobs
    except Exception as e:
        print(f"[国企自检] 国企专项自检失败，使用通用自检结果: {e}")
        return jobs


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


# ============ 生成 H5 岗位推荐页面 ============
def generate_h5_report(user: dict, jobs: list[dict]) -> str:
    """生成自包含的 H5 页面，手机浏览器直接打开查看，返回文件路径"""
    user_id = user.get('id', 'unknown')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def esc(v):
        return html.escape(str(v)) if v else '—'

    def list_items(val):
        if isinstance(val, str):
            items = [x.strip() for x in val.split('\n') if x.strip()]
        elif isinstance(val, list):
            items = val
        else:
            items = []
        return ''.join(f'<li>{html.escape(str(x))}</li>' for x in items)

    type_colors = {
        "国企": "#dc2626",
        "私企": "#2563eb",
        "外企": "#16a34a",
    }

    cards = []
    for idx, job in enumerate(jobs, 1):
        etype = job.get('enterprise_type', '—')
        etype_color = type_colors.get(etype, "#6b7280")
        cards.append(f"""
    <div class="card">
      <div class="card-header">
        <span class="job-index">{idx}</span>
        <div class="job-title-wrap">
          <h2>{esc(job.get('job_title'))}</h2>
          <span class="tag" style="background:{etype_color}">{esc(etype)}</span>
          {f'<span class="tag source-tag">{esc(job.get("source", "AI推荐"))}</span>' if job.get('source') else ''}
        </div>
      </div>
      <div class="card-body">
        <div class="info-row">
          <div class="info-item"><span class="label">公司</span><span class="value">{esc(job.get('company'))}</span></div>
          <div class="info-item"><span class="label">薪资</span><span class="value salary">{esc(job.get('salary_range', '面议'))}</span></div>
        </div>
        <div class="info-row">
          <div class="info-item"><span class="label">匹配度</span><span class="value match">{esc(job.get('match_score', 0))}%</span></div>
          <div class="info-item"><span class="label">地点</span><span class="value">{esc(job.get('work_location'))}</span></div>
        </div>
        <div class="match-bar"><div class="match-fill" style="width:{esc(job.get('match_score', 0))}%"></div></div>
        <div class="section"><h3>📋 岗位职责</h3><ul>{list_items(job.get('responsibilities'))}</ul></div>
        <div class="section"><h3>✅ 任职要求</h3><ul>{list_items(job.get('requirements'))}</ul></div>
        <div class="section"><h3>🎁 福利待遇</h3><ul>{list_items(job.get('benefits'))}</ul></div>
        <div class="section"><h3>📈 职业发展</h3><p>{esc(job.get('development', '暂无信息'))}</p></div>
        <div class="platform-links">
          <div class="platform-title">🔗 点击查看真实在招岗位</div>
          <div class="platform-hint">💡 提示：进入招聘平台后，请手动选择城市「{esc(user.get('city', ''))}」以获取当地岗位</div>
          <div class="platform-btns">
            {''.join(f'<a class="platform-btn" href="{esc(sl["url"])}" target="_blank">{sl["icon"]} {esc(sl["name"])}</a>' for sl in job.get('search_links', []))}
          </div>
        </div>
      </div>
    </div>""")

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>智能岗位推荐报告</title>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#1f2937;line-height:1.6;max-width:640px;margin:0 auto;padding-bottom:40px}}
    .header{{background:linear-gradient(135deg,#2563eb,#7c3aed);color:#fff;padding:32px 20px 24px;text-align:center;position:sticky;top:0;z-index:10;box-shadow:0 2px 12px rgba(37,99,235,.3)}}
    .header h1{{font-size:22px;margin-bottom:6px}}
    .header .date{{font-size:12px;opacity:.85}}
    .user-info{{background:#fff;margin:12px;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
    .user-info h2{{font-size:15px;color:#2563eb;margin-bottom:12px}}
    .user-info .grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
    .user-info .item{{font-size:13px}}
    .user-info .item .k{{color:#6b7280;margin-right:4px}}
    .user-info .item .v{{color:#1f2937;font-weight:600}}
    .card{{background:#fff;margin:12px;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
    .card-header{{display:flex;align-items:center;gap:12px;padding:16px;background:linear-gradient(90deg,#eff6ff,#f0f9ff)}}
    .job-index{{width:28px;height:28px;border-radius:50%;background:#2563eb;color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;flex-shrink:0}}
    .job-title-wrap{{flex:1;min-width:0}}
    .job-title-wrap h2{{font-size:16px;color:#1f2937}}
    .tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;color:#fff;margin-top:2px}}
    .source-tag{{background:#16a34a!important;margin-left:4px}}
    .card-body{{padding:16px}}
    .info-row{{display:flex;gap:12px;margin-bottom:8px}}
    .info-item{{flex:1;display:flex;flex-direction:column}}
    .info-item .label{{font-size:11px;color:#9ca3af}}
    .info-item .value{{font-size:14px;font-weight:600;color:#1f2937}}
    .info-item .value.salary{{color:#dc2626}}
    .info-item .value.match{{color:#16a34a}}
    .match-bar{{height:6px;background:#e5e7eb;border-radius:3px;margin:8px 0 16px;overflow:hidden}}
    .match-fill{{height:100%;background:linear-gradient(90deg,#16a34a,#22c55e);border-radius:3px;transition:width .3s}}
    .section{{margin-top:14px}}
    .section h3{{font-size:13px;color:#374151;margin-bottom:6px}}
    .section ul{{padding-left:18px}}
    .section ul li{{font-size:13px;color:#4b5563;margin-bottom:4px}}
    .section p{{font-size:13px;color:#4b5563}}
    .platform-links{{margin-top:16px;border-top:1px dashed #e5e7eb;padding-top:14px}}
    .platform-title{{font-size:13px;color:#374151;margin-bottom:8px;font-weight:600}}
    .platform-hint{{font-size:11px;color:#9ca3af;margin-bottom:10px;background:#f3f4f6;padding:6px 10px;border-radius:6px}}
    .platform-btns{{display:flex;flex-wrap:wrap;gap:8px}}
    .platform-btn{{display:inline-block;padding:8px 14px;border-radius:8px;font-size:12px;font-weight:600;text-decoration:none;color:#fff;background:linear-gradient(135deg,#2563eb,#7c3aed)}}
    .platform-btn:nth-child(4n+1){{background:linear-gradient(135deg,#2563eb,#3b82f6)}}
    .platform-btn:nth-child(4n+2){{background:linear-gradient(135deg,#16a34a,#22c55e)}}
    .platform-btn:nth-child(4n+3){{background:linear-gradient(135deg,#ea580c,#f97316)}}
    .platform-btn:nth-child(4n){{background:linear-gradient(135deg,#dc2626,#ef4444)}}
    .footer{{text-align:center;padding:20px;font-size:11px;color:#9ca3af}}
  </style>
</head>
<body>
  <div class="header">
    <h1>📋 智能岗位推荐报告</h1>
    <div class="date">{datetime.now().strftime("%Y年%m月%d日 %H:%M")} 生成</div>
  </div>
  <div class="user-info">
    <h2>👤 求职者信息</h2>
    <div class="grid">
      <div class="item"><span class="k">城市</span><span class="v">{esc(user.get('city'))}</span></div>
      <div class="item"><span class="k">学历</span><span class="v">{esc(user.get('degree'))}</span></div>
      <div class="item"><span class="k">工作经验</span><span class="v">{esc(user.get('experience'))}</span></div>
      <div class="item"><span class="k">求职方向</span><span class="v">{esc(user.get('field'))}</span></div>
      <div class="item"><span class="k">权威证书</span><span class="v">{esc(user.get('certifications') or '无')}</span></div>
    </div>
  </div>
  {''.join(cards)}
  <div class="footer">本报告由智能岗位推荐系统自动生成 | Powered by 智谱 GLM-4-Flash</div>
</body>
</html>"""

    filename = f"job_h5_user{user_id}_{timestamp}.html"
    filepath = os.path.join(REPORT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[H5] 已生成: {filepath}")
    return filepath


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

        # 各平台搜索链接
        doc.add_heading('查看真实在招岗位', level=3)
        for sl in job.get('search_links', []):
            p = doc.add_paragraph()
            run = p.add_run(f"{sl['icon']} {sl['name']}：{sl['url']}")
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x25, 0x63, 0xeb)

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
    filename = f"job_report_user{user_id}_{timestamp}.docx"
    filepath = os.path.join(REPORT_DIR, filename)
    doc.save(filepath)
    print(f"[报告] 已生成: {filepath}")
    return filepath


# ============ 上传报告到 Supabase Storage ============
STORAGE_BUCKET = "reports"  # 需要在 Supabase 创建名为 reports 的公开 bucket


def upload_to_storage(filepath: str, content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document") -> str | None:
    """上传文件到 Supabase Storage，返回公开下载链接；失败则返回 None"""
    filename = os.path.basename(filepath)
    try:
        with open(filepath, "rb") as f:
            file_data = f.read()
        upload_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": content_type,
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


# ============ 邮件推送 ============
def send_email(user: dict, h5_url: str | None, jobs: list[dict]):
    """通过 SMTP 发送邮件，包含 H5 链接和岗位摘要"""
    user_email = user.get('email')
    if not user_email:
        print("[邮件] 用户未提供邮箱，跳过")
        return
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS]):
        print("[邮件] SMTP 未配置，跳过邮件推送")
        return

    city = user.get('city', '—')
    field = user.get('field', '求职方向')
    subject = f"【岗位推荐】{field} - {city}（{datetime.now().strftime('%m月%d日 %H:%M')}）"

    # 岗位摘要
    job_lines = []
    for i, j in enumerate(jobs, 1):
        job_lines.append(
            f"  {i}. {j.get('job_title', '—')}"
            f" | 匹配度 {j.get('match_score', 0)}%"
            f" | 薪资 {j.get('salary_range', '面议')}"
            f" | {j.get('enterprise_type', '—')}"
        )
    jobs_summary = "\n".join(job_lines)

    body = f"""您好！

您的智能岗位推荐报告已生成。

══════════════════════════════
求职者：{city} | {field}
══════════════════════════════

本次推荐 {len(jobs)} 个岗位：
{jobs_summary}

──────────────────────────────
📱 点击查看完整岗位推荐详情（H5页面）：
{h5_url or '（链接生成失败，请稍后在GitHub Actions中查看）'}
──────────────────────────────

H5页面中包含：
  - 每个岗位的详细职责、任职要求、福利待遇
  - 各官方招聘平台的真实在招岗位搜索链接
    （国聘网/国资委/人社部/新职业网/企业官网）

祝您求职顺利！

---
智能岗位推荐系统
生成时间：{datetime.now().strftime("%Y年%m月%d日 %H:%M")}
Powered by 智谱 GLM-4-Flash
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = user_email

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [user_email], msg.as_string())
        print(f"[邮件] 已发送至 {user_email}")
    except Exception as e:
        print(f"[邮件] 发送失败: {e}")


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
        md_lines.append(f"| 来源 | {j.get('source', 'AI推荐方向')} |")
        md_lines.append(f"")
        # 各平台搜索链接
        if j.get('search_links'):
            md_lines.append(f"**🔗 查看真实在招岗位：**")
            for sl in j['search_links']:
                md_lines.append(f"- [{sl['icon']} {sl['name']}]({sl['url']})")
            md_lines.append(f"")
        md_lines.append(f"---")
        md_lines.append(f"")
    # 查看链接（H5 页面，手机直接打开）
    if download_url:
        md_lines.append(f"📱 **[点击查看完整岗位推荐详情]({download_url})**")
        md_lines.append(f"")
        md_lines.append(f"> 手机浏览器直接打开，查看每个岗位的职责、要求、福利等完整信息")
    else:
        md_lines.append(f"> 完整岗位推荐报告已生成，请前往 GitHub Actions 下载")
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
                # 先生成 H5 页面并上传，获取可直接跳转的链接
                h5_path = generate_h5_report(u, saved)
                h5_url = upload_to_storage(h5_path, content_type="text/html; charset=utf-8")
                # 将每个岗位的详情链接指向 H5 页面
                if h5_url:
                    for j in saved:
                        j["detail_link"] = h5_url
                # 生成 docx 报告（详情链接已指向 H5 页面）
                report_path = generate_docx_report(u, saved)
                generated_reports.append(report_path)
                # 推送微信/邮箱，H5 链接可直接在手机浏览器跳转
                push_wechat(u, saved, h5_url)
                # 邮件推送 H5 链接至用户邮箱
                send_email(u, h5_url, saved)
                print(f"[主流程] 用户 {u['id']} 推荐了 {len(saved)} 个岗位，H5+docx+邮件已推送")
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
