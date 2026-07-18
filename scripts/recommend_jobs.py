#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
岗位招聘信息爬取模块
====================
从多个招聘平台爬取真实在招岗位，返回结构化数据供后续生成 H5 报告和推送。

数据来源（按优先级）：
1. 国聘网（国资央企招聘平台）— 公开API，最可靠
2. BOSS直聘 — Playwright 渲染
3. 智联招聘 — Playwright 渲染
4. 国资委央企招聘 — 静态HTML

使用方式：
    from recommend_jobs import generate_recommendations
    jobs = generate_recommendations(user_dict)
"""

import json
import time
import re
import os
import random
import urllib.parse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ============================================================
# 常量定义
# ============================================================

# 通用请求头
COMMON_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# 请求超时（秒）
REQUEST_TIMEOUT = 20

# 每个网站爬取超时
SITE_TIMEOUT = 20

# 请求间隔（秒）
REQUEST_INTERVAL_MIN = 1.0
REQUEST_INTERVAL_MAX = 2.0

# 学历等级映射（数值越大学历越高）
EDU_LEVEL = {
    "不限": 0,
    "大专": 1,
    "专科": 1,
    "本科": 2,
    "学士": 2,
    "硕士": 3,
    "研究生": 3,
    "博士": 4,
    "MBA/EMBA": 3,
}

# 经验等级映射（数值越大经验要求越高）
EXP_LEVEL = {
    "不限": 0,
    "无经验": 0,
    "应届": 1,
    "应届生": 1,
    "应届毕业生": 1,
    "1年以下": 1,
    "1年": 1,
    "1-3年": 2,
    "1~3年": 2,
    "3-5年": 3,
    "3~5年": 3,
    "5-10年": 4,
    "5~10年": 4,
    "10年以上": 5,
}

# ============================================================
# 央企招聘官网数据源（URL + 名称）
# ============================================================
NATIONAL_SOE_SOURCES = [
    {
        "name": "中石油",
        "urls": [
            "http://zhaopin.cnpc.com.cn/",
        ],
        "wechat_name": "中国石油招聘",
    },
    {
        "name": "南方电网",
        "urls": [
            "https://zhaopin.csg.cn/",
            "https://zhaopin.csg.cn/#/recruitment-social",
        ],
        "wechat_name": "南网50Hz",
    },
    {
        "name": "国家电网",
        "urls": [
            "https://zhaopin.sgcc.com.cn/",
        ],
        "wechat_name": "国家电网招聘",
    },
    {
        "name": "中石化",
        "urls": [
            "https://job.sinopec.com/",
        ],
        "wechat_name": "中国石化招聘",
    },
    {
        "name": "中国海油",
        "urls": [
            "https://zhaopin.cnooc.com.cn/",
        ],
        "wechat_name": "中国海油",
    },
    {
        "name": "中国移动",
        "urls": [
            "https://job.10086.cn/",
            "https://campus.10086.cn/",
        ],
        "wechat_name": "中国移动招聘",
    },
    {
        "name": "中国电信",
        "urls": [
            "https://campus.51job.com/chinatelecom/",
        ],
        "wechat_name": "中国电信招聘",
    },
    {
        "name": "中国联通",
        "urls": [
            "https://hr.chinaunicom.cn/",
        ],
        "wechat_name": "中国联通招聘",
    },
    {
        "name": "中国建筑",
        "urls": [
            "https://cscec.zhiye.com/",
        ],
        "wechat_name": "中国建筑招聘",
    },
    {
        "name": "华润集团",
        "urls": [
            "https://crc.wintalent.cn/",
            "https://www.crc.com.cn/rlzy_43682/zxns/",
        ],
        "wechat_name": "华润招聘",
    },
    {
        "name": "招商局集团",
        "urls": [
            "https://www.cmhk.com/main/rlzy/rczp/",
        ],
        "wechat_name": "百年招商局",
    },
    {
        "name": "中国中铁",
        "urls": [
            "https://www.crecg.com.cn/",
        ],
        "wechat_name": "中国中铁招聘",
    },
    {
        "name": "中粮集团",
        "urls": [
            "https://cofco.zhiye.com/",
        ],
        "wechat_name": "中粮招聘",
    },
    {
        "name": "中国航天科工",
        "urls": [
            "https://zhaopin.casic.cn/",
        ],
        "wechat_name": "中国航天科工招聘",
    },
    {
        "name": "中国船舶",
        "urls": [
            "https://zhaopin.cssc.net.cn/",
        ],
        "wechat_name": "中国船舶招聘",
    },
    {
        "name": "国家电投",
        "urls": [
            "https://hr.cpic.com.cn/",
        ],
        "wechat_name": "国家电投",
    },
]

# ============================================================
# 城市 → 地方国企映射表
# ============================================================
LOCAL_SOE_MAP = {
    "长沙": [
        {"name": "长沙银行", "urls": ["https://cscb.zhiye.com/", "https://www.cscb.cn/"]},
        {"name": "湖南银行", "urls": ["https://www.hunan-bank.com/96599/gywx/rczp/index.shtml", "https://www.hunan-bank.com/"]},
        {"name": "湖南建投集团", "urls": ["https://www.hnjg.com.cn/"]},
        {"name": "兴湘集团", "urls": ["https://www.hnxtg.com/"]},
        {"name": "湖南高速集团", "urls": ["https://www.hngs.net/"]},
        {"name": "长沙轨交集团", "urls": ["https://www.hncsmtr.com/"]},
        {"name": "湖南中烟工业", "urls": ["http://www.hnti.com.cn/"]},
        {"name": "长沙水业集团", "urls": ["http://www.cssy.com.cn/"]},
        {"name": "湖南机场管理集团", "urls": ["https://www.hna-ca.com.cn/"]},
    ],
    "北京": [
        {"name": "北京银行", "urls": ["https://www.bankofbeijing.com.cn/"]},
        {"name": "北京农商银行", "urls": ["https://www.bjrcb.com/"]},
        {"name": "首钢集团", "urls": ["https://www.shougang.com.cn/"]},
        {"name": "北汽集团", "urls": ["https://www.baicgroup.com.cn/"]},
        {"name": "京能集团", "urls": ["https://www.jnenergy.com/"]},
    ],
    "上海": [
        {"name": "浦发银行", "urls": ["https://www.spdb.com.cn/"]},
        {"name": "上海银行", "urls": ["https://www.bosc.cn/"]},
        {"name": "上汽集团", "urls": ["https://www.saicsa.com/", "https://www.saicmotor.com/"]},
        {"name": "上海电气", "urls": ["https://www.shanghai-electric.com/"]},
        {"name": "申通地铁", "urls": ["https://www.shmetro.com/"]},
    ],
    "深圳": [
        {"name": "深圳地铁", "urls": ["https://www.szmc.net/"]},
        {"name": "深圳能源", "urls": ["https://www.sec.com.cn/"]},
        {"name": "深圳水务", "urls": ["https://www.sz-water.com.cn/"]},
    ],
    "广州": [
        {"name": "广州银行", "urls": ["https://www.gzcb.com.cn/"]},
        {"name": "广汽集团", "urls": ["https://www.gac.com.cn/"]},
        {"name": "广州地铁", "urls": ["https://www.gzmtr.com/"]},
    ],
    "成都": [
        {"name": "成都银行", "urls": ["https://www.bocd.com.cn/"]},
        {"name": "成都轨交集团", "urls": ["https://www.chengdurail.com/"]},
    ],
    "武汉": [
        {"name": "武汉农村商业银行", "urls": ["https://www.whrcb.com/"]},
        {"name": "武汉地铁", "urls": ["https://www.wuhanrt.com/"]},
        {"name": "湖北交投集团", "urls": ["https://www.hbjt.com.cn/"]},
    ],
    "杭州": [
        {"name": "杭州银行", "urls": ["https://www.hzbank.com.cn/"]},
        {"name": "杭州地铁", "urls": ["https://www.hzmetro.com/"]},
    ],
    "南京": [
        {"name": "南京银行", "urls": ["https://www.njcb.com.cn/"]},
        {"name": "南京地铁", "urls": ["https://www.njmetro.com.cn/"]},
    ],
    "西安": [
        {"name": "长安银行", "urls": ["https://www.ccbbchina.com/"]},
        {"name": "西安地铁", "urls": ["http://www.xianrail.com/"]},
    ],
    "重庆": [
        {"name": "重庆银行", "urls": ["https://www.cqcbank.com/"]},
        {"name": "重庆农村商业银行", "urls": ["https://www.cqrcb.com/"]},
        {"name": "重庆轨交集团", "urls": ["https://www.cqmetro.cn/"]},
    ],
}


# 同省城市映射（用于城市匹配的扩展判断）
PROVINCE_MAP = {
    "长沙": "湖南", "株洲": "湖南", "湘潭": "湖南", "衡阳": "湖南",
    "武汉": "湖北", "宜昌": "湖北", "襄阳": "湖北",
    "广州": "广东", "深圳": "广东", "佛山": "广东", "东莞": "广东",
    "杭州": "浙江", "宁波": "浙江", "温州": "浙江",
    "成都": "四川", "绵阳": "四川",
    "南京": "江苏", "苏州": "江苏", "无锡": "江苏",
    "西安": "陕西",
    "重庆": "重庆",
}


# ============================================================
# 辅助函数
# ============================================================

def _safe_request(url, method="GET", headers=None, json_body=None, timeout=REQUEST_TIMEOUT, verify_ssl=True):
    """
    安全的 HTTP 请求封装，带异常处理。
    verify_ssl=False 时跳过 SSL 证书验证（用于国企等旧证书网站）。
    """
    default_headers = {
        "User-Agent": COMMON_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if headers:
        default_headers.update(headers)

    # 跳过 SSL 验证时抑制警告
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        if method.upper() == "POST":
            resp = requests.post(
                url, headers=default_headers, json=json_body, timeout=timeout, verify=verify_ssl
            )
        else:
            resp = requests.get(url, headers=default_headers, timeout=timeout, verify=verify_ssl)
        resp.raise_for_status()
        return resp
    except requests.exceptions.Timeout:
        print(f"  [WARNING] 请求超时: {url}")
        return None
    except requests.exceptions.ConnectionError as e:
        # SSL 证书问题时自动重试（跳过验证）
        err_str = str(e)
        if any(kw in err_str for kw in ["SSL", "CERTIFICATE", "UNSAFE_LEGACY"]):
            print(f"  [INFO] SSL证书问题，跳过验证重试: {url}")
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                if method.upper() == "POST":
                    resp = requests.post(
                        url, headers=default_headers, json=json_body, timeout=timeout, verify=False
                    )
                else:
                    resp = requests.get(url, headers=default_headers, timeout=timeout, verify=False)
                resp.raise_for_status()
                return resp
            except Exception as e2:
                print(f"  [WARNING] SSL跳过验证后仍失败: {url} - {e2}")
                return None
        print(f"  [WARNING] 连接错误: {url} - {e}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"  [WARNING] HTTP错误: {url} - {e}")
        return None
    except Exception as e:
        print(f"  [WARNING] 请求异常: {url} - {e}")
        return None


def _parse_edu_level(edu_str):
    """从字符串中解析学历等级"""
    if not edu_str:
        return 0
    edu_str = str(edu_str).strip()
    for key, val in EDU_LEVEL.items():
        if key in edu_str:
            return val
    return 0


def _parse_exp_level(exp_str):
    """从字符串中解析经验等级"""
    if not exp_str:
        return 0
    exp_str = str(exp_str).strip()
    for key, val in EXP_LEVEL.items():
        if key in exp_str:
            return val
    # 尝试数字匹配
    m = re.search(r"(\d+)\s*年", exp_str)
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
    delay = random.uniform(REQUEST_INTERVAL_MIN, REQUEST_INTERVAL_MAX)
    time.sleep(delay)


def _extract_section(text, keywords, max_lines=10):
    """
    从岗位描述文本中提取特定部分（职责/要求等）。
    策略：找到关键词所在行作为起点，一直捕获到下一个段落标题或文本结尾。
    """
    if not text:
        return ""

    # 所有已知的段落标题关键词
    all_section_headers = [
        "岗位职责", "工作内容", "职位描述", "工作职责", "主要职责", "职位要求",
        "任职要求", "岗位要求", "任职资格", "任职条件", "应聘条件",
        "福利待遇", "薪酬福利", "薪资福利", "工作时间", "工作地点",
        "联系方式", "公司介绍", "企业介绍", "备注",
    ]

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return ""

    # 找到关键词起始行
    start_idx = -1
    for i, line in enumerate(lines):
        for kw in keywords:
            if kw in line:
                start_idx = i
                break
        if start_idx >= 0:
            break

    if start_idx < 0:
        return ""

    # 从起始行开始，一直捕获到下一个段落标题（不包括当前段落标题）
    result = []
    for i in range(start_idx, len(lines)):
        line = lines[i]
        # 如果不是起始行，且遇到了新的段落标题，停止
        if i > start_idx:
            is_new_section = any(header in line for header in all_section_headers)
            if is_new_section:
                # 但要排除当前段落的标题在内容中的重复出现
                current_kw_in_line = any(kw in line for kw in keywords)
                if not current_kw_in_line:
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
    # 如果没有明确分节，返回前几行
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
    req = _extract_section(contents, ["任职要求", "岗位要求", "任职资格", "任职条件", "应聘条件", "职位要求"])
    if req:
        return req
    # 从全文中提取包含"要求"关键词的行
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


def _determine_enterprise_type(company_info_str, source):
    """根据公司信息字符串判断企业类型"""
    text = str(company_info_str) if company_info_str else ""
    if any(kw in text for kw in ["央企", "国企", "国有", "国资委", "中央企业"]):
        return "国企"
    if any(kw in text for kw in ["外资", "外企", "合资", "外商独资"]):
        return "外企"
    if any(kw in text for kw in ["民营", "私企", "私企", "私营", "股份制"]):
        return "私企"
    # 根据来源推断
    if source in ["国聘网", "国资委央企招聘"]:
        return "国企"
    return "私企"


def _generate_development(enterprise_type, source):
    """根据企业类型生成职业发展前景描述"""
    if enterprise_type == "国企":
        return "国企平台稳定，晋升通道清晰，福利保障完善"
    elif enterprise_type == "外企":
        return "国际化平台，职业发展路径多元，薪酬体系完善"
    else:
        return "市场化薪酬，成长空间大，适合快速积累经验"


def _generate_benefits(contents):
    """从岗位描述中提取福利待遇"""
    if not contents:
        return "详见岗位详情页"
    benefit_keywords = [
        "五险一金", "六险二金", "五险二金", "七险一金", "七险二金",
        "年终奖", "年终奖金", "年底双薪",
        "带薪年假", "年假",
        "餐补", "餐费补贴", "免费三餐", "免费午餐",
        "交通补贴", "通讯补贴", "住房补贴",
        "体检", "定期体检",
        "补充医疗", "商业保险",
        "弹性工作", "周末双休", "双休",
        "股票期权", "期权",
        "培训", "晋升", "团建",
    ]
    found = []
    text = str(contents)
    for kw in benefit_keywords:
        if kw in text:
            found.append(kw)
    if found:
        # 去重
        seen = set()
        unique = []
        for b in found:
            if b not in seen:
                seen.add(b)
                unique.append(b)
        return "/".join(unique)
    # 默认福利（国企常见福利）
    return "五险一金/年终奖/带薪年假/定期体检"


def _is_city_match(job_location, user_city):
    """判断岗位地点是否匹配用户城市"""
    if not job_location or not user_city:
        return False
    job_loc = str(job_location).replace("市", "").strip()
    user_c = str(user_city).replace("市", "").strip()
    return user_c in job_loc or job_loc in user_c


# 主要城市列表（用于从文本中提取工作地点）
_ALL_CITIES = [
    "北京", "上海", "广州", "深圳", "杭州", "成都", "长沙", "武汉", "南京",
    "西安", "苏州", "重庆", "天津", "郑州", "青岛", "沈阳", "大连", "厦门",
    "合肥", "济南", "哈尔滨", "福州", "昆明", "贵阳", "南宁", "石家庄",
    "太原", "长春", "南昌", "兰州", "海口", "呼和浩特", "银川", "西宁",
    "乌鲁木齐", "拉萨", "株洲", "湘潭", "衡阳", "宜昌", "襄阳", "佛山",
    "东莞", "宁波", "温州", "绵阳", "无锡", "常州", "绍兴", "嘉兴",
]


def _detect_city_from_text(text):
    """
    从文本中提取城市名称。
    优先匹配 "XX招聘" 或 "【XX招聘】" 模式，其次匹配城市名出现。
    """
    if not text:
        return ""

    text = str(text)

    # 模式1: 【XX招聘】 或 XX招聘
    m = re.search(r"[【\[]?\s*([北京上海广州深圳杭州成都长沙武汉南京西安苏州重庆天津郑州青岛沈阳大连厦门合肥济南哈尔滨福州昆明贵阳南宁石家庄太原长春南昌兰州海口呼和浩特银川西宁乌鲁木齐拉萨株洲湘潭衡阳宜昌襄阳佛山东莞宁波温州绵阳无锡常州绍兴嘉兴]{2,4})\s*(?:招聘|招贤|招新)", text)
    if m:
        return m.group(1)

    # 模式2: 城市名 + 地点关键词
    m = re.search(r"(工作地点|地点|地址|所在地)[：:]\s*([北京上海广州深圳杭州成都长沙武汉南京西安苏州重庆天津郑州青岛沈阳大连厦门合肥济南哈尔滨福州昆明贵阳南宁石家庄太原长春南昌兰州海口呼和浩特银川西宁乌鲁木齐拉萨株洲湘潭衡阳宜昌襄阳佛山东莞宁波温州绵阳无锡常州绍兴嘉兴]{2,4})", text)
    if m:
        return m.group(2)

    # 模式3: 直接匹配已知城市名（取第一个出现的）
    for city in _ALL_CITIES:
        if city in text:
            return city

    return ""


# ============================================================
# 匹配度计算
# ============================================================

def calculate_match_score(job, user):
    """
    计算岗位与用户的匹配度 (0-100)。

    评分维度（城市已在前置筛选完成，专业方向第一优先）：
    - 方向匹配 (0-50)：求职方向与岗位名称/描述相关度（第一优先级）
    - 学历匹配 (0-25)：用户学历 >= 岗位要求 = 高分
    - 经验匹配 (0-25)：用户经验 >= 岗位要求 = 高分
    """
    score = 0

    # --- 方向匹配 (0-50) ★ 第一优先级 ---
    user_field = (user.get("field") or user.get("direction") or "").lower().strip()
    job_title = (job.get("job_title") or "").lower()
    job_desc = (job.get("_raw_contents") or job.get("job_desc") or "").lower()

    if user_field:
        # 拆分：英文=核心技能(Python/Java), 中文=通用角色(开发/工程师)
        en_skills = [w.lower() for w in re.findall(r'[a-zA-Z0-9]+', user_field)]
        cn_roles = re.findall(r'[\u4e00-\u9fff]+', user_field)

        # 生成中文双字词（bigrams），适配"财务会计"→"财务"+"会计"的部分匹配
        cn_bigrams = set()
        for role in cn_roles:
            if len(role) >= 2:
                for i in range(len(role) - 1):
                    cn_bigrams.add(role[i:i+2])

        # 1. 完整字段匹配在标题中 → 满分
        if user_field in job_title:
            score += 50
        # 2. 全部英文技能词出现在标题中
        elif en_skills and all(kw in job_title for kw in en_skills):
            score += 45
        # 3. 至少一个英文技能词出现在标题中 (核心技能对口)
        elif en_skills and any(kw in job_title for kw in en_skills):
            score += 35
        # 4. 英文技能词出现在描述中
        elif en_skills and any(kw in job_desc for kw in en_skills):
            score += 20
        # 5. 中文 bigram 匹配标题 — 纯中文方向的核心逻辑
        elif cn_bigrams:
            title_bigram_match = sum(1 for bg in cn_bigrams if bg in job_title)
            title_bigram_ratio = title_bigram_match / len(cn_bigrams) if cn_bigrams else 0
            if title_bigram_ratio >= 0.5:
                score += 40  # 标题中大部分 bigram 命中
            elif title_bigram_match > 0:
                score += 25  # 标题中部分 bigram 命中
            else:
                # 标题不匹配，看描述
                desc_bigram_match = sum(1 for bg in cn_bigrams if bg in job_desc)
                desc_bigram_ratio = desc_bigram_match / len(cn_bigrams) if cn_bigrams else 0
                if desc_bigram_ratio >= 0.5:
                    score += 15  # 描述中大部分命中
                elif desc_bigram_match > 0:
                    score += 8   # 描述中少量命中
                else:
                    score += 0   # 完全不命中
        # 6. 中文角色词出现在标题中 (短词后备)
        elif cn_roles and any(kw in job_title for kw in cn_roles):
            score += 10
        # 7. 中文角色词出现在描述中
        elif cn_roles and any(kw in job_desc for kw in cn_roles):
            score += 5
        # 7. 完全不对口
        else:
            score += 0
    else:
        score += 25  # 无方向信息，给中间分

    # --- 学历匹配 (0-25) ---
    user_edu = user.get("degree") or user.get("education") or ""
    job_edu = job.get("_raw_edu") or job.get("education_req") or ""
    user_edu_level = _parse_edu_level(user_edu)
    job_edu_level = _parse_edu_level(job_edu)
    if job_edu_level == 0:
        score += 20  # 不限学历
    elif user_edu_level >= job_edu_level:
        score += 25  # 完全满足
    elif user_edu_level == job_edu_level - 1:
        score += 15  # 差一档
    else:
        score += 5

    # --- 经验匹配 (0-25) ---
    user_exp = user.get("experience") or ""
    job_exp = job.get("_raw_exp") or job.get("experience_req") or ""
    user_exp_level = _parse_exp_level(user_exp)
    job_exp_level = _parse_exp_level(job_exp)
    if job_exp_level == 0:
        score += 20  # 不限经验
    elif user_exp_level >= job_exp_level:
        score += 25  # 经验满足
    elif user_exp_level == job_exp_level - 1:
        score += 15  # 差一档
    else:
        score += 5

    # 如果方向完全不匹配，总分上限压低（防止不对口岗位排到前面）
    if user_field and score <= 50:  # 方向0分 + 学历 + 经验 ≤ 50
        score = min(score, 40)

    return min(score, 100)


# ============================================================
# 爬虫：国聘网（API）
# ============================================================

def crawl_iguopin(keyword, city=None):
    """
    爬取国聘网（国资央企招聘平台）岗位数据。
    使用公开 API，最可靠的数据源。
    """
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

            # 薪资
            min_wage = item.get("min_wage") or ""
            max_wage = item.get("max_wage") or ""
            if min_wage and max_wage:
                salary_range = f"{min_wage}-{max_wage}元/月"
            elif min_wage:
                salary_range = f"{min_wage}元/月起"
            else:
                salary_range = item.get("salary") or "面议"

            # 学历/经验
            edu = item.get("education_cn") or item.get("education") or ""
            exp = item.get("experience_cn") or item.get("experience") or item.get("work_years") or ""

            # 地点
            district_list = item.get("district_list") or []
            if isinstance(district_list, list) and district_list:
                work_location = district_list[0].get("area_cn") or ""
            else:
                work_location = item.get("city") or item.get("city_cn") or ""

            # 岗位描述
            contents = item.get("contents") or item.get("description") or item.get("job_desc") or ""

            # 公司信息
            company_info = item.get("company_info") or {}
            if isinstance(company_info, dict):
                nature = company_info.get("nature_cn") or company_info.get("nature") or ""
            else:
                nature = str(company_info)

            enterprise_type = _determine_enterprise_type(nature + " " + company_name, "国聘网")

            detail_link = f"https://www.iguopin.com/job/detail?id={job_id}" if job_id else ""

            job_obj = {
                "job_title": job_name,
                "company": company_name,
                "enterprise_type": enterprise_type,
                "detail_link": detail_link,
                "salary_range": salary_range,
                "responsibilities": _extract_responsibilities(contents),
                "requirements": _extract_requirements(contents, edu, exp),
                "benefits": _generate_benefits(contents),
                "development": _generate_development(enterprise_type, "国聘网"),
                "work_location": work_location or "全国",
                "source": "国聘网（真实数据）",
                "search_keyword": keyword,
                "_raw_contents": contents,
                "_raw_edu": edu,
                "_raw_exp": exp,
            }
            results.append(job_obj)
        except Exception as e:
            print(f"  [WARNING] 解析国聘网岗位失败: {e}")
            continue

    print(f"[国聘网] 成功解析 {len(results)} 条岗位")
    return results


# ============================================================
# Playwright 选择器自动探测
# ============================================================

def _find_job_cards(page, selectors, site_name):
    """
    逐个尝试 CSS 选择器，找到第一个返回结果的即采用。
    如果所有选择器都返回 0 个结果，调用 _auto_detect_job_cards 进行 DOM 自动分析。

    参数:
        page: Playwright page 对象
        selectors: list[str]，CSS 选择器列表（按优先级排序）
        site_name: 站点名称，用于日志

    返回:
        list: 匹配到的 ElementHandle 列表（可能为空）
    """
    for sel in selectors:
        try:
            cards = page.query_selector_all(sel)
            if cards:
                print(f"[{site_name}] 选择器命中: {sel} -> {len(cards)} 个卡片")
                return cards
        except Exception as e:
            print(f"[{site_name}] 选择器异常 ({sel}): {e}")

    print(f"[{site_name}] 所有预设选择器均未匹配，启动 DOM 自动探测...")
    detected = _auto_detect_job_cards(page, site_name)
    if detected:
        print(f"[{site_name}] DOM 自动探测成功，找到 {len(detected)} 个卡片")
    else:
        print(f"[{site_name}] DOM 自动探测也未找到岗位卡片")
    return detected


def _auto_detect_job_cards(page, site_name):
    """
    通过 JavaScript 分析 DOM 结构，自动寻找疑似岗位卡片的元素。

    策略:
    1. 找到所有 class 名包含 job/position/card/item/list 等关键词的元素
    2. 筛选出包含薪资模式（数字+K/元/万）或公司关键词的元素
    3. 取这些元素的共同最近父级容器作为卡片集合
    4. 去重并返回
    """
    try:
        # 用 JS 在页面上执行 DOM 分析
        js_code = """
        () => {
            // Step 1: 收集疑似卡片元素
            const jobKeywords = /job|position|card|item|list|result|vacancy|seek/i;
            const salaryPattern = /\\d+[kK万]|元\\/月|元\\/天|薪|面议|月薪|年薪|\\d+-\\d+/;
            const companyPattern = /公司|集团|有限|科技|股份|控股|研究院|研究所|中心|局|院|厂/;

            // 排除非内容区域（footer、nav、header、sidebar、filter等，含文本匹配）
            const excludeClsPattern = /footer|nav-bar|sidebar|header|popup|modal|copyright|banner|notice-bar|login|register|toolbar|menu|filter-condition|pagination|page/;
            const excludeTextPattern = /版权所有|Copyright|copyight|ICP备|备案号|公司首页|官方微博|官方微信|APP下载|常见问题|清空$|^城市$/;
            function isExcluded(el) {
                // 检查 class 名排除
                let current = el;
                while (current && current !== document.body) {
                    const cls = (current.className || '').toString();
                    if (excludeClsPattern.test(cls)) return true;
                    current = current.parentElement;
                }
                // 检查文本内容排除（避免版权/备案/导航/筛选栏等非岗位区域）
                const text = (el.innerText || '').substring(0, 200);
                if (excludeTextPattern.test(text)) return true;
                return false;
            }

            // 所有包含 job 相关 class 的元素
            const candidates = [];
            const allElements = document.querySelectorAll('*');

            for (const el of allElements) {
                // 先排除非内容区域（在 class 检查之前）
                if (isExcluded(el)) continue;

                const cls = el.className || '';
                const clsStr = typeof cls === 'string' ? cls : '';
                if (!jobKeywords.test(clsStr)) continue;

                // 检查元素内是否包含疑似薪资或公司信息
                const text = el.innerText || '';
                if (text.length < 10 || text.length > 1000) continue;

                const hasSalary = salaryPattern.test(text);
                const hasCompany = companyPattern.test(text);

                if (hasSalary || hasCompany) {
                    candidates.push({
                        el: el,
                        cls: clsStr,
                        text: text.substring(0, 200),
                        depth: el.getBoundingClientRect().width,
                    });
                }
            }

            // Step 2: 如果候选元素太少，用更宽泛的策略 —— 找所有 <li> 或 <div> 中包含薪资信息的
            if (candidates.length < 2) {
                const listItems = document.querySelectorAll('li, div[class]');
                for (const el of listItems) {
                    const text = el.innerText || '';
                    if (text.length < 15 || text.length > 800) continue;
                    if (el.children.length > 10) continue; // 跳过容器级元素

                    const hasSalary = salaryPattern.test(text);
                    if (!hasSalary) continue;

                    // 确保不是嵌套在已选元素里的子元素
                    const cls = el.className || '';
                    const clsStr = typeof cls === 'string' ? cls : '';
                    candidates.push({
                        el: el,
                        cls: clsStr,
                        text: text.substring(0, 200),
                        depth: el.getBoundingClientRect().width,
                    });
                }
            }

            // Step 3: 去重 —— 移除被其他候选元素包含的子元素
            const unique = [];
            for (let i = 0; i < candidates.length; i++) {
                const el1 = candidates[i].el;
                let isParent = false;
                for (let j = 0; j < candidates.length; j++) {
                    if (i === j) continue;
                    const el2 = candidates[j].el;
                    // 如果 el1 包含 el2，则 el1 是父容器，跳过
                    if (el1.contains(el2) && el1 !== el2) {
                        isParent = true;
                        break;
                    }
                }
                if (!isParent) {
                    unique.push(candidates[i]);
                }
            }

            // Step 4: 限制数量
            const result = unique.slice(0, 30);

            // 返回选择器信息供 Playwright 使用
            // 为每个找到的元素标记一个 data 属性
            const markedSelectors = [];
            result.forEach((item, idx) => {
                const marker = `__auto_card_${idx}`;
                item.el.setAttribute('data-auto-card', marker);
                markedSelectors.push({
                    marker: marker,
                    cls: item.cls,
                    preview: item.text.substring(0, 100),
                });
            });

            return markedSelectors;
        }
        """
        markers = page.evaluate(js_code)

        if not markers:
            return []

        # Python 层面的二次过滤：排除疑似非岗位区域（版权/页脚/筛选栏等）
        _EXCLUDE_CLS_RE = re.compile(
            r"footer|nav-bar|sidebar|header|popup|modal|copyright|banner"
            r"|notice-bar|login|register|toolbar|menu|pagination|page"
            r"|filter-condition|bg-|navbar",
            re.IGNORECASE,
        )
        _EXCLUDE_TXT_RE = re.compile(
            r"版权所有|Copyright|copyight|ICP备|备案号|公司首页|官方微博"
            r"|官方微信|APP下载|常见问题|清空\s*$|^城市\s*$"
            r"|请求\s*ID|Security Verification|Captcha|验证码"
            r"|DNS解析失败|Network is unreachable|connection refused",
        )
        # 排除极短/无意义的 class 名（如 't j', 'a b' 等单字母组合）
        _EXCLUDE_CLS_INVALID = re.compile(r"^[a-z]\s[a-z]$", re.IGNORECASE)

        cards = []
        for m in markers:
            cls_str = m.get("cls", "")
            prw_str = m.get("preview", "")

            if _EXCLUDE_CLS_RE.search(cls_str):
                continue
            if _EXCLUDE_CLS_INVALID.match(cls_str):
                continue
            if _EXCLUDE_TXT_RE.search(prw_str):
                continue

            sel = f"[data-auto-card='{m['marker']}']"
            try:
                el = page.query_selector(sel)
                if el:
                    cards.append(el)
                    # 记录探测到的选择器，便于下次更新预设选择器
                    print(f"  [{site_name}] 探测到卡片: class='{cls_str[:60]}' 预览: {prw_str[:50]}...")
            except Exception:
                continue

        return cards

    except Exception as e:
        print(f"  [{site_name}] DOM 自动探测异常: {e}")
        return []


def _extract_text(element, selectors, attr=None):
    """
    从元素中按选择器优先级提取文本或属性。
    参数:
        element: Playwright ElementHandle
        selectors: list[str]，CSS 选择器列表
        attr: 如果指定则提取属性值，否则提取 inner_text
    返回:
        str: 提取到的文本/属性值，失败返回空字符串
    """
    for sel in selectors:
        try:
            child = element.query_selector(sel)
            if child:
                if attr:
                    val = child.get_attribute(attr)
                    if val:
                        return val.strip()
                else:
                    text = child.inner_text()
                    if text.strip():
                        return text.strip()
        except Exception:
            continue
    return ""


# ============================================================
# 爬虫：BOSS直聘（Playwright）
# ============================================================

def _load_saved_cookies(site_name, data_dir=None):
    """
    加载本地保存的已登录 Cookie 文件。
    文件位置: data/{site_name}_cookies.json
    返回 list[dict] 或空列表。
    """
    import os
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    cookie_file = os.path.join(data_dir, f"{site_name}_cookies.json")
    if not os.path.exists(cookie_file):
        return []
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        if isinstance(cookies, list) and len(cookies) > 0:
            print(f"  [Cookie] 已加载 {site_name} 的 {len(cookies)} 个 cookies ({cookie_file})")
            return cookies
    except Exception as e:
        print(f"  [Cookie] 解析失败 ({cookie_file}): {e}")
    return []


def crawl_boss(keyword, city=None):
    """
    爬取BOSS直聘岗位数据。
    需要使用 Playwright 渲染 JS 页面。
    """
    print(f"\n[BOSS直聘] 开始爬取，关键词: {keyword}，城市: {city}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[BOSS直聘] Playwright 未安装，跳过")
        return []

    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://www.zhipin.com/web/geek/job?query={encoded_keyword}"
    if city:
        # BOSS直聘城市编码映射（部分主要城市）
        city_code_map = {
            "北京": "101010100", "上海": "101020100", "广州": "101280100",
            "深圳": "101280600", "杭州": "101210100", "成都": "101270100",
            "长沙": "101250100", "武汉": "101200100", "南京": "101190100",
            "西安": "101110100", "苏州": "101190400", "重庆": "101040100",
            "天津": "101030100", "郑州": "101180100", "青岛": "101120200",
            "沈阳": "101070100", "大连": "101070200", "厦门": "101230200",
            "合肥": "101220100", "济南": "101120100", "哈尔滨": "101050100",
            "福州": "101230100", "昆明": "101290100", "贵阳": "101260100",
            "南宁": "101300100", "石家庄": "101090100", "太原": "101100100",
            "长春": "101060100", "南昌": "101240100", "兰州": "101160100",
            "海口": "101310100", "呼和浩特": "101080100", "银川": "101170100",
            "西宁": "101150100", "乌鲁木齐": "101130100", "拉萨": "101140100",
        }
        city_code = city_code_map.get(city.replace("市", ""))
        if city_code:
            url += f"&city={city_code}"

    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = browser.new_context(
                user_agent=COMMON_UA,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )
            page = context.new_page()

            # 尝试加载已保存的 BOSS直聘 Cookie（可选，需手动准备）
            saved_cookies = _load_saved_cookies("boss")
            if saved_cookies:
                context.add_cookies(saved_cookies)
                print("[BOSS直聘] 已注入保存的 cookies，尝试已登录状态搜索")
            else:
                print("[BOSS直聘] 未找到保存的 cookies，将以游客模式访问（大概率被拦截）")

            # 设置反检测
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            """)

            print(f"[BOSS直聘] 正在加载页面: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=SITE_TIMEOUT * 1000)
            except Exception as e:
                print(f"[BOSS直聘] 页面加载超时或失败: {e}")
                browser.close()
                return []

            # 等待页面渲染
            wait_seconds = random.randint(3, 5)
            print(f"[BOSS直聘] 等待页面渲染 {wait_seconds} 秒...")
            page.wait_for_timeout(wait_seconds * 1000)

            # 检查是否被反爬或要求登录
            try:
                page_content = page.content()
            except Exception:
                print("[BOSS直聘] ⚠️ 页面仍在导航中，跳过该网站")
                browser.close()
                return []
            page_title = page.title()
            if "安全验证" in page_content or "验证码" in page_content or "slider" in page_content.lower():
                print("[BOSS直聘] ⚠️ 被反爬拦截，跳过该网站")
                browser.close()
                return []
            if "登录" in page_title or "注册" in page_title:
                print("[BOSS直聘] ⚠️ 需要登录才能查看搜索结果（已重定向到登录页），跳过该网站")
                browser.close()
                return []

            # 尝试获取岗位列表 —— 使用选择器自动探测机制
            # BOSS直聘的岗位卡片选择器（按优先级排序，逐个尝试）
            boss_selectors = [
                ".job-card-wrapper",
                ".search-job-result li",
                ".job-list li",
                "[class*='job-card']",
                "[class*='job-item']",
                ".job-card-body",
                "ul.job-list-box li",
                ".search-job-result .job-card-wrapper",
                "li[ka]",
            ]
            job_cards = _find_job_cards(page, boss_selectors, "BOSS直聘")

            # ★ 批量 JS 提取：避免逐个 ElementHandle 操作时 context 丢失
            # BOSS直聘页面会动态重渲染 DOM，导致 ElementHandle 失效（"Cannot find context"）
            # 改为在单次 page.evaluate 中一次性提取所有卡片数据
            if job_cards:
                print(f"[BOSS直聘] 使用批量JS提取 {min(len(job_cards), 30)} 个卡片数据...")
                try:
                    extracted_data = page.evaluate("""
                        () => {
                            const cards = document.querySelectorAll(
                                'li[ka], .job-card-wrapper, .search-job-result li, ' +
                                '.job-list li, [class*="job-card"], [class*="job-item"], ' +
                                '.job-card-body, ul.job-list-box li'
                            );
                            const results = [];
                            for (const card of cards) {
                                if (results.length >= 30) break;
                                try {
                                    // 岗位名称
                                    let jobTitle = '';
                                    const titleSels = ['.job-name', '.job-title', '[class*="job-name"]', '.job-info .name', 'span[title]'];
                                    for (const sel of titleSels) {
                                        const el = card.querySelector(sel);
                                        if (el && el.innerText.trim()) { jobTitle = el.innerText.trim(); break; }
                                    }

                                    // 公司名称
                                    let companyName = '';
                                    const compSels = ['.company-name', '.company-info', '[class*="company-name"]', '.company-info .name', '[class*="companyName"]'];
                                    for (const sel of compSels) {
                                        const el = card.querySelector(sel);
                                        if (el && el.innerText.trim()) { companyName = el.innerText.trim(); break; }
                                    }

                                    // 薪资
                                    let salary = '';
                                    const salSels = ['.salary', '.job-salary', '[class*="salary"]', '.job-info .salary', '.red'];
                                    for (const sel of salSels) {
                                        const el = card.querySelector(sel);
                                        if (el && el.innerText.trim()) { salary = el.innerText.trim(); break; }
                                    }

                                    // 地点
                                    let workLocation = '';
                                    const areaSels = ['.job-area', '.job-area-wrapper', '[class*="area"]', '.job-info .job-area', '[class*="city"]'];
                                    for (const sel of areaSels) {
                                        const el = card.querySelector(sel);
                                        if (el && el.innerText.trim()) { workLocation = el.innerText.trim(); break; }
                                    }

                                    // 学历
                                    let edu = '';
                                    const eduSels = ['.job-info .edu', '[class*="edu"]', '.job-detail .edu', '[class*="degree"]'];
                                    for (const sel of eduSels) {
                                        const el = card.querySelector(sel);
                                        if (el && el.innerText.trim()) { edu = el.innerText.trim(); break; }
                                    }

                                    // 详情链接
                                    let detailLink = '';
                                    const linkEl = card.querySelector('a.job-card-left, a[href*="job_detail"], a[href*="/job/"], a');
                                    if (linkEl) {
                                        let href = linkEl.getAttribute('href') || '';
                                        if (href && !href.startsWith('http')) {
                                            detailLink = 'https://www.zhipin.com' + href;
                                        } else {
                                            detailLink = href;
                                        }
                                    }

                                    if (jobTitle && companyName) {
                                        results.push({ jobTitle, companyName, salary, workLocation, edu, detailLink });
                                    }
                                } catch(e) { continue; }
                            }
                            return results;
                        }
                    """)

                    print(f"[BOSS直聘] 批量JS提取到 {len(extracted_data)} 条有效数据")

                    for item in extracted_data:
                        try:
                            job_title = item.get("jobTitle", "")
                            company_name = item.get("companyName", "")
                            if not job_title or not company_name:
                                continue

                            salary_range = item.get("salary", "") or "面议"
                            work_location = item.get("workLocation", "") or "全国"
                            edu = item.get("edu", "")
                            detail_link = item.get("detailLink", "")

                            enterprise_type = _determine_enterprise_type(company_name, "BOSS直聘")

                            job_obj = {
                                "job_title": job_title,
                                "company": company_name,
                                "enterprise_type": enterprise_type,
                                "detail_link": detail_link,
                                "salary_range": salary_range,
                                "responsibilities": "详见岗位详情页",
                                "requirements": f"学历要求：{edu}" if edu else "详见岗位详情页",
                                "benefits": "详见岗位详情页",
                                "development": _generate_development(enterprise_type, "BOSS直聘"),
                                "work_location": work_location,
                                "source": "BOSS直聘（真实数据）",
                                "search_keyword": keyword,
                                "_raw_contents": "",
                                "_raw_edu": edu,
                                "_raw_exp": "",
                            }
                            results.append(job_obj)
                        except Exception as e:
                            print(f"  [WARNING] 解析BOSS直聘批量数据失败: {e}")
                            continue

                except Exception as e:
                    print(f"[BOSS直聘] 批量JS提取异常: {e}")
                    # 回退到逐个解析（可能仍会失败，但作为最后手段）
                    print("[BOSS直聘] 回退到逐个ElementHandle解析...")
                    for card in job_cards[:30]:
                        try:
                            job_title = _extract_text(card, [
                                ".job-name", ".job-title", "[class*='job-name']",
                                ".job-info .name", "span[title]",
                            ])
                            company_name = _extract_text(card, [
                                ".company-name", ".company-info", "[class*='company-name']",
                                ".company-info .name", "[class*='companyName']",
                            ])
                            salary_range = _extract_text(card, [
                                ".salary", ".job-salary", "[class*='salary']",
                                ".job-info .salary", ".red",
                            ]) or "面议"
                            work_location = _extract_text(card, [
                                ".job-area", ".job-area-wrapper", "[class*='area']",
                                ".job-info .job-area", "[class*='city']",
                            ])
                            edu = _extract_text(card, [
                                ".job-info .edu", "[class*='edu']", ".job-detail .edu",
                                ".job-info span", "[class*='degree']",
                            ])
                            detail_link = ""
                            link_el = card.query_selector(
                                "a.job-card-left, a[href*='job_detail'], a[href*='/job/'], a"
                            )
                            if link_el:
                                href = link_el.get_attribute("href") or ""
                                if href and not href.startswith("http"):
                                    detail_link = "https://www.zhipin.com" + href
                                else:
                                    detail_link = href

                            if not job_title or not company_name:
                                continue

                            enterprise_type = _determine_enterprise_type(company_name, "BOSS直聘")
                            job_obj = {
                                "job_title": job_title, "company": company_name,
                                "enterprise_type": enterprise_type, "detail_link": detail_link,
                                "salary_range": salary_range, "responsibilities": "详见岗位详情页",
                                "requirements": f"学历要求：{edu}" if edu else "详见岗位详情页",
                                "benefits": "详见岗位详情页",
                                "development": _generate_development(enterprise_type, "BOSS直聘"),
                                "work_location": work_location or "全国",
                                "source": "BOSS直聘（真实数据）", "search_keyword": keyword,
                                "_raw_contents": "", "_raw_edu": edu, "_raw_exp": "",
                            }
                            results.append(job_obj)
                        except Exception as e2:
                            print(f"  [WARNING] 逐个解析也失败: {e2}")
                            continue

            browser.close()
    except Exception as e:
        print(f"[BOSS直聘] 爬取异常: {e}")
        return []

    print(f"[BOSS直聘] 成功解析 {len(results)} 条岗位")
    return results


#!/usr/bin/env python3
# ... license/copyright info ...
# 爬虫：智联招聘（Playwright）
# ============================================================

def crawl_zhaopin(keyword, city=None):
    """
    爬取智联招聘岗位数据。
    DOM 结构（2026-07 验证）：
    .joblist-box__item → 岗位卡片
      .jobinfo__name-row → 岗位名称
      .jobinfo__salary → 薪资
      .jobinfo__other-info-item:nth-child(1) → 地点
      .jobinfo__other-info-item:nth-child(2) → 经验
      .jobinfo__other-info-item:nth-child(3) → 学历
      .companyinfo__name → 公司名称
      .companyinfo__tag → 企业类型标签
    """
    print(f"\n[智联招聘] 开始爬取，关键词: {keyword}，城市: {city}")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[智联招聘] Playwright 未安装，跳过")
        return []

    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://sou.zhaopin.com/?kw={encoded_keyword}"
    if city:
        url += f"&jl={urllib.parse.quote(city)}"

    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = browser.new_context(
                user_agent=COMMON_UA,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = context.new_page()

            # 反检测
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
                window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };
            """)

            # 先访问首页建立 cookie
            try:
                page.goto("https://www.zhaopin.com/", wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(2000)
            except Exception:
                pass

            print(f"[智联招聘] 正在加载搜索页: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=SITE_TIMEOUT * 1000)
            except Exception as e:
                print(f"[智联招聘] 搜索页加载超时: {e}")
                browser.close()
                return []

            page.wait_for_timeout(5000)

            page_title = page.title()
            print(f"[智联招聘] 页面标题: {page_title}")

            # 快速检测安全验证页面（不等待 DOM 解析）
            if "Security Verification" in page_title or "安全验证" in page_title:
                print("[智联招聘] ⚠️ 触发安全验证页面（GitHub Actions IP 被限制），跳过")
                browser.close()
                return []

            # 智联招聘岗位卡片 —— 已验证选择器 (2026-07)
            job_cards = page.query_selector_all(".joblist-box__item")
            print(f"[智联招聘] ✓ 找到 {len(job_cards)} 个岗位卡片 (.joblist-box__item)")

            # 如果没有卡片，再检查是否被反爬
            if not job_cards:
                try:
                    page_content = page.content()
                except Exception:
                    print("[智联招聘] ⚠️ 页面仍在加载中，跳过")
                    browser.close()
                    return []
                # 真正的反爬特征（不在正常页面源码中）
                real_block_signs = ["请完成安全验证", "拖动滑块", "geetest_embed", "滑动验证", "Security Verification", "gcaptcha"]
                if any(s in page_content[:10000] for s in real_block_signs):
                    print("[智联招聘] ⚠️ 触发反爬验证，跳过该网站")
                    browser.close()
                    return []
                else:
                    html_snippet = page_content[:2000]
                    print(f"[智联招聘] ⚠️ 未找到卡片（非反爬原因），页面HTML前2000字符: {html_snippet}")

            for card in job_cards[:30]:
                try:
                    # 岗位名称 .jobinfo__name-row
                    job_title = _extract_text(card, [
                        ".jobinfo__name-row", ".jobinfo__name",
                        ".job-name", "[class*='jobName']",
                    ])

                    # 公司名称 .companyinfo__name
                    company_name = _extract_text(card, [
                        ".companyinfo__name", ".company-name",
                        "[class*='companyName']", ".company-info a",
                    ])

                    # 薪资 .jobinfo__salary
                    salary_range = _extract_text(card, [
                        ".jobinfo__salary", ".salary", "[class*='salary']",
                    ]) or "面议"

                    # 地点/经验/学历 —— .jobinfo__other-info-item
                    other_items = card.query_selector_all(".jobinfo__other-info-item")
                    work_location = ""
                    exp_text = ""
                    edu = ""
                    for idx, item in enumerate(other_items[:4]):
                        t = item.inner_text().strip() if item else ""
                        if idx == 0:
                            work_location = t  # 第一个：地点
                        elif idx == 1:
                            exp_text = t        # 第二个：经验
                        elif idx == 2:
                            edu = t             # 第三个：学历

                    # 公司标签（企业类型信息）
                    company_tag = _extract_text(card, [
                        ".companyinfo__tag", "[class*='companyTag']",
                    ])

                    # 详情链接 —— 尝试多种方式
                    detail_link = ""
                    # 方式1: card 本身是 a 标签
                    if card.evaluate("el => el.tagName") == "A":
                        href = card.get_attribute("href") or ""
                        detail_link = href
                    # 方式2: card 内的 a 标签
                    if not detail_link:
                        detail_link = _extract_text(card, [
                            "a[href*='jobs.zhaopin.com']",
                            "a[data-link]", "a.joblist-box__item",
                        ], attr="href")
                    # 方式3: companyinfo__name 的 a 标签
                    if not detail_link:
                        detail_link = _extract_text(card, [
                            ".companyinfo__name",
                        ], attr="href")

                    if not detail_link:
                        detail_link = url  # 兜底

                    if not job_title or not company_name:
                        continue

                    # 根据公司标签或名称判断企业类型
                    enterprise_type = _determine_enterprise_type(
                        company_tag + " " + company_name, "智联招聘"
                    )

                    # 构建 requirements 字符串
                    requirements_parts = []
                    if edu:
                        requirements_parts.append(f"学历要求：{edu}")
                    if exp_text:
                        requirements_parts.append(f"经验要求：{exp_text}")
                    requirements = "\n".join(requirements_parts) if requirements_parts else "详见岗位详情页"

                    job_obj = {
                        "job_title": job_title,
                        "company": company_name,
                        "enterprise_type": enterprise_type,
                        "detail_link": detail_link,
                        "salary_range": salary_range if salary_range else "面议",
                        "responsibilities": "详见岗位详情页",
                        "requirements": requirements,
                        "benefits": "详见岗位详情页",
                        "development": _generate_development(enterprise_type, "智联招聘"),
                        "work_location": work_location or city or "全国",
                        "source": "智联招聘（真实数据）",
                        "search_keyword": keyword,
                        "_raw_contents": company_tag or "",
                        "_raw_edu": edu,
                        "_raw_exp": exp_text,
                    }
                    results.append(job_obj)
                except Exception as e:
                    print(f"  [WARNING] 解析智联招聘岗位卡片失败: {e}")
                    continue

            browser.close()
    except Exception as e:
        print(f"[智联招聘] 爬取异常: {e}")
        return []

    print(f"[智联招聘] ✓ 成功解析 {len(results)} 条岗位")
    return results


# ============================================================
# 爬虫：国资委央企招聘（静态HTML）
# ============================================================

def crawl_sasac(keyword, city=None):
    """
    爬取国资委央企招聘公告。
    静态 HTML，使用 requests + BeautifulSoup。
    """
    print(f"\n[国资委] 开始爬取，关键词: {keyword}")
    # 尝试多个可能的国资委招聘页面URL
    sasac_urls = [
        "http://www.sasac.gov.cn/n2588035/n2588105/index.html",
        "https://www.sasac.gov.cn/n2588035/n2588105/index.html",
        "http://www.sasac.gov.cn/n2588035/c15456054/list.html",
        "http://www.sasac.gov.cn/n2588035/n2588105/c15456054/list.html",
    ]

    resp = None
    base_url = sasac_urls[0]
    for url in sasac_urls:
        resp = _safe_request(url)
        if resp:
            base_url = url
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

    # 尝试多种选择器匹配公告列表
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
                # 宽松匹配：关键词的每个字都在标题中
                kw_chars = set(keyword.replace(" ", ""))
                title_chars = set(title)
                if len(kw_chars & title_chars) / max(len(kw_chars), 1) < 0.3:
                    continue

            # 补全链接
            if href and not href.startswith("http"):
                if href.startswith("/"):
                    detail_link = "http://www.sasac.gov.cn" + href
                else:
                    detail_link = "http://www.sasac.gov.cn/n2588035/n2588105/" + href
            else:
                detail_link = href

            # 尝试获取发布单位（从父元素或标题中提取）
            parent_text = ""
            if item.parent:
                parent_text = item.parent.get_text(strip=True)
            # 尝试从标题中提取公司名
            company_name = "国资委央企"
            m = re.match(r"^(.+?)(?:招聘|招录|招考|公告|通知)", title)
            if m:
                company_name = m.group(1).strip()

            job_obj = {
                "job_title": title,
                "company": company_name,
                "enterprise_type": "国企",
                "detail_link": detail_link,
                "salary_range": "详见公告",
                "responsibilities": "详见岗位详情页",
                "requirements": "详见岗位详情页",
                "benefits": "央企福利待遇（五险二金/年终奖/带薪年假）",
                "development": "央企平台稳定，晋升通道清晰，福利保障完善",
                "work_location": city or "全国",
                "source": "国资委央企招聘（真实数据）",
                "search_keyword": keyword,
                "_raw_contents": parent_text,
                "_raw_edu": "",
                "_raw_exp": "",
            }
            results.append(job_obj)
        except Exception as e:
            print(f"  [WARNING] 解析国资委岗位失败: {e}")
            continue

    print(f"[国资委] 成功解析 {len(results)} 条岗位")
    return results


# ============================================================
# 爬虫：央企招聘官网（中石油/南方电网/国家电网等）
# ============================================================

def crawl_national_soe(keyword, city=None):
    """
    爬取央企招聘官网（中石油、南方电网、国家电网、中石化等）。
    逐个尝试每个央企的招聘页面，使用 requests + BeautifulSoup 解析。
    如果静态页面解析失败，尝试用 Playwright 渲染。
    """
    print(f"\n[央企官网] 开始爬取 {len(NATIONAL_SOE_SOURCES)} 个央企招聘网站，关键词: {keyword}，城市: {city}")
    results = []

    for soe in NATIONAL_SOE_SOURCES:
        soe_name = soe["name"]
        soe_urls = soe.get("urls", [soe.get("url", "")])
        print(f"  [{soe_name}] 尝试爬取...")
        soe_results = []
        had_http_response = False  # 是否收到过非网络错误的HTTP响应

        for url in soe_urls:
            resp = _safe_request(url, verify_ssl=False)
            if not resp:
                # 检查是否是网络错误（非HTTP错误）—— DNS/连接/超时
                # 如果是网络错误，标记为不可达。如果是HTTP错误(404/412/502)，服务器存在。
                # 我们在 _safe_request 中无法区分，但通过返回值是否为None来统一处理。
                _random_delay()
                continue

            had_http_response = True
            try:
                resp.encoding = resp.apparent_encoding or "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")

                # 通用解析策略：寻找包含"招聘""岗位""职位"的链接和列表项
                # 策略1: 寻找新闻/公告列表
                items = soup.select(
                    "ul li a, .list li a, .news_list li a, "
                    ".content li a, .job-list li, [class*='job'] li, "
                    "[class*='recruit'] li, [class*='position'] li, "
                    "table tr, .article-list li"
                )

                for item in items[:20]:
                    try:
                        link_el = item if item.name == "a" else item.find("a")
                        if not link_el:
                            continue

                        title = link_el.get_text(strip=True)
                        href = link_el.get("href", "")

                        if not title or len(title) < 4:
                            continue

                        # 过滤：包含招聘/岗位/职位/应届/社招等关键词
                        recruit_kw = ["招聘", "岗位", "职位", "应届", "社招", "校园", "招录",
                                      "公告", "招考", "招贤", "招新", "人才", "招工"]
                        if not any(kw in title for kw in recruit_kw):
                            continue

                        # 关键词匹配（宽松）
                        if keyword:
                            kw_lower = keyword.lower()
                            title_lower = title.lower()
                            # 关键词直接匹配 或 关键词分词匹配
                            kw_words = [w for w in re.split(r"[/\-_,，\s]+", keyword) if len(w) >= 2]
                            if kw_lower not in title_lower and not any(w in title_lower for w in kw_words):
                                # 不严格过滤，保留所有招聘信息（因为央企招聘公告标题可能不含具体岗位）
                                pass

                        # 补全链接
                        if href and not href.startswith("http"):
                            if href.startswith("/"):
                                detail_link = url.rstrip("/").rsplit("/", 1)[0].rsplit("/", 1)[0] + href
                            else:
                                detail_link = url.rstrip("/") + "/" + href
                        else:
                            detail_link = href

                        # 获取周边文本作为描述
                        parent_text = ""
                        if item.parent:
                            parent_text = item.parent.get_text(strip=True)[:500]

                        job_obj = {
                            "job_title": title,
                            "company": soe_name,
                            "enterprise_type": "国企",
                            "detail_link": detail_link,
                            "salary_range": "详见公告",
                            "responsibilities": "详见岗位详情页",
                            "requirements": "详见岗位详情页",
                            "benefits": "央企福利待遇（五险二金/年终奖/带薪年假/企业年金）",
                            "development": "央企平台稳定，晋升通道清晰，福利保障完善",
                            "work_location": _detect_city_from_text(title + " " + parent_text) or city or "全国",
                            "source": f"{soe_name}官网（真实数据）",
                            "search_keyword": keyword,
                            "_raw_contents": parent_text,
                            "_raw_edu": "",
                            "_raw_exp": "",
                        }
                        soe_results.append(job_obj)
                    except Exception as e:
                        continue

                if soe_results:
                    print(f"    [{soe_name}] 从 {url} 解析到 {len(soe_results)} 条")
                    break  # 成功获取就不再尝试备用URL

            except Exception as e:
                print(f"    [{soe_name}] 解析失败 ({url}): {e}")

            _random_delay()

        # 如果静态解析失败且有HTTP响应，尝试 Playwright 兜底
        # 如果从未收到过HTTP响应（纯网络错误），跳过 Playwright 避免浪费20秒超时
        if not soe_results and had_http_response:
            soe_results = _crawl_soe_with_playwright(soe_name, soe_urls, keyword, city)
        elif not soe_results and not had_http_response:
            print(f"    [{soe_name}] 所有URL网络不可达，跳过 Playwright 兜底")

        results.extend(soe_results)
        print(f"  [{soe_name}] 共获取 {len(soe_results)} 条")

    print(f"[央企官网] 总计解析 {len(results)} 条岗位")
    return results


def _crawl_soe_with_playwright(soe_name, urls, keyword, city):
    """用 Playwright 渲染央企招聘页面（静态解析失败时的兜底）"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=COMMON_UA, viewport={"width": 1920, "height": 1080}, locale="zh-CN",
            )
            page = context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            for url in urls:
                try:
                    print(f"    [{soe_name}] Playwright 加载: {url}")
                    page.goto(url, wait_until="domcontentloaded", timeout=10000)  # 已失败过，降到10s
                    page.wait_for_timeout(2000)  # 已失败过，降到2s

                    # 通用选择器探测
                    selectors = [
                        "[class*='job'] li", "[class*='recruit'] li", "[class*='position'] li",
                        ".list li", ".news_list li", "ul.list li a",
                        "[class*='job'] a", "[class*='recruit'] a",
                        "table tr", ".article-list li", ".content-list li",
                    ]
                    cards = _find_job_cards(page, selectors, soe_name)

                    for card in cards[:15]:
                        try:
                            text = card.inner_text().strip()
                            link_el = card if card.evaluate("el => el.tagName") == "A" else card.query_selector("a")
                            href = link_el.get_attribute("href") if link_el else ""
                            title = text[:100] if text else ""

                            if not title or len(title) < 4:
                                continue

                            if href and not href.startswith("http"):
                                href = url.rstrip("/").rsplit("/", 1)[0].rsplit("/", 1)[0] + href if href.startswith("/") else url.rstrip("/") + "/" + href

                            results.append({
                                "job_title": title.split("\n")[0][:80],
                                "company": soe_name,
                                "enterprise_type": "国企",
                                "detail_link": href or url,
                                "salary_range": "详见公告",
                                "responsibilities": "详见岗位详情页",
                                "requirements": "详见岗位详情页",
                                "benefits": "央企福利待遇（五险二金/年终奖/带薪年假）",
                                "development": "央企平台稳定，晋升通道清晰，福利保障完善",
                                "work_location": _detect_city_from_text(title + " " + text) or city or "全国",
                                "source": f"{soe_name}官网（真实数据）",
                                "search_keyword": keyword,
                                "_raw_contents": text,
                                "_raw_edu": "",
                                "_raw_exp": "",
                            })
                        except Exception:
                            continue

                    if results:
                        break
                except Exception as e:
                    print(f"    [{soe_name}] Playwright 加载失败 ({url}): {e}")

            browser.close()
    except Exception as e:
        print(f"    [{soe_name}] Playwright 异常: {e}")

    return results


# ============================================================
# 爬虫：地方国企（按用户城市匹配）
# ============================================================

def crawl_local_soe(keyword, city=None):
    """
    根据用户所在城市，爬取该城市的地方国企招聘信息。
    如用户在长沙，爬取长沙银行、湖南银行、湖南建工等。
    """
    if not city:
        print("\n[地方国企] 未提供城市信息，跳过")
        return []

    city_key = city.replace("市", "").strip()
    local_soes = LOCAL_SOE_MAP.get(city_key, [])

    if not local_soes:
        print(f"\n[地方国企] 暂未配置「{city}」的地方国企列表，跳过")
        return []

    print(f"\n[地方国企] 开始爬取「{city}」的 {len(local_soes)} 个地方国企招聘网站")
    results = []

    for soe in local_soes:
        soe_name = soe["name"]
        soe_urls = soe.get("urls", [soe.get("url", "")])

        soe_results = []
        had_http_response = False  # 是否收到过非网络错误的HTTP响应

        # 先直接使用 SOE 配置中的 URL（已经过验证的招聘页面）
        for url in soe_urls:
            if not url:
                continue
            print(f"  [{soe_name}] 爬取 {url}...")
            resp = _safe_request(url, verify_ssl=False)
            if not resp:
                _random_delay()
                continue

            had_http_response = True

            try:
                resp.encoding = resp.apparent_encoding or "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")
                items = soup.select(
                    "ul li a, .list li a, .news_list li a, "
                    "[class*='job'] li, [class*='recruit'] li, "
                    "[class*='position'] li, table tr, "
                    ".article-list li, [class*='career'] li"
                )
                for item in items[:15]:
                    try:
                        link_el = item if item.name == "a" else item.find("a")
                        if not link_el:
                            continue
                        title = link_el.get_text(strip=True)
                        href = link_el.get("href", "")
                        if not title or len(title) < 5:
                            continue
                        # 过滤掉明显非招聘的内容
                        skip_kw = ["招标", "中标", "谈判", "视窗", "loading", "首页", "上一页", "下一页"]
                        if any(kw in title for kw in skip_kw):
                            continue
                        recruit_kw = ["招聘", "岗位", "职位", "应届", "社招", "校园",
                                      "招录", "公告", "招考", "人才", "招工", "简历",
                                      "报名", "应聘", "录用", "录用公示"]
                        if not any(kw in title for kw in recruit_kw):
                            continue
                        if href and not href.startswith("http"):
                            href = url.rstrip("/") + (href if href.startswith("/") else "/" + href)
                        parent_text = item.parent.get_text(strip=True)[:500] if item.parent else ""
                        soe_results.append({
                            "job_title": title, "company": soe_name, "enterprise_type": "国企",
                            "detail_link": href, "salary_range": "详见公告",
                            "responsibilities": "详见岗位详情页", "requirements": "详见岗位详情页",
                            "benefits": "国企福利待遇（五险二金/年终奖/带薪年假）",
                            "development": f"{soe_name}地方国企平台稳定",
                            "work_location": city, "source": f"{soe_name}官网（真实数据）",
                            "search_keyword": keyword, "_raw_contents": parent_text,
                            "_raw_edu": "", "_raw_exp": "",
                        })
                    except Exception:
                        continue

                if soe_results:
                    print(f"    [{soe_name}] 从 {url} 解析到 {len(soe_results)} 条")
                    break

            except Exception as e:
                print(f"    [{soe_name}] 解析失败 ({url}): {e}")

            _random_delay()

        # 如果有HTTP响应但HTML解析失败，用 Playwright 兜底
        # 如果从未收到过HTTP响应（纯网络错误），跳过 Playwright 避免浪费20秒超时
        if not soe_results and had_http_response:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-setuid-sandbox",
                              "--disable-blink-features=AutomationControlled",
                              "--ignore-certificate-errors"],
                    )
                    context = browser.new_context(
                        user_agent=COMMON_UA, viewport={"width": 1920, "height": 1080},
                        locale="zh-CN", ignore_https_errors=True,
                    )
                    context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        window.chrome = { runtime: {}, app: {} };
                    """)
                    page = context.new_page()
                    for url in soe_urls:
                        if not url:
                            continue
                        print(f"    [{soe_name}] Playwright 加载 {url}...")
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=20000)
                            page.wait_for_timeout(4000)
                            html = page.content()
                            soup = BeautifulSoup(html, "lxml")
                            items = soup.select(
                                "ul li a, .list li a, .news_list li a, "
                                "[class*='job'] li, [class*='recruit'] li, "
                                "[class*='position'] li, a[href]"
                            )
                            for item in items[:12]:
                                try:
                                    link_el = item if item.name == "a" else item.find("a")
                                    if not link_el:
                                        continue
                                    title = link_el.get_text(strip=True)
                                    href = link_el.get("href", "")
                                    if not title or len(title) < 5:
                                        continue
                                    skip_kw = ["招标", "中标", "谈判", "视窗", "loading", "首页", "上一页"]
                                    if any(kw in title for kw in skip_kw):
                                        continue
                                    recruit_kw = ["招聘", "岗位", "职位", "应届", "社招", "校园",
                                                  "招录", "公告", "招考", "人才", "招工",
                                                  "报名", "应聘", "录用公示"]
                                    if not any(kw in title for kw in recruit_kw):
                                        continue
                                    if href and not href.startswith("http"):
                                        href = url.rstrip("/") + (href if href.startswith("/") else "/" + href)
                                    soe_results.append({
                                        "job_title": title, "company": soe_name,
                                        "enterprise_type": "国企", "detail_link": href,
                                        "salary_range": "详见公告", "responsibilities": "详见岗位详情页",
                                        "requirements": "详见岗位详情页",
                                        "benefits": "国企福利待遇（五险二金/年终奖/带薪年假）",
                                        "development": f"{soe_name}地方国企平台稳定",
                                        "work_location": city, "source": f"{soe_name}官网（真实数据）",
                                        "search_keyword": keyword, "_raw_contents": "",
                                        "_raw_edu": "", "_raw_exp": "",
                                    })
                                except Exception:
                                    continue
                            if soe_results:
                                print(f"    [{soe_name}] Playwright 解析到 {len(soe_results)} 条")
                                break
                        except Exception as e:
                            print(f"    [{soe_name}] Playwright 失败: {e}")
                    browser.close()
            except ImportError:
                pass

        results.extend(soe_results)
        print(f"  [{soe_name}] 共获取 {len(soe_results)} 条")

    print(f"[地方国企] 总计解析 {len(results)} 条岗位")
    return results


# ============================================================
# ============================================================
# AI 提取：从微信公众号文章提取结构化岗位（火山方舟 DeepSeek V4）
# ============================================================

_ARK_API_KEY = os.environ.get("ARK_API_KEY", "")
_ARK_ENDPOINT = os.environ.get("ARK_ENDPOINT", "")


def _extract_jobs_with_ai(article_text, user_field, user_city):
    """使用火山方舟 DeepSeek V4 Pro 从公众号文章正文提取岗位。"""
    if not _ARK_API_KEY or not _ARK_ENDPOINT:
        return []

    text_snippet = article_text[:3000]

    prompt = f"""你是招聘信息提取助手。从以下公众号文章提取所有招聘岗位。

要求:
1. 只提取与「{user_field}」相关的岗位
2. 优先提取「{user_city}」的岗位
3. 每个岗位输出: {{"job_title":"","company":"","salary":"","location":""}}
4. 无相关岗位返回 []

只返回 JSON 数组:"""

    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {_ARK_API_KEY}"},
            json={"model": _ARK_ENDPOINT, "messages": [
                {"role": "user", "content": prompt + "\n" + text_snippet}
            ], "max_tokens": 1500, "temperature": 0.1},
            timeout=30,
        )
        if resp.status_code != 200:
            return []
        content = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r"\[.*\]", content, re.DOTALL)
        return json.loads(match.group()) if match else []
    except Exception:
        return []


# 爬虫：微信公众号招聘文章（通过搜狗微信搜索）
# ============================================================

# 时效性阈值：只取发布在 960 小时（40天）内的文章
_WECHAT_MAX_HOURS = 960

# 已验证的公众号白名单缓存（蓝V认证），避免对同一账号重复检测
_VERIFIED_ACCOUNTS_CACHE = set()
_UNVERIFIED_ACCOUNTS_CACHE = set()


def _parse_sogou_publish_time(time_text):
    """解析搜狗微信搜索结果的发布时间，返回 datetime 或 None。

    搜狗页面上的时间格式：
    - "7月15日" → 今年7月15日
    - "3天前" → 3天前
    - "5小时前" → 5小时前
    - "30分钟前" → 30分钟前
    - "昨天" → 昨天
    """
    if not time_text:
        return None
    text = time_text.strip()

    now = datetime.now()
    try:
        # "X天前"
        m = re.match(r"(\d+)\s*天前", text)
        if m:
            days = int(m.group(1))
            from datetime import timedelta
            return now - timedelta(days=days)

        # "X小时前"
        m = re.match(r"(\d+)\s*小时前", text)
        if m:
            hours = int(m.group(1))
            from datetime import timedelta
            return now - timedelta(hours=hours)

        # "X分钟前"
        m = re.match(r"(\d+)\s*分钟前", text)
        if m:
            minutes = int(m.group(1))
            from datetime import timedelta
            return now - timedelta(minutes=minutes)

        # "昨天"
        if "昨天" in text:
            from datetime import timedelta
            return now - timedelta(days=1)

        # "X月X日"
        m = re.match(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            year = now.year
            # 如果月份比当前月份大，说明是去年的
            if month > now.month:
                year -= 1
            return datetime(year, month, day)

        # "X年X月X日"
        m = re.match(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
        if m:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        pass

    return None


def _is_within_time_window(publish_time, max_hours=_WECHAT_MAX_HOURS):
    """判断发布时间是否在时间窗口内。"""
    if publish_time is None:
        return False  # 无法解析时间的，保守跳过
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=max_hours)
    return publish_time >= cutoff


def _check_wechat_account_verified(page, article_url):
    """在 Playwright 已打开的公众号文章页上检查账号是否为蓝V认证。

    策略：三层过滤
    1. 页面DOM检测：查找认证标识元素
    2. 账号名称白名单：匹配已知央企/国企/政府机构名称
    3. 账号名称黑名单：排除中介/猎头/招聘资讯类订阅号

    返回 (verified: bool, account_name: str, account_type: str)
    """
    account_name = ""
    account_type = "unknown"

    try:
        # 从页面提取公众号昵称
        nickname_el = page.query_selector(".rich_media_meta_nickname, #js_name, .wx_follow_nickname")
        if nickname_el:
            account_name = nickname_el.inner_text().strip()

        # === 第1层：页面DOM认证标识检测 ===
        verify_selectors = [
            "#js_profile_qrcode .profile_verify_icon",
            ".rich_media_meta_nickname .verify_icon",
            "#js_verify",
            "[class*='wx_verify']",
        ]
        for sel in verify_selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    title_attr = el.get_attribute("title") or ""
                    title_lower = title_attr.lower()
                    if any(kw in title_lower for kw in ["政府", "事业单位", "机关"]):
                        return True, account_name, "government"
                    if any(kw in title_lower for kw in ["企业", "公司", "集团"]):
                        return True, account_name, "enterprise"
                    if any(kw in title_lower for kw in ["媒体", "新闻"]):
                        return True, account_name, "media"
                    # 有认证标识但无法归类，视为企业认证
                    return True, account_name, "enterprise"
            except Exception:
                continue

        # === 第2层：账号名称白名单（已知央企/国企/政府） ===
        known_official = (
            _ALL_KNOWN_OFFICIAL_ACCOUNTS()  # 动态构建
        )
        if account_name:
            for official_name in known_official:
                if official_name in account_name:
                    return True, account_name, "enterprise"

        # === 第3层：黑名单模式（中介/猎头/招聘资讯类订阅号） ===
        _INTERMEDIARY_PATTERNS = re.compile(
            r"招聘|人才网|人才市场|猎头|人力|HR|兼职|临时工|"
            r"信息平台|资讯|服务网|工作室|Studio|"
            r"每日|大全|汇总|推送|速递|快讯|"
            r"中公|华图|粉笔|导氮|优聘|灵动|智联|前程|猎聘|"
            r"小景|小助手",
        )
        if account_name and _INTERMEDIARY_PATTERNS.search(account_name):
            return False, account_name, "intermediary"

        # 账号名太短或无法判断 → 保守拒绝
        if account_name and len(account_name) < 4:
            return False, account_name, "suspicious_short"

        return False, account_name, "unverified"
    except Exception:
        return False, account_name, "unknown"


def _ALL_KNOWN_OFFICIAL_ACCOUNTS():
    """构建已知官方账号名称列表（央企+地方国企+政府机构简称）。"""
    names = set()
    for soe in NATIONAL_SOE_SOURCES:
        names.add(soe["name"])
    for city_soes in LOCAL_SOE_MAP.values():
        for s in city_soes:
            names.add(s["name"])
    # 常见政府/事业单位关键词
    names.update([
        "中国", "国家", "中央", "国务院", "人力资源社会保障",
        "湖南省", "长沙市", "长沙", "湖南",
        "清华大学", "北京大学", "浙江大学",
    ])
    return sorted(names, key=len, reverse=True)  # 长名称优先匹配


def crawl_wechat_sogou(keyword, city=None):
    """
    ★ 通过搜狗微信搜索大量爬取国企招聘文章。
    不局限于官方招聘网站，全面覆盖国企微信公众号发布的招聘信息。

    搜索策略：
    1. 央企 + 城市：中石油长沙招聘、南方电网长沙招聘...
    2. 地方国企 + 城市：长沙银行招聘、湖南银行招聘...
    3. 通用：长沙 国企招聘、Python开发 招聘 长沙
    4. 每个词取 5 篇文章，去重后返回
    """
    print(f"\n[微信公众号] ★ 搜狗微信搜索（覆盖央企+地方国企公众号），关键词: {keyword}，城市: {city}")

    city_key = (city or "").replace("市", "").strip()
    local_soenames = [s["name"] for s in LOCAL_SOE_MAP.get(city_key, [])]

    # 构建搜索词组合 —— 优先搜专业+城市，再搜央企通用
    search_terms = []

    # ★ 1. 关键词 + 城市组合（最高优先，最精准）
    if keyword and city:
        search_terms.append(f"{city} {keyword} 招聘")
        search_terms.append(f"{keyword} {city} 招聘")
        search_terms.append(f"{city} {keyword}")
        search_terms.append(f"{keyword} 招聘 {city}")
    elif keyword:
        search_terms.append(f"{keyword} 招聘")

    # 2. 城市 + 国企通用搜索
    if city:
        search_terms.append(f"{city} 国企 招聘")
        search_terms.append(f"{city} 央企 招聘")
        search_terms.append(f"{city} 事业单位 招聘")

    # 3. 每个央企 + 城市组合
    for soe in NATIONAL_SOE_SOURCES:
        if city:
            search_terms.append(f"{soe['name']} {city} 招聘")
        search_terms.append(f"{soe['name']} 招聘")

    # 4. 每个地方国企
    for name in local_soenames:
        search_terms.append(f"{name} 招聘")
        if city:
            search_terms.append(f"{name} {city}")

    # 去重并限制（最多30条搜索，足够多）
    search_terms = list(dict.fromkeys(search_terms))[:30]

    results = []
    headers = {
        "User-Agent": COMMON_UA,
        "Referer": "https://weixin.sogou.com/",
    }

    # 去重用
    seen_titles = set()

    for term in search_terms:
        if len(seen_titles) >= 40:  # 凑够40篇就停
            print(f"  [微信搜索] 已收集 {len(seen_titles)} 篇，停止搜索")
            break

        encoded_term = urllib.parse.quote(term)
        search_url = f"https://weixin.sogou.com/weixin?type=2&query={encoded_term}"

        resp = _safe_request(search_url, headers=headers)
        if not resp:
            _random_delay()
            continue

        try:
            resp.encoding = resp.apparent_encoding or "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")

            articles = soup.select(
                ".news-list li, .news-box li, .results li, "
                "[class*='news-item'], [class*='article-item'], "
                "div.txt-box, div.news-box > div"
            )

            found = 0
            for article in articles:
                if found >= 5:
                    break
                try:
                    # 记录文章时间文本（搜狗 HTML 中时间不易可靠解析，
                    # 真正的时效性过滤在 Playwright 获取文章页面时执行）
                    time_el = article.select_one(
                        ".s3, .s4, [class*='p-time'], [class*='date'], "
                        "span:last-of-type"
                    )
                    publish_time_str = time_el.get_text(strip=True) if time_el else ""

                    title_el = article.select_one(
                        "h3 a, h4 a, .tit a, [class*='title'] a, a[target='_blank']"
                    )
                    title = title_el.get_text(strip=True) if title_el else ""
                    href = title_el.get("href", "") if title_el else ""

                    if not title or len(title) < 5:
                        continue

                    # 去重
                    title_key = title[:50]
                    if title_key in seen_titles:
                        continue
                    seen_titles.add(title_key)

                    summary_el = article.select_one(
                        "p.txt-info, .s-p, [class*='summary'], [class*='desc'], p"
                    )
                    summary = summary_el.get_text(strip=True) if summary_el else ""

                    account_el = article.select_one(
                        ".account, .s2, [class*='account'], [class*='author'], .gzh-box .tit"
                    )
                    account_name = account_el.get_text(strip=True) if account_el else ""

                    if href and not href.startswith("http"):
                        href = "https://weixin.sogou.com" + href

                    # 判断是否包含招聘相关内容
                    recruit_kw = ["招聘", "岗位", "职位", "招录", "招考", "招新", "人才"]
                    full_text = title + summary
                    if not any(kw in full_text for kw in recruit_kw):
                        continue

                    # 尝试从标题/摘要中提取公司名
                    company_name = account_name or "国企公众号"
                    for soe in NATIONAL_SOE_SOURCES:
                        if soe["name"] in title or soe["name"] in summary:
                            company_name = soe["name"]
                            break
                    if company_name == account_name or company_name == "国企公众号":
                        for local_name in local_soenames:
                            if local_name in title or local_name in summary:
                                company_name = local_name
                                break

                    detected_city = _detect_city_from_text(title + " " + summary)
                    work_location = detected_city if detected_city else (city or "全国")

                    job_obj = {
                        "job_title": title[:80],
                        "company": company_name,
                        "enterprise_type": "国企",
                        "detail_link": href or search_url,
                        "salary_range": "详见公告",
                        "responsibilities": summary[:200] if summary else "详见岗位详情页",
                        "requirements": "详见岗位详情页",
                        "benefits": "国企福利待遇（五险二金/年终奖/带薪年假）",
                        "development": "国企平台稳定，晋升通道清晰，福利保障完善",
                        "work_location": work_location,
                        "source": f"微信公众号-{account_name}（真实数据）" if account_name else "微信公众号（真实数据）",
                        "search_keyword": keyword,
                        "_raw_contents": summary,
                        "_raw_edu": "",
                        "_raw_exp": "",
                        # 用于后续资质校验和时效过滤
                        "_publish_time_str": publish_time_str,
                        "_account_name": account_name,
                    }
                    results.append(job_obj)
                    found += 1
                except Exception:
                    continue

            if found > 0:
                print(f"  [微信搜索] 「{term}」→ {found} 篇新文章 (累计 {len(seen_titles)} 篇)")

        except Exception as e:
            print(f"    [微信搜索] 解析失败 ({term}): {e}")

        _random_delay()

    # 尝试用 AI 从文章正文中提取结构化岗位信息
    if _ARK_API_KEY and _ARK_ENDPOINT and results:
        ai_jobs = _extract_from_wechat_articles_with_ai(results, keyword, city)
        if ai_jobs:
            print(f"[微信公众号] ★ AI 从文章正文提取到 {len(ai_jobs)} 个结构化岗位")
            # AI 提取的岗位替换原有浅层结果（标题摘要太粗糙）
            results = ai_jobs
        else:
            print(f"[微信公众号] ★ AI 未提取到结构化岗位，保留原始结果")

    print(f"[微信公众号] ★ 总计 {len(results)} 篇招聘文章（来自 {len(search_terms)} 个搜索词）")
    return results


def _extract_from_wechat_articles_with_ai(articles, keyword, city):
    """用 Playwright 获取文章正文 + AI 提取结构化岗位。"""
    ai_jobs = []
    seen = set()

    # Step 1: 用 Playwright 批量获取文章正文和真实链接
    article_texts = _fetch_wechat_articles_with_playwright(articles[:10])

    # Step 2: 分批调用 AI
    # 每批 3 篇，避免文本过长导致 AI 超时
    for i in range(0, len(article_texts), 3):
        chunk = article_texts[i:i+3]
        combined = "\n---\n".join(t["text"] for t in chunk)

        extracted = _extract_jobs_with_ai(combined, keyword, city)
        for ej in extracted:
            job_title = ej.get("job_title", "")
            company = ej.get("company", "国企")
            salary = ej.get("salary", "详见公告")
            location = ej.get("location", city or "全国")

            if not job_title or len(job_title) < 3:
                continue

            # 尝试匹配到原始文章的真实链接
            detail_link = ""
            for at in chunk:
                if job_title in at["text"] or company in at["text"]:
                    detail_link = at.get("wechat_url", "")
                    break

            # 如果没有真实链接，生成搜索链接
            if not detail_link:
                detail_link = _build_search_link(job_title, company, city)

            ai_jobs.append({
                "job_title": job_title[:80],
                "company": company,
                "enterprise_type": "国企",
                "detail_link": detail_link,
                "salary_range": salary,
                "responsibilities": "详见岗位详情页",
                "requirements": "详见岗位详情页",
                "benefits": "国企福利待遇（五险二金/年终奖/带薪年假）",
                "development": "国企平台稳定",
                "work_location": location,
                "source": "微信公众号-AI提取（真实数据）",
                "search_keyword": keyword,
                "_raw_contents": combined[:500],
                "_raw_edu": "",
                "_raw_exp": "",
            })

    return ai_jobs


def _fetch_wechat_articles_with_playwright(articles):
    """用 Playwright 批量打开搜狗微信链接，获取文章正文和真实 mp.weixin.qq.com 链接。"""
    results = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        # 降级：只用标题和摘要
        for a in articles:
            title = a.get("job_title", "")
            summary = a.get("_raw_contents", "")
            if title and len(title) > 2:
                results.append({"text": f"标题:{title}\n摘要:{summary}", "wechat_url": ""})
        return results

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=COMMON_UA, viewport={"width": 1920, "height": 1080}, locale="zh-CN",
            )
            page = context.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )

            for article in articles:
                url = article.get("detail_link", "")
                title = article.get("job_title", "")
                summary = article.get("_raw_contents", "")
                account_name = article.get("_account_name", "")

                # ★ 账号白名单快速通道：已被验证过的账号直接通过
                if account_name and account_name in _VERIFIED_ACCOUNTS_CACHE:
                    pass  # 已验证，直接走后续流程
                elif account_name and account_name in _UNVERIFIED_ACCOUNTS_CACHE:
                    print(f"    [资质过滤] 跳过未认证账号: {account_name}")
                    continue

                if not url or "sogou.com" not in url:
                    results.append({"text": f"标题:{title}\n摘要:{summary}", "wechat_url": url if url else ""})
                    continue

                try:
                    # ★ 关键技巧：每篇文章先回搜狗搜索页建立 cookie 和 referer，
                    # 让搜狗以为是真人浏览行为，再跳转文章链接就不会触发反爬
                    page.goto("https://weixin.sogou.com/weixin?type=2", wait_until="domcontentloaded", timeout=10000)
                    page.wait_for_timeout(500)
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(3000)
                    final_url = page.url

                    if "mp.weixin.qq.com" in final_url:
                        # 先获取页面HTML，用于时间 + 资质双重校验
                        html = page.content()
                        from bs4 import BeautifulSoup as _BS
                        soup = _BS(html, "lxml")

                        # ★ 时效性校验：从公众号文章页提取发布时间
                        publish_time_selectors = [
                            "#publish_time", ".rich_media_meta_text",
                            "#meta_content time", "[class*='publish']",
                            "time", "em#publish_time",
                        ]
                        article_publish_dt = None
                        for pts in publish_time_selectors:
                            pt_el = soup.select_one(pts)
                            if pt_el:
                                pt_text = pt_el.get_text(strip=True) or pt_el.get("datetime", "")
                                article_publish_dt = _parse_sogou_publish_time(pt_text)
                                if article_publish_dt:
                                    break
                        if not _is_within_time_window(article_publish_dt):
                            ts = article_publish_dt.strftime("%Y-%m-%d") if article_publish_dt else "未知"
                            print(f"    [时效过滤] 跳过: {title[:25]} (发布于 {ts}, 超出{_WECHAT_MAX_HOURS}h)")
                            continue

                        # ★ 账号资质校验：检查是否为蓝V认证官方公众号
                        if account_name and account_name not in _VERIFIED_ACCOUNTS_CACHE:
                            verified, _, acct_type = _check_wechat_account_verified(page, final_url)
                            if verified:
                                _VERIFIED_ACCOUNTS_CACHE.add(account_name)
                                print(f"    [资质校验] ✅ 认证账号: {account_name} ({acct_type})")
                            else:
                                _UNVERIFIED_ACCOUNTS_CACHE.add(account_name)
                                print(f"    [资质过滤] ❌ 未认证账号: {account_name}, 跳过")
                                continue

                        body = soup.find("div", id="js_content")
                        text = body.get_text(separator="\n", strip=True)[:2000] if body else title + "\n" + summary
                        results.append({"text": text, "wechat_url": final_url})
                        print(f"    [微信正文] ✅ {title[:25]}")
                    elif "antispider" in final_url:
                        # 被拦，降级为标题摘要
                        results.append({"text": f"标题:{title}\n摘要:{summary}", "wechat_url": ""})
                        print(f"    [微信正文] ⚠️ 反爬: {title[:20]}")
                    else:
                        results.append({"text": f"标题:{title}\n摘要:{summary}", "wechat_url": ""})
                        print(f"    [微信正文] ⚠️ 未到公众号: {title[:20]}")

                except Exception as e:
                    print(f"    [微信正文] ❌ {title[:20]}: {e}")
                    results.append({"text": f"标题:{title}\n摘要:{summary}", "wechat_url": ""})

            browser.close()

    except Exception as e:
        print(f"    [微信正文] Playwright 整体失败: {e}")
        for a in articles:
            title = a.get("job_title", "")
            summary = a.get("_raw_contents", "")
            if title and len(title) > 2:
                results.append({"text": f"标题:{title}\n摘要:{summary}", "wechat_url": ""})

    return results


def _build_search_link(job_title, company, city):
    """为没有详情链接的岗位生成搜索链接。"""
    query = f"{company} {job_title} {city or ''}".strip()
    encoded = urllib.parse.quote(query)
    return f"https://www.iguopin.com/search?keyword={encoded}"


# ============================================================
# 爬虫：国聘网城市定向搜索
# ============================================================

def crawl_iguopin_by_city(keyword, city):
    """
    国聘网城市定向搜索：使用城市筛选参数精准搜索目标城市岗位。
    比通用搜索更精准，专门用于确保有足够的目标城市岗位。
    """
    if not city:
        return crawl_iguopin(keyword, city)

    print(f"\n[国聘网-城市定向] 搜索「{city}」的「{keyword}」岗位")
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

    # 国聘网城市编码映射
    iguopin_city_map = {
        "北京": "110100", "上海": "310100", "广州": "440100",
        "深圳": "440300", "杭州": "330100", "成都": "510100",
        "长沙": "430100", "武汉": "420100", "南京": "320100",
        "西安": "610100", "苏州": "320500", "重庆": "500100",
        "天津": "120100", "郑州": "410100", "青岛": "370200",
        "沈阳": "210100", "大连": "210200", "厦门": "350200",
        "合肥": "340100", "济南": "370100", "哈尔滨": "230100",
        "福州": "350100", "昆明": "530100", "贵阳": "520100",
        "南宁": "450100", "石家庄": "130100", "太原": "140100",
        "长春": "220100", "南昌": "360100", "兰州": "620100",
        "海口": "460100", "呼和浩特": "150100", "银川": "640100",
        "西宁": "630100", "乌鲁木齐": "650100", "拉萨": "540100",
    }
    city_code = iguopin_city_map.get(city.replace("市", ""))

    # 搜索策略1: 带城市编码的精准搜索 + 城市名关键词补充
    payloads = []
    if city_code:
        payloads.append({"page": 1, "page_size": 50, "keyword": keyword, "city": city_code})
    payloads.append({"page": 1, "page_size": 50, "keyword": f"{keyword} {city}"})

    results = []
    for payload in payloads:
        resp = _safe_request(api_url, method="POST", headers=headers, json_body=payload)
        if not resp:
            continue

        try:
            data = resp.json()
            job_list = data.get("data", {}).get("list", []) if isinstance(data, dict) else []

            for item in job_list:
                try:
                    job_id = item.get("job_id") or ""
                    job_name = item.get("job_name") or ""
                    company_name = item.get("company_name") or ""
                    if not job_name or not company_name:
                        continue

                    # 薪资
                    min_wage = item.get("min_wage") or ""
                    max_wage = item.get("max_wage") or ""
                    if min_wage and max_wage:
                        salary_range = f"{min_wage}-{max_wage}元/月"
                    elif min_wage:
                        salary_range = f"{min_wage}元/月起"
                    else:
                        salary_range = item.get("salary") or "面议"

                    edu = item.get("education_cn") or ""
                    exp = item.get("experience_cn") or ""
                    contents = item.get("contents") or ""

                    district_list = item.get("district_list") or []
                    if isinstance(district_list, list) and district_list:
                        work_location = district_list[0].get("area_cn") or city
                    else:
                        work_location = city  # 城市定向搜索默认为该城市

                    company_info = item.get("company_info") or {}
                    nature = company_info.get("nature_cn", "") if isinstance(company_info, dict) else ""

                    enterprise_type = _determine_enterprise_type(nature + " " + company_name, "国聘网")
                    detail_link = f"https://www.iguopin.com/job/detail?id={job_id}" if job_id else ""

                    job_obj = {
                        "job_title": job_name,
                        "company": company_name,
                        "enterprise_type": enterprise_type,
                        "detail_link": detail_link,
                        "salary_range": salary_range,
                        "responsibilities": _extract_responsibilities(contents),
                        "requirements": _extract_requirements(contents, edu, exp),
                        "benefits": _generate_benefits(contents),
                        "development": _generate_development(enterprise_type, "国聘网"),
                        "work_location": work_location,
                        "source": "国聘网-城市定向（真实数据）",
                        "search_keyword": keyword,
                        "_raw_contents": contents,
                        "_raw_edu": edu,
                        "_raw_exp": exp,
                    }
                    results.append(job_obj)
                except Exception:
                    continue

            if results:
                print(f"  [国聘网-城市定向] 本次搜索返回 {len(job_list)} 条，累计 {len(results)} 条")

        except Exception as e:
            print(f"  [国聘网-城市定向] JSON解析失败: {e}")

        _random_delay()

    # 去重
    seen = set()
    deduped = []
    for r in results:
        key = (r["job_title"].lower(), r["company"].lower())
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    print(f"[国聘网-城市定向] 共获取 {len(deduped)} 条「{city}」岗位")
    return deduped


# ============================================================
# 城市筛选
# ============================================================

def filter_by_city(jobs, city, min_count=5):
    """
    ★ 严格城市筛选：只保留用户常驻城市的岗位。

    规则：
    - 只返回 work_location 匹配用户城市的岗位
    - 如果匹配岗位 < min_count，仍然只返回城市匹配的（不补充全国岗位）
    - 如果城市匹配为 0，打印警告但仍返回空列表（不放宽要求）
    """
    if not city:
        return jobs

    city_jobs = [j for j in jobs if _is_city_match(j.get("work_location", ""), city)]
    other_jobs = [j for j in jobs if not _is_city_match(j.get("work_location", ""), city)]

    print(f"  严格城市筛选: 匹配「{city}」的岗位 {len(city_jobs)} 个，其他城市 {len(other_jobs)} 个（已排除）")

    if len(city_jobs) == 0:
        print(f"  ⚠️ 警告: 没有找到{city}的岗位！将不返回任何结果（不放宽城市要求）")
    elif len(city_jobs) < min_count:
        print(f"  ⚠️ {city}岗位仅 {len(city_jobs)} 个（不足{min_count}个），但仍只保留{city}岗位")

    return city_jobs


# ============================================================
# 搜索链接生成
# ============================================================

def build_search_links(job_title, company=None):
    """
    为每个岗位生成多平台搜索链接。
    主流程会调用此函数，为每个岗位生成在各平台的搜索入口。
    """
    if not job_title:
        return {}

    encoded_title = urllib.parse.quote(job_title)
    links = {
        "国聘网": f"https://www.iguopin.com/search?keyword={encoded_title}",
        "BOSS直聘": f"https://www.zhipin.com/web/geek/job?query={encoded_title}",
        "智联招聘": f"https://sou.zhaopin.com/?kw={encoded_title}",
        "前程无忧": f"https://search.51job.com/list/000000,000000,0000,00,9,99,{encoded_title},2,1.html",
        "猎聘": f"https://www.liepin.com/zhaopin/?key={encoded_title}",
    }

    if company:
        encoded_company = urllib.parse.quote(company)
        links["企业查询"] = f"https://www.qcc.com/search?key={encoded_company}"

    return links


# ============================================================
# 主函数：generate_recommendations
# ============================================================

def generate_recommendations(user):
    """
    根据用户信息从多个招聘平台爬取真实在招岗位。

    参数:
        user (dict): 用户信息字典，包含:
            - id: 用户ID
            - city: 期望工作城市
            - degree: 学历（本科/硕士/博士）
            - experience: 工作经验（如"3年"）
            - field: 求职方向/关键词
            - certifications: 权威证书（可能为空）
            - email: 邮箱

    返回:
        list[dict]: 岗位推荐列表，每个字典包含:
            - job_title: 岗位名称
            - company: 公司名称
            - enterprise_type: 企业类型（国企/私企/外企）
            - match_score: 匹配度 0-100
            - detail_link: 详情链接
            - salary_range: 薪资范围
            - responsibilities: 岗位职责
            - requirements: 任职要求
            - benefits: 福利待遇
            - development: 职业发展前景
            - work_location: 工作地点
            - source: 数据来源标注
            - search_keyword: 搜索关键词
    """
    print("=" * 60)
    print(f"开始生成岗位推荐 | 用户ID: {user.get('id', 'unknown')}")
    print(f"城市: {user.get('city', '未知')} | 学历: {user.get('degree', '未知')} | "
          f"经验: {user.get('experience', '未知')} | 方向: {user.get('field', '未知')}")
    print("=" * 60)

    keyword = user.get("field") or user.get("direction") or ""
    city = user.get("city") or ""

    if not keyword:
        print("[ERROR] 缺少求职方向关键词")
        return []

    if not city:
        print("[WARNING] 未提供常驻城市，无法进行城市定向搜索")

    print(f"\n★★★ 策略: 以「{city}」常驻城市为第一优先，专业方向为第二优先 ★★★")

    all_jobs = []

    # ------------------------------------------------
    # 1. 国聘网-城市定向搜索（最高优先级，精准匹配城市）
    # ------------------------------------------------
    try:
        print(f"\n>>> [1/7] 爬取国聘网（{city}城市定向）...")
        iguopin_city_jobs = crawl_iguopin_by_city(keyword, city)
        all_jobs.extend(iguopin_city_jobs)
        print(f"国聘网-城市定向返回 {len(iguopin_city_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[国聘网-城市定向] 爬取失败: {e}")

    # ------------------------------------------------
    # 2. 国聘网通用搜索（补充数据）
    # ------------------------------------------------
    try:
        print("\n>>> [2/7] 爬取国聘网（通用搜索）...")
        _random_delay()
        iguopin_jobs = crawl_iguopin(keyword, city)
        all_jobs.extend(iguopin_jobs)
        print(f"国聘网通用返回 {len(iguopin_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[国聘网] 爬取失败: {e}")

    # ------------------------------------------------
    # 3. 央企招聘官网（中石油/南方电网/国家电网等）
    # ------------------------------------------------
    try:
        print("\n>>> [3/7] 爬取央企招聘官网（中石油/南方电网/国家电网等）...")
        _random_delay()
        soe_jobs = crawl_national_soe(keyword, city)
        all_jobs.extend(soe_jobs)
        print(f"央企官网返回 {len(soe_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[央企官网] 爬取失败: {e}")

    # ------------------------------------------------
    # 4. 地方国企（按用户城市匹配，如长沙银行/湖南银行）
    # ------------------------------------------------
    try:
        print(f"\n>>> [4/7] 爬取{city}地方国企招聘...")
        _random_delay()
        local_soe_jobs = crawl_local_soe(keyword, city)
        all_jobs.extend(local_soe_jobs)
        print(f"地方国企返回 {len(local_soe_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[地方国企] 爬取失败: {e}")

    # ------------------------------------------------
    # 5. 微信公众号招聘文章（搜狗微信搜索）
    # ------------------------------------------------
    try:
        print("\n>>> [5/7] 爬取微信公众号招聘文章（搜狗微信搜索）...")
        _random_delay()
        wechat_jobs = crawl_wechat_sogou(keyword, city)
        all_jobs.extend(wechat_jobs)
        print(f"微信公众号返回 {len(wechat_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[微信公众号] 爬取失败: {e}")

    # ------------------------------------------------
    # 6. BOSS直聘（Playwright渲染）
    # ------------------------------------------------
    try:
        print("\n>>> [6/7] 爬取BOSS直聘...")
        _random_delay()
        boss_jobs = crawl_boss(keyword, city)
        all_jobs.extend(boss_jobs)
        print(f"BOSS直聘返回 {len(boss_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[BOSS直聘] 爬取失败: {e}")

    # ------------------------------------------------
    # 7. 智联招聘（Playwright渲染）
    # ------------------------------------------------
    try:
        print("\n>>> [7/7] 爬取智联招聘...")
        _random_delay()
        zhaopin_jobs = crawl_zhaopin(keyword, city)
        all_jobs.extend(zhaopin_jobs)
        print(f"智联招聘返回 {len(zhaopin_jobs)} 条，累计 {len(all_jobs)} 条")
    except Exception as e:
        print(f"[智联招聘] 爬取失败: {e}")

    # ------------------------------------------------
    # 去重
    # ------------------------------------------------
    print(f"\n去重前: {len(all_jobs)} 条")
    seen = set()
    deduped = []
    for job in all_jobs:
        key = (job.get("job_title", "").lower(), job.get("company", "").lower())
        if key not in seen:
            seen.add(key)
            deduped.append(job)
    print(f"去重后: {len(deduped)} 条")

    # ------------------------------------------------
    # 城市筛选
    # ------------------------------------------------
    print("\n按城市筛选...")
    filtered = filter_by_city(deduped, city, min_count=5)

    # ------------------------------------------------
    # 计算匹配度
    # ------------------------------------------------
    print("\n计算匹配度...")
    for job in filtered:
        job["match_score"] = calculate_match_score(job, user)

    # 按匹配度排序
    filtered.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    # ------------------------------------------------
    # 清理临时字段
    # ------------------------------------------------
    for job in filtered:
        job.pop("_raw_contents", None)
        job.pop("_raw_edu", None)
        job.pop("_raw_exp", None)

    # 按匹配度过滤：>=50 分才推荐，不足5条时放宽到 >=30
    min_score = 50
    qualified = [j for j in filtered if j.get("match_score", 0) >= min_score]
    if len(qualified) < 5:
        min_score = 30
        qualified = [j for j in filtered if j.get("match_score", 0) >= min_score]
        print(f"\n⚠️ >=50分仅 {len([j for j in filtered if j.get('match_score',0) >= 50])} 条，放宽到 >=30 分")

    # 限制返回数量（最多20条）
    result = qualified[:20]

    print("\n" + "=" * 60)
    print(f"岗位推荐生成完成！共 {len(result)} 条岗位")
    print(f"来源统计:")
    source_count = {}
    for job in result:
        src = job.get("source", "未知")
        source_count[src] = source_count.get(src, 0) + 1
    for src, cnt in source_count.items():
        print(f"  {src}: {cnt} 条")
    print("=" * 60)

    return result


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    # 测试用例
    test_user = {
        "id": 1,
        "city": "长沙",
        "degree": "硕士",
        "experience": "3年",
        "field": "Python开发",
        "certifications": "PMP",
        "email": "test@example.com",
    }

    jobs = generate_recommendations(test_user)
    print(f"\n返回 {len(jobs)} 条岗位推荐:")
    for i, job in enumerate(jobs, 1):
        print(f"\n--- 岗位 {i} ---")
        print(f"  岗位名称: {job.get('job_title')}")
        print(f"  公司: {job.get('company')}")
        print(f"  企业类型: {job.get('enterprise_type')}")
        print(f"  匹配度: {job.get('match_score')}")
        print(f"  薪资: {job.get('salary_range')}")
        print(f"  地点: {job.get('work_location')}")
        print(f"  来源: {job.get('source')}")
        print(f"  详情链接: {job.get('detail_link')}")
