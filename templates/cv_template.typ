#import "@preview/brilliant-cv:2.0.0": *

#let metadata = (
  language: "zh",
  layout: (
    awesome_color: "skyblue",
    before_section_skip: "1pt",
    before_entry_skip: "1pt",
    before_entry_description_skip: "1pt",
    header: (header_align: "left", display_profile_photo: false, profile_photo_path: ""),
    entry: (display_entry_society_first: false, display_logo: false),
  ),
  personal: (
    first_name: "三",
    last_name: "张",
    info: (
      phone: "+86 138-0000-0000",
      email: "zhangsan@example.com",
      linkedin: "linkedin.com/in/zhangsan",
      github: "github.com/zhangsan",
      location: "北京",
    ),
  ),
  inject: (
    inject_ai_prompt: false,
    inject_keywords: false,
    injected_keywords_list: (),
  ),
  lang: (
    zh: (
      header_quote: "资深软件工程师，专注于推荐系统与分布式架构",
      cv_footer: "简历",
    ),
    non_latin: (name: "张三", font: "Heiti SC"),
  ),
)

#show: cv.with(metadata)

#let cvSection = cvSection.with(metadata: metadata)
#let cvEntry = cvEntry.with(metadata: metadata)

// ===== 教育背景 =====
#cvSection("教育背景")

#cvEntry(
  title: [硕士, 计算机科学与技术],
  society: [清华大学],
  date: [2020.09 - 2023.06],
  location: [北京],
  description: list(
    [研究方向：自然语言处理与知识图谱],
    [获国家奖学金（Top 1%）],
  ),
)

#cvEntry(
  title: [学士, 软件工程],
  society: [北京大学],
  date: [2016.09 - 2020.06],
  location: [北京],
  description: list(
    [校级优秀毕业生],
    [ACM-ICPC 亚洲区域赛金牌],
  ),
)

// ===== 工作经历 =====
#cvSection("工作经历")

#cvEntry(
  title: [后端开发工程师],
  society: [字节跳动],
  date: [2023.07 - 至今],
  location: [北京],
  description: list(
    [负责智能推荐引擎的后端微服务开发与维护，日处理请求量 10 亿+],
    [主导设计了基于 Redis + Kafka 的实时特征计算管道，将特征更新延迟降低至 30 秒以内],
    [使用 Go 语言重构核心排序服务，QPS 提升 40%，P99 延迟降低 35%],
    [搭建自动化压测与性能监控体系，保障 618 大促期间服务可用性 99.99%],
  ),
)

#cvEntry(
  title: [算法实习生],
  society: [腾讯],
  date: [2022.06 - 2022.09],
  location: [深圳],
  description: list(
    [参与微信搜一搜语义理解模块优化，基于 BERT 微调查询意图分类模型],
    [构建大规模用户行为数据的离线特征挖掘管线（Spark + Hive）],
    [将长尾查询的搜索准确率提升 12%（通过数据增强与负采样策略）],
  ),
)

// ===== 项目经历 =====
#cvSection("项目经历")

#cvEntry(
  title: [Smart-HR: 智能简历匹配系统],
  society: [项目负责人 & 核心开发者],
  date: [2022.09 - 2023.05],
  location: [Python, PyTorch, FastAPI, Elasticsearch, Docker],
  description: list(
    [基于 Sentence-BERT 实现简历与 JD 语义匹配模块，Top-5 召回率达 92%],
    [设计混合检索架构：Elasticsearch 关键词检索 + Faiss 向量检索，支持百万级简历库秒级查询],
    [使用 FastAPI 搭建 RESTful API 服务，集成 Swagger 文档与 JWT 鉴权],
  ),
)

#cvEntry(
  title: [NewsFlow: 实时新闻聚合与推荐],
  society: [后端开发者],
  date: [2021.10 - 2022.03],
  location: [Go, Kafka, PostgreSQL, Redis, Kubernetes],
  description: list(
    [设计并实现基于事件溯源（Event Sourcing）的新闻流处理架构],
    [使用 Kafka 实现新闻爬取、清洗、向量化的流式处理管道],
    [搭建基于 Prometheus + Grafana 的全链路监控看板，实现分钟级异常告警],
  ),
)

// ===== 技能 =====
#cvSection("技能")

#cvSkill(
  type: [编程语言],
  info: [Go #hBar() Python #hBar() Rust #hBar() Java #hBar() TypeScript],
)

#cvSkill(
  type: [框架与工具],
  info: [PyTorch #hBar() FastAPI #hBar() gRPC #hBar() Kafka #hBar() Redis #hBar() Docker #hBar() Kubernetes],
)

#cvSkill(
  type: [领域],
  info: [推荐系统 #hBar() 自然语言处理 #hBar() 分布式系统 #hBar() 搜索引擎],
)

#cvSkill(
  type: [语言],
  info: [中文（母语） #hBar() 英语（CET-6）],
)
