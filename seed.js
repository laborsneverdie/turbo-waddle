// 种子数据脚本 —— 多元化岗位数据
// 覆盖 IT开发 / 财务会计 / 人力资源 / 市场营销 / 行政管理 / 法务 / 设计 等多方向
// 用法：node seed.js

const sampleStateOwned = [
  // ==================== 财务会计 ====================
  { job_title: '财务会计', company_name: '中国中车株洲所', city: '株洲', education_req: '本科', experience_req: '1-3年', salary: '10-15K', job_desc: '负责总账、成本核算、财务报表编制，熟悉企业会计准则。', job_url: 'https://example.com/job/15', publish_time: '2026-05-15' },
  { job_title: '财务主管', company_name: '中国移动研究院', city: '北京', education_req: '本科', experience_req: '3-5年', salary: '18-28K', job_desc: '负责财务预算管理、成本控制、税务筹划，中级会计职称以上优先。', job_url: 'https://example.com/job/62', publish_time: '2026-06-18' },
  { job_title: '审计专员', company_name: '中国南方航空', city: '广州', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '内部审计与风险控制，熟悉审计准则，CPA优先。', job_url: 'https://example.com/job/63', publish_time: '2026-06-12' },
  { job_title: '成本会计', company_name: '中国二重集团', city: '绵阳', education_req: '本科', experience_req: '1-3年', salary: '10-15K', job_desc: '负责制造成本核算、存货管理、成本分析。', job_url: 'https://example.com/job/64', publish_time: '2026-06-08' },
  { job_title: '出纳', company_name: '天津港集团', city: '天津', education_req: '大专', experience_req: '1-3年', salary: '7-10K', job_desc: '负责现金收付、银行结算、票据管理。', job_url: 'https://example.com/job/65', publish_time: '2026-06-10' },
  { job_title: '财务分析师', company_name: '国家电网湖南公司', city: '长沙', education_req: '本科', experience_req: '3-5年', salary: '15-22K', job_desc: '负责财务数据分析、经营预测、投资回报分析，熟悉用友NC。', job_url: 'https://example.com/job/66', publish_time: '2026-06-15' },
  { job_title: '税务专员', company_name: '中国石油', city: '成都', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责税务申报、税收筹划、税务合规检查。', job_url: 'https://example.com/job/67', publish_time: '2026-06-14' },
  { job_title: '财务会计', company_name: '中国电子科技集团', city: '武汉', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '负责日常账务处理、费用报销审核、月末结账。', job_url: 'https://example.com/job/68', publish_time: '2026-06-11' },
  { job_title: '财务经理', company_name: '招商局集团', city: '深圳', education_req: '硕士', experience_req: '5-10年', salary: '25-40K', job_desc: '全面负责财务管理工作，中级以上职称，CPA/CMA优先。', job_url: 'https://example.com/job/69', publish_time: '2026-06-05' },
  { job_title: '预算管理专员', company_name: '东风汽车集团', city: '武汉', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责年度预算编制、预算执行分析、成本控制。', job_url: 'https://example.com/job/70', publish_time: '2026-06-09' },
  { job_title: '会计', company_name: '中国电信集团', city: '上海', education_req: '本科', experience_req: '1-3年', salary: '13-18K', job_desc: '负责收入核算、应收账款管理、账龄分析，熟悉金蝶软件。', job_url: 'https://example.com/job/71', publish_time: '2026-06-13' },
  { job_title: '审计经理', company_name: '国家电网', city: '北京', education_req: '硕士', experience_req: '5-10年', salary: '25-38K', job_desc: '内部审计体系建设与执行，CPA必备。', job_url: 'https://example.com/job/72', publish_time: '2026-06-07' },
  { job_title: '资金管理专员', company_name: '中国工商银行', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '14-20K', job_desc: '负责资金调度、现金流管理、银行对账。', job_url: 'https://example.com/job/73', publish_time: '2026-06-16' },

  // ==================== 人力资源 ====================
  { job_title: '人力资源专员', company_name: '中国航天科工', city: '北京', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责招聘、培训、绩效管理，熟悉劳动法。', job_url: 'https://example.com/job/74', publish_time: '2026-06-15' },
  { job_title: 'HRBP', company_name: '中国南方航空', city: '广州', education_req: '本科', experience_req: '3-5年', salary: '18-28K', job_desc: '业务部门人力资源合作伙伴，负责人才盘点与组织发展。', job_url: 'https://example.com/job/75', publish_time: '2026-06-10' },
  { job_title: '薪酬福利专员', company_name: '中国银联', city: '上海', education_req: '本科', experience_req: '1-3年', salary: '14-20K', job_desc: '负责薪酬核算、社保公积金管理、个税申报。', job_url: 'https://example.com/job/76', publish_time: '2026-06-08' },
  { job_title: '培训主管', company_name: '湖南广电集团', city: '长沙', education_req: '本科', experience_req: '3-5年', salary: '13-18K', job_desc: '负责企业培训体系建设、课程开发与内训师管理。', job_url: 'https://example.com/job/77', publish_time: '2026-06-12' },
  { job_title: '招聘专员', company_name: '中国建筑', city: '深圳', education_req: '本科', experience_req: '1-3年', salary: '12-17K', job_desc: '负责社会招聘与校园招聘，熟悉主流招聘渠道。', job_url: 'https://example.com/job/78', publish_time: '2026-06-14' },
  { job_title: '人力资源经理', company_name: '浪潮集团', city: '济南', education_req: '本科', experience_req: '5-10年', salary: '20-30K', job_desc: '全面负责HR六大模块，有制造业HR经验优先。', job_url: 'https://example.com/job/79', publish_time: '2026-06-06' },
  { job_title: '员工关系专员', company_name: '中国一汽集团', city: '长春', education_req: '本科', experience_req: '1-3年', salary: '10-15K', job_desc: '负责员工入离职、劳动合同管理、劳动争议处理。', job_url: 'https://example.com/job/80', publish_time: '2026-06-11' },

  // ==================== 行政管理 ====================
  { job_title: '行政专员', company_name: '中国石油', city: '成都', education_req: '本科', experience_req: '1-3年', salary: '8-12K', job_desc: '负责日常行政事务、会议组织、档案管理。', job_url: 'https://example.com/job/81', publish_time: '2026-06-18' },
  { job_title: '办公室主任', company_name: '中国中车株洲所', city: '株洲', education_req: '本科', experience_req: '5-10年', salary: '15-22K', job_desc: '负责办公室全面管理、公文写作、对外协调。', job_url: 'https://example.com/job/82', publish_time: '2026-06-05' },
  { job_title: '综合管理岗', company_name: '中国邮政储蓄银行', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '负责行政后勤、物资采购、固定资产管理。', job_url: 'https://example.com/job/83', publish_time: '2026-06-10' },
  { job_title: '行政主管', company_name: '长安汽车集团', city: '重庆', education_req: '本科', experience_req: '3-5年', salary: '12-18K', job_desc: '负责行政制度制定、企业文化建设、大型活动组织。', job_url: 'https://example.com/job/84', publish_time: '2026-06-09' },
  { job_title: '前台行政', company_name: '宁波舟山港集团', city: '宁波', education_req: '大专', experience_req: '1年以下', salary: '6-9K', job_desc: '负责前台接待、来访登记、会议室管理。', job_url: 'https://example.com/job/85', publish_time: '2026-06-15' },

  // ==================== 市场营销 ====================
  { job_title: '市场专员', company_name: '中国石油', city: '成都', education_req: '本科', experience_req: '应届', salary: '8-12K', job_desc: '负责品牌活动与合作推广。', job_url: 'https://example.com/job/8', publish_time: '2026-06-19' },
  { job_title: '品牌经理', company_name: '湖南广电集团', city: '长沙', education_req: '本科', experience_req: '3-5年', salary: '18-25K', job_desc: '负责集团品牌战略规划与推广执行。', job_url: 'https://example.com/job/86', publish_time: '2026-06-14' },
  { job_title: '销售经理', company_name: '中国建筑', city: '深圳', education_req: '本科', experience_req: '3-5年', salary: '15-25K', job_desc: '负责工程项目市场拓展与客户关系维护。', job_url: 'https://example.com/job/87', publish_time: '2026-06-11' },
  { job_title: '商务专员', company_name: '中国电科海康集团', city: '杭州', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责商务谈判、合同管理、招投标文件编制。', job_url: 'https://example.com/job/88', publish_time: '2026-06-13' },
  { job_title: '客户经理', company_name: '中国联通湖南分公司', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责政企客户关系维护与业务拓展。', job_url: 'https://example.com/job/89', publish_time: '2026-06-16' },
  { job_title: '渠道拓展专员', company_name: '贵州茅台集团', city: '贵阳', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '负责经销商渠道开发与维护。', job_url: 'https://example.com/job/90', publish_time: '2026-06-08' },

  // ==================== 法务 ====================
  { job_title: '法务专员', company_name: '中国移动研究院', city: '北京', education_req: '硕士', experience_req: '1-3年', salary: '15-22K', job_desc: '负责合同审核、法律咨询、知识产权管理，通过司法考试。', job_url: 'https://example.com/job/91', publish_time: '2026-06-12' },
  { job_title: '合规主管', company_name: '招商局集团', city: '深圳', education_req: '硕士', experience_req: '3-5年', salary: '22-32K', job_desc: '负责合规体系建设、反洗钱、反腐败合规审查。', job_url: 'https://example.com/job/92', publish_time: '2026-06-07' },
  { job_title: '法务经理', company_name: '中国南方航空', city: '广州', education_req: '硕士', experience_req: '5-10年', salary: '25-38K', job_desc: '全面负责公司法务事务，持有律师执业证。', job_url: 'https://example.com/job/93', publish_time: '2026-06-10' },

  // ==================== 设计 ====================
  { job_title: 'UI设计师', company_name: '中国电信集团', city: '上海', education_req: '本科', experience_req: '1-3年', salary: '14-22K', job_desc: '负责运营平台界面设计，熟练使用Figma/Sketch。', job_url: 'https://example.com/job/94', publish_time: '2026-06-15' },
  { job_title: '视觉设计师', company_name: '湖南广电集团', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责新媒体视觉设计、海报制作、品牌VI维护。', job_url: 'https://example.com/job/95', publish_time: '2026-06-10' },

  // ==================== IT/技术类（保留原有） ====================
  { job_title: '软件开发工程师', company_name: '中国移动研究院', city: '北京', education_req: '本科', experience_req: '1-3年', salary: '15-25K', job_desc: '参与核心业务系统研发与优化，熟练掌握 Java / Go。', job_url: 'https://example.com/job/1', publish_time: '2026-06-15' },
  { job_title: '前端开发工程师', company_name: '中国电信集团', city: '上海', education_req: '本科', experience_req: '1-3年', salary: '14-22K', job_desc: '负责运营平台前端建设，熟悉 Vue/React。', job_url: 'https://example.com/job/2', publish_time: '2026-06-10' },
  { job_title: '产品经理', company_name: '国家电网', city: '北京', education_req: '硕士', experience_req: '3-5年', salary: '20-30K', job_desc: '负责能源数字化产品规划与推进。', job_url: 'https://example.com/job/3', publish_time: '2026-06-01' },
  { job_title: '数据分析师', company_name: '中国邮政储蓄银行', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '12-20K', job_desc: '业务数据分析与报表建设，会 SQL / Python。', job_url: 'https://example.com/job/4', publish_time: '2026-05-28' },
  { job_title: '运维工程师', company_name: '中国建筑', city: '深圳', education_req: '大专', experience_req: '3-5年', salary: '12-18K', job_desc: '负责企业内部系统运维与监控。', job_url: 'https://example.com/job/5', publish_time: '2026-05-20' },
  { job_title: 'Java 工程师', company_name: '中国工商银行', city: '长沙', education_req: '本科', experience_req: '3-5年', salary: '18-28K', job_desc: '核心金融系统研发，有 Spring Cloud 经验。', job_url: 'https://example.com/job/6', publish_time: '2026-06-12' },
  { job_title: '测试工程师', company_name: '中国航天科工', city: '北京', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '功能测试、自动化测试编写。', job_url: 'https://example.com/job/7', publish_time: '2026-06-18' },
  { job_title: '算法工程师', company_name: '南方电网', city: '广州', education_req: '硕士', experience_req: '3-5年', salary: '22-35K', job_desc: '负责电力调度算法与模型研发。', job_url: 'https://example.com/job/9', publish_time: '2026-06-05' },
  { job_title: '前端开发工程师', company_name: '湖南广电集团', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责新媒体平台前端开发，熟悉 React / Vue。', job_url: 'https://example.com/job/10', publish_time: '2026-06-20' },
  { job_title: '软件测试工程师', company_name: '中联重科', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '负责工程机械控制系统测试，编写自动化测试脚本。', job_url: 'https://example.com/job/11', publish_time: '2026-06-08' },
  { job_title: '大数据开发工程师', company_name: '中国联通湖南分公司', city: '长沙', education_req: '本科', experience_req: '3-5年', salary: '15-25K', job_desc: '大数据平台建设与维护，熟悉 Hadoop / Spark。', job_url: 'https://example.com/job/12', publish_time: '2026-06-18' },
  { job_title: '网络安全工程师', company_name: '中国电子科技集团', city: '武汉', education_req: '本科', experience_req: '1-3年', salary: '14-22K', job_desc: '网络安全防护与渗透测试。', job_url: 'https://example.com/job/13', publish_time: '2026-06-12' },
  { job_title: '电气工程师', company_name: '国家电网湖南公司', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '电力系统运维与技术支持。', job_url: 'https://example.com/job/14', publish_time: '2026-06-05' },
  { job_title: '大数据工程师', company_name: '中国银联', city: '上海', education_req: '本科', experience_req: '3-5年', salary: '20-32K', job_desc: '大数据平台建设与数据治理，熟悉 Hadoop/Spark。', job_url: 'https://example.com/job/16', publish_time: '2026-06-14' },
  { job_title: '云计算工程师', company_name: '招商局集团', city: '深圳', education_req: '本科', experience_req: '3-5年', salary: '18-30K', job_desc: '云平台架构设计与运维，熟悉 AWS / 阿里云。', job_url: 'https://example.com/job/17', publish_time: '2026-06-08' },
  { job_title: 'Java 开发工程师', company_name: '中国南方航空', city: '广州', education_req: '本科', experience_req: '1-3年', salary: '15-24K', job_desc: '航空业务系统后端研发。', job_url: 'https://example.com/job/18', publish_time: '2026-06-16' },
  { job_title: '前端开发工程师', company_name: '中国铁建湖南分公司', city: '衡阳', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '负责企业内部管理系统前端开发。', job_url: 'https://example.com/job/19', publish_time: '2026-06-01' },
  { job_title: '前端开发工程师', company_name: '东风汽车集团', city: '武汉', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责车联网平台前端开发。', job_url: 'https://example.com/job/20', publish_time: '2026-06-10' },
  { job_title: '机械工程师', company_name: '中国航天三江集团', city: '宜昌', education_req: '本科', experience_req: '3-5年', salary: '14-20K', job_desc: '负责航天产品机械结构设计。', job_url: 'https://example.com/job/21', publish_time: '2026-06-03' },
  { job_title: '软件开发工程师', company_name: '中国电科海康集团', city: '杭州', education_req: '本科', experience_req: '1-3年', salary: '14-22K', job_desc: '安防领域软件开发，熟悉 C++/Java。', job_url: 'https://example.com/job/22', publish_time: '2026-06-18' },
  { job_title: '测试工程师', company_name: '浙江省交通投资集团', city: '杭州', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '智能交通系统测试与质量保证。', job_url: 'https://example.com/job/23', publish_time: '2026-06-15' },
  { job_title: 'Java 开发工程师', company_name: '宁波舟山港集团', city: '宁波', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '港口物流信息化系统研发。', job_url: 'https://example.com/job/24', publish_time: '2026-06-10' },
  { job_title: '前端开发工程师', company_name: '中国电子科技集团十四所', city: '南京', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '负责雷达信息系统前端开发。', job_url: 'https://example.com/job/25', publish_time: '2026-06-12' },
  { job_title: '数据分析师', company_name: '苏宁云商', city: '南京', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '电商数据分析与用户画像。', job_url: 'https://example.com/job/26', publish_time: '2026-06-08' },
  { job_title: '嵌入式工程师', company_name: '中国中车戚墅堰所', city: '苏州', education_req: '本科', experience_req: '3-5年', salary: '15-25K', job_desc: '轨道交通嵌入式系统研发。', job_url: 'https://example.com/job/27', publish_time: '2026-06-01' },
  { job_title: '软件开发工程师', company_name: '中国电子科技集团三十所', city: '成都', education_req: '本科', experience_req: '1-3年', salary: '12-20K', job_desc: '信息安全产品研发。', job_url: 'https://example.com/job/28', publish_time: '2026-06-14' },
  { job_title: 'Java 工程师', company_name: '中国西电集团', city: '西安', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '电力设备信息化系统开发。', job_url: 'https://example.com/job/30', publish_time: '2026-06-15' },
  { job_title: '前端开发工程师', company_name: '陕西电子信息集团', city: '西安', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '军工电子信息系统前端开发。', job_url: 'https://example.com/job/31', publish_time: '2026-06-10' },
  { job_title: '运维工程师', company_name: '天津港集团', city: '天津', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '港口信息化系统运维。', job_url: 'https://example.com/job/32', publish_time: '2026-06-12' },
  { job_title: 'Java 开发工程师', company_name: '中国汽车技术研究中心', city: '天津', education_req: '本科', experience_req: '3-5年', salary: '15-24K', job_desc: '汽车检测信息化平台研发。', job_url: 'https://example.com/job/33', publish_time: '2026-06-08' },
  { job_title: '前端开发工程师', company_name: '长安汽车集团', city: '重庆', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '智能座舱前端界面开发。', job_url: 'https://example.com/job/34', publish_time: '2026-06-18' },
  { job_title: '测试工程师', company_name: '中国兵器装备集团', city: '重庆', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '武器装备软件测试。', job_url: 'https://example.com/job/35', publish_time: '2026-06-05' },
  { job_title: '软件开发工程师', company_name: '中国电子科技集团三十八所', city: '合肥', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '雷达信号处理软件开发。', job_url: 'https://example.com/job/36', publish_time: '2026-06-16' },
  { job_title: 'Java 工程师', company_name: '江淮汽车集团', city: '合肥', education_req: '本科', experience_req: '1-3年', salary: '11-17K', job_desc: '车联网平台后端开发。', job_url: 'https://example.com/job/37', publish_time: '2026-06-10' },
  { job_title: '前端开发工程师', company_name: '厦门建发集团', city: '厦门', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '供应链管理平台前端开发。', job_url: 'https://example.com/job/38', publish_time: '2026-06-14' },
  { job_title: '数据分析师', company_name: '福建省电子信息集团', city: '福州', education_req: '本科', experience_req: '1-3年', salary: '11-17K', job_desc: '电子信息产业数据分析。', job_url: 'https://example.com/job/39', publish_time: '2026-06-09' },
  { job_title: '软件开发工程师', company_name: '浪潮集团', city: '济南', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '云计算与大数据平台研发。', job_url: 'https://example.com/job/40', publish_time: '2026-06-17' },
  { job_title: '运维工程师', company_name: '山东港口集团', city: '青岛', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '智慧港口系统运维。', job_url: 'https://example.com/job/41', publish_time: '2026-06-08' },
  { job_title: '前端开发工程师', company_name: '河南能源化工集团', city: '郑州', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '企业信息化平台前端开发。', job_url: 'https://example.com/job/42', publish_time: '2026-06-13' },
  { job_title: '测试工程师', company_name: '中国一拖集团', city: '洛阳', education_req: '本科', experience_req: '1-3年', salary: '9-14K', job_desc: '农机控制系统测试。', job_url: 'https://example.com/job/43', publish_time: '2026-06-02' },
  { job_title: '软件开发工程师', company_name: '中国航空工业集团沈飞', city: '沈阳', education_req: '本科', experience_req: '1-3年', salary: '11-18K', job_desc: '航空制造信息化系统开发。', job_url: 'https://example.com/job/44', publish_time: '2026-06-15' },
  { job_title: 'Java 工程师', company_name: '大连港集团', city: '大连', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '港口物流系统后端开发。', job_url: 'https://example.com/job/45', publish_time: '2026-06-10' },
  { job_title: '前端开发工程师', company_name: '中国一汽集团', city: '长春', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '智能网联汽车前端开发。', job_url: 'https://example.com/job/46', publish_time: '2026-06-16' },
  { job_title: '软件开发工程师', company_name: '哈电集团', city: '哈尔滨', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '电力设备信息化系统研发。', job_url: 'https://example.com/job/47', publish_time: '2026-06-12' },
  { job_title: 'Java 工程师', company_name: '江西铜业集团', city: '南昌', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '矿业信息化系统开发。', job_url: 'https://example.com/job/48', publish_time: '2026-06-18' },
  { job_title: '前端开发工程师', company_name: '河钢集团', city: '石家庄', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '钢铁行业信息化平台前端开发。', job_url: 'https://example.com/job/49', publish_time: '2026-06-14' },
  { job_title: '测试工程师', company_name: '中车唐山公司', city: '唐山', education_req: '本科', experience_req: '1-3年', salary: '9-14K', job_desc: '轨道交通产品测试。', job_url: 'https://example.com/job/50', publish_time: '2026-06-05' },
  { job_title: '数据分析师', company_name: '晋能控股集团', city: '太原', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '能源行业数据分析与决策支持。', job_url: 'https://example.com/job/51', publish_time: '2026-06-11' },
  { job_title: 'Java 开发工程师', company_name: '云南白药集团', city: '昆明', education_req: '本科', experience_req: '1-3年', salary: '11-17K', job_desc: '医药信息化平台开发。', job_url: 'https://example.com/job/52', publish_time: '2026-06-16' },
  { job_title: '前端开发工程师', company_name: '贵州茅台集团', city: '贵阳', education_req: '本科', experience_req: '1-3年', salary: '11-17K', job_desc: '企业数字化平台前端开发。', job_url: 'https://example.com/job/53', publish_time: '2026-06-13' },
  { job_title: '运维工程师', company_name: '广西柳工集团', city: '南宁', education_req: '本科', experience_req: '1-3年', salary: '9-15K', job_desc: '工程机械信息化系统运维。', job_url: 'https://example.com/job/54', publish_time: '2026-06-10' },
  { job_title: '软件开发工程师', company_name: '内蒙古电力集团', city: '呼和浩特', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '电力信息化系统研发。', job_url: 'https://example.com/job/55', publish_time: '2026-06-09' },
  { job_title: '前端开发工程师', company_name: '金川集团', city: '兰州', education_req: '本科', experience_req: '1-3年', salary: '9-14K', job_desc: '有色金属行业信息化前端开发。', job_url: 'https://example.com/job/56', publish_time: '2026-06-07' },
  { job_title: 'Java 工程师', company_name: '海南农垦集团', city: '海口', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '热带农业信息化系统开发。', job_url: 'https://example.com/job/57', publish_time: '2026-06-15' },
  { job_title: '运维工程师', company_name: '西藏天路集团', city: '拉萨', education_req: '本科', experience_req: '1-3年', salary: '10-18K', job_desc: '交通信息化系统运维，有高原补贴。', job_url: 'https://example.com/job/58', publish_time: '2026-06-01' },
  { job_title: '数据分析师', company_name: '宁夏能源集团', city: '银川', education_req: '本科', experience_req: '1-3年', salary: '9-14K', job_desc: '能源数据分析与预测。', job_url: 'https://example.com/job/59', publish_time: '2026-06-08' },
  { job_title: '软件开发工程师', company_name: '青海盐湖工业集团', city: '西宁', education_req: '本科', experience_req: '1-3年', salary: '9-15K', job_desc: '盐湖资源信息化管理平台研发。', job_url: 'https://example.com/job/60', publish_time: '2026-06-05' },
  { job_title: '前端开发工程师', company_name: '新疆中泰集团', city: '乌鲁木齐', education_req: '本科', experience_req: '1-3年', salary: '10-17K', job_desc: '化工行业信息化前端开发。', job_url: 'https://example.com/job/61', publish_time: '2026-06-12' },
];

const samplePrivate = [
  // ==================== 财务会计 ====================
  { job_title: '财务会计', company_name: '万兴科技', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责公司日常账务处理、纳税申报、财务报表编制，熟悉金蝶财务软件。', job_url: 'https://example.com/job/p56', publish_time: '2026-06-15' },
  { job_title: '财务分析师', company_name: '美团', city: '北京', education_req: '本科', experience_req: '3-5年', salary: '20-35K', job_desc: '负责业务线财务分析、预算管理、经营决策支持，CPA优先。', job_url: 'https://example.com/job/p57', publish_time: '2026-06-12' },
  { job_title: '审计师', company_name: '字节跳动', city: '北京', education_req: '本科', experience_req: '3-5年', salary: '22-35K', job_desc: '内部审计与风险管理，四大会计师事务所经验优先。', job_url: 'https://example.com/job/p58', publish_time: '2026-06-10' },
  { job_title: '成本会计', company_name: '三一重工', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '负责制造成本核算、BOM成本管理、成本差异分析。', job_url: 'https://example.com/job/p59', publish_time: '2026-06-08' },
  { job_title: '出纳', company_name: '兴盛优选', city: '长沙', education_req: '大专', experience_req: '1-3年', salary: '6-10K', job_desc: '负责现金银行收付、日记账登记、费用报销审核。', job_url: 'https://example.com/job/p60', publish_time: '2026-06-14' },
  { job_title: '税务经理', company_name: '阿里巴巴', city: '杭州', education_req: '本科', experience_req: '5-10年', salary: '30-50K', job_desc: '负责集团税务筹划与合规管理，注册税务师优先。', job_url: 'https://example.com/job/p61', publish_time: '2026-06-09' },
  { job_title: '财务BP', company_name: '腾讯', city: '深圳', education_req: '本科', experience_req: '3-5年', salary: '22-35K', job_desc: '业务财务合作伙伴，负责预算管控与经营分析。', job_url: 'https://example.com/job/p62', publish_time: '2026-06-11' },
  { job_title: '财务会计', company_name: '顺丰科技', city: '深圳', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '负责日常账务核算、发票管理、月度结账。', job_url: 'https://example.com/job/p63', publish_time: '2026-06-13' },
  { job_title: '资金专员', company_name: '拼多多', city: '上海', education_req: '本科', experience_req: '1-3年', salary: '15-22K', job_desc: '负责资金调拨、现金流预测、银行授信管理。', job_url: 'https://example.com/job/p64', publish_time: '2026-06-10' },
  { job_title: '会计主管', company_name: '网易', city: '广州', education_req: '本科', experience_req: '3-5年', salary: '18-28K', job_desc: '负责总账管理、合并报表、财务制度优化，中级职称。', job_url: 'https://example.com/job/p65', publish_time: '2026-06-07' },

  // ==================== 人力资源 ====================
  { job_title: 'HRBP', company_name: '字节跳动', city: '北京', education_req: '本科', experience_req: '3-5年', salary: '25-40K', job_desc: '技术团队人力资源合作伙伴，负责人才招聘与组织发展。', job_url: 'https://example.com/job/p66', publish_time: '2026-06-16' },
  { job_title: '招聘专员', company_name: '美团', city: '北京', education_req: '本科', experience_req: '1-3年', salary: '15-22K', job_desc: '负责技术岗位社会招聘，熟悉主流招聘平台。', job_url: 'https://example.com/job/p67', publish_time: '2026-06-14' },
  { job_title: '培训主管', company_name: '芒果 TV', city: '长沙', education_req: '本科', experience_req: '3-5年', salary: '13-18K', job_desc: '负责企业培训体系搭建、新员工培训、领导力发展项目。', job_url: 'https://example.com/job/p68', publish_time: '2026-06-12' },
  { job_title: '薪酬福利专员', company_name: '小米', city: '北京', education_req: '本科', experience_req: '1-3年', salary: '14-20K', job_desc: '负责薪酬核算、社保公积金、个税申报、人力成本分析。', job_url: 'https://example.com/job/p69', publish_time: '2026-06-08' },
  { job_title: '人力资源经理', company_name: '安克创新', city: '长沙', education_req: '本科', experience_req: '5-10年', salary: '20-30K', job_desc: '全面负责公司人力资源战略规划与执行。', job_url: 'https://example.com/job/p70', publish_time: '2026-06-05' },
  { job_title: '人事专员', company_name: '斗鱼', city: '武汉', education_req: '本科', experience_req: '1-3年', salary: '10-15K', job_desc: '负责员工入离职、档案管理、考勤统计。', job_url: 'https://example.com/job/p71', publish_time: '2026-06-11' },
  { job_title: '组织发展专员', company_name: '腾讯', city: '深圳', education_req: '硕士', experience_req: '3-5年', salary: '22-35K', job_desc: '负责组织架构优化、人才盘点与继任计划。', job_url: 'https://example.com/job/p72', publish_time: '2026-06-09' },

  // ==================== 行政管理 ====================
  { job_title: '行政专员', company_name: '小红书', city: '上海', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责办公室行政事务、活动策划、供应商管理。', job_url: 'https://example.com/job/p73', publish_time: '2026-06-15' },
  { job_title: '综合管理岗', company_name: '万兴科技', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '10-15K', job_desc: '负责行政后勤、资产管理、办公环境维护。', job_url: 'https://example.com/job/p74', publish_time: '2026-06-12' },
  { job_title: '行政主管', company_name: '科大讯飞', city: '合肥', education_req: '本科', experience_req: '3-5年', salary: '14-20K', job_desc: '负责行政制度制定、企业文化建设、大型活动组织。', job_url: 'https://example.com/job/p75', publish_time: '2026-06-10' },
  { job_title: '前台文员', company_name: '百词斩', city: '成都', education_req: '大专', experience_req: '应届', salary: '5-8K', job_desc: '负责前台接待、来访登记、快递收发。', job_url: 'https://example.com/job/p76', publish_time: '2026-06-14' },

  // ==================== 市场营销 ====================
  { job_title: '品牌经理', company_name: '小红书', city: '上海', education_req: '本科', experience_req: '3-5年', salary: '25-40K', job_desc: '负责品牌策略制定与整合营销传播。', job_url: 'https://example.com/job/p77', publish_time: '2026-06-16' },
  { job_title: '运营专员', company_name: '兴盛优选', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '社区团购平台运营，数据分析与活动策划。', job_url: 'https://example.com/job/p11', publish_time: '2026-06-20' },
  { job_title: '客户经理', company_name: '顺丰科技', city: '深圳', education_req: '本科', experience_req: '3-5年', salary: '18-28K', job_desc: '负责大客户关系维护与业务拓展，有物流行业经验优先。', job_url: 'https://example.com/job/p78', publish_time: '2026-06-13' },
  { job_title: '渠道经理', company_name: '蜜雪冰城', city: '郑州', education_req: '本科', experience_req: '3-5年', salary: '15-25K', job_desc: '负责加盟商渠道拓展与运营管理。', job_url: 'https://example.com/job/p79', publish_time: '2026-06-11' },
  { job_title: '商务专员', company_name: '极米科技', city: '成都', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责商务谈判、合同管理、回款跟进。', job_url: 'https://example.com/job/p80', publish_time: '2026-06-09' },
  { job_title: '市场推广经理', company_name: '哔哩哔哩', city: '上海', education_req: '本科', experience_req: '3-5年', salary: '20-30K', job_desc: '负责用户增长与市场推广策略执行。', job_url: 'https://example.com/job/p81', publish_time: '2026-06-14' },
  { job_title: '销售代表', company_name: '海尔智家', city: '青岛', education_req: '大专', experience_req: '1-3年', salary: '10-18K', job_desc: '负责区域市场产品销售与客户开发。', job_url: 'https://example.com/job/p82', publish_time: '2026-06-12' },

  // ==================== 法务 ====================
  { job_title: '法务专员', company_name: '字节跳动', city: '北京', education_req: '硕士', experience_req: '1-3年', salary: '18-28K', job_desc: '负责合同审核与知识产权保护，通过司法考试。', job_url: 'https://example.com/job/p83', publish_time: '2026-06-15' },
  { job_title: '合规专员', company_name: '拼多多', city: '上海', education_req: '本科', experience_req: '1-3年', salary: '15-22K', job_desc: '负责电商合规审查、数据合规管理。', job_url: 'https://example.com/job/p84', publish_time: '2026-06-10' },

  // ==================== 设计 ====================
  { job_title: 'UI/UX 设计师', company_name: '网易', city: '杭州', education_req: '本科', experience_req: '1-3年', salary: '15-25K', job_desc: '产品交互与视觉设计，熟练使用Figma。', job_url: 'https://example.com/job/p10', publish_time: '2026-06-14' },
  { job_title: '平面设计师', company_name: '美图公司', city: '厦门', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '负责品牌视觉设计与营销物料制作。', job_url: 'https://example.com/job/p85', publish_time: '2026-06-11' },

  // ==================== IT/技术类（保留原有） ====================
  { job_title: '前端开发工程师', company_name: '字节跳动', city: '北京', education_req: '本科', experience_req: '3-5年', salary: '25-45K', job_desc: '核心业务前端架构设计与研发。', job_url: 'https://example.com/job/p1', publish_time: '2026-06-18' },
  { job_title: '后端开发工程师', company_name: '阿里巴巴', city: '杭州', education_req: '本科', experience_req: '3-5年', salary: '25-45K', job_desc: '分布式系统设计与研发。', job_url: 'https://example.com/job/p2', publish_time: '2026-06-17' },
  { job_title: '产品经理', company_name: '腾讯', city: '深圳', education_req: '本科', experience_req: '1-3年', salary: '20-35K', job_desc: '社交产品规划与迭代。', job_url: 'https://example.com/job/p3', publish_time: '2026-06-16' },
  { job_title: 'iOS 开发', company_name: '小米', city: '北京', education_req: '本科', experience_req: '1-3年', salary: '18-30K', job_desc: 'iOS App 研发与性能优化。', job_url: 'https://example.com/job/p4', publish_time: '2026-06-12' },
  { job_title: '数据工程师', company_name: '美团', city: '北京', education_req: '本科', experience_req: '3-5年', salary: '22-38K', job_desc: '数据平台建设、数仓治理。', job_url: 'https://example.com/job/p5', publish_time: '2026-06-10' },
  { job_title: 'Java 工程师', company_name: '万兴科技', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '15-25K', job_desc: '负责数字创意软件产品后端研发，熟悉微服务架构。', job_url: 'https://example.com/job/p6', publish_time: '2026-06-08' },
  { job_title: 'Java 工程师', company_name: '拼多多', city: '上海', education_req: '本科', experience_req: '1-3年', salary: '20-35K', job_desc: '核心交易系统研发。', job_url: 'https://example.com/job/p7', publish_time: '2026-06-02' },
  { job_title: '前端实习生', company_name: '芒果 TV', city: '长沙', education_req: '本科', experience_req: '应届', salary: '8-12K', job_desc: '视频平台前端开发实习，熟悉 Vue/React。', job_url: 'https://example.com/job/p8', publish_time: '2026-05-30' },
  { job_title: '测试开发', company_name: '微软', city: '北京', education_req: '本科', experience_req: '3-5年', salary: '25-40K', job_desc: '测试平台与自动化建设。', job_url: 'https://example.com/job/p9', publish_time: '2026-06-01' },
  { job_title: 'Python 开发工程师', company_name: '安克创新', city: '长沙', education_req: '本科', experience_req: '1-3年', salary: '14-22K', job_desc: '电商数据分析平台后端开发，熟悉 Django / FastAPI。', job_url: 'https://example.com/job/p12', publish_time: '2026-06-15' },
  { job_title: '嵌入式软件工程师', company_name: '三一重工', city: '长沙', education_req: '本科', experience_req: '3-5年', salary: '18-28K', job_desc: '工程机械嵌入式系统研发，熟悉 C/C++。', job_url: 'https://example.com/job/p13', publish_time: '2026-06-10' },
  { job_title: '前端开发工程师', company_name: '小红书', city: '上海', education_req: '本科', experience_req: '1-3年', salary: '22-35K', job_desc: '社区产品前端研发，熟悉 React。', job_url: 'https://example.com/job/p14', publish_time: '2026-06-16' },
  { job_title: '产品经理', company_name: '哔哩哔哩', city: '上海', education_req: '本科', experience_req: '3-5年', salary: '25-40K', job_desc: '视频平台产品规划与迭代。', job_url: 'https://example.com/job/p15', publish_time: '2026-06-14' },
  { job_title: '后端开发工程师', company_name: '大疆创新', city: '深圳', education_req: '本科', experience_req: '3-5年', salary: '25-40K', job_desc: '无人机云平台后端研发。', job_url: 'https://example.com/job/p16', publish_time: '2026-06-12' },
  { job_title: '前端开发工程师', company_name: '顺丰科技', city: '深圳', education_req: '本科', experience_req: '1-3年', salary: '18-28K', job_desc: '物流科技平台前端开发。', job_url: 'https://example.com/job/p17', publish_time: '2026-06-08' },
  { job_title: 'Java 工程师', company_name: '唯品会', city: '广州', education_req: '本科', experience_req: '3-5年', salary: '20-32K', job_desc: '电商平台核心系统研发。', job_url: 'https://example.com/job/p18', publish_time: '2026-06-10' },
  { job_title: '前端开发工程师', company_name: '网易', city: '广州', education_req: '本科', experience_req: '1-3年', salary: '18-28K', job_desc: '游戏社区前端开发。', job_url: 'https://example.com/job/p19', publish_time: '2026-06-15' },
  { job_title: '前端开发工程师', company_name: '菜鸟网络', city: '杭州', education_req: '本科', experience_req: '1-3年', salary: '18-28K', job_desc: '物流科技前端开发。', job_url: 'https://example.com/job/p20', publish_time: '2026-06-13' },
  { job_title: '前端开发工程师', company_name: '百词斩', city: '成都', education_req: '本科', experience_req: '1-3年', salary: '14-22K', job_desc: '教育科技产品前端开发。', job_url: 'https://example.com/job/p21', publish_time: '2026-06-12' },
  { job_title: 'Java 工程师', company_name: '极米科技', city: '成都', education_req: '本科', experience_req: '3-5年', salary: '18-28K', job_desc: '智能投影设备后端服务研发。', job_url: 'https://example.com/job/p22', publish_time: '2026-06-09' },
  { job_title: '前端开发工程师', company_name: '斗鱼', city: '武汉', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '直播平台前端开发。', job_url: 'https://example.com/job/p23', publish_time: '2026-06-11' },
  { job_title: 'Java 开发工程师', company_name: '金山办公', city: '武汉', education_req: '本科', experience_req: '1-3年', salary: '14-22K', job_desc: '办公软件后端服务研发。', job_url: 'https://example.com/job/p24', publish_time: '2026-06-08' },
  { job_title: '前端开发工程师', company_name: '孩子王', city: '南京', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '母婴零售数字化前端开发。', job_url: 'https://example.com/job/p25', publish_time: '2026-06-15' },
  { job_title: 'Python 工程师', company_name: '途牛旅游', city: '南京', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '在线旅游平台后端开发。', job_url: 'https://example.com/job/p26', publish_time: '2026-06-10' },
  { job_title: 'Java 工程师', company_name: '中科创达', city: '西安', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '智能操作系统研发。', job_url: 'https://example.com/job/p27', publish_time: '2026-06-14' },
  { job_title: '前端开发工程师', company_name: '核桃编程', city: '西安', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '在线教育平台前端开发。', job_url: 'https://example.com/job/p28', publish_time: '2026-06-09' },
  { job_title: '前端开发工程师', company_name: '融创文旅', city: '天津', education_req: '本科', experience_req: '1-3年', salary: '11-17K', job_desc: '文旅数字化前端开发。', job_url: 'https://example.com/job/p29', publish_time: '2026-06-13' },
  { job_title: 'Java 工程师', company_name: '猪八戒网', city: '重庆', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '企业服务平台后端研发。', job_url: 'https://example.com/job/p30', publish_time: '2026-06-11' },
  { job_title: '前端开发工程师', company_name: '江小白', city: '重庆', education_req: '本科', experience_req: '1-3年', salary: '11-17K', job_desc: '新零售前端开发。', job_url: 'https://example.com/job/p31', publish_time: '2026-06-07' },
  { job_title: '前端开发工程师', company_name: '科大讯飞', city: '合肥', education_req: '本科', experience_req: '1-3年', salary: '14-22K', job_desc: 'AI 平台前端开发，熟悉 React。', job_url: 'https://example.com/job/p32', publish_time: '2026-06-17' },
  { job_title: 'Java 开发工程师', company_name: '美图公司', city: '厦门', education_req: '本科', experience_req: '1-3年', salary: '13-20K', job_desc: '影像处理平台后端研发。', job_url: 'https://example.com/job/p33', publish_time: '2026-06-12' },
  { job_title: '前端开发工程师', company_name: '4399游戏', city: '厦门', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '游戏运营平台前端开发。', job_url: 'https://example.com/job/p34', publish_time: '2026-06-08' },
  { job_title: '前端开发工程师', company_name: '浪潮信息', city: '济南', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '服务器管理平台前端开发。', job_url: 'https://example.com/job/p35', publish_time: '2026-06-10' },
  { job_title: 'Java 工程师', company_name: '海尔智家', city: '青岛', education_req: '本科', experience_req: '3-5年', salary: '15-25K', job_desc: '智能家居 IoT 平台后端研发。', job_url: 'https://example.com/job/p36', publish_time: '2026-06-14' },
  { job_title: '前端开发工程师', company_name: '蜜雪冰城', city: '郑州', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '新茶饮数字化平台前端开发。', job_url: 'https://example.com/job/p37', publish_time: '2026-06-12' },
  { job_title: 'Java 开发工程师', company_name: '网龙网络', city: '福州', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: '在线教育平台后端研发。', job_url: 'https://example.com/job/p38', publish_time: '2026-06-09' },
  { job_title: '前端开发工程师', company_name: '东软集团', city: '沈阳', education_req: '本科', experience_req: '1-3年', salary: '11-17K', job_desc: '医疗信息化前端开发。', job_url: 'https://example.com/job/p39', publish_time: '2026-06-14' },
  { job_title: 'Java 工程师', company_name: '亿达信息', city: '大连', education_req: '本科', experience_req: '1-3年', salary: '12-18K', job_desc: 'IT 服务外包平台研发。', job_url: 'https://example.com/job/p40', publish_time: '2026-06-10' },
  { job_title: '前端开发工程师', company_name: '修正药业', city: '长春', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '医药电商前端开发。', job_url: 'https://example.com/job/p41', publish_time: '2026-06-08' },
  { job_title: 'Java 开发工程师', company_name: '飞鹤乳业', city: '哈尔滨', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '乳业数字化系统后端研发。', job_url: 'https://example.com/job/p42', publish_time: '2026-06-11' },
  { job_title: '前端开发工程师', company_name: '仁和药业', city: '南昌', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '医药电商前端开发。', job_url: 'https://example.com/job/p43', publish_time: '2026-06-07' },
  { job_title: 'Java 工程师', company_name: '以岭药业', city: '石家庄', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '医药信息化系统研发。', job_url: 'https://example.com/job/p44', publish_time: '2026-06-09' },
  { job_title: '前端开发工程师', company_name: '美特好', city: '太原', education_req: '本科', experience_req: '1-3年', salary: '9-14K', job_desc: '零售数字化前端开发。', job_url: 'https://example.com/job/p45', publish_time: '2026-06-05' },
  { job_title: 'Java 开发工程师', company_name: '云南白药', city: '昆明', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '大健康平台后端研发。', job_url: 'https://example.com/job/p46', publish_time: '2026-06-13' },
  { job_title: '前端开发工程师', company_name: '满帮集团', city: '贵阳', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '货运平台前端开发。', job_url: 'https://example.com/job/p47', publish_time: '2026-06-10' },
  { job_title: 'Java 工程师', company_name: '柳工机械', city: '南宁', education_req: '本科', experience_req: '1-3年', salary: '9-15K', job_desc: '工程机械信息化研发。', job_url: 'https://example.com/job/p48', publish_time: '2026-06-06' },
  { job_title: '前端开发工程师', company_name: '伊利集团', city: '呼和浩特', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '乳业数字化前端开发。', job_url: 'https://example.com/job/p49', publish_time: '2026-06-14' },
  { job_title: 'Java 开发工程师', company_name: '奇正藏药', city: '兰州', education_req: '本科', experience_req: '1-3年', salary: '9-14K', job_desc: '医药信息化系统研发。', job_url: 'https://example.com/job/p50', publish_time: '2026-06-08' },
  { job_title: '前端开发工程师', company_name: '海航科技', city: '海口', education_req: '本科', experience_req: '1-3年', salary: '10-16K', job_desc: '航空科技前端开发。', job_url: 'https://example.com/job/p51', publish_time: '2026-06-12' },
  { job_title: 'Java 工程师', company_name: '西藏奇正藏药', city: '拉萨', education_req: '本科', experience_req: '1-3年', salary: '11-18K', job_desc: '藏药信息化系统开发，有高原补贴。', job_url: 'https://example.com/job/p52', publish_time: '2026-06-02' },
  { job_title: '前端开发工程师', company_name: '共享集团', city: '银川', education_req: '本科', experience_req: '1-3年', salary: '9-14K', job_desc: '铸造行业数字化前端开发。', job_url: 'https://example.com/job/p53', publish_time: '2026-06-05' },
  { job_title: 'Java 开发工程师', company_name: '青海互助青稞酒', city: '西宁', education_req: '本科', experience_req: '1-3年', salary: '9-14K', job_desc: '酒业信息化系统研发。', job_url: 'https://example.com/job/p54', publish_time: '2026-06-10' },
  { job_title: '前端开发工程师', company_name: '特变电工', city: '乌鲁木齐', education_req: '本科', experience_req: '1-3年', salary: '10-17K', job_desc: '电力设备数字化前端开发。', job_url: 'https://example.com/job/p55', publish_time: '2026-06-14' },
];

async function seed() {
  const base = process.env.API_BASE || 'http://localhost:' + (process.env.PORT || 3000);

  console.log('正在导入国企岗位...');
  const res1 = await fetch(base + '/api/state-jobs/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: sampleStateOwned })
  });
  const d1 = await res1.json();
  console.log('国企岗位:', JSON.stringify(d1));

  console.log('正在导入私企/外企岗位...');
  const res2 = await fetch(base + '/api/private-jobs/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: samplePrivate })
  });
  const d2 = await res2.json();
  console.log('私企/外企岗位:', JSON.stringify(d2));

  console.log('\n✅ 导入完成！现在可以刷新页面重新提交求职信息了。');
}

seed().catch(function(e) { console.error('导入失败:', e.message); process.exit(1); });
