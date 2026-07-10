/**
 * 生成项目交付报告 PDF
 * 运行: node generate_pdf.js
 */

const PDFDocument = require('pdfkit');
const fs = require('fs');

// 中文字体路径
const FONT_PATH = 'C:/Windows/Fonts/msyh.ttc';
const OUTPUT_PATH = 'C:/Users/LEO/Desktop/12wsx/项目交付报告_智能岗位推荐.pdf';

// 创建 PDF 文档
const doc = new PDFDocument({
  size: 'A4',
  margins: { top: 60, bottom: 60, left: 55, right: 55 },
  info: {
    Title: '智能岗位推荐系统 - 项目交付报告',
    Author: 'CodeBuddy',
    Subject: 'Next.js + Supabase 智能岗位推荐 Web 应用',
    CreationDate: new Date(),
  },
});

// 输出流
const stream = fs.createWriteStream(OUTPUT_PATH);
doc.pipe(stream);

// 注册中文字体
doc.registerFont('ChineseFont', FONT_PATH, 'MicrosoftYaHei');

// ========== 颜色定义 ==========
const COLORS = {
  primary: '#2563eb',
  secondary: '#1e40af',
  accent: '#3b82f6',
  text: '#1f2937',
  lightText: '#6b7280',
  success: '#16a34a',
  bgLight: '#f0f9ff',
  border: '#e5e7eb',
};

// ========== 工具函数 ==========
function drawLine(y, color = COLORS.border) {
  doc.moveTo(55, y).lineTo(540, y).strokeColor(color).lineWidth(0.5).stroke();
}

function addTitle(text) {
  doc.font('ChineseFont').fontSize(28).fillColor(COLORS.primary).text(text, { align: 'center' });
  doc.moveDown(0.3);
}

function addSubtitle(text) {
  doc.font('ChineseFont').fontSize(12).fillColor(COLORS.lightText).text(text, { align: 'center' });
  doc.moveDown(1.5);
}

function addSectionTitle(num, title) {
  doc.moveDown(0.8);
  // 背景条
  const y = doc.y;
  doc.rect(55, y - 2, 485, 26).fill(COLORS.bgLight);
  doc.font('ChineseFont').fontSize(14).fillColor(COLORS.primary)
    .text(`  ${num}. ${title}`, 58, y + 4);
  doc.moveDown(0.8);
}

function addBody(text, options = {}) {
  doc.font('ChineseFont').fontSize(10.5).fillColor(options.color || COLORS.text)
    .text(text, { lineGap: 6, ...options });
  doc.moveDown(0.3);
}

function addBold(label, value) {
  const x = doc.x;
  const y = doc.y;
  doc.font('ChineseFont').fontSize(10.5).fillColor(COLORS.secondary).text(`${label}: `, x, y, { continued: true });
  doc.fillColor(COLORS.text).text(value || '—');
  doc.moveDown(0.15);
}

function addBulletPoint(text, indent = 70) {
  const x = indent;
  const y = doc.y;
  doc.font('ChineseFont').fontSize(10.5).fillColor(COLORS.accent).text('\u2022', x - 12, y);
  doc.fillColor(COLORS.text).text(text, x, y, { width: 430 });
  doc.moveDown(0.25);
}

function addTable(headers, rows) {
  const colWidths = [130, 355];
  const startX = 55;
  let y = doc.y;

  // 表头背景
  doc.rect(startX, y, 485, 24).fill('#eff6ff');
  
  // 表头文字
  let x = startX + 10;
  headers.forEach((h, i) => {
    doc.font('ChineseFont').fontSize(10).fillColor(COLORS.primary)
      .text(h, x, y + 6, { width: colWidths[i] - 14 });
    x += colWidths[i];
  });

  y += 24;

  // 数据行
  rows.forEach((row, idx) => {
    // 计算行高
    const rowHeight = Math.max(22, 18);
    
    // 交替背景
    if (idx % 2 === 1) {
      doc.rect(startX, y, 485, rowHeight).fill('#fafafa');
    }

    // 分隔线
    doc.moveTo(startX, y).lineTo(startX + 485, y).strokeColor(COLORS.border).lineWidth(0.3).stroke();

    // 行数据
    x = startX + 10;
    row.forEach((cell, i) => {
      doc.font('ChineseFont').fontSize(9.5).fillColor(COLORS.text)
        .text(cell, x, y + 4, { width: colWidths[i] - 14 });
      x += colWidths[i];
    });

    y += rowHeight;
  });

  // 底线
  doc.moveTo(startX, y).lineTo(startX + 485, y).strokeColor(COLORS.border).lineWidth(0.5).stroke();
  doc.y = y + 10;
}

function checkPageSpace(needed = 100) {
  if (doc.y > 750 - needed) {
    doc.addPage();
  }
}

// ==================== 页面内容 ====================

// ===== 封面 =====
doc.rect(0, 0, 595.28, 841.89).fill('#0f172a');

// 装饰圆
doc.circle(500, 150, 120).fillOpacity(0.08).fill(COLORS.accent);
doc.circle(80, 700, 100).fillOpacity(0.06).fill(COLORS.accent);

doc.moveDown(8);
addTitle('智能岗位推荐系统');
doc.moveDown(0.3);
doc.font('ChineseFont').fontSize(16).fillColor('#94a3b8').text('项目交付报告', { align: 'center' });

drawLine(doc.y + 5, '#334155');
doc.moveDown(1.5);

const coverInfo = [
  ['技术栈', 'Next.js 14 + TypeScript + Tailwind CSS'],
  ['后端', 'Supabase (PostgreSQL)'],
  ['AI 引擎', 'DeepSeek Chat API'],
  ['部署方式', 'Vercel / GitHub Actions'],
];

coverInfo.forEach(([label, value]) => {
  doc.font('ChineseFont').fontSize(11).fillColor('#94a3b8')
    .text(label, { align: 'center', continued: true })
    .fillColor('#e2e8f0').text(`   ${value}`, { align: 'left' });
  doc.moveDown(0.5);
});

doc.moveDown(4);
doc.font('ChineseFont').fontSize(10).fillColor('#64748b')
  .text(`生成日期: ${new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })}`, { align: 'center' });

// ===== 目录页 =====
doc.addPage();
addSectionTitle('', '目 录');
doc.moveDown(0.5);

const tocItems = [
  ['一', '项目概述'],
  ['二', '功能特性'],
  ['三', '技术架构'],
  ['四', '文件结构说明'],
  ['五', 'API 接口文档'],
  ['六', '数据库设计'],
  ['七', '定时任务配置'],
  ['八', '核心代码展示'],
  ['九', '环境变量配置'],
  ['十', '部署指南'],
];

tocItems.forEach(([num, title], idx) => {
  const y = doc.y;
  doc.font('ChineseFont').fontSize(12).fillColor(COLORS.primary).text(num, 75, y);
  doc.fillColor(COLORS.text).text(title, 105, y);
  drawLine(doc.y + 2, '#f0f0f0');
  doc.moveDown(0.4);
});

// ===== 一、项目概述 =====
doc.addPage();
addSectionTitle('一', '项目概述');
addBody(
  '本项目是一个基于 AI 的智能岗位推荐 Web 应用。用户填写个人求职信息（城市、学历、经验、求职方向等），' +
  '系统自动通过 DeepSeek AI 分析并生成个性化岗位推荐结果。推荐任务由 GitHub Actions 定时触发（每 8 小时），' +
  '支持微信推送通知。'
);
doc.moveDown(0.3);
addBody('核心价值:', { color: COLORS.primary });
addBulletPoint('智能化推荐 — 基于 DeepSeek 大模型分析用户画像，精准匹配岗位');
addBulletPoint('自动化运行 — GitHub Actions 定时触发，无需人工干预');
addBulletPoint('多渠道通知 — 支持 PushPlus 微信实时推送推荐结果');
addBulletPoint('现代化前端 — Next.js 14 + React 18 + Tailwind CSS 响应式设计');

checkPageSpace(200);

// ===== 二、功能特性 =====
addSectionTitle('二', '功能特性');
addTable(
  ['功能模块', '详细描述'],
  [
    ['求职信息表单', '收集城市、学历、经验、方向、证书、邮箱等信息'],
    ['AI 岗位推荐', '调用 DeepSeek API 根据画像生成 3 条匹配岗位'],
    ['推荐历史查看', '按用户 ID 展示历史推荐记录卡片列表'],
    ['定时推荐任务', 'GitHub Actions 每 8 小时自动执行一次推荐'],
    ['微信推送通知', '通过 PushPlus 将推荐结果推送到微信'],
    ['响应式 UI', '适配桌面端和移动端的现代界面设计'],
  ]
);

// ===== 三、技术架构 =====
doc.addPage();
addSectionTitle('三', '技术架构');
addBody('前端技术栈:', { color: COLORS.primary });
addBulletPoint('Next.js 14 — App Router 架构，SSR/SSG 支持');
addBulletPoint('React 18 — 组件化开发，useState/useEffect 状态管理');
addBulletPoint('TypeScript 5.7 — 类型安全，完整的类型定义');
addBulletPoint('Tailwind CSS 3.4 — 原子化 CSS，快速构建现代 UI');
addBulletPoint('pg 8.22 — Node.js PostgreSQL 客户端（本地开发用）');

doc.moveDown(0.5);
addBody('后端 / 数据层:', { color: COLORS.primary });
addBulletPoint('Supabase — 托管 PostgreSQL 数据库，提供认证和 REST API');
addBulletPoint('PostgREST — Supabase 内置的 RESTful API 层');
addBulletPoint('RLS 行级安全 — 数据库级别的访问控制策略');
addBulletPoint('psycopg2-binary — Python PostgreSQL 客户端（已替换为 REST API）');

doc.moveDown(0.5);
addBody('AI & 自动化:', { color: COLORS.primary });
addBulletPoint('DeepSeek Chat API — 大语言模型，用于生成个性化岗位推荐');
addBulletPoint('GitHub Actions — CI/CD 平台，负责定时执行推荐脚本');
addBulletPoint('PushPlus — 微信推送服务，将推荐通知发送给用户');

checkPageSpace(250);

// ===== 四、文件结构 =====
addSectionTitle('四', '文件结构说明');
const fileStructure = `job-recommend/
├── app/
│   ├── api/
│   │   ├── submit/route.ts          # POST 用户资料提交 API
│   │   └── recommendations/route.ts # GET 推荐结果查询 API
│   ├── history/page.tsx             # 推荐历史页面
│   ├── page.tsx                     # 首页（表单页面）
│   ├── layout.tsx                   # 全局布局
│   └── globals.css                  # 全局样式
├── lib/
│   └── db.ts                        # PostgreSQL 连接池（本地开发）
├── scripts/
│   └── recommend_jobs.py            # 定时推荐主脚本（REST API 方案）
├── .github/workflows/
│   └── job-recommend.yml            # GitHub Actions 定时任务配置
├── requirements.txt                 # Python 依赖
├── package.json                     # Node.js 依赖
├── next.config.js                   # Next.js 配置
└── tailwind.config.ts               # Tailwind CSS 配置`;

doc.font('Courier').fontSize(8.5).fillColor('#374151').text(fileStructure, { lineGap: 2 });

// ===== 五、API 接口 =====
doc.addPage();
addSectionTitle('五', 'API 接口文档');

addBody('POST /api/submit — 提交用户资料', { color: COLORS.primary, bold: true });
doc.moveDown(0.2);
addBold('请求方法', 'POST');
addBold('Content-Type', 'application/json');
addBold('请求参数', '');
addTable(
  ['参数名', '类型 | 必填 | 说明'],
  [
    ['city', 'string | 必填 | 所在城市'],
    ['degree', 'string | 必填 | 最高学历（大专~博士）'],
    ['experience', 'string | 必填 | 工作经验描述'],
    ['field', 'string | 必填 | 求职方向'],
    ['certifications', 'string | 选填 | 权威证书'],
    ['email', 'string | 选填 | 联系邮箱'],
  ]
);
addBold('返回示例', '{ "userId": 42 } (HTTP 201)');
doc.moveDown(0.5);

checkPageSpace(300);

addBody('GET /api/recommendations?userId=XXX — 查询推荐结果', { color: COLORS.primary, bold: true });
doc.moveDown(0.2);
addBold('请求方法', 'GET');
addBold('查询参数', 'userId (number, 必填)');
addBold('返回字段', '');
addTable(
  ['字段名', '类型 | 说明'],
  [
    ['id', 'integer | 推荐记录 ID'],
    ['job_title', 'string | 岗位名称'],
    ['company', 'string | 公司名称'],
    ['enterprise_type', 'string | 企业类型 (国企/私企/外企)'],
    ['match_score', 'integer | 匹配度 (0-100)'],
    ['detail_link', 'string | 岗位详情链接'],
    ['user_id', 'integer | 关联的用户 ID'],
    ['created_at', 'string | 创建时间'],
  ]
);

// ===== 六、数据库设计 =====
doc.addPage();
addSectionTitle('六', '数据库设计');

addBody('user_profiles 表 — 用户资料', { color: COLORS.primary, bold: true });
doc.moveDown(0.2);
addTable(
  ['字段名', '类型 | 说明'],
  [
    ['id', 'serial PK | 自增主键'],
    ['city', 'varchar | 所在城市'],
    ['degree', 'varchar | 最高学历'],
    ['experience', 'varchar | 工作经验'],
    ['field', 'varchar | 求职方向'],
    ['certifications', 'varchar | 权威证书（可空）'],
    ['email', 'varchar | 邮箱（可空）'],
    ['created_at', 'timestampz | 创建时间'],
  ]
);
doc.moveDown(0.5);

addBody('job_recommendations 表 — 推荐结果', { color: COLORS.primary, bold: true });
doc.moveDown(0.2);
addTable(
  ['字段名', '类型 | 说明'],
  [
    ['id', 'serial PK | 自增主键'],
    ['user_id', 'integer FK | 关联 user_profiles.id'],
    ['job_title', 'varchar | 岗位名称'],
    ['company', 'varchar | 公司名'],
    ['enterprise_type', 'varchar | 国企/私企/外企'],
    ['match_score', 'integer | 匹配度 0-100'],
    ['detail_link', 'varchar | 详情链接 URL'],
    ['created_at', 'timestampz | 创建时间'],
  ]
);

checkPageSpace(200);

// ===== 七、定时任务 =====
doc.addPage();
addSectionTitle('七', '定时任务配置');

addBody('GitHub Actions Cron 工作流', { color: COLORS.primary, bold: true });
doc.moveDown(0.3);
addBold('文件位置', '.github/workflows/job-recommend.yml');
addBold('执行频率', '每 8 小时整点 (cron: 0 */8 * * *) UTC');
addBold('触发方式', '定时调度 + 手动触发 (workflow_dispatch)');
addBold('运行环境', 'ubuntu-latest, Python 3.11, 超时 10 分钟');

doc.moveDown(0.5);
addBody('执行流程:', { color: COLORS.primary });
addBulletPoint('Step 1 — 检出代码仓库 (actions/checkout@v4)');
addBulletPoint('Step 2 — 设置 Python 3.11 环境');
addBulletPoint('Step 3 — 安装 Python 依赖 (pip install -r requirements.txt)');
addBulletPoint('Step 4 — 执行推荐脚本 (python scripts/recommend_jobs.py)');

doc.moveDown(0.5);
addBody('所需 GitHub Secrets:', { color: COLORS.primary });
addTable(
  ['Secret 名称', '说明'],
  [
    ['SUPABASE_URL', 'Supabase 项目 URL (https://xxx.supabase.co)'],
    ['SUPABASE_KEY', 'service_role 密钥 (eyJ... 开头)'],
    ['DEEPSEEK_APL_KEY', 'DeepSeek API 密钥'],
    ['PUSHPLUS_TOKEN', 'PushPlus 微信推送 token (可选)'],
  ]
);

// ===== 八、核心代码展示 =====
doc.addPage();
addSectionTitle('八', '核心代码展示');

addBody('8.1 推荐脚本主流程 (recommend_jobs.py)', { color: COLORS.primary, bold: true });
doc.moveDown(0.2);
const pyCode1 = `# 初始化
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPAB_KEY = os.environ.get("SUPABASE_KEY")
HEADERS = {"apikey": SUPAB_KEY, "Authorization": f"Bearer {SUPAB_KEY}"}

def fetch_users():
    """REST API 读取所有用户"""
    resp = requests.get(f"{URL}/rest/v1/user_profiles?order=desc", headers=HEADERS)
    return resp.json()

def generate_recommendations(user):
    """调用 DeepSeek AI 生成 3 条推荐"""
    client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(model="deepseek-chat", ...)
    return json.loads(resp.choices[0].message.content)

def save_recommendations(user_id, jobs):
    """REST API 写入推荐结果"""
    for j in jobs:
        requests.post(f"{URL}/rest/v1/job_recommendations", headers=HEADERS, json={...})`;

doc.font('Courier').fontSize(7.5).fillColor('#1e293b').text(pyCode1, { lineGap: 1.5 });
doc.moveDown(0.5);

checkPageSpace(280);

addBody('8.2 表单提交 API (route.ts)', { color: COLORS.primary, bold: true });
doc.moveDown(0.2);
const tsCode1 = `import { queryOne } from "@/lib/db";

export async function POST(req: NextRequest) {
  const { city, degree, experience, field, certifications, email } = await req.json();
  const data = await queryOne<{ id: number }>(
    \`INSERT INTO public.user_profiles (city, degree, experience, field, certifications, email)
     VALUES ($1, $2, $3, $4, $5, \$6) RETURNING id\`,
    [city, degree, experience, field, certifications, email]
  );
  return NextResponse.json({ userId: data.id }, { status: 201 });
}`;

doc.font('Courier').fontSize(7.5).fillColor('#1e293b').text(tsCode1, { lineGap: 1.5 });

// ===== 九、环境变量 =====
doc.addPage();
addSectionTitle('九', '环境变量配置');

addBody('.env.local — 本地开发', { color: COLORS.primary, bold: true });
doc.moveDown(0.2);
const envLocal = `DATABASE_URL=postgresql://postgres:[密码]@db.clihwbzomhctkxooldbz.supabase.co:5432/postgres

# Next.js
NEXT_PUBLIC_SUPABASE_URL=https://clihwbzomhctkxooldbz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...anon_key...`;
doc.font('Courier').fontSize(8.5).fillColor('#374151').text(envLocal, { lineGap: 2 });
doc.moveDown(0.5);

addBody('GitHub Secrets — Actions 使用', { color: COLORS.primary, bold: true });
doc.moveDown(0.2);
addTable(
  ['Secret 名称', '值来源 / 说明'],
  [
    ['SUPABASE_URL', 'Settings > API > Project URL'],
    ['SUPABASE_KEY', 'Settings > API > service_role secret'],
    ['DEEPSEEK_APL_KEY', 'platform.deepseek.com > API Keys'],
    ['PUSHPLUS_TOKEN', 'pushplus.plus > 登录获取 token'],
  ]
);

// ===== 十、部署指南 =====
doc.addPage();
addSectionTitle('十', '部署指南');

addBody('步骤 1 — 克隆项目', { color: COLORS.primary, bold: true });
addBody('git clone https://github.com/laborsneverdie/turbo-waddle.git && cd turbo-waddle');
doc.moveDown(0.3);

addBody('步骤 2 — 本地安装依赖', { color: COLORS.primary, bold: true });
addBody('npm install\n# 创建 .env.local 并填入 DATABASE_URL');
doc.moveDown(0.3);

addBody('步骤 3 — 启动开发服务器', { color: COLORS.primary, bold: true });
addBody('npm run dev  # 访问 http://localhost:3000');
doc.moveDown(0.3);

addBody('步骤 4 — Vercel 一键部署', { color: COLORS.primary, bold: true });
addBulletPoint('连接 GitHub 仓库到 Vercel');
addBulletPoint('Framework Preset 选择 Next.js');
addBulletPoint('在 Vercel Environment Variables 中添加 DATABASE_URL');
addBulletPoint('点击 Deploy，等待构建完成');
doc.moveDown(0.3);

addBody('步骤 5 — 配置 GitHub Actions 定时任务', { color: COLORS.primary, bold: true });
addBulletPoint('进入仓库 Settings > Secrets and variables > Actions');
addBulletPoint('添加 SUPABASE_URL、SUPABASE_KEY、DEEPSEEK_APL_KEY、PUSHPLUS_TOKEN');
addBulletPoint('提交 .github/workflows/job-recommend.yml 后自动生效');
addBulletPoint('可在 Actions 页面手动 Run workflow 测试');

doc.moveDown(1);
drawLine(doc.y);
doc.moveDown(0.5);

// 页脚
doc.font('ChineseFont').fontSize(9).fillColor(COLORS.lightText)
  .text('本报告由 CodeBuddy 自动生成', { align: 'center' });
doc.moveDown(0.2);
doc.fontSize(8).fillColor('#d1d5db')
  .text('智能岗位推荐系统 | Next.js + Supabase + DeepSeek', { align: 'center' });

// ========== 结束 ==========
doc.end();

stream.on('finish', () => {
  console.log(`\n✅ PDF 已生成: ${OUTPUT_PATH}`);
  console.log(`   文件大小: ${(fs.statSync(OUTPUT_PATH).size / 1024).toFixed(1)} KB`);
});
