"""
岗位推荐脚本（每8小时由 GitHub Actions 触发）
使用 Supabase REST API，不依赖数据库直连，避免端口 5432 不可达问题

流程：
  1. 通过 REST API 读取所有用户资料
  2. 获取岗位推荐数据（由 workbuddy 爬取程序填充）
  3. 通过 REST API 写入 job_recommendations 表
  4. 生成 H5/docx 岗位推荐报告
  5. 通过 PushPlus 微信推送 + SMTP 邮件推送
"""

import os
import sys
import json
import html
import re
import time
import random
import smtplib
import traceback
from urllib.parse import quote
from datetime import datetime
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

# ============ 初始化客户端 ============
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # service_role key（绕过 RLS）
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


# ============ 爬虫辅助函数 ============
COMMON_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20  # 每个网站爬取超时（秒）

# 学历等级映射
_EDU_LEVEL = {
    "不限": 0, "大专": 1, "专科": 1, "本科": 2, "学士": 2,
    "硕士": 3, "研究生": 3, "博士": 4, "MBA": 3,
}
# 经验等级映射
_EXP_LEVEL = {
    "不限": 0, "无经验": 0, "应届": 1, "1年以下": 1, "1年": 1,
    "1-3年": 2, "3-5年": 3, "5-10年": 4, "10年以上": 5,
}


def _safe_request(url, method="GET", headers=None, json_body=None, timeout=REQUEST_TIMEOUT):
    """安全的 HTTP 请求封装"""
    default_headers = {
        "User-Agent": COMMON_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if headers:
        default_headers.update(headers)
    try:
        if method.upper() == "POST":
            resp = requests.post(url, headers=default_headers, json=json_body, timeout=timeout)
        else:
            resp = requests.get(url, headers=default_headers, timeout=timeout)
        resp.raise_for_status()
        return resp
    except requests.exceptions.Timeout:
        print(f"  [WARNING] 请求超时: {url}")
        return None
    except Exception as e:
        print(f"  [WARNING] 请求异常: {url} - {e}")
        return None


def _parse_edu_level(edu_str):
    """从字符串中解析学历等级"""
    if not edu_str:
        return 0
    for key, val in _EDU_LEVEL.items():
        if key in str(edu_str):
            return val
    return 0


def _parse_exp_level(exp_str):
    """从字符串中解析经验等级"""
    if not exp_str:
        return 0
    for key, val in _EXP_LEVEL.items():
        if key in str(exp_str):
            return val
    m = re.search(r"(\d+)\s*年", str(exp_str))
    if m:
        years = int(m.group(1))
        if years <= 1:
            return 1
        elif years <= 3:
            return 2
        elif years <= 5:
            return 3
        elif years <= 10:
            return 4
        else:
            return 5
    return 0


def _parse_experience_years(exp_str):
    """从用户经验字符串中解析年数"""
    if not exp_str:
        return 0
    m = re.search(r"(\d+)", str(exp_str))
    return int(m.group(1)) if m else 0


def _random_delay():
    """随机延迟，避免频繁请求"""
    time.sleep(random.uniform(1.0, 2.0))


def _extract_section(text, keywords, max_lines=10):
    """从岗位描述中提取特定部分（职责/要求等）"""
    if not text:
        return ""
    all_headers = [
        "岗位职责", "工作内容", "职位描述", "工作职责", "主要职责",
        "任职要求", "岗位要求", "任职资格", "任职条件", "应聘条件",
        "福利待遇", "薪酬福利", "工作时间", "工作地点", "联系方式",
    ]
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return ""
    start_idx = -1
    for i, line in enumerate(lines):
        if any(kw in line for kw in keywords):
            start_idx = i
            break
    if start_idx < 0:
        return ""
    result = []
    for i in range(start_idx, len(lines)):
        line = lines[i]
        if i > start_idx and any(h in line for h in all_headers):
            if not any(kw in line for kw in keywords):
                break
        result.append(line)
        if len(result) >= max_lines:
            break
    return "\n".join(result) if result else ""


def _extract_responsibilities(contents):
    """从岗位描述中提取岗位职责"""
    if not contents:
        return "详见岗位详情页"
    resp = _extract_section(contents, ["岗位职责", "工作内容", "职位描述", "工作职责", "主要职责"])
    if resp:
        return resp
    lines = [l.strip() for l in contents.split("\n") if l.strip()]
    return "\n".join(lines[:8]) if lines else "详见岗位详情页"


def _extract_requirements(contents, edu_str="", exp_str=""):
    """从岗位描述中提取任职要求"""
    if not contents:
        parts = []
        if edu_str:
            parts.append(f"学历要求：{edu_str}")
        if exp_str:
            parts.append(f"经验要求：{exp_str}")
        return "\n".join(parts) if parts else "详见岗位详情页"
    req = _extract_section(contents, ["任职要求", "岗位要求", "任职资格", "任职条件", "应聘条件"])
    if req:
        return req
    lines = contents.split("\n")
    req_lines = [l.strip() for l in lines if any(kw in l for kw in ["要求", "具备", "熟悉", "掌握", "优先", "以上"])]
    if req_lines:
        return "\n".join(req_lines[:8])
    parts = []
    if edu_str:
        parts.append(f"学历要求：{edu_str}")
    if exp_str:
        parts.append(f"经验要求：{exp_str}")
    return "\n".join(parts) if parts else "详见岗位详情页"


def _generate_benefits(contents):
    """从岗位描述中提取福利待遇"""
    if not contents:
        return "五险一金/年终奖/带薪年假/定期体检"
    benefit_keywords = [
        "五险一金", "六险二金", "五险二金", "七险一金", "七险二金",
        "年终奖", "年底双薪", "带薪年假", "餐补", "免费三餐", "免费午餐",
        "交通补贴", "通讯补贴", "住房补贴", "体检", "补充医疗", "商业保险",
        "弹性工作", "周末双休", "双休", "股票期权", "期权", "培训", "团建",
    ]
    found = []
    text = str(contents)
    for kw in benefit_keywords:
        if kw in text:
            found.append(kw)
    if found:
        seen = set()
        unique = []
        for b in found:
            if b not in seen:
                seen.add(b)
                unique.append(b)
        return "/".join(unique)
    return "五险一金/年终奖/带薪年假/定期体检"


def _determine_enterprise_type(info_str, source):
    """根据公司信息字符串判断企业类型"""
    text = str(info_str) if info_str else ""
    if any(kw in text for kw in ["央企", "国企", "国有", "国资委", "中央企业"]):
        return "国企"
    if any(kw in text for kw in ["外资", "外企", "合资", "外商独资"]):
        return "外企"
    if source in ["国聘网", "国资委央企招聘"]:
        return "国企"
    return "私企"


def _generate_development(enterprise_type):
    """根据企业类型生成职业发展前景描述"""
    if enterprise_type == "国企":
        return "国企平台稳定，晋升通道清晰，福利保障完善"
    elif enterprise_type == "外企":
        return "国际化平台，职业发展路径多元，薪酬体系完善"
    else:
        return "市场化薪酬，成长空间大，适合快速积累经验"


def _is_city_match(job_location, user_city):
    """判断岗位地点是否匹配用户城市"""
    if not job_location or not user_city:
        return False
    job_loc = str(job_location).replace("市", "").strip()
    user_c = str(user_city).replace("市", "").strip()
    return user_c in job_loc or job_loc in user_c


# ============ 匹配度计算 ============
def calculate_match_score(job, user):
    """
    计算岗位与用户的匹配度 (0-100)。
    学历匹配(25) + 经验匹配(25) + 方向匹配(30) + 城市匹配(20)
    """
    score = 0
    # 学历匹配 (0-25)
    user_edu = user.get("degree") or user.get("education") or ""
    job_edu = job.get("_raw_edu", "")
    user_edu_level = _parse_edu_level(user_edu)
    job_edu_level = _parse_edu_level(job_edu)
    if job_edu_level == 0:
        score += 20
    elif user_edu_level >= job_edu_level:
        score += 25
    elif user_edu_level == job_edu_level - 1:
        score += 15
    else:
        score += 5
    # 经验匹配 (0-25)
    user_exp = user.get("experience") or ""
    job_exp = job.get("_raw_exp", "")
    user_exp_level = _parse_exp_level(user_exp)
    job_exp_level = _parse_exp_level(job_exp)
    if job_exp_level == 0:
        score += 20
    elif user_exp_level >= job_exp_level:
        score += 25
    elif user_exp_level == job_exp_level - 1:
        score += 15
    else:
        score += 5
    # 方向匹配 (0-30)
    user_field = (user.get("field") or user.get("direction") or "").lower().strip()
    job_title = (job.get("job_title") or "").lower()
    job_desc = (job.get("_raw_contents") or "").lower()
    if user_field:
        if user_field in job_title:
            score += 30
        elif any(w in job_title for w in user_field.split() if len(w) >= 2):
            score += 20
        elif user_field in job_desc:
            score += 15
        else:
            field_kws = [w for w in re.split(r"[/\-_,，\s]+", user_field) if len(w) >= 2]
            match_cnt = sum(1 for kw in field_kws if kw in job_title or kw in job_desc)
            score += min(match_cnt * 8, 20) if match_cnt > 0 else 5
    else:
        score += 10
    # 城市匹配 (0-20)
    user_city = user.get("city", "")
    job_location = job.get("work_location", "")
    if _is_city_match(job_location, user_city):
        score += 20
    elif job_location:
        score += 5
    else:
        score += 5
    return max(0, min(100, score))


# ============ 爬虫：国聘网（API）============
def crawl_iguopin(keyword, city=None):
    """爬取国聘网（国资央企招聘平台）岗位数据，使用公开API"""
    print(f"\n[国聘网] 开始爬取，关键词: {keyword}，城市: {city}")
    api_url = "https://gp-api.iguopin.com/api/jobs/v1/list"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Device": "pc",
        "Subsite": "cujiuye",
        "Version": "5.0.0",
        "User-Agent": COMMON_UA,
        "Referer": "https://www.iguopin.com/",
        "Origin": "https://www.iguopin.com",
    }
    payload = {"page": 1, "page_size": 50, "keyword": keyword}
    resp = _safe_request(api_url, method="POST", headers=headers, json_body=payload)
    if not resp:
        print("[国聘网] API请求失败")
        return []
    try:
        data = resp.json()
    except Exception as e:
        print(f"[国聘网] JSON解析失败: {e}")
        return []
    job_list = []
    if isinstance(data, dict):
        job_list = data.get("data", {}).get("list", [])
    elif isinstance(data, list):
        job_list = data
    print(f"[国聘网] API返回 {len(job_list)} 条岗位")
    results = []
    for item in job_list:
        try:
            job_id = item.get("job_id") or item.get("id") or ""
            job_name = item.get("job_name") or item.get("name") or ""
            company_name = item.get("company_name") or item.get("company") or ""
            if not job_name or not company_name:
                continue
            min_wage = item.get("min_wage") or ""
            max_wage = item.get("max_wage") or ""
            if min_wage and max_wage:
                salary_range = f"{min_wage}-{max_wage}元/月"
            elif min_wage:
                salary_range = f"{min_wage}元/月起"
            else:
                salary_range = item.get("salary") or "面议"
            edu = item.get("education_cn") or item.get("education") or ""
            exp = item.get("experience_cn") or item.get("experience") or item.get("work_years") or ""
            district_list = item.get("district_list") or []
            if isinstance(district_list, list) and district_list:
                work_location = district_list[0].get("area_cn") or ""
            else:
                work_location = item.get("city") or item.get("city_cn") or ""
            contents = item.get("contents") or item.get("description") or ""
            company_info = item.get("company_info") or {}
            nature = company_info.get("nature_cn", "") if isinstance(company_info, dict) else str(company_info)
            enterprise_type = _determine_enterprise_type(nature + " " + company_name, "国聘网")
            detail_link = f"https://www.iguopin.com/job/detail?id={job_id}" if job_id else ""
            results.append({
                "job_title": job_name,
                "company": company_name,
                "enterprise_type": enterprise_type,
                "detail_link": detail_link,
                "salary_range": salary_range,
                "responsibilities": _extract_responsibilities(contents),
                "requirements": _extract_requirements(contents, edu, exp),
                "benefits": _generate_benefits(contents),
                "development": _generate_development(enterprise_type),
                "work_location": work_location or "全国",
                "source": "国聘网（真实数据）",
                "search_keyword": keyword,
                "_raw_contents": contents,
                "_raw_edu": edu,
                "_raw_exp": exp,
            })
        except Exception as e:
            print(f"  [WARNING] 解析国聘网岗位失败: {e}")
    print(f"[国聘网] 成功解析 {len(results)} 条岗位")
    return results


# ============ 爬虫：BOSS直聘（Playwright）============
def crawl_boss(keyword, city=None):
    """爬取BOSS直聘岗位数据，需要Playwright渲染JS页面"""
    print(f"\n[BOSS直聘] 开始爬取，关键词: {keyword}，城市: {city}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[BOSS直聘] Playwright 未安装，跳过")
        return []
    encoded_kw = quote(keyword)
    url = f"https://www.zhipin.com/web/geek/job?query={encoded_kw}"
    if city:
        city_map = {
            "北京": "101010100", "上海": "101020100", "广州": "101280100",
            "深圳": "101280600", "杭州": "101210100", "成都": "101270100",
            "长沙": "101250100", "武汉": "101200100", "南京": "101190100",
            "西安": "101110100", "苏州": "101190400", "重庆": "101040100",
            "天津": "101030100", "郑州": "101180100", "青岛": "101120200",
            "厦门": "101230200", "合肥": "101220100", "济南": "101120100",
        }
        city_code = city_map.get(city.replace("市", ""))
        if city_code:
            url += f"&city={city_code}"
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=COMMON_UA, viewport={"width": 1920, "height": 1080}, locale="zh-CN",
            )
            page = context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            """)
            print(f"[BOSS直聘] 正在加载页面: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT * 1000)
            except Exception as e:
                print(f"[BOSS直聘] 页面加载超时或失败: {e}")
                browser.close()
                return []
            wait_sec = random.randint(3, 5)
            print(f"[BOSS直聘] 等待页面渲染 {wait_sec} 秒...")
            page.wait_for_timeout(wait_sec * 1000)
            page_content = page.content()
            if "安全验证" in page_content or "验证码" in page_content:
                print("[BOSS直聘] 被反爬拦截，跳过该网站")
                browser.close()
                return []
            job_cards = page.query_selector_all(".job-card-wrapper, .search-job-result li, .job-list li")
            if not job_cards:
                job_cards = page.query_selector_all("[class*='job-card'], [class*='job-item']")
            print(f"[BOSS直聘] 找到 {len(job_cards)} 个岗位卡片")
            for card in job_cards[:30]:
                try:
                    title_el = card.query_selector(".job-name, .job-title, [class*='job-name']")
                    job_title = title_el.inner_text().strip() if title_el else ""
                    company_el = card.query_selector(".company-name, .company-info, [class*='company-name']")
                    company_name = company_el.inner_text().strip() if company_el else ""
                    salary_el = card.query_selector(".salary, .job-salary, [class*='salary']")
                    salary_range = salary_el.inner_text().strip() if salary_el else "面议"
                    area_el = card.query_selector(".job-area, .job-area-wrapper, [class*='area']")
                    work_location = area_el.inner_text().strip() if area_el else ""
                    edu_el = card.query_selector(".job-info .edu, [class*='edu'], .job-detail .edu")
                    edu = edu_el.inner_text().strip() if edu_el else ""
                    link_el = card.query_selector("a.job-card-left, a[href*='job_detail'], a")
                    detail_link = ""
                    if link_el:
                        href = link_el.get_attribute("href") or ""
                        detail_link = ("https://www.zhipin.com" + href) if href and not href.startswith("http") else href
                    if not job_title or not company_name:
                        continue
                    enterprise_type = _determine_enterprise_type(company_name, "BOSS直聘")
                    results.append({
                        "job_title": job_title, "company": company_name,
                        "enterprise_type": enterprise_type, "detail_link": detail_link,
                        "salary_range": salary_range or "面议",
                        "responsibilities": "详见岗位详情页",
                        "requirements": f"学历要求：{edu}" if edu else "详见岗位详情页",
                        "benefits": "详见岗位详情页",
                        "development": _generate_development(enterprise_type),
                        "work_location": work_location or "全国",
                        "source": "BOSS直聘（真实数据）", "search_keyword": keyword,
                        "_raw_contents": "", "_raw_edu": edu, "_raw_exp": "",
                    })
                except Exception as e:
                    print(f"  [WARNING] 解析BOSS直聘岗位卡片失败: {e}")
            browser.close()
    except Exception as e:
        print(f"[BOSS直聘] 爬取异常: {e}")
    print(f"[BOSS直聘] 成功解析 {len(results)} 条岗位")
    return results


# ============ 爬虫：智联招聘（Playwright）============
def crawl_zhaopin(keyword, city=None):
    """爬取智联招聘岗位数据，需要Playwright渲染JS页面"""
    print(f"\n[智联招聘] 开始爬取，关键词: {keyword}，城市: {city}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[智联招聘] Playwright 未安装，跳过")
        return []
    encoded_kw = quote(keyword)
    url = f"https://sou.zhaopin.com/?kw={encoded_kw}"
    if city:
        url += f"&jl={quote(city)}"
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=COMMON_UA, viewport={"width": 1920, "height": 1080}, locale="zh-CN",
            )
            page = context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            """)
            print(f"[智联招聘] 正在加载页面: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT * 1000)
            except Exception as e:
                print(f"[智联招聘] 页面加载超时或失败: {e}")
                browser.close()
                return []
            wait_sec = random.randint(3, 5)
            print(f"[智联招聘] 等待页面渲染 {wait_sec} 秒...")
            page.wait_for_timeout(wait_sec * 1000)
            page_content = page.content()
            if "安全验证" in page_content or "验证码" in page_content:
                print("[智联招聘] 被反爬拦截，跳过该网站")
                browser.close()
                return []
            job_cards = page.query_selector_all(
                ".joblist-box__item, .positionList .joblist-box__item, [class*='jobCard'], [class*='job-card'], .sou-job-item"
            )
            if not job_cards:
                job_cards = page.query_selector_all(".joblist-box li, .resultList div")
            print(f"[智联招聘] 找到 {len(job_cards)} 个岗位卡片")
            for card in job_cards[:30]:
                try:
                    title_el = card.query_selector(".jobinfo__name, .job-name, [class*='jobName'], [class*='job-name']")
                    job_title = title_el.inner_text().strip() if title_el else ""
                    company_el = card.query_selector(".companyinfo__name, .company-name, [class*='companyName'], [class*='company-name']")
                    company_name = company_el.inner_text().strip() if company_el else ""
                    salary_el = card.query_selector(".jobinfo__salary, .salary, [class*='salary'], [class*='Salary']")
                    salary_range = salary_el.inner_text().strip() if salary_el else "面议"
                    area_el = card.query_selector(".jobinfo__area, .job-area, [class*='area'], [class*='city']")
                    work_location = area_el.inner_text().strip() if area_el else ""
                    edu_el = card.query_selector(".jobinfo__edu, .edu, [class*='edu'], [class*='degree']")
                    edu = edu_el.inner_text().strip() if edu_el else ""
                    link_el = card.query_selector("a[href*='jobs.zhaopin.com'], a[href*='/jobdetail'], a")
                    detail_link = ""
                    if link_el:
                        href = link_el.get_attribute("href") or ""
                        detail_link = ("https://sou.zhaopin.com" + href) if href and not href.startswith("http") else href
                    if not job_title or not company_name:
                        continue
                    enterprise_type = _determine_enterprise_type(company_name, "智联招聘")
                    results.append({
                        "job_title": job_title, "company": company_name,
                        "enterprise_type": enterprise_type, "detail_link": detail_link,
                        "salary_range": salary_range or "面议",
                        "responsibilities": "详见岗位详情页",
                        "requirements": f"学历要求：{edu}" if edu else "详见岗位详情页",
                        "benefits": "详见岗位详情页",
                        "development": _generate_development(enterprise_type),
                        "work_location": work_location or "全国",
                        "source": "智联招聘（真实数据）", "search_keyword": keyword,
                        "_raw_contents": "", "_raw_edu": edu, "_raw_exp": "",
                    })
                except Exception as e:
                    print(f"  [WARNING] 解析智联招聘岗位卡片失败: {e}")
            browser.close()
    except Exception as e:
        print(f"[智联招聘] 爬取异常: {e}")
    print(f"[智联招聘] 成功解析 {len(results)} 条岗位")
    return results


# ============ 爬虫：国资委央企招聘（静态HTML）============
def crawl_sasac(keyword, city=None):
    """爬取国资委央企招聘公告，静态HTML用requests+BeautifulSoup"""
    print(f"\n[国资委] 开始爬取，关键词: {keyword}")
    sasac_urls = [
        "http://www.sasac.gov.cn/n2588035/n2588105/index.html",
        "https://www.sasac.gov.cn/n2588035/n2588105/index.html",
        "http://www.sasac.gov.cn/n2588035/c15456054/list.html",
    ]
    resp = None
    for url in sasac_urls:
        resp = _safe_request(url)
        if resp:
            break
        _random_delay()
    if not resp:
        print("[国资委] 所有URL请求均失败，跳过")
        return []
    try:
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"[国资委] HTML解析失败: {e}")
        return []
    results = []
    items = soup.select("ul.list li, .list li, .news_list li, .content li, li a")
    print(f"[国资委] 找到 {len(items)} 个列表项")
    for item in items[:50]:
        try:
            link_el = item if item.name == "a" else item.find("a")
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            if not title or len(title) < 5:
                continue
            # 关键词过滤
            if keyword and keyword.lower() not in title.lower():
                kw_chars = set(keyword.replace(" ", ""))
                title_chars = set(title)
                if len(kw_chars & title_chars) / max(len(kw_chars), 1) < 0.3:
                    continue
            if href and not href.startswith("http"):
                detail_link = "http://www.sasac.gov.cn" + href if href.startswith("/") else "http://www.sasac.gov.cn/n2588035/n2588105/" + href
            else:
                detail_link = href
            company_name = "国资委央企"
            m = re.match(r"^(.+?)(?:招聘|招录|招考|公告|通知)", title)
            if m:
                company_name = m.group(1).strip()
            results.append({
                "job_title": title, "company": company_name, "enterprise_type": "国企",
                "detail_link": detail_link, "salary_range": "详见公告",
                "responsibilities": "详见岗位详情页", "requirements": "详见岗位详情页",
                "benefits": "央企福利待遇（五险二金/年终奖/带薪年假）",
                "development": "央企平台稳定，晋升通道清晰，福利保障完善",
                "work_location": city or "全国", "source": "国资委央企招聘（真实数据）",
                "search_keyword": keyword, "_raw_contents": "", "_raw_edu": "", "_raw_exp": "",
            })
        except Exception as e:
            print(f"  [WARNING] 解析国资委岗位失败: {e}")
    print(f"[国资委] 成功解析 {len(results)} 条岗位")
    return results


def filter_by_city(jobs, city, min_count=5):
    """按城市筛选岗位，不足时补充全国岗位"""
    if not city:
        return jobs
    city_jobs = [j for j in jobs if _is_city_match(j.get("work_location", ""), city)]
    other_jobs = [j for j in jobs if not _is_city_match(j.get("work_location", ""), city)]
    print(f"  城市筛选: 匹配{city}的岗位 {len(city_jobs)} 个，其他 {len(other_jobs)} 个")
    if len(city_jobs) >= min_count:
        return city_jobs
    print(f"  {city}岗位不足{min_count}个，补充全国岗位")
    return city_jobs + other_jobs


# ============ 获取岗位推荐数据（由 workbuddy 爬取程序实现）============
# TODO: 由 workbuddy 爬取程序填充此函数
# 返回格式：list[dict]，每个 dict 包含以下字段：
#   job_title, company, enterprise_type, match_score, detail_link,
#   salary_range, responsibilities, requirements, benefits, development,
#   work_location, source, search_keyword
def generate_recommendations(user: dict) -> list[dict]:
    """获取岗位推荐数据 — 从4个招聘平台爬取真实在招岗位"""
    city = user.get('city', '')
    field = user.get('field', '')
    degree = user.get('degree', '')
    experience = user.get('experience', '')
    print(f"[推荐] 用户 {user.get('id')} 的岗位推荐由 workbuddy 爬取程序生成")
    print(f"[推荐] 求职方向: {field}, 城市: {city}, 学历: {degree}, 经验: {experience}")

    if not field:
        print("[ERROR] 缺少求职方向关键词")
        return []

    all_jobs = []

    # 1. 国聘网（最高优先级，公开API）
    try:
        print("\n>>> [1/4] 爬取国聘网...")
        iguopin_jobs = crawl_iguopin(field, city)
        all_jobs.extend(iguopin_jobs)
        print(f"国聘网返回 {len(iguopin_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[国聘网] 爬取失败: {e}")

    # 2. BOSS直聘（Playwright渲染）
    try:
        print("\n>>> [2/4] 爬取BOSS直聘...")
        _random_delay()
        boss_jobs = crawl_boss(field, city)
        all_jobs.extend(boss_jobs)
        print(f"BOSS直聘返回 {len(boss_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[BOSS直聘] 爬取失败: {e}")

    # 3. 智联招聘（Playwright渲染）
    try:
        print("\n>>> [3/4] 爬取智联招聘...")
        _random_delay()
        zhaopin_jobs = crawl_zhaopin(field, city)
        all_jobs.extend(zhaopin_jobs)
        print(f"智联招聘返回 {len(zhaopin_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[智联招聘] 爬取失败: {e}")

    # 4. 国资委央企招聘（静态HTML）
    try:
        print("\n>>> [4/4] 爬取国资委央企招聘...")
        _random_delay()
        sasac_jobs = crawl_sasac(field, city)
        all_jobs.extend(sasac_jobs)
        print(f"国资委返回 {len(sasac_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[国资委] 爬取失败: {e}")

    # 去重
    print(f"\n去重前: {len(all_jobs)} 条")
    seen = set()
    deduped = []
    for job in all_jobs:
        key = (job.get("job_title", "").lower(), job.get("company", "").lower())
        if key not in seen:
            seen.add(key)
            deduped.append(job)
    print(f"去重后: {len(deduped)} 条")

    # 城市筛选
    print("\n按城市筛选...")
    filtered = filter_by_city(deduped, city, min_count=5)

    # 计算匹配度
    print("\n计算匹配度...")
    for job in filtered:
        job["match_score"] = calculate_match_score(job, user)

    # 按匹配度排序
    filtered.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    # 清理临时字段 + 生成 search_links
    for job in filtered:
        job.pop("_raw_contents", None)
        job.pop("_raw_edu", None)
        job.pop("_raw_exp", None)
        # 调用已有的 build_search_links 生成多平台搜索链接
        job["search_links"] = build_search_links(
            keyword=job.get("job_title", ""),
            city=city,
            enterprise_type=job.get("enterprise_type", ""),
            job_title=job.get("job_title", ""),
        )

    # 限制返回数量（最多20条）
    result = filtered[:20]

    print("\n" + "=" * 50)
    print(f"岗位推荐生成完成！共 {len(result)} 条岗位")
    source_count = {}
    for job in result:
        src = job.get("source", "未知")
        source_count[src] = source_count.get(src, 0) + 1
    for src, cnt in source_count.items():
        print(f"  {src}: {cnt} 条")
    print("=" * 50)

    return result


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
