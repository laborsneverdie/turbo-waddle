# 响应式求职推荐网站

Vue + Node.js + SQLite

## 项目特性

- 📝 用户信息表单（首页）
  - 常住城市、最高学历、工作年限、求职方向、个人邮箱、微信推送 SendKey
  - 提交后显示成功提示，并基于用户信息推荐岗位

- 💾 后端（Node.js + Express + sql.js）
  - 用户信息增删改查
  - 岗位数据分两张表：`jobs_state`（国企）、`jobs_private`（私企/外企）
  - 岗位字段：岗位名称、公司名称、公司类型、工作城市、学历要求、经验要求、薪资范围、岗位职责、招聘链接、发布时间

- 🎯 推荐算法：70% 国企 + 30% 私企/外企，优先国企优先匹配
- 📱 移动端完美适配，表单紧凑

## 目录结构

```
job-recommend/
├── package.json
├── server.js        # 后端服务 + API
├── seed.js          # 批量插入示例岗位脚本
├── jobs.db          # SQLite 数据库（启动后自动创建）
├── index.html       # 用户信息填写（Vue 表单 + 推荐结果）
├── admin.html       # 用户列表 / 管理员页
├── job-detail.html  # 岗位详情页
├── style.css        # 响应式样式
└── .gitignore
```

## 启动方式

```bash
cd job-recommend
npm install
# 启动服务
npm start
# 另开终端，批量插入示例岗位
node seed.js
# 打开浏览器访问服务（默认 http://localhost:3000，线上部署由平台自动分配地址）
```

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/users` | 提交用户信息 |
| GET | `/api/users` | 查询用户列表（最多200条 |
| GET | `/api/users/:id` | 查询单个用户 |
| PUT | `/api/users/:id` | 更新用户信息 |
| DELETE | `/api/users/:id` | 删除用户 |
| POST | `/api/jobs/batch` | 岗位批量插入 `{ source: 'state'\|'private', items: [...] }` |
| GET | `/api/jobs?source=state&city=&keyword=` | 岗位列表查询 |
| POST | `/api/recommend` | 根据用户信息推荐岗位：`{ city, education, experience, direction, size }` |
| GET | `/api/stats` | 数据总览统计 |

## 页面说明

- `index.html`（/）：用户表单 + 成功提示 + 岗位推荐卡片。
- `admin.html`（/admin.html）：数据总览 + 用户列表，支持删除。
