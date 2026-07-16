# 投递材料 · NVIDIA Sr Software Engineer, Networking (JR2015006)

> 投递方式：Workday 在线申请（非邮件）。本材料含①申请填表要点②英文正文(可粘贴到"Why are you interested"框/Cover Letter)③简历侧重要点④操作步骤。
> 岗位：Sr Software Engineer - Networking | Req ID JR2015006 | 北京融科资讯中心 C 座 3.56km
> 学历：**不卡学历** — JD 原文 "or equivalent experience"，美国公司全球统一不设 211/985。

---

## 核实结论（第52轮）

1. **投递流程（已核实，第41/43轮 Workday API 实抓）**：NVIDIA 用 Workday 门户 `nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`。流程：搜索 JR2015006 → 点 Apply → 登录（注册账号或 LinkedIn 一键登录）→ 上传**英文简历 PDF** → 填基本信息（教育/工作经历，教育填本科即可，"or equivalent experience"覆盖）→ EEO 问卷（自愿、非强制）→ 提交。
2. **是否有 HR 邮箱 / 脉脉内推**：NVIDIA **无公开投递 HR 邮箱**（美企统一走 Workday）。内推渠道：①脉脉搜"NVIDIA 内推"找员工发 Req ID JR2015006；②LinkedIn 搜 NVIDIA 北京 Networking 团队员工发消息附简历。**建议先脉脉内推再 Workday 直投**（内推可绕过初筛、加 visibility）。
3. **岗位在线状态**：Workday 公共搜索 API 有 2000 条最新职位上限，JR2015006 是较早 requisition（2015xxx），**无法通过搜索 API 翻页定位**（offset>2000 回绕到首页）。第41/43/51轮（均 2026-07-16 当天）已通过 Workday API 确认在招并拿到 JD 原文。投递前请候选人直接在 **NVIDIA 招聘页搜索框输入 JR2015006** 确认仍可 Apply（若已下架会显示 "This job is no longer active"）。
4. **JD 要点（第41轮实抓）**：C/C++ Linux kernel modes；**Kernel & DPDK strongly preferred**；L2/L3 协议栈；优势项 RDMA/DPDK/NCCL；5+ 年；"or equivalent experience"不卡学历。
5. **备选岗位**：若 JR2015006 已关闭，JR2015068 "Senior Networking Software Engineer, Linux Kernel Drivers"（实抓确认在招，Posted 10 Days Ago）JD 几乎一致，但工作地 **Santa Clara, CA**（非北京，需赴美）。另有 JR2015012 RDMA（北京/上海，6+ 年，第41轮高匹配）可作北京备选。

---

## ✉️ 英文申请正文（可粘贴到 Cover Letter / "Why NVIDIA" 文本框）

**Subject（如邮件内推用）:** Application for Sr Software Engineer, Networking (JR2015006) — Yibo Wang — 7yr Linux Kernel / BPF ~1000 patches / Ultra-low-latency Networking

Dear NVIDIA Hiring Team,

I am applying for the **Sr Software Engineer, Networking (JR2015006)** position in Beijing. With 7 years of Linux kernel and low-latency networking engineering, my background maps directly to the JD's emphasis on C/C++ kernel-mode development, Kernel & DPDK, and L2/L3 protocols. Below is how my experience aligns with your requirements.

**① C/C++ Linux kernel-mode development — BPF subsystem, ~1000 upstream patches**
- Contributed and merged approximately **1000 patches to the Linux kernel BPF subsystem** (verifier, bpf syscall, program-type extensions, BTF) while backporting high-version BPF features onto a 4.19 enterprise kernel, fixing verifier errors that caused ~100 test-case failures.
- Deep, hands-on work across scheduler, memory (buddy/SLAB), VFS, network stack, interrupts, RAS, and locking — 4 years maintaining the UOS server kernel at UnionTech (统信软件).

**② Kernel & DPDK (strongly preferred) — production ultra-low-latency networking**
- Tuned the ARM-platform UDP gateway for the **Shanghai Stock Exchange to 150K concurrent connections at average latency <100μs**: softirq CPU pinning, interrupt coalescing, network-stack parameter tuning, and **userspace zero-copy via DPDK/gazelle**. Independently wrote a ~300-line kernel module to surface NIC interrupt statistics.
- This is directly on-target for kernel + DPDK high-performance networking with strict latency SLAs.

**③ L2/L3 protocols & large-scale network stack — Baidu Cloud IaaS**
- Currently building Baidu Cloud IaaS public image and software-source infrastructure (since 2025.7); earlier work spans the full network stack, L2 forwarding debugging (resolved ebt_do_table read-write lock + LSE atomic lock contention saturating a CPU), and distributed storage/IO consistency across ~100TB.

**④ Advantage: RDMA / DPDK / NCCL & observability**
- eBPF (bcc/libbpf) observability for kernel performance and stability analysis — directly transferable to RDMA/NCCL collective-communication performance profiling and network-fault root-cause analysis.
- Diagnosed hardware panics from single-bit flips (do_page_fault), architecture-specific io_uring fork bugs (申威), and memory-integrity tool page-alignment issues — the kind of deep triage NVIDIA networking infrastructure demands.

**⑤ Why I fit NVIDIA Networking**
- The combination of kernel-mode C mastery, DPDK production hardening at sub-100μs latency, BPF upstream contribution volume, and IaaS-scale network infrastructure is rare and exactly what the JR2015006 role requires. I do not need sponsorship constraints beyond local Beijing employment.

JD states "or equivalent experience" — my 7 years of verifiable upstream kernel contribution and production low-latency networking work is offered in lieu of an elite-university credential.

Thank you for your consideration. I would welcome the opportunity to discuss how my background can contribute to NVIDIA's networking software team.

Best regards,
Yibo Wang
Phone: +86 18792901259
Email: lucienwyb@qq.com
Location: Beijing (near Beiyi Sanyuan, ~3.5km from NVIDIA Rongke office)

---

## 📄 简历需突出的要点（英文简历改写清单）

首页一句话定位（置顶）：
> **Linux Kernel Developer | 7 yr | BPF ~1000 upstream patches | DPDK ultra-low-latency (<100μs) | ARM/x86 | IaaS Networking**

1. **BPF ~1000 patches**：单独成段，写清子系统（verifier/bpf syscall/BTF）、补丁数量级、可量化效果。**务必附 LKML / kernel.org commit 链接**（这是 NVIDIA 最看重的硬通货）。
2. **上交所 UDP 150K 并发 <100μs**：作为"kernel + DPDK production hardening"硬证据，写明软中断绑核、中断聚合、网络栈调优、gazelle/DPDK 用户态零拷贝、自写网卡中断内核模块。
3. **百度云 IaaS 网络栈**：大规模分发基础设施、~100TB 跨区一致性、网络栈/IO 调优——命中"L2/L3 protocols & large-scale networking"。
4. **DPDK/gazelle/RDMA/NCCL 优势项**：把 DPDK 经验前置；eBPF 可观测能力包装为"RDMA/NCCL 集合通信性能 profile + 网络故障根因分析"的迁移点。
5. **ARM 经验**：上交所调优在飞腾 ARM 平台做、RAS 调研（SDEI 中断）、Zynq ARM SoC bring-up——命中 ARM 服务器网络栈。
6. **弱化学历**：教育放简历靠后；用 "or equivalent experience" 话术，工程产出盖过学历。英文简历用动词开头（Contributed/Merged/Tuned/Diagnosed），量化为主。
7. **debug 亮点**：申威 io_uring fork 段错误、单 bit 翻转 do_page_fault、ebt_do_table 读写锁——展示深度 triage 能力（NVIDIA infra 团队看重）。

---

## ⏱️ 投递操作步骤（约 5 分钟）

1. 打开 `https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite`
2. 搜索框输入 `JR2015006` → 进入岗位详情 → 确认"Apply"按钮可点（若提示 no longer active 则改投 JR2015012 RDMA 或 JR2015068）
3. 点 **Apply** → 用 LinkedIn 一键登录或注册 Workday 账号
4. 上传**英文简历 PDF**（重命名 `Yibo-Wang-Resume-Networking-Engineer.pdf`）
5. 填工作经历（突出 7 年）、教育（本科，备注 "or equivalent experience"）
6. 将上方【英文正文】粘贴到 Cover Letter / "Why are you interested" 文本框（如有）
7. EEO 问卷：自愿填写（可不答种族/性别，非强制）→ 提交
8. **同步走内推**：脉脉搜"NVIDIA 内推"→ 发 JR2015006 + 英文简历 → 双管齐下

> ⚠️ 务必先准备 LKML / kernel.org 的 BPF commit 列表链接，附在简历或 Cover Letter——这是 NVIDIA Kernel 岗最强差异化。
> ⚠️ NVIDIA 北京融科 C 座 3.56km，965 外企 WLB 好，50-80 万 + RSU（Staff 80-120 万），不卡学历，是非 211 候选人高薪对口外企真路径。
