const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const initSqlJs = require('sql.js');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '5mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(express.static(__dirname));

// ---- 数据库初始化 ----
const DB_PATH = path.join(__dirname, 'jobs.db');
let db;

function saveDb() {
  const data = db.export();
  const buffer = Buffer.from(data);
  fs.writeFileSync(DB_PATH, buffer);
}

function initDb(SQL) {
  // 创建表
  db.run(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      city TEXT NOT NULL,
      education TEXT NOT NULL,
      experience TEXT NOT NULL,
      direction TEXT NOT NULL,
      qualification TEXT,
      skills TEXT,
      email TEXT NOT NULL,
      sendkey TEXT,
      created_at TEXT DEFAULT (datetime('now','localtime'))
    );
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS jobs_state (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      company TEXT NOT NULL,
      company_type TEXT DEFAULT '国企',
      city TEXT NOT NULL,
      education TEXT,
      experience TEXT,
      salary TEXT,
      duties TEXT,
      link TEXT,
      published_at TEXT
    );
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS jobs_private (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      company TEXT NOT NULL,
      company_type TEXT DEFAULT '私企',
      city TEXT NOT NULL,
      education TEXT,
      experience TEXT,
      salary TEXT,
      duties TEXT,
      link TEXT,
      published_at TEXT
    );
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS state_owned_jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_title TEXT NOT NULL,
      company_name TEXT NOT NULL,
      city TEXT NOT NULL,
      education_req TEXT,
      experience_req TEXT,
      salary TEXT,
      job_desc TEXT,
      job_url TEXT,
      publish_time TEXT,
      create_time TEXT DEFAULT (datetime('now','localtime'))
    );
  `);
  db.run(`
    CREATE TABLE IF NOT EXISTS private_jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_title TEXT NOT NULL,
      company_name TEXT NOT NULL,
      city TEXT NOT NULL,
      education_req TEXT,
      experience_req TEXT,
      salary TEXT,
      job_desc TEXT,
      job_url TEXT,
      publish_time TEXT,
      create_time TEXT DEFAULT (datetime('now','localtime'))
    );
  `);

  // 兼容旧表结构（尝试添加缺失列，忽略已存在的）
  try { db.run('ALTER TABLE users ADD COLUMN qualification TEXT'); } catch (e) {}
  try { db.run('ALTER TABLE users ADD COLUMN skills TEXT'); } catch (e) {}
  try { db.run('ALTER TABLE jobs_state ADD COLUMN skills TEXT'); } catch (e) {}
  try { db.run('ALTER TABLE jobs_private ADD COLUMN skills TEXT'); } catch (e) {}
}

// ---- sql.js 查询辅助函数 ----
function run(sql, params = []) {
  db.run(sql, params);
  saveDb();
}

function get(sql, params = []) {
  const stmt = db.prepare(sql);
  if (params.length > 0) stmt.bind(params);
  let row = null;
  if (stmt.step()) {
    row = stmt.getAsObject();
  }
  stmt.free();
  return row;
}

function all(sql, params = []) {
  const stmt = db.prepare(sql);
  if (params.length > 0) stmt.bind(params);
  const rows = [];
  while (stmt.step()) {
    rows.push(stmt.getAsObject());
  }
  stmt.free();
  return rows;
}

// ---- 启动时加载数据库 ----
(async () => {
  const SQL = await initSqlJs();
  if (fs.existsSync(DB_PATH)) {
    try {
      const fileBuffer = fs.readFileSync(DB_PATH);
      db = new SQL.Database(fileBuffer);
      console.log('从文件加载数据库成功');
    } catch (e) {
      console.log('数据库文件损坏，创建新数据库:', e.message);
      db = new SQL.Database();
    }
  } else {
    console.log('数据库文件不存在，创建新数据库');
    db = new SQL.Database();
  }
  initDb(SQL);
  // 仅在全新数据库时写入一次
  saveDb();
  console.log('数据库已初始化');
})();

// ---- 城市 → 省份/直辖市映射 ----
const CITY_PROVINCE = {
  // 直辖市
  '北京': '北京', '北京市': '北京',
  '上海': '上海', '上海市': '上海',
  '天津': '天津', '天津市': '天津',
  '重庆': '重庆', '重庆市': '重庆',
  // 广东
  '广州': '广东', '广州市': '广东', '深圳': '广东', '深圳市': '广东',
  '东莞': '广东', '东莞市': '广东', '佛山': '广东', '佛山市': '广东',
  '珠海': '广东', '珠海市': '广东', '惠州': '广东', '惠州市': '广东',
  '中山': '广东', '中山市': '广东', '江门': '广东', '江门市': '广东',
  '汕头': '广东', '汕头市': '广东',
  // 湖南
  '长沙': '湖南', '长沙市': '湖南', '株洲': '湖南', '株洲市': '湖南',
  '湘潭': '湖南', '湘潭市': '湖南', '衡阳': '湖南', '衡阳市': '湖南',
  '岳阳': '湖南', '岳阳市': '湖南', '常德': '湖南', '常德市': '湖南',
  // 湖北
  '武汉': '湖北', '武汉市': '湖北', '宜昌': '湖北', '宜昌市': '湖北',
  '襄阳': '湖北', '襄阳市': '湖北', '荆州': '湖北', '荆州市': '湖北',
  // 浙江
  '杭州': '浙江', '杭州市': '浙江', '宁波': '浙江', '宁波市': '浙江',
  '温州': '浙江', '温州市': '浙江', '嘉兴': '浙江', '嘉兴市': '浙江',
  // 江苏
  '南京': '江苏', '南京市': '江苏', '苏州': '江苏', '苏州市': '江苏',
  '无锡': '江苏', '无锡市': '江苏', '常州': '江苏', '常州市': '江苏',
  '徐州': '江苏', '徐州市': '江苏',
  // 四川
  '成都': '四川', '成都市': '四川', '绵阳': '四川', '绵阳市': '四川',
  // 陕西
  '西安': '陕西', '西安市': '陕西',
  // 安徽
  '合肥': '安徽', '合肥市': '安徽',
  // 福建
  '厦门': '福建', '厦门市': '福建', '福州': '福建', '福州市': '福建',
  // 山东
  '济南': '山东', '济南市': '山东', '青岛': '山东', '青岛市': '山东',
  // 河南
  '郑州': '河南', '郑州市': '河南', '洛阳': '河南', '洛阳市': '河南',
  // 辽宁
  '沈阳': '辽宁', '沈阳市': '辽宁', '大连': '辽宁', '大连市': '辽宁',
  // 吉林
  '长春': '吉林', '长春市': '吉林',
  // 黑龙江
  '哈尔滨': '黑龙江', '哈尔滨市': '黑龙江',
  // 江西
  '南昌': '江西', '南昌市': '江西',
  // 河北
  '石家庄': '河北', '石家庄市': '河北', '唐山': '河北', '唐山市': '河北',
  // 山西
  '太原': '山西', '太原市': '山西',
  // 云南
  '昆明': '云南', '昆明市': '云南',
  // 贵州
  '贵阳': '贵州', '贵阳市': '贵州',
  // 广西
  '南宁': '广西', '南宁市': '广西',
  // 内蒙古
  '呼和浩特': '内蒙古', '呼和浩特市': '内蒙古',
  // 甘肃
  '兰州': '甘肃', '兰州市': '甘肃',
  // 海南
  '海口': '海南', '海口市': '海南',
  // 西藏
  '拉萨': '西藏', '拉萨市': '西藏',
  // 宁夏
  '银川': '宁夏', '银川市': '宁夏',
  // 青海
  '西宁': '青海', '西宁市': '青海',
  // 新疆
  '乌鲁木齐': '新疆', '乌鲁木齐市': '新疆',
};

/** 根据城市名获取省份，支持模糊匹配 */
function getProvince(cityName) {
  if (!cityName) return null;
  // 先精确匹配
  if (CITY_PROVINCE[cityName]) return CITY_PROVINCE[cityName];
  // 尝试去掉"市"字匹配
  const short = cityName.replace(/市$/, '');
  if (CITY_PROVINCE[short]) return CITY_PROVINCE[short];
  // 尝试加"市"字匹配
  if (CITY_PROVINCE[short + '市']) return CITY_PROVINCE[short + '市'];
  // 模糊匹配：遍历所有城市映射
  for (const [city, province] of Object.entries(CITY_PROVINCE)) {
    if (city.includes(cityName) || cityName.includes(city)) {
      return province;
    }
  }
  return null;
}

// ---- 评分系统 ----
const EDU_ORDER = {
  '不限': 0, '大专': 1, '双非本科': 2, '211本科': 3, '985本科': 4,
  '本科': 2.5, '双非硕士': 5, '211硕士': 6, '985硕士': 7,
  '硕士': 6, '博士': 8
};
const EXP_ORDER = { '不限': 0, '应届': 1, '1年以下': 2, '1-3年': 3, '3-5年': 4, '5-10年': 5, '10年以上': 6 };

function eduScore(req, user) {
  const r = EDU_ORDER[req] ?? 0;
  const u = EDU_ORDER[user] ?? 99;
  if (r === 0) return 2;
  if (u >= r) return 3;
  return 0;
}

function expScore(req, user) {
  const r = EXP_ORDER[req] ?? 0;
  const u = EXP_ORDER[user] ?? 99;
  if (r === 0) return 2;
  if (u >= r) return 3;
  return 0;
}

/** 计算经验接近度：差值越小，得分越高（0-5分） */
function expProximityScore(req, user) {
  const r = EXP_ORDER[req] ?? 0;
  const u = EXP_ORDER[user] ?? 0;
  if (r === 0) return 2; // 岗位不限经验，给中间分
  const diff = Math.abs(u - r);
  if (diff === 0) return 5; // 完全匹配
  if (diff === 1) return 4;
  if (diff === 2) return 2;
  return 0;
}

/** 解析薪资字符串，返回中位数（单位：K） */
function parseSalaryMedian(salaryStr) {
  if (!salaryStr) return 0;
  // 匹配 "15-25K" 或 "15-25k" 或 "15K-25K"
  const m = salaryStr.match(/(\d+)\s*[-~至到]\s*(\d+)\s*[Kk]/);
  if (m) return (parseInt(m[1]) + parseInt(m[2])) / 2;
  // 匹配单个数 "15K"
  const s = salaryStr.match(/(\d+)\s*[Kk]/);
  if (s) return parseInt(s[1]);
  return 0;
}

function parseSkills(text) {
  if (!text) return [];
  return text
    .split(/[,，、\s]+/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

function matchAndSort(jobs, user) {
  const userSkills = parseSkills(user.skills || '');
  return jobs
    .map((j) => {
      let score = 0;
      if (j.city && user.city && j.city.includes(user.city)) score += 4;
      score += eduScore(j.education, user.education);
      score += expScore(j.experience, user.experience);
      if (j.title && user.direction && (j.title.includes(user.direction) || (j.duties || '').includes(user.direction))) score += 3;
      if (userSkills.length > 0) {
        const jobText = (j.title + ' ' + (j.duties || '') + ' ' + (j.skills || '')).toLowerCase();
        for (const sk of userSkills) {
          if (jobText.includes(sk)) score += 2;
        }
      }
      return { ...j, _score: score };
    })
    .sort((a, b) => b._score - a._score);
}

function matchAndSortV2(jobs, user) {
  const userSkills = parseSkills(user.skills || '');
  const userQualification = parseSkills(user.qualification || ''); // 专业资质关键词
  const userProvince = getProvince(user.city);
  const userDir = (user.direction || '').toLowerCase();

  // 方向关键词映射表：将求职方向映射到相关岗位关键词
  const DIRECTION_KEYWORDS = {
    '财务会计': ['会计', '财务', '审计', '税务', '出纳', '成本', '核算', '报表', '总账', '资金', '预算'],
    '人力资源': ['人力资源', '人事', 'HR', '招聘', '薪酬', '绩效', '培训', '员工关系', '组织发展'],
    '行政管理': ['行政', '文秘', '前台', '档案', '后勤', '办公室主任', '综合管理'],
    '市场营销': ['市场', '营销', '品牌', '推广', '销售', '商务', '客户', '渠道', '运营'],
    '法务': ['法务', '律师', '合规', '合同', '知识产权', '法律'],
    '设计': ['设计', 'UI', 'UX', '美工', '视觉', '平面', '交互', '创意'],
    '产品经理': ['产品', '需求', '规划', '原型', 'PRD'],
    '前端开发': ['前端', 'Web', 'H5', 'React', 'Vue', 'Angular', 'JavaScript', 'CSS', 'HTML', '小程序'],
    '后端开发': ['后端', 'Java', 'Go', 'Python', 'C++', 'Node', 'PHP', '服务端', 'API', '微服务', 'Spring'],
    '测试': ['测试', 'QA', '自动化', '质量'],
    '运维': ['运维', 'DevOps', 'Linux', 'Docker', 'Kubernetes', '监控', '部署'],
    '数据分析': ['数据', '分析', 'BI', 'SQL', 'Python', '报表', '数仓', 'ETL', '大数据'],
    '人工智能': ['AI', '算法', '机器学习', '深度学习', 'NLP', 'CV', '推荐'],
    '嵌入式': ['嵌入式', '单片机', 'ARM', 'C/C++', 'RTOS', '硬件'],
    '电气工程': ['电气', '电力', '自动化', 'PLC', '配电'],
    '机械工程': ['机械', '结构', 'CAD', '制造', '工艺'],
  };

  // 计算方向相关性得分 (0-20分)
  function directionRelevanceScore(jobTitle, jobDesc) {
    const text = ((jobTitle || '') + ' ' + (jobDesc || '')).toLowerCase();
    let bestScore = 0;

    // 遍历所有方向组，找到与用户方向最匹配的
    for (const [dirKey, keywords] of Object.entries(DIRECTION_KEYWORDS)) {
      // 用户的求职方向是否属于这个方向组
      const dirLower = dirKey.toLowerCase();
      const userDirMatches = userDir.includes(dirLower) || dirLower.includes(userDir);

      if (!userDirMatches) continue;

      // 计算岗位文本与方向关键词的匹配度
      let matchCount = 0;
      for (const kw of keywords) {
        if (text.includes(kw.toLowerCase())) {
          matchCount++;
        }
      }

      // 得分：0-20，基础匹配1个关键词=8分，每多1个+3分，上限20
      let dirScore = matchCount > 0 ? Math.min(8 + (matchCount - 1) * 3, 20) : 0;

      // 如果岗位标题直接包含用户的求职方向词，额外加分
      if (jobTitle && jobTitle.toLowerCase().includes(userDir)) {
        dirScore = Math.min(dirScore + 5, 20);
      }

      bestScore = Math.max(bestScore, dirScore);
    }

    return bestScore;
  }

  // 第一步：标记城市关系并评分
  const scored = jobs
    .map((j) => {
      let score = 0;
      let cityRelation = 'cross_province'; // 默认跨省

      if (j.city && user.city) {
        const jobProvince = getProvince(j.city);
        const isSameCity = j.city.includes(user.city) || user.city.includes(j.city);
        const isSameProvince = userProvince && jobProvince && userProvince === jobProvince;

        if (isSameCity) {
          cityRelation = 'same_city';
          score += 10; // 同城 +10
        } else if (isSameProvince) {
          cityRelation = 'same_province';
          score += 5; // 同省周边城市 +5
        }
      }

      // 方向相关性得分（0-20，核心评分因子）
      const dirScore = directionRelevanceScore(j.job_title, j.job_desc);
      score += dirScore;

      // 学历/经验匹配
      score += eduScore(j.education_req, user.education);
      score += expScore(j.experience_req, user.experience);
      // 经验接近度得分（0-5，同优先级内区分岗位）
      score += expProximityScore(j.experience_req, user.experience);

      // 薪资中位数（用于同优先级内次级排序）
      const salaryMedian = parseSalaryMedian(j.salary);

      // 专业资质匹配：用户的 qualification 关键词出现在岗位描述中
      if (userQualification.length > 0) {
        const jobText = (j.job_title + ' ' + (j.job_desc || '')).toLowerCase();
        for (const qk of userQualification) {
          if (jobText.includes(qk)) score += 4;
        }
      }

      // 技能关键词匹配
      if (userSkills.length > 0) {
        const jobText = (j.job_title + ' ' + (j.job_desc || '')).toLowerCase();
        for (const sk of userSkills) {
          if (jobText.includes(sk)) score += 3;
        }
      }

      return { ...j, _score: score, _dirScore: dirScore, _cityRelation: cityRelation, _salaryMedian: salaryMedian };
    });

  // 第二步：按方向相关性过滤 —— 方向完全不匹配的岗位排到最后
  const relevant = scored.filter(j => j._dirScore >= 8);
  const irrelevant = scored.filter(j => j._dirScore < 8);

  // 相关岗位按城市关系+评分排序
  const relSameCity = relevant.filter(j => j._cityRelation === 'same_city').sort((a, b) => b._score - a._score);
  const relSameProvince = relevant.filter(j => j._cityRelation === 'same_province').sort((a, b) => b._score - a._score);
  const relCross = relevant.filter(j => j._cityRelation === 'cross_province').sort((a, b) => b._score - a._score);

  // 不相关岗位按城市关系+评分排序（作为后备）
  const irrSameCity = irrelevant.filter(j => j._cityRelation === 'same_city').sort((a, b) => b._score - a._score);
  const irrSameProvince = irrelevant.filter(j => j._cityRelation === 'same_province').sort((a, b) => b._score - a._score);
  const irrCross = irrelevant.filter(j => j._cityRelation === 'cross_province').sort((a, b) => b._score - a._score);

  // 按优先级合并：相关 > 不相关，同城 > 同省 > 跨省
  const result = [
    ...relSameCity, ...relSameProvince, ...relCross,
    ...irrSameCity, ...irrSameProvince, ...irrCross
  ];

  return result;
}

// ---- 用户接口 ----
app.post('/api/users', (req, res) => {
  const { city, education, experience, direction, qualification, skills, email, sendkey } = req.body || {};
  if (!city || !education || !experience || !direction || !qualification || !email) {
    return res.status(400).json({ ok: false, msg: '请填写所有必填字段（含专业资质与权威证书）' });
  }
  run('INSERT INTO users (city, education, experience, direction, qualification, skills, email, sendkey) VALUES (?,?,?,?,?,?,?,?)',
    [city, education, experience, direction, qualification || '', skills || '', email, sendkey || '']);
  // sql.js 的 last_insert_rowid() 可能返回异常，改用 MAX(id) 获取最新 ID
  const row = get('SELECT MAX(id) AS id FROM users');
  res.json({ ok: true, id: row.id, msg: '提交成功，已为您生成岗位推荐' });
});

app.get('/api/users', (req, res) => {
  const rows = all('SELECT * FROM users ORDER BY id DESC LIMIT 200');
  res.json({ ok: true, data: rows });
});

app.get('/api/users/:id', (req, res) => {
  const row = get('SELECT * FROM users WHERE id = ?', [req.params.id]);
  if (!row) return res.status(404).json({ ok: false, msg: '未找到用户' });
  res.json({ ok: true, data: row });
});

app.put('/api/users/:id', (req, res) => {
  const { city, education, experience, direction, qualification, skills, email, sendkey } = req.body || {};
  const existing = get('SELECT * FROM users WHERE id = ?', [req.params.id]);
  if (!existing) return res.status(404).json({ ok: false, msg: '未找到用户' });
  run('UPDATE users SET city=?, education=?, experience=?, direction=?, qualification=?, skills=?, email=?, sendkey=? WHERE id=?',
    [city || existing.city, education || existing.education, experience || existing.experience,
      direction || existing.direction, qualification ?? existing.qualification, skills ?? existing.skills,
      email || existing.email, sendkey ?? existing.sendkey, req.params.id]);
  res.json({ ok: true, msg: '更新成功' });
});

app.delete('/api/users/:id', (req, res) => {
  run('DELETE FROM users WHERE id = ?', [req.params.id]);
  res.json({ ok: true, msg: '删除成功' });
});

// ---- 旧岗位接口 ----
app.post('/api/jobs/batch', (req, res) => {
  const { source, items } = req.body || {};
  const table = source === 'private' ? 'jobs_private' : 'jobs_state';
  if (!Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ ok: false, msg: 'items 必须为非空数组' });
  }
  for (const it of items) {
    run(`INSERT INTO ${table} (title, company, company_type, city, education, experience, salary, duties, link, published_at) VALUES (?,?,?,?,?,?,?,?,?,?)`,
      [it.title, it.company, it.company_type || (table === 'jobs_state' ? '国企' : '私企'), it.city, it.education || '不限', it.experience || '不限', it.salary || '面议', it.duties || '', it.link || '', it.published_at || new Date().toISOString().slice(0, 10)]);
  }
  const total = get(`SELECT COUNT(*) AS c FROM ${table}`).c;
  res.json({ ok: true, inserted: items.length, total, table });
});

app.get('/api/jobs', (req, res) => {
  const { source, city, keyword } = req.query;
  const table = source === 'private' ? 'jobs_private' : 'jobs_state';
  let sql = `SELECT * FROM ${table} WHERE 1=1`;
  const params = [];
  if (city) { sql += ' AND city LIKE ?'; params.push(`%${city}%`); }
  if (keyword) { sql += ' AND (title LIKE ? OR company LIKE ? OR duties LIKE ?)'; params.push(`%${keyword}%`, `%${keyword}%`, `%${keyword}%`); }
  sql += ' ORDER BY id DESC LIMIT 200';
  const rows = all(sql, params);
  res.json({ ok: true, data: rows, total: rows.length, table });
});

// ---- 新增：state_owned_jobs 批量插入 ----
app.post('/api/state-jobs/batch', (req, res) => {
  const { items } = req.body || {};
  if (!Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ ok: false, msg: 'items 必须为非空数组' });
  }
  for (const it of items) {
    run('INSERT INTO state_owned_jobs (job_title, company_name, city, education_req, experience_req, salary, job_desc, job_url, publish_time) VALUES (?,?,?,?,?,?,?,?,?)',
      [it.job_title, it.company_name, it.city, it.education_req || '', it.experience_req || '', it.salary || '', it.job_desc || '', it.job_url || '', it.publish_time || '']);
  }
  const total = get('SELECT COUNT(*) AS c FROM state_owned_jobs').c;
  res.json({ ok: true, inserted: items.length, total, table: 'state_owned_jobs' });
});

// ---- 新增：private_jobs 批量插入 ----
app.post('/api/private-jobs/batch', (req, res) => {
  const { items } = req.body || {};
  if (!Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ ok: false, msg: 'items 必须为非空数组' });
  }
  for (const it of items) {
    run('INSERT INTO private_jobs (job_title, company_name, city, education_req, experience_req, salary, job_desc, job_url, publish_time) VALUES (?,?,?,?,?,?,?,?,?)',
      [it.job_title, it.company_name, it.city, it.education_req || '', it.experience_req || '', it.salary || '', it.job_desc || '', it.job_url || '', it.publish_time || '']);
  }
  const total = get('SELECT COUNT(*) AS c FROM private_jobs').c;
  res.json({ ok: true, inserted: items.length, total, table: 'private_jobs' });
});

// ---- 岗位推荐接口 ----
app.post('/api/recommend', (req, res) => {
  const { user_id } = req.body || {};

  if (!user_id) {
    return res.status(400).json({ ok: false, msg: '缺少参数 user_id' });
  }
  const user = get('SELECT * FROM users WHERE id = ?', [user_id]);
  if (!user) {
    return res.status(404).json({ ok: false, msg: '未找到该用户，请先提交求职信息' });
  }

  const TOTAL = 10;
  const STATE_TARGET = 7;
  const PRIVATE_TARGET = 3;

  // 从新表读取国企和私企岗位
  const stateAll = all('SELECT job_title, company_name, city, education_req, experience_req, salary, job_desc, job_url, publish_time, id FROM state_owned_jobs');
  const privateAll = all('SELECT job_title, company_name, city, education_req, experience_req, salary, job_desc, job_url, publish_time, id FROM private_jobs');

  const stateSorted = matchAndSortV2(stateAll, user);
  const privateSorted = matchAndSortV2(privateAll, user);

  // 去重：按 job_title + company_name 唯一
  const dedup = (arr) => {
    const seen = new Set();
    return arr.filter(j => {
      const key = (j.job_title + '|' + j.company_name).toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };

  // 去重后的排序结果
  const stateDeduped = dedup(stateSorted);
  const privateDeduped = dedup(privateSorted);

  // 分离同城/同省/跨省
  const filterByRelation = (arr, relation) => arr.filter(j => j._cityRelation === relation);

  const stateSameCity = filterByRelation(stateDeduped, 'same_city');
  const stateSameProvince = filterByRelation(stateDeduped, 'same_province');
  const stateCross = filterByRelation(stateDeduped, 'cross_province');

  const privateSameCity = filterByRelation(privateDeduped, 'same_city');
  const privateSameProvince = filterByRelation(privateDeduped, 'same_province');
  const privateCross = filterByRelation(privateDeduped, 'cross_province');

  // 核心规则：优先同城 → 不够则同省补充 → 再不够才跨省（禁止跨省出现在同省够用的情况下）
  // minDirScore: 最低方向相关性分数，低于此分的岗位只在后备不足时使用
  function pickWithPriority(sameCity, sameProvince, cross, target, minDirScore) {
    let picked = [];
    const usedKeys = new Set();

    // 分离相关和不相关的岗位
    const relevant = (arr) => arr.filter(j => (j._dirScore || 0) >= minDirScore);
    const irrelevant = (arr) => arr.filter(j => (j._dirScore || 0) < minDirScore);

    const tryPick = (pool) => {
      for (const j of pool) {
        if (picked.length >= target) break;
        const key = (j.job_title + '|' + j.company_name).toLowerCase();
        if (!usedKeys.has(key)) {
          picked.push(j);
          usedKeys.add(key);
        }
      }
    };

    // 第一优先级：同城相关岗位
    tryPick(relevant(sameCity));

    // 第二优先级：同省相关岗位
    if (picked.length < target) tryPick(relevant(sameProvince));

    // 第三优先级：跨省相关岗位
    if (picked.length < target) tryPick(relevant(cross));

    // 第四优先级：同城不相关岗位（仅在相关岗位不够时）
    if (picked.length < target) tryPick(irrelevant(sameCity));

    // 第五优先级：同省不相关岗位
    if (picked.length < target) tryPick(irrelevant(sameProvince));

    // 第六优先级：跨省不相关岗位
    if (picked.length < target) tryPick(irrelevant(cross));

    return picked;
  }

  const MIN_DIR_SCORE = 8; // 方向相关性最低阈值

  let statePicked = pickWithPriority(stateSameCity, stateSameProvince, stateCross, STATE_TARGET, MIN_DIR_SCORE);
  let privatePicked = pickWithPriority(privateSameCity, privateSameProvince, privateCross, PRIVATE_TARGET, MIN_DIR_SCORE);

  // 国企不足由私企补充（同样遵循方向相关性+同城优先规则）
  if (statePicked.length < STATE_TARGET) {
    const usedKeys = new Set([...statePicked, ...privatePicked].map(j => (j.job_title + '|' + j.company_name).toLowerCase()));
    const tryFill = (pool) => {
      for (const j of pool) {
        if (statePicked.length >= STATE_TARGET) break;
        const key = (j.job_title + '|' + j.company_name).toLowerCase();
        if (!usedKeys.has(key)) {
          statePicked.push(j);
          usedKeys.add(key);
        }
      }
    };
    const relevant = (arr) => arr.filter(j => (j._dirScore || 0) >= MIN_DIR_SCORE);
    const irrelevant = (arr) => arr.filter(j => (j._dirScore || 0) < MIN_DIR_SCORE);
    // 优先相关岗位
    tryFill(relevant(privateSameCity));
    tryFill(relevant(privateSameProvince));
    tryFill(relevant(privateCross));
    // 相关不够再补不相关
    tryFill(irrelevant(privateSameCity));
    tryFill(irrelevant(privateSameProvince));
    tryFill(irrelevant(privateCross));
  }

  // 私企不足由国企补充（同样遵循方向相关性+同城优先规则）
  if (privatePicked.length < PRIVATE_TARGET) {
    const usedKeys = new Set([...statePicked, ...privatePicked].map(j => (j.job_title + '|' + j.company_name).toLowerCase()));
    const tryFill = (pool) => {
      for (const j of pool) {
        if (privatePicked.length >= PRIVATE_TARGET) break;
        const key = (j.job_title + '|' + j.company_name).toLowerCase();
        if (!usedKeys.has(key)) {
          privatePicked.push(j);
          usedKeys.add(key);
        }
      }
    };
    const relevant = (arr) => arr.filter(j => (j._dirScore || 0) >= MIN_DIR_SCORE);
    const irrelevant = (arr) => arr.filter(j => (j._dirScore || 0) < MIN_DIR_SCORE);
    tryFill(relevant(stateSameCity));
    tryFill(relevant(stateSameProvince));
    tryFill(relevant(stateCross));
    tryFill(irrelevant(stateSameCity));
    tryFill(irrelevant(stateSameProvince));
    tryFill(irrelevant(stateCross));
  }

  // 最终按同城→同省→跨省排序，同层内按评分降序
  // 国企和私企混合后按城市关系分组
  const allPicked = [...statePicked, ...privatePicked];

  function sortByScore(arr) {
    return arr.slice().sort((a, b) => {
      // 主排序：综合评分降序
      const diff = b._score - a._score;
      if (diff !== 0) return diff;
      // 次级排序1：经验要求越接近用户越好（经验接近度得分高的排前面）
      // 这里直接比较 experience_req 与用户 experience 的差值
      const userExpOrder = EXP_ORDER[user.experience] ?? 0;
      const aExpOrder = EXP_ORDER[a.experience_req] ?? 0;
      const bExpOrder = EXP_ORDER[b.experience_req] ?? 0;
      const aExpDiff = aExpOrder === 0 ? 999 : Math.abs(userExpOrder - aExpOrder);
      const bExpDiff = bExpOrder === 0 ? 999 : Math.abs(userExpOrder - bExpOrder);
      if (aExpDiff !== bExpDiff) return aExpDiff - bExpDiff;
      // 次级排序2：薪资中位数越高越优先
      return (b._salaryMedian || 0) - (a._salaryMedian || 0);
    });
  }

  const sameCity = sortByScore(allPicked.filter(j => j._cityRelation === 'same_city'));
  const sameProvince = sortByScore(allPicked.filter(j => j._cityRelation === 'same_province'));
  const crossProvince = sortByScore(allPicked.filter(j => j._cityRelation === 'cross_province'));

  const merged = [...sameCity, ...sameProvince, ...crossProvince];

  res.json({
    ok: true,
    user: {
      id: user.id,
      city: user.city,
      education: user.education,
      experience: user.experience,
      direction: user.direction
    },
    total: merged.length,
    state_count: statePicked.length,
    private_count: privatePicked.length,
    jobs: merged
  });
});

app.get('/api/stats', (req, res) => {
  const users = get('SELECT COUNT(*) AS c FROM users').c;
  const s1 = get('SELECT COUNT(*) AS c FROM jobs_state').c;
  const s2 = get('SELECT COUNT(*) AS c FROM state_owned_jobs').c;
  const p1 = get('SELECT COUNT(*) AS c FROM jobs_private').c;
  const p2 = get('SELECT COUNT(*) AS c FROM private_jobs').c;
  res.json({ ok: true, users, stateOwned: s1 + s2, privateForeign: p1 + p2 });
});

// 等数据库初始化完成后再启动监听
const startServer = () => {
  if (!db) {
    setTimeout(startServer, 100);
    return;
  }
  app.listen(PORT, () => {
    console.log(`求职推荐服务已启动，端口: ${PORT}`);
  });
};
startServer();
