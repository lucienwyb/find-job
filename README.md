# find-job — 北京海淀前沿公司求职调研

目标：为 **王毅博**（Linux 内核/系统/嵌入式 7 年，应用物理本科，现居北京北医三院附近）筛选前沿方向公司，双轨策略：
- **进取型**：Agent 应用架构 / 大模型 / 机器人 / 智驾 / AI4Science（兴趣+创意优先）
- **躺平型**：钱多 + 事少（强 WLB）+ 离家近（≤10km 优先）

硬约束：距北医三院 ≤10km 优先中关村；排除 996/大小周/7×24 on-call（躺平型）；学历非 211 是核心变量。

## 目录结构

```
.
├── README.md                   本文件
├── SESSION-HANDOFF.md          ★会话迁移说明（新会话先读这个 + memory.md）
├── companies.md                ★全部公司调研总表 + 行动总表 + 投递执行清单（1771行）
├── memory.md                   ★51轮调研逐轮记录（避免重复抓取）
├── applications.md             投递进展跟踪表
├── outreach-messages.md        内推私信 / Boss 招呼语
├── interview-cheatsheet.md     面试讲点速查
├── interview_qa_rehearsal.md   面试技术问答预演
├── offer-decision-matrix.md    offer 决策矩阵
├── d0-launch-checklist.md      启动投递检查清单
├── resumes/                    简历（原始 + 5 份针对性变体）
│   ├── resume.md
│   ├── resume-航天版.md
│   ├── resume-机器人版.md
│   ├── resume-大模型Infra版.md
│   ├── resume-01ai平台版.md
│   └── resume-智驾系统版.md
├── reports/                    各公司/方向深度评估报告
│   ├── career-direction-debate.md   职业方向探讨（v2=Agent应用架构师技术侧）
│   ├── kagent-runtime-spec.md        自研 agent runtime 项目规格书
│   ├── galaxy-space-assessment.md
│   ├── galbot-robotera-match-report.md
│   ├── zhipu-moonshot-deep-report.md
│   ├── 01ai-assessment-and-action-plan.md
│   ├── job-match-assessment.md
│   └── ai4science-play.md
├── 投递/                       ★投递材料（复制即发的邮件正文/话术）
│   └── 投递-ISCAS-OS工程师.md
└── scrape/                     招聘门户抓取（可复用）
    ├── scripts/                73 个 playwright/curl 抓取脚本
    └── data/                   278 个原始抓取产物（html/json/txt，JD 原文）
```

## 快速接续

新会话读 `SESSION-HANDOFF.md` 即可快速继承上下文，含候选人画像、51轮浓缩结论、最优投递清单、抓取方法学、网络环境、接续指引。

## 参考坐标
- 北医三院：北京市海淀区花园北路49号（约 39.9833°N, 116.3622°E）
- 10km 半径覆盖：海淀大部分（学院路/知春路/苏州街/上地/西二旗边缘/五道口/牡丹园）

## 远端
git@github.com:lucienwyb/find-job.git
