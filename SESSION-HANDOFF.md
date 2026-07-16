# 会话迁移说明（SESSION-HANDOFF）

> 本文件用于跨会话/跨 Agent 继承求职调研上下文。新会话的 AI（或候选人本人）读这一份 + `memory.md` 即可快速接续，不必重读全部 1771 行 companies.md。

最后更新：2026-07-16｜仓库：github.com/lucienwyb/find-job｜共 80 commit、51 轮调研

---

## 一、候选人画像（投递时务必对齐）

- **王毅博**，Linux 内核/系统/嵌入式 **7 年**，C 精通，eBPF/perf/crash/ftrace，ARM/x86/Zynq。
- 应用物理本科（**西安理工大学，非 211**）——这是最大约束，部分岗卡 211/985，需内推或选不卡学历的岗。
- 现职百度云 IaaS 镜像/软件源研发（2025.7 起）。
- 住北京**北医三院**（39.9833, 116.3622）附近，中关村 10km 内优先。
- 诉求双轨：**进取型**（兴趣+创意，Agent 应用架构/大模型/机器人/智驾/AI4Science）+ **躺平型**（钱多事少离家近，强 WLB）。
- 两大核心战绩（投递必挂）：① 向 Linux 内核 BPF 子系统提交并合入 **约 1000 个补丁** ② 上交所 **UDP 15 万并发平均延时 <100μs**（软中断绑核+中断聚合+网络栈调优）。另有闻翔 Zynq 全栈 bring-up（uboot/kernel/rootfs/设备树/驱动 + AD9361 + ~7000 行 FPGA 控制）。

---

## 二、调研结论（51 轮浓缩）

### 9 大赛道全覆盖（地址全部核实可信，无遗留冲突）
Agent 应用架构 / 大模型 Infra / AI4Science / 智驾 / 具身数据仿真 / AIOps 可观测 / 芯片底层 / 银行金融科技 / 央企外企事业编。

### 关键纠错记录（避免重复踩坑）
- **红帽 Red Hat 北京不可投**：IBM 2024-25 裁员后中国区内核 HC 清零，仅留销售。Workday API 搜 Beijing=0。
- **IBM 已关闭**：盘古大观办公点 2025-3 停止业务，总部迁上海。
- **烽火通信在武汉**：烽火科技大厦在武汉洪山区，不在北京，"1.1-2km 极近"系子 agent LLM 幻觉误报。
- **银联北京分公司**：西城区闹市口大街 1 号院 2 号楼 4 层（~7.8km）。**方圆大厦 4.2km 是误判**（方圆大厦属云动九天，非银联）。
- **第四范式**：已迁至上地西路 28 号弘源·新时代 A 座（~7.3km）。旧地址"中关村东路 1 号院 2.51km"和"清河 5.72km"均作废。
- **瑞莱智慧 RealAI 不对口**：它的"安全"是 AI 模型对抗安全（对抗样本/深度伪造），不是系统/内核安全，官网零 eBPF/kernel 词汇。
- **潞晨 ColossalAI**：注册大兴亦庄 ~25km 超距，"3.6km 估"是错的。

---

## 三、★最优投递清单（按命中率×不卡学历×通勤近排序，从上往下投）

### 躺平型（保底，钱多事少离家近）
| # | 目标 | 投递方式 | 关键点 |
|---|---|---|---|
| ★1 | **ISCAS 软件所 OS 工程师** | 邮件 `jiran@iscas.ac.cn`（主题：应聘操作系统工程师+王毅博） | JD 要求"Linux 内核上游有影响力 + openEuler 等发行版长期贡献"，bpf~1000 补丁+统信 openEuler 贡献**完全对口**，本科可投不卡 211 不卡年龄，3.0km，命中率最高，本周内发 |
| ★2 | **NVIDIA JR2015006** | nvidia.wd5.myworkdayjobs.com 搜 JR2015006→Apply | 英文简历，不卡学历"or equivalent experience"，3.56km，50-80 万+RSU，965 |
| ★3 | **安谋科技 SOC Driver** | mokahr/apply/armchina/885→内推入口 Tab | JD 量身定制（ARM 内核驱动+设备树+KVM VFIO+FPGA bring-up），走内推绕 HR，3.85km，40-80 万 |
| 4 | 工行数据中心 | job.icbc.com.cn | 西三旗 5.8km，总行直属正编，不卡学历，保底 |
| 5 | 中行数据中心 | （官网招聘栏） | 海淀黑山扈永丰路 299 号 9.8km，正式行员，不卡明文 |
| 6 | 微软 MSRA Researcher | careers.microsoft.com + 脉脉内推 | 120-180 万，965，不卡学历，需做 AI Systems 叙事转换找内推 |

### 进取型（兴趣+对口+高薪）
| # | 目标 | 投递方式 | 关键点 |
|---|---|---|---|
| ★1 | **星动纪元 Linux BSP** | 飞书直投 k0fqxcszc9.jobs.feishu.cn（岗位 7571785644297521459） | JD 95+ 量身定制（Linux 裁剪/SoC BSP U-Boot 设备树/外设驱动/调度中断优化/OTA），闻翔 Zynq 全栈直接命中 |
| ★2 | **清程极智 智能计算研发** | 飞书直投 chitu-ai.jobs.feishu.cn（岗位 7621017904042314003） | 本科+不卡学历，中关村东路 1 号院 9 号楼 305（3.2km），RDMA/NVlink/HPC/Slurm 对口，翟季冬清华系 |
| ★3 | **月之暗面**（6 个月仅 3 岗，必须先脉脉内推） | 先脉脉内推→mokahr/apply/moonshot/148506 | 投递顺序锁死：①高性能分布式存储（7-16 发，eBPF 命中 90+）②Coding Agent（06-30，88）③Infra 系统应用（12-02，82）。裸投被学历初筛刷掉浪费名额 |
| ★4 | **银河通用 GALBOT** | mokahr/social-recruitment/yinhetongyong/165929 | 5 岗可全投：OS 研发（95）/嵌入式人形（20-40K 真实）/系统软件（88）/BSP（85深圳）/架构师（85），bpf~1000 补丁挂链接 |
| 5 | 云杉 DeepFlow | `hr@yunshan.net` + 先在 github.com/deepflowio/deepflow 提 PR | 2.4km，eBPF 对口，内核→Agent 最短路径 |
| 6 | 深势科技 HPC | 飞书 Hire dptechnology.jobs.feishu.cn + `hr@dp.tech` | 4.6km，JD perf/VTune/SIMD/锁竞争与内核 1:1 命中，硕士达标 |
| 7 | 寒武纪 | mokahr/apply/cambricon/1113 | 高性能通信库/AI 编译器等 8 高匹配，标"急" |
| 8 | 智谱 Agent Infra | mokahr/social-recruitment/zphz/148983 | Agent Infra 开发（88）/推理 Infra（85） |

> 每个目标的**完整 JD 原文 + 投递流程 + 简历侧重要点**见 `companies.md` 对应章节，投的时候照抄即可。

---

## 四、文件索引

> 仓库已结构化归档，见 `README.md` 目录树。

### 核心文档（根目录，投递时用）
- `companies.md`（1771 行）— 全部公司调研总表 + 行动总表 + 投递执行清单
- `memory.md`（589 行）— 51 轮调研逐轮记录，避免重复抓取
- `applications.md` — 投递进展跟踪表
- `outreach-messages.md` — 内推私信/Boss 招呼语
- `interview_qa_rehearsal.md` — 面试技术问答预演
- `interview-cheatsheet.md` — 面试讲点速查
- `offer-decision-matrix.md` — offer 决策矩阵
- `d0-launch-checklist.md` — 启动投递检查清单

### `resumes/` — 简历
- `resume.md`（原始）+ `resume-{航天,机器人,大模型Infra,01ai平台,智驾系统}版.md`（5 份变体）

### `reports/` — 评估报告
- `career-direction-debate.md`（v2 方向=Agent 应用架构师技术侧）
- `kagent-runtime-spec.md`（自研 agent runtime 项目规格书）
- `galaxy-space-assessment.md` / `galbot-robotera-match-report.md` / `zhipu-moonshot-deep-report.md` / `01ai-assessment-and-action-plan.md` / `job-match-assessment.md` / `ai4science-play.md`

### `投递/` — 投递材料（复制即发）
- `投递-ISCAS-OS工程师.md`（邮件主题+正文+简历要点）
- 后续其他目标的投递材料也放这里

### `scrape/` — 招聘门户抓取（可复用）
- `scrape/scripts/`（73 个）— playwright/curl 抓取脚本（`scrape_*.py` / `pw_*.py` / `r44_*.py`）
- `scrape/data/`（278 个）— 原始抓取产物（`r36b_*.txt/json` / `live*_.html` / `r44_*` / `yh_*.html` 等，含 JD 原文）

### 抓取方法学（复用时参考 companies.md "门户方法学"节）
- mokahr 两路径：`social-recruitment/{slug}`（银河通用）和 `apply/{slug}`（月之暗面）。necromancer 加密但前端 JS 解密后渲染 DOM 即明文。
- hotjob（地平线）API 返回 JSON 明文。
- Workday（NVIDIA/微软/红帽）有公开 CXS API 可抓岗位列表。
- 招聘公告用搜狗微信 weixin.sogou.com 搜（可达）。
- 银河航天 zhiye 门户已死（停放页），改走猎聘 193 岗 + `hr@yinhe.ht`。
- CETC 十五所 hotjob 社招门户 404 废弃，改走 `zhaopin.cetc.com.cn`（WAF，浏览器直连）+ 公众号"中国电科招聘"。

---

## 五、网络环境（复现抓取时必读）

- 外网必须：`export https_proxy=http://100.66.66.64:8765 http_proxy=http://100.66.66.64:8765`
- WebFetch 工具不通，用 curl/python+代理 或 playwright headless。
- Boss/脉脉/猎聘/jobui 强反爬，拿不到 JD；优先百度百科工商地址 + 官网静态页 + 搜狗微信 + headless 渲染 SPA。
- pip 内网镜像：`http://mirrors.baidubce.com/pypi/simple`
- 所有文件存 `/pulp`（容器根会丢）。

---

## 六、当前状态 & 下一步

- **循环 job 已停**（原进取型 `770de1e6`、躺平型 `885fb309` 已 CronDelete）。
- **情报调研彻底完成**，不再需要继续抓取（边际价值极低）。
- **下一步真正该做的是动手投递**，从上文"最优投递清单"★1 开始（ISCAS / 星动纪元）。
- 投递后若有面试/offer，可重新 `/loop` 或起新 agent 跟踪反馈、准备面试话术。

---

## 七、给新会话 AI 的接续指引

如果候选人回来要求继续，先判断意图：
1. **要投递材料** → 读 `companies.md` 对应公司章节 + `resume-*.md`，起草邮件正文/脉脉话术/简历精修。**不要代发邮件**（账号凭证风险），写成"可复制粘贴的成品"。
2. **要跟踪新岗位动态** → 按上文方法学用 headless 复查 8 家招聘门户（重点月之暗面/银河通用/地平线是否有 7-16 后新岗），更新 companies.md/memory.md 并 commit+push。
3. **要补某家公司深挖** → 读 memory.md 看是否已覆盖，避免重复。
4. **要重新启动循环** → 用 CronCreate 建 durable job，进取型+躺平型错开，每 20min，参照 memory.md 续轮次号。
5. **要改约束**（放宽距离/换城市/纳算法岗等）→ 在 memory.md 记录新约束后重新筛选。

**切记**：学历（西安理工非 211）是贯穿所有决策的核心约束；eBPF（bpf~1000 补丁）是进取型最稀缺的差异化武器；上交所 UDP<100μs 是低延迟高并发的硬证据。投递材料务必挂这两项。
