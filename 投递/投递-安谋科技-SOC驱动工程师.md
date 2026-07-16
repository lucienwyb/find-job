# 投递材料 · 安谋科技 SOC Driver Engineer

> 投递方式：mokahr 在线申请（优先内推 Tab）+ 邮件直投 recruitment@armchina.com
> 岗位：Sr/Staff SOC Driver Engineer | app.mokahr.com/apply/armchina/885 | 2026-07-01 发布
> 北京融科资讯中心 C 座 7 层 3.85km | Senior 40-60 万 / Staff 50-80 万
> 学历：**大概率不卡学历** — JD 未提 211/985，合资实体社招看经验；但 HR 初筛可能学历过滤，**走 mokahr 内推入口可绕过 HR 直接到部门面试官**。

---

## 核实结论（第52轮）

1. **mokahr 投递流程（已核实，与银河通用同）**：安谋科技用 mokahr 门户 `app.mokahr.com/apply/armchina/885`。流程：登录（手机号验证码）→ 进入岗位详情 → 点"申请职位"→ 填基本信息/教育/工作经历 → 上传**中文简历 PDF** → 问卷（如有）→ 提交。**内推入口**：岗位详情页有"内推"Tab，选"找朋友内推"或直接走员工内推链接（绕 HR 初筛）。与银河通用 GALBOT、寒武纪同一 mokahr 系统，操作完全一致。
2. **内推 / HR 邮箱**：HR 邮箱 **recruitment@armchina.com**（已验证）。建议双投：①mokahr 内推 Tab（优先，绕学历初筛）②邮件发 recruitment@armchina.com 抄岗位标题。脉脉搜"安谋科技 内推"/"ARM 中国 内推"找员工。
3. **JD 要点（第41轮实抓，量身定制级）**：ARM 服务器 CPU Linux 内核驱动 + 设备树/ACPI + PCIe/I2C/SPI + KVM VFIO 直通 + perf + FPGA bring-up，5+ 年。另有 SOC Software Engineer（7+ 年，正好匹配）、SOC Firmware（高）、SOC Software Architect（10+ 年）可同投。
4. **学历策略**：JD 无 211/985 字样，合资实体（安谋科技是 ARM 中国合资公司）社招重经验。但 HR 初筛有学历过滤风险→**优先内推 Tab 把简历直接送部门**。本科 + 7 年强经验 + 闻翔 Zynq ARM bring-up 是最稀缺对口点，内推后命中率极高。

---

## ✉️ 邮件正文（直发 recruitment@armchina.com，可同步用）

**邮件主题：** 应聘 SOC Driver Engineer（2026-07-01 发布）— 王毅博 — 7年Linux内核/Zynq ARM全栈bring-up/BPF约1000补丁

安谋科技招聘团队，您好：

我是王毅博，看到贵司招聘「SOC Driver Engineer」岗，JD 要求（ARM 服务器 CPU Linux 内核驱动、设备树/ACPI、PCIe/I2C/SPI、KVM VFIO 直通、perf、FPGA bring-up）与我的背景高度匹配，特此投递。

## 与岗位要求逐条对应

**① ARM 服务器 CPU Linux 内核驱动**
- 统信软件 4 年 UOS 服务器内核开发维护，负责内核调度/内存(伙伴/SLAB)/VFS/网络协议栈/中断/锁全模块开发与调优；向 Linux 内核 **BPF 子系统合入约 1000 个补丁**（verifier、bpf syscall、BTF）。
- ARM 平台实战：上交所网络性能调优在**飞腾 ARM 平台**完成（15 万并发 UDP 平均延时 <100μs）；ARM 架构 RAS 调研（SDEI 中断机制 + 内存错误注入验证，飞腾联合项目）。

**② 设备树 / ACPI**
- 闻翔 Zynq（ARM SoC）全栈 bring-up：**Petalinux 移植 U-Boot/kernel/rootfs**，编写 **SPI/LCD/触摸屏/PL UartLite 设备树与驱动**，移植 AD9361 射频驱动——设备树从 0 到 1 的实战经验，直接命中 JD 最稀缺项。

**③ PCIe / I2C / SPI**
- 闻翔 Zynq 项目中 SPI 设备树驱动开发 + PL UartLite 外设驱动；嵌入式 Linux 裁剪/移植/驱动全流程；FPGA 控制代码重构约 7000 行（PL/PS 交互）。

**④ KVM VFIO 直通**
- 内核虚拟化方向：namespace/cgroup/KVM 体系熟悉（统信内核维护涵盖虚拟化子系统）；VFIO 设备直通机制理解 + 内核驱动适配经验可迁移。

**⑤ perf + FPGA bring-up**
- **perf/ftrace/eBPF(bcc/libbpf)/crash/kdump** 长期深度使用：定位过 do_page_fault 单 bit 翻转宕机、申威 io_uring fork 段错误、ARM 二层转发软中断占满 CPU（ebt_do_table 读写锁 + LSE 原子锁）等疑难问题。
- 闻翔 Zynq FPGA bring-up：Petalinux 全栈移植 + PL（FPGA 可编程逻辑）与 PS（ARM）协同 + 示波器/频谱仪硬件调试，**FPGA bring-up 是 JD 显式要求，候选人正中靶心**。

**⑥ 5+ 年经验**
- 7 年 Linux 内核/系统/嵌入式研发，C 精通；现职百度云 IaaS 镜像/软件源研发（2025.7 起）。

附件为详细简历，JD 几乎为我的经验量身定制（ARM 内核驱动 + 设备树 + FPGA bring-up + perf），期待进一步沟通。谢谢！

王毅博
电话：18792901259
邮箱：lucienwyb@qq.com

---

## 📄 简历需突出的要点（中文简历改写清单，基于 resume-机器人版.md 调整）

首页一句话定位（置顶）：
> **7年 Linux 内核开发 | BPF约1000补丁合入主线 | ARM(Zynq/飞腾)全栈bring-up | 设备树/驱动 | perf/eBPF | 低延时网络<100μs**

1. **闻翔 Zynq ARM 全栈 bring-up 置顶**：U-Boot/kernel/rootfs 移植、**设备树编写**（SPI/LCD/触摸屏/UartLite）、AD9361 驱动移植、FPGA 控制代码 7000 行重构——这是该岗**最稀缺对口点**（会设备树+FPGA bring-up 的内核人极少），必须放工作经历第一段突出。
2. **BPF ~1000 补丁**：单独成段，附 LKML/kernel.org commit 链接。ARM 服务器 CPU 内核驱动岗，上游贡献是硬通货。
3. **ARM 平台实战**：上交所飞腾 ARM 平台调优（15 万并发 <100μs）+ ARM RAS 调研（SDEI/内存错误注入）——命中"ARM 服务器 CPU"。
4. **perf/ftrace/eBPF/crash**：作为调试工具段重点写，列疑难 bug 案例（单 bit 翻转、io_uring fork、ebt_do_table 锁）。
5. **KVM/VFIO**：把虚拟化子系统维护经验点出（namespace/cgroup/KVM），VFIO 直通原理理解可迁移。
6. **统信 openEuler 内核维护**：4 年服务器内核全模块开发，对应"Linux 内核驱动"基线。
7. **弱化学历**：教育放靠后；用 7 年产出 + 闻翔 ARM bring-up 盖过学历。建议**走内推 Tab 绕 HR 初筛**。

---

## ⏱️ 投递操作步骤（约 5 分钟）

1. 打开 `https://app.mokahr.com/apply/armchina/885`
2. 搜索"SOC Driver Engineer"→ 进入岗位详情（确认 2026-07-01 发布的在招岗）
3. **优先走内推**：点岗位页"内推"Tab → 找朋友内推 / 用员工内推链接（绕过 HR 学历初筛，简历直送部门）
4. 若无内推人：直接点"申请职位"→ 登录（手机号验证码）→ 填基本信息/教育/工作经历 → 上传**中文简历 PDF**（命名`王毅博-简历-SOC驱动工程师.pdf`）→ 提交
5. **同步邮件直投**：发 recruitment@armchina.com，主题粘贴上方，正文粘贴上方邮件（替换手机号/邮箱）+ 附简历 PDF
6. **脉脉内推**：搜"安谋科技 内推"找员工，发岗位标题 + 简历

> ⚠️ 该岗 JD 为候选人量身定制级（ARM 内核驱动 + 设备树 + FPGA bring-up + perf + KVM），是躺平型外企高薪对口首选，建议本周内投。走内推 Tab 绕学历是关键。
> ⚠️ 同门户可顺投 SOC Software Engineer（7+ 年正好）作第二选择。
