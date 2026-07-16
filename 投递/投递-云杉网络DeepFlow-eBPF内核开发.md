# 投递材料 · 云杉网络 DeepFlow eBPF/内核开发工程师

> 投递方式：**① 先在 GitHub `github.com/deepflowio/deepflow` 提 PR ② 再发邮件至 `hr@yunshan.net`**
> 岗位：eBPF/内核开发 + 观测智能体 Agent 方向 | 云杉网络 DeepFlow
> 工作地：北京（距候选人 ~2.4km，通勤友好）
> 学历：本科可投（开源贡献盖过学历）。

---

## 核实结论

1. **DeepFlow 项目背景**：云杉网络开源 eBPF 可观测平台 `github.com/deepflowio/deepflow`，核心是 eBPF 采集内核网络/应用数据 + 智能体 Agent 做根因分析。eBPF/内核开发是其技术根基。
2. **投递路径（内核 → Agent 最短路径）**：候选人 7 年内核 + BPF ~1000 补丁是 DeepFlow eBPF 侧的天然命中；Agent 方向靠 eBPF 可观测 + 系统级根因分析迁移。**先提 PR 展示 eBPF 实力，再发邮件附 PR 链接**——开源公司最看重 PR。
3. **匹配度**：eBPF/内核开发 95+（BPF ~1000 补丁直接命中）；Agent 方向 80+（系统级可观测 + 根因分析可迁移，LLM Agent 侧靠学习）。
4. **HR / 内推**：`hr@yunshan.net`（公开邮箱）。内推渠道：①脉脉搜"云杉网络 内推" / "DeepFlow 内推"；②官网 yunshan.net 招聘页；③GitHub DeepFlow issue/PR 引起 maintainer 注意。建议 PR + 邮件双管齐下。

---

## ✉️ 邮件主题（直接复制）

[应聘] eBPF/内核开发工程师 — 王毅博 — 7年Linux内核 / BPF约1000补丁 / 系统级可观测

---

## ✉️ 邮件正文（直接复制）

DeepFlow 团队您好：

我是王毅博，7 年 Linux 内核研发，向 Linux 内核 **BPF 子系统合入约 1000 个补丁**（verifier/bpf syscall/程序类型扩展/BTF），是 BPF 子系统在国内的主要贡献者之一。看到 DeepFlow 的 eBPF 可观测 + Agent 智能体方向，我的背景是"内核 → Agent"的最短路径，特此应聘。

## 一、eBPF / 内核开发（JD 核心，直接命中）

- **BPF 子系统约 1000 补丁**：在 4.19 企业内核上回合高版本 bpf/btf 特性，修复校验出错致近百用例失败；覆盖 verifier、bpf 系统调用、程序类型扩展、BTF。附 LKML commit 链接：[请在此插入候选人 LKML/GitHub commit 链接]。
- **bcc/libbpf 长期实战**：生产环境用 eBPF 做网络/IO/调度可观测与故障根因分析。
- 统信 4 年 UOS 服务器内核：调度/内存/网络栈/VFS/中断/锁全模块开发与调优。

## 二、系统级可观测 / 根因分析（Agent 方向基础）

- ftrace/perf/火焰图/eBPF/Kdump/Crash 定位多类疑难：
  - 申威 io_uring fork io 线程段错误（架构代码）
  - 硬件随机单 bit 翻转 → do_page_fault
  - ARM 二层转发软中断占满 CPU（ebt_do_table 读写锁 + LSE 原子锁）
  - memcg 滑动平均统计 vs 测试用例
  - dim 内存完整性工具页对齐问题
- 这些"内核现场 → 根因"的定位能力，正是 DeepFlow Agent 做智能根因分析的底层基础。

## 三、低延时网络可观测（DeepFlow 核心场景：网络可观测）

- 上交所 UDP 网关：**15 万并发平均延时 <100μs**——软中断绑核 + 中断聚合 + 网络栈调优 + gazelle/DPDK 用户态零拷贝。
- 独立编写网卡中断信息展示内核模块约 300 行。
- 对网络栈 tracepoint/kprobe/eBPF 采集链路有深度理解——直接对口 DeepFlow 的网络可观测。

## 四、大规模 Infra（Agent 数据平台侧）

- 现职百度云 IaaS 镜像/软件源研发：~100TB 跨区域存储一致性架构重构，分布式 IO/网络调优——大规模可观测数据平台的基础设施视角。
- kpatch 热补丁产品化：集群滚动升级/灰度回滚经验。

## 五、GitHub PR（已附）

我已在 `github.com/deepflowio/deepflow` 提交 PR：[请在此插入 PR 链接]
（PR 内容建议：见下方 GitHub PR 指引）

C 精通，7 年内核 + eBPF 实战。期待与 DeepFlow 团队进一步沟通 eBPF 可观测与 Agent 智能体的系统挑战。

简历附上，感谢！

王毅博
18792901259 | lucienwyb@qq.com

---

## 🔧 GitHub PR 指引（投递前必做）

### 目标
在 `github.com/deepflowio/deepflow` 提一个**高质量 PR**，展示 eBPF/内核能力，作为邮件投递的强背书。开源公司（云杉）最看重 PR。

### PR 方向建议（按可行性排序）

1. **首选：eBPF 采集侧 bug 修复 / 性能优化**
   - Fork `deepflowio/deepflow` → clone → 重点关注 `agent/` 目录下 eBPF 相关代码（`agent/src/ebpf/` 或类似路径）。
   - 在 `agent/src/ebpf/` 下找：①已知 issue 标"good first issue"/"help wanted"的；②ebpf 程序的边界条件/内存泄漏/锁竞争问题；③tracepoint/kprobe 采集逻辑的优化点。
   - 候选人 BPF ~1000 补丁经验，定位 eBPF 代码问题不难。

2. **次选：文档/示例补全**
   - 若代码侧短期难出 PR，可补 eBPF 采集链路的文档/示例（如某个采集器的使用说明、性能调优指南）。
   - 文档 PR 虽含金量低，但能快速建立贡献者身份。

3. **备选：issue 讨论参与**
   - 在 issue 区参与 eBPF/内核相关讨论，展示专业度，吸引 maintainer 注意。

### PR 操作步骤

1. Fork `github.com/deepflowio/deepflow` 到自己账号
2. `git clone` fork 仓库 → 新建分支（如 `fix/ebpf-xxx`）
3. 定位问题 → 改代码 → 本地测试（`make` / `cargo test` 视项目而定）
4. `git push` → 在 GitHub 发起 PR，标题清晰（如 `fix(ebpf): handle NULL deref in xxx collector`），描述：问题现象/根因/修复方案/测试结果
5. PR 合并后，将链接填入邮件正文 `[请在此插入 PR 链接]` 处

### 注意

> ⚠️ PR 不求大，求"对"。一个 ebpf 采集侧的小 bug 修复 + 清晰描述，比大而泛的 PR 有效。
> ⚠️ 若时间紧，可先发邮件（邮件中说明"PR 进行中，预计 X 日内提交"），再补 PR。但**有 PR 再发邮件效果最好**。
> ⚠️ DeepFlow 是 Rust 为主（agent 侧），候选人 Rust 无生产经验——eBPF 侧 C 代码仍可贡献，但建议面试前补 Rust 基础。

---

## 📄 简历需突出的要点（基于 resume-大模型Infra版.md 调整）

首页一句话定位（置顶）：
> **7年Linux内核 | BPF约1000补丁(附LKML链接) | eBPF(bcc/libbpf)系统级可观测 | 低延时网络15万并发<100μs | 内核→Agent最短路径**

1. **BPF ~1000 补丁置顶 + LKML 链接**：这是 DeepFlow eBPF 侧的命门，简历首页显式附 commit 链接。
2. **eBPF 可观测能力**：bcc/libbpf 生产实战 + 网络栈 tracepoint/kprobe 采集理解——直接对口 DeepFlow 网络可观测。
3. **疑难根因定位清单**：申威 io_uring 段错误 / 单 bit 翻转 do_page_fault / ARM 二层转发锁竞争 / memcg 统计——展示"内核现场 → 根因"能力，对口 Agent 智能根因分析。
4. **上交所 UDP <100μs**：网络可观测硬证据 + 独立编写网卡中断信息展示内核模块 ~300 行。
5. **百度云 IaaS**：大规模可观测数据平台的基础设施视角。
6. **GitHub PR 链接**：简历中附 DeepFlow PR 链接（如有），开源公司最看重。
7. **弱化学历**：本科可投，BPF 补丁 + PR 是盖过学历的硬通货。
8. **诚实标注**：Rust 无生产经验（DeepFlow agent 侧 Rust 为主）——简历不必编造，面试坦承"eBPF 侧 C 代码可贡献，Rust 学习中"。

---

## ⏱️ 投递操作步骤

### A. GitHub PR（先做，1-3 天）

1. Fork `github.com/deepflowio/deepflow` → clone → 新建分支
2. 在 `agent/src/ebpf/`（或类似路径）找 eBPF 采集侧 bug/优化点
3. 改代码 → 本地测试 → push → 发起 PR（标题清晰 + 描述完整）
4. 复制 PR 链接备用

### B. 邮件投递（PR 后发）

1. 收件人：`hr@yunshan.net`
2. 主题：`[应聘] eBPF/内核开发工程师 — 王毅博 — 7年Linux内核 / BPF约1000补丁 / 系统级可观测`
3. 正文：复制上方邮件模板，将 `[请在此插入 PR 链接]` 替换为实际 PR URL，将 `[请在此插入候选人 LKML/GitHub commit 链接]` 替换为 BPF 补丁链接
4. 附件：`resume-大模型Infra版.md` 导出的 PDF（命名 `王毅博-简历-eBPF内核开发工程师.pdf`）
5. 发送

### C. 内推（可选，并行）

1. 脉脉搜"云杉网络 内推" / "DeepFlow 内推"找员工
2. 发岗位标题 + 简历 + PR 链接，请其内推

### 注意

> ⚠️ 内核 → Agent 最短路径：BPF ~1000 补丁是命门，PR + LKML 链接是核心背书。
> ⚠️ 工作地北京，距候选人 ~2.4km，通勤友好，高优。
> ⚠️ DeepFlow agent 侧 Rust 为主，eBPF 侧 C 仍可贡献；面试前补 Rust 基础是加分项。
> ⚠️ 若 PR 短期难出，可先发邮件说明"PR 进行中"，但**有 PR 再发邮件效果最好**。
