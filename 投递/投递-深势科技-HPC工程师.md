# 投递材料 · 深势科技 DP Technology HPC工程师

> 投递方式：**① 飞书 Hire 直投 `dptechnology.jobs.feishu.cn`（岗位 ID 7308616169388443923）② 邮件 `hr@dp.tech`**
> 岗位：HPC 工程师 | 深势科技 DP Technology
> 工作地：北京（距候选人 ~4.6km，通勤友好）
> 学历：**硕士达标，无 211 要求** — JD 未卡 211/985。候选人本科，但 perf/crash + BPF ~1000 补丁 + Zynq ARM NEON 实战可盖过学历。

---

## 核实结论

1. **投递入口（双通道）**：
   - ① **飞书 Hire**：`dptechnology.jobs.feishu.cn` 搜索岗位 ID `7308616169388443923` 或"HPC"→ 岗位详情 → "投递简历"→ 上传 PDF + 填表。
   - ② **邮件**：`hr@dp.tech`，附简历 PDF + 正文。
   - 建议双通道并行：飞书 Hire 走正式流程 + 邮件附正文增加 visibility。
2. **JD 关键词（据第 53 轮任务说明）**：AI4S 核心模块 x86/ARM/GPU/昇腾 移植优化 + perf/VTune/Nsight + SIMD/锁竞争 + C++/Rust。硕士达标无 211 要求。
3. **匹配度评估**：perf/crash 实战 + BPF ~1000 补丁 + 闻翔 Zynq ARM NEON + 上交所 UDP 锁竞争——对口"性能分析 + SIMD + 锁竞争 + 多架构（x86/ARM）"。GPU/昇腾侧无直接经验，靠多架构 + 系统性能分析迁移。
4. **HR / 内推**：`hr@dp.tech`（公开邮箱）。内推渠道：①脉脉搜"深势科技 内推" / "DP Technology 内推"；②官网 dptechnology.com 招聘页。建议飞书直投 + 邮件 + 脉脉内推三管齐下。

---

## ✉️ 邮件主题（直接复制）

[应聘] HPC工程师 — 王毅博 — 7年Linux内核 / BPF约1000补丁 / perf+crash实战 / ARM NEON+多架构移植

---

## ✉️ 邮件正文（直接复制，发 hr@dp.tech）

深势科技招聘团队您好：

我是王毅博，7 年 Linux 内核 + 多架构系统性能优化，应聘「HPC 工程师」。我的背景在性能分析（perf/crash/eBPF）、SIMD（ARM NEON）、锁竞争调优、多架构移植（x86/ARM/Zynq/申威/飞腾）上与 JD 高度契合：

## 一、性能分析：perf / VTune / Nsight（JD 核心）

- **perf/ftrace/eBPF/Crash 长期实战**（7 年内核研发日常工具）：
  - 定位申威 io_uring fork io 线程段错误（架构代码级）
  - 硬件随机单 bit 翻转 → do_page_fault
  - ARM 二层转发软中断占满 CPU（ebt_do_table 读写锁 + LSE 原子锁）
  - memcg 滑动平均统计 vs 测试用例
  - dim 内存完整性工具页对齐问题
- perf 火焰图/缓存/分支预测/锁竞争调优是日常；VTune/Nsight 无直接生产经验，但 perf 深度经验可平滑迁移到 VTune/Nsight 的微架构级 profile。

## 二、SIMD / 锁竞争（JD 强调项）

- **ARM NEON 实战**：闻翔 Zynq 平台 ARM SoC + FPGA bring-up，涉及 ARM NEON 指令优化（基带信号处理/AD9361 射频数据路径）。
- **锁竞争调优**：上交所 UDP 15 万并发平均延时 <100μs——软中断绑核 + 中断聚合 + 锁竞争调优（ebt_do_table 读写锁、LSE 原子锁定位）。生产级锁竞争根因分析硬证据。

## 三、多架构移植：x86/ARM/GPU/昇腾（JD 核心）

- **多架构内核适配经验**：x86 服务器（上交所低延时调优、百度云 IaaS）、ARM（Zynq 全栈 bring-up、统信 UOS ARM 服务器内核）、申威（io_uring 架构代码）、飞腾（RAS 联合项目）。
- 多架构移植的内核态/编译/ABI/性能差异理解到位——x86/ARM/GPU/昇腾的跨芯片移植，系统底层侧可迁移。
- GPU/昇腾侧无直接生产经验，但百度云 GPU 集群 IaaS 侧有接触；C/C++ + 多架构经验迁移成本低。

## 四、BPF 约 1000 补丁（系统级性能分析背书）

- 向 Linux 内核 **BPF 子系统合入约 1000 补丁**（verifier/bpf syscall/BTF），附 LKML commit 链接：[请在此插入链接]。
- eBPF(bcc/libbpf) 是 HPC 系统级性能 profile 的最强可观测武器，可用于 GPU/通信/算子链路瓶颈根因分析。

## 五、C/C++/Rust 基线

- C 精通（7 年内核 C），Shell/Python 熟练，C++ 基础；Rust 无生产经验但系统底层迁移成本低。

JD 的 perf/crash 实战 + SIMD + 锁竞争 + 多架构移植是我的核心强项；GPU/昇腾/VTune/Nsight 侧靠多架构 + 系统性能分析迁移。期待进一步沟通 AI4S 核心模块的 HPC 优化挑战。

简历附上，感谢！

王毅博
18792901259 | lucienwyb@qq.com

---

## ✉️ 飞书 Hire"自我介绍/求职信"框（可粘贴，精简版）

您好，我是王毅博，应聘「HPC 工程师」。7 年 Linux 内核 + 多架构系统性能优化：

**① 性能分析（perf/crash/eBPF，JD 核心）**
- perf/ftrace/eBPF/Crash 7 年实战：定位申威 io_uring 段错误、单 bit 翻转 do_page_fault、ARM 二层转发锁竞争、memcg 统计等疑难。
- 向 Linux 内核 BPF 子系统合入约 1000 补丁（附 LKML 链接）。

**② SIMD / 锁竞争（JD 强调项）**
- ARM NEON 实战（闻翔 Zynq 基带/AD9361 射频数据路径）。
- 上交所 UDP 15 万并发 <100μs：锁竞争调优（ebt_do_table 读写锁 + LSE 原子锁定位）。

**③ 多架构移植（x86/ARM/GPU/昇腾，JD 核心）**
- x86/ARM/Zynq/申威/飞腾 多架构内核适配；GPU/昇腾靠多架构迁移。

**④ C/C++/Rust 基线**
- C 精通，Shell/Python 熟练，C++ 基础。

期待进一步沟通。

---

## 📄 简历需突出的要点（基于 resume-大模型Infra版.md 调整）

首页一句话定位（置顶）：
> **7年Linux内核 | BPF约1000补丁(附LKML链接) | perf/crash/eBPF系统级性能分析 | 多架构移植(x86/ARM/申威/飞腾) | ARM NEON+锁竞争实战**

1. **perf/crash 实战清单置顶**：申威 io_uring 段错误 / 单 bit 翻转 do_page_fault / ARM 二层转发锁竞争 / memcg 统计 / dim 页对齐——展示"内核现场 → 根因"的微架构级 profile 能力，对口 JD perf/VTune/Nsight。
2. **BPF ~1000 补丁 + LKML 链接**：系统级性能分析强背书。
3. **ARM NEON 实战**：闻翔 Zynq 基带/AD9361 射频数据路径——对口 JD SIMD（虽非 x86 AVX，但 SIMD 指令优化方法论通用）。
4. **锁竞争调优**：上交所 UDP 15 万并发 <100μs + ebt_do_table 读写锁 + LSE 原子锁定位——对口 JD 锁竞争。
5. **多架构移植清单**：x86/ARM/Zynq/申威/飞腾——对口 JD x86/ARM/GPU/昇腾移植。
6. **弱化学历**：本岗硕士达标无 211 要求，候选人本科——教育放靠后；用 perf/crash 实战 + BPF 补丁 + 多架构盖过。简历不必隐瞒本科，但重点用战绩压住。
7. **诚实标注**：GPU/昇腾/VTune/Nsight 无直接生产经验——简历不必编造，面试坦承"perf 深度经验可迁移 VTune/Nsight，多架构经验可迁移 GPU/昇腾"。
8. **Rust 诚实标注**：无生产经验，系统底层迁移成本低。

---

## ⏱️ 投递操作步骤（双通道，约 10 分钟）

### A. 飞书 Hire 直投（正式流程）

1. 打开 `https://dptechnology.jobs.feishu.cn`（或岗位直达链接含 ID 7308616169388443923）
2. 搜索"HPC"或直接进入岗位 ID 7308616169388443923 详情页
3. 点"投递简历"→ 手机号验证码 / 微信扫码登录
4. 上传**中文简历 PDF**（命名 `王毅博-简历-HPC工程师.pdf`，基于 resume-大模型Infra版.md 导出）
5. 将上方【飞书自我介绍精简版】粘贴到求职信/自我介绍框（如有）→ 填基本信息（教育填本科西安理工大学，工作经历按简历顺序）→ 提交
6. 截图保存申请号

### B. 邮件投递（增加 visibility）

1. 收件人：`hr@dp.tech`
2. 主题：`[应聘] HPC工程师 — 王毅博 — 7年Linux内核 / BPF约1000补丁 / perf+crash实战 / ARM NEON+多架构移植`
3. 正文：复制上方邮件模板，将 `[请在此插入链接]` 替换为 BPF 补丁 LKML/GitHub 链接
4. 附件：`王毅博-简历-HPC工程师.pdf`
5. 发送

### C. 脉脉内推（并行）

1. 脉脉搜"深势科技 内推" / "DP Technology 内推"找员工
2. 发岗位标题 + 简历，请其内推

### 注意

> ⚠️ 本岗硕士达标无 211 要求，候选人本科——perf/crash 实战 + BPF ~1000 补丁 + 多架构移植是盖过学历的硬通货，简历重点压这几项。
> ⚠️ 工作地北京，距候选人 ~4.6km，通勤友好。
> ⚠️ 简历用 resume-大模型Infra版.md，重点强化"perf/crash 实战清单 + ARM NEON + 多架构移植"三段。
> ⚠️ GPU/昇腾/VTune/Nsight 侧无直接经验，面试话术要准备好（perf 迁移 VTune/Nsight，多架构迁移 GPU/昇腾）。
> ⚠️ 飞书 Hire + 邮件双通道并行，增加 visibility。
