================================================================================
王毅博 面试技术问答预演集（6家岗位 + 通用高频）
基于简历真实项目，答题要点强调深度与可追问细节，不编造。
================================================================================

================================================================================
一、银河航天 星载软件工程师（载荷）——Zynq/嵌入式Linux/星载可靠性
================================================================================

Q1：Zynq PS-PL 交互怎么做？AXI 总线细节讲一下。
答题要点：
- Zynq是PS(ARM Cortex-A9双核)+PL(FPGA)异构。PS-PL之间通过AXI总线互联，三类接口要分清：
  - AXI HP（High Performance）口：直接连DDR控制器，用于PL大块数据DMA搬移（如AD9361射频数据流），不走Cache，带宽高。简历中AD9361数据通路应走HP口。
  - AXI GP（General Purpose）口：PS当master配PL寄存器，用于控制面（读FPGA状态/写控制寄存器）。UartLite IP的寄存器映射就经GP口。
  - AXI ACP（Cache Coherent）：连L2 cache，适合需要一致性场景，星载少用。
- 关键点：地址映射在设备树里配pl节点ranges，用户态通过/dev/mem或UIO映射寄存器；PL侧时钟要PS给（FCLK_CLK0），在设备树里配clocks。
- 可追问：HP口突发长度（burst 16 for AXI3）、位宽（32/64位）、AXI协议的outstanding事务对吞吐影响。答：实际调过UartLite波特率/中断号，AD9361走HP DMA，PL侧时序收敛由FPGA同事负责，我负责PS侧驱动和设备树。

Q2：AD9361驱动移植具体做了什么？
答题要点：
- AD9361是射频收发芯片，通过SPI配寄存器+数据口走DMA。主线有adi/ad9361驱动（ad9361.c，后改名axi_adc/iio框架）。
- 移植工作：把主线驱动适配到Petalinux内核版本（4.19），解决接口/宏变更；设备树里配ad9361节点（spi-max-frequency、reg、中断、ref-clock-frequency、ADI AXI DMAC节点）；FPGA侧用ADI参考的axi_dmac IP做数据搬运，PS侧配HP口地址。
- 踩坑：SPI速率与FCLK时钟配错会初始化失败；AD9361的calibration需要指定clock，设备树没配对会卡在校准。
- 诚实边界：驱动框架基于ADI参考，我做的是平台适配和参数调通，不是从零写。

Q3：随机bit翻转怎么定位的？SEU与地面bit翻转区别？
答题要点：
- 现场现象：do_page_fault宕机，但访问的地址"看起来正常"，crash分析发现是数据被改。怀疑bit翻转。
- 定位手段：
  - mcelog / rasdaemon 采集硬件报错（x86有mcelog；ARM上有RAS扩展，依赖固件SDEI中断上报内存错误，简历中"RAS调研SDEI中断+内存错误注入"就是这个）。
  - edac内核框架：把内存错误上报到sysfs（/sys/devices/system/edac/mc/），可统计CE(Correctable Error)/UE。
  - 注入实验：ARM RAS用内存错误注入（ERRideset/ERRIDR寄存器或固件PSCI接口），验证从硬件中断→SDEI→内核EDAC→rasdaemon全链路。
- SEU(Single Event Upset单粒子翻转)与地面bit翻转：
  - 地面bit翻转主因是α粒子/电磁干扰/器件老化，发生率低（SLC flash FIT量级）。
  - 空间SEU是高能粒子（重离子/质子）穿透，翻转率高1-2个数量级，且有多bit翻转(MBU)风险，单字节ECC可能不够。
  - 对策：ECC内存（SEC-DED，纠正单bit检测双bit）、内存冗余(TMR三模冗余/页面隔离)、FPGA配置区scrubbing(周期回读CRC并重配)、关键变量CRC校验。
- 可追问"dim内存完整性页对齐"：内存完整性检测要求被测页对齐到边界(4KB页/2MB大页)，否则跨页检测不准。dim工具校验内存时按页对齐填充pattern。

Q4：PREEMPT_RT硬实时了解多少？星载任务能上吗？
答题要点：
- 诚实：简历未做PREEMPT_RT实时性项目，15万并发<100us是软实时优化，不是硬实时。
- PREEMPT_RT原理：把内核大部分自旋锁改成rt_mutex（可睡眠互斥），强制线程化中断，让几乎所有内核路径可抢占，把调度延迟压到微秒级抖动可控。
- 星载权衡：PRETEMPT_RT牺牲吞吐换确定性，星载载荷数据处理量大时可能不合算；传统做法是关键控制环用裸核/FPGA或隔离CPU+完全公平策略关闭（isolcpus+迁移禁止）。
- 可讲：我做的15万并发<100us用的是"软中断绑核+中断聚合+独立写网卡中断"思路，本质上靠隔离和减开销而不是抢占，对抖动敏感场景我会用isolcpus+PREEMPT_RT组合。
- 如果被问没做过的：坦承没做过PREEMPT_RT内核改，但理解原理。

Q5：kpatch在轨热补丁思路？空间环境能直接用吗？
答题要点：
- 简历：kpatch产品化——仿红帽rpm spec打包，做的是"产品化"（打包分发、灰度、回滚），不是kpatch框架本身开发。
- kpatch原理：基于ftrace/livepatch机制，构造一致性模型——等旧函数所有线程退出栈后再切到新函数（kpatch的"shadow stack"/task switch点），通过stop_machine保证原子性。
- 在轨场景适配：
  - 卫星上行带宽窄，热补丁patch小（KB级）比整机升级合适。
  - 难点：空间单粒子可能让热补丁本身失配；旧函数栈长时间不退出（长任务）会卡stop_machine；需要看门狗兜底。
  - 实操：补丁先地面验证→上注→灰度到一个核→全核生效→异常自动回滚到旧函数（livepatch支持disable）。
- 诚实：kpatch产品化我做的是打包和灰度流程，livepatch内核机制本身是社区现成的。

================================================================================
二、星动纪元 BSP/底层驱动 ——板级bring-up/驱动移植
================================================================================

Q1：bring-up一块新板子的步骤？
答题要点（以Zynq+ARM经验外推）：
1. 上电前：电源时序检查（多路电源上电顺序）、原理图确认各电源域、时钟、复位电路。
2. 上电后串口先出：bootrom日志→看是否有任何输出；无输出先查时钟/复位/电压/JTAG能否挂上。
3. U-Boot移植：先跑通SPL（DDR init是难点，需要时序参数从Xilinx/DDR controller工具生成），再跑通U-Boot主体（串口、网口、SD卡）。
4. Kernel bring-up：设备树先配最小集（串口console+根文件系统），能挂上rootfs后再逐个加驱动（网口、SPI、I2C、USB）。
5. 驱动逐个点亮：每个外设单独测，确认中断能进、寄存器能读、数据能收发。
6. 压力测试：长时间跑+温度循环。
- 简历对应：Petalinux移植uboot/kernel/rootfs就是这套流程，SPI/LCD/触摸屏/UartLite设备树驱动是第5步。

Q2：Petalinux移植踩过什么坑？设备树怎么改？
答题要点：
- Petalinux坑：
  - BSP版本与Vivado版本强绑定（Vivado生成的hardware handoff .hdf要和Petalinux对上），版本错会设备树生成失败。
  - kernel config碎片化：Petalinux默认config不全，要menuconfig补驱动选项（如某SPI控制器、AD9361 IIO框架）。
  - rootfs：默认太臃肿，用Petalinux的rootfs config精简，或换Yocto/Buildroot。
- 设备树改法：
  - dtsi里pl节点下加子节点：compatible、reg（AXI地址）、interrupts（中断号+parent）、clocks、spi-max-frequency等。
  - UartLite节点示例：compatible="xlnx,opb-uartlite-1.02.b"或"xlnx,xps-uartlite-1.02.a"，reg=<0x42C00000 0x10000>，interrupts=<0 29 1>（SPI号+中断号+触发类型），clock-frequency。
  - 设备树编译dtc检查语法，/proc/device-tree验证内核是否正确解析。
- 触摸屏：用input子系统，设备树配好interrupt和axes-gpio，校准用tslib。

Q3：SPI驱动移植流程？SPI/LCD/触摸屏怎么接的？
答题要点：
- SPI控制器驱动（master/zynq-spi）：Petalinux自带，配设备树给时钟、中断、num-cs。
- SPI设备驱动（如AD9361、屏控制器）：写或移植spidev，注册spi_driver，probe里spi_setup设模式(CPOL/CPHA)/频率/位宽，用spi_sync/spi_async传输。
- 串口协议分包+idle中断接收：UartLite接收，硬件idle中断（FIFO空闲一段时间触发）作为分包信号，避免逐字节处理开销，中断里读FIFO到buffer再上抛。
- LCD：framebuffer或DRM，看屏接口类型（PL侧用AXI-DMA搬图）。

Q4：实时性怎么调？15万并发<100us怎么做到的？软中断绑核具体？
答题要点（这是核心亮点，要讲透）：
- 场景：上交所行情UDP低延时，单容器15万包/秒，端到端<100us。
- 手段（分层）：
  1. 网络栈参数：net.core.busy_read/busy_poll开启，SO_BUSY_POLL让socket主动轮询网卡队列；减少netdev_budget；关闭一些不必要功能。
  2. 软中断绑核（关键）：RPS/RSS把网卡多队列绑到指定核；XPS设发送队列CPU亲和；isolcpus隔离业务核；再把软中断(NAPI/NET_RX)固定到业务核，避免软中断抢其他核。
  3. 中断聚合：网卡中断coalescing（rx-usecs/tx-usecs），低延时场景反而要降低聚合粒度（设小rx-usecs）让中断及时上来；或用NAPI轮询模式彻底绕中断。
  4. 独立写网卡中断展示内核模块300行：写了个内核模块，把网卡接收中断单独绑到某核并做轻量化处理（可能直接在硬中断/软中断里快速投递到用户态），绕过完整协议栈。300行精简但体现从netfilter/中断处理到底层的能力。
  5. gazelle/dpdk环境：dpdk完全旁路内核（用户态驱动+轮询），gazelle是半旁路（基于lwIP在内核态加速）。终极方案上dpdk。
- 测量：perf/ftrace测中断到用户态时间分布；统计p99/p999而非平均。
- 可追问"软中断绑核具体"：/proc/softirqs看分布；smp_affinity(/proc/irq/NR/smp_affinity位图)绑硬中断；RPS设/sys/class/net/ethX/queues/rx-N/rps_cpus绑软中断；用taskset把业务进程绑到同一核做cache亲和。

Q5：FPGA控制7000行重构怎么做的？架构？
答题要点：
- 7000行FPGA控制代码（PS侧C代码，控制PL侧逻辑，不是Verilog）：原代码耦合严重、可读性差、无版本管理。
- 重构思路：模块化分层（硬件抽象层=寄存器读写，协议层=控制时序，业务层=功能调用）；统一错误处理；加日志框架；按功能拆文件。
- 诚实边界：是PS侧嵌入式C重构，不是RTL重构；体现的是C工程能力（简历C精通）和嵌入式架构能力，与BSP岗相关。

================================================================================
三、银河通用 嵌入式软件（主控/感知板）——多SoC/传感器驱动
================================================================================

Q1：多SoC怎么协同？跨芯片数据通路？
答题要点：
- 诚实：简历主要是单SoC(Zynq)经验，多SoC协作是推断。
- 常见架构：主控SoC(如RK3588/TDA4) + 感知SoC(可能多个)，通过千兆/万兆网口或PCIe互联；共享内存通过RPMsg/OpenAMP（AMP双系统场景）。
- 传感器接入：MIPI-CSI摄像头走ISP；激光雷达/IMU走SPI/I2C/UART/以太网；时间同步用PTP或硬件GPIO同步信号。
- 可讲：我熟悉设备树驱动模型和SPI/串口协议，传感器bring-up套路一样；多SoC协同如果用RPMsg我能快速上手。

Q2：传感器驱动移植？IMU/激光雷达？
答题要点：
- 简历对应：SPI驱动移植、AD9361射频驱动、串口协议分包+idle中断。
- 通用思路：看传感器datasheet的SPI/UART协议帧格式→选子系统(IIO for IMU是标准框架)→设备树配片选/中断/频率→驱动实现probe/read_raw→用户态用/sys或字符设备读。
- IMU经IIO：iio_device_alloc，配置channels(accel/gyro/temp)，trigger和buffer支持连续采样。
- 时间戳：驱动里打时间戳要用单调时钟(ktime_get_boottime)，传感器融合对时延敏感。
- 可问的：数据流要不要走DMA？高频IMU(8kHz)必须DMA+ring buffer。

Q3：实时性/低延时在机器人感知里怎么做？
答题要点：
- 简历迁移：15万并发<100us的网络低延时经验可直接迁移到传感器数据链路低延时。
- 手段：绑核隔离(isolcpus)、IRQ亲和、PREEMPT_RT(感知对抖动敏感，比纯吞吐重要)、内核旁路(SPDK/DPDK思路用于高速相机/雷达)。
- 诚实：机器人感知的实时性要求通常比金融行情低一档(ms级而非us级)，但抖动控制思路一致。

Q4：设备树和驱动模型深入？
答题要点：
- platform_driver + of_match_table匹配设备树compatible；probe拿of_iomap/of_get_property读设备树资源。
- 设备树overlay(运行时加载dtbo)：感知板可热插拔时有用。
- pinctrl：每个外设要配引脚复用，Petalinux里在pinctrl节点配。
- 可讲：我写过SPI/LCD/触摸/UartLite的设备树节点和对应驱动绑定，of_match_table、devm_iomap、devm_request_irq一套标准流程。

Q5：中断上下半部在传感器场景的应用？
答题要点（接通用高频，但落地到传感器）：
- 传感器高频中断(如IMU每sample一中断)必须用threaded_irq：上半部硬中断只唤醒线程化下半部，下半部在进程上下文处理(读FIFO、解算、拷贝到ring buffer)。
- 或用workqueue：不实时但可睡眠。
- 简历idle中断接收就是上半部读FIFO+下半部分包的典型结构。

================================================================================
四、智谱 系统软件/Infra ——集群稳定性/性能调优
================================================================================

Q1：100T软件源怎么重构的？pulp架构？QPS/带宽怎么测？
答题要点（核心项目）：
- 痛点：旧rsync架构跨区域一致性有IO问题——rsync全量比对+跨地域传输，文件多(100T元数据)时IO和耗时不收敛；一致性靠rsync本身不保证原子。
- 调研开源：对比debmirror/apt-mirror/bandersnatch(pypi)/pulp。选pulp因为：内容寻址(storage按artifact hash去重)、插件式(rpm/deb/file/pypi/容器)、同步原语基于发布版本(snapshot原子切换)、有API和task队列。
- pulp架构：pulpcore(api+content app+worker) + plugin + postgres + redis。content app serve /pulp/content/，artifact存到storage(S3/本地)。
- 单容器QPS/带宽测：用wrk/hey打/content/接口测QPS；用大文件下载测带宽；发现单容器带宽上限受gunicorn worker数和网卡/磁盘IO限制，水平扩展content app。
- 重构方案：本地cache层(nginx/proxy cache命中热点)+pulp多副本+CDN。跨区域用pulp的replicate功能或对象存储跨区复制。
- 诚实边界：这是"调研+分析"阶段产出，不是已上线运维，要如实说"我做了架构分析和压测，选型落地中"。

Q2：集群稳定性怎么保障？
答题要点：
- 通用思路（简历网络栈调优经验迁移）：监控 Prometheus(节点CPU/内存/网卡/磁盘IO/容器指标) + alert；容量规划(带宽/QPS水位)；混沌演练(kill进程/断网/磁盘满)。
- 内核层：合理设vm.dirty_ratio/dirty_background_ratio防IO突刺；网络栈参数(net.core.somaxconn/netdev_max_backlog/tcp相关)；cgroup限制单租户资源。
- 调度/亲和：容器绑核避免跨NUMA；CPU manager static policy。
- 诚实：大集群稳定性我是基于内核调优能力推断，不是已有大集群运维实绩，要说明。

Q3：eBPF可观测做了什么？
答题要点：
- 简历：eBPF(bcc/libbpf)是工具，用于调优时trace。具体可讲：
  - bcc的profile/offcputrace/biolatency在调优时定位瓶颈（如15万并发场景看软中断耗时分布）。
  - libbpf写自定义tracepoint/kprobe：比如trace网络栈各层耗时(XDP→netif_receive_skb→ip_rcv→tcp_v4_rcv)定位<100us花在哪。
  - 可观测迁移到集群：用bpftrace/pixie在k8s里trace pod网络/文件IO，无需改业务代码。
- 诚实：eBPF我用于一次性trace定位，没做成长驻可观测平台；但懂bcc/libbpf开发，能给k8s可观测出方案。

Q4：线上内核panic怎么定位？crash怎么用？
答题要点（亮点：解过架构bug）：
- 流程：内核panic配kdump，crash vmcore → crash工具分析。
- crash命令：bt(backtrace)、ps(进程)、kmem(内存)、struct(结构体)、dev(设备)、log(dmesg)、mod(模块)。
- 简历案例：
  - 申威io_uring fork io线程段错误：架构代码bug。io_uring fork io线程时架构层(可能是TLB/上下文)处理有问题，定位到架构代码某处缺页/上下文切换。crash看io_uring worker线程栈+架构相关函数。
  - 随机bit翻转→do_page_fault：页表项被改，crash看页表+对比正常页表项。
  - ARM二层转发软中断占满CPU：ebt_do_table读写锁+lse原子锁——读写锁拿不到导致软中断忙等CPU打满，定位到ebtables在二层转发的锁竞争。
- 通用：CONFIG_KALLSYMS/DEBUG_INFO要开，否则栈是地址。

Q5：性能调优方法论？火焰图怎么用？
答题要点：
- perf record -F 99 -ag → perf script → flamegraph.pl。看on-CPU火焰图找宽栈(耗时函数)。
- off-CPU火焰图(perf record -e sched:sched_switch)找阻塞——适合"不耗CPU但慢"的场景。
- 简历应用：15万并发场景用火焰图发现某锁/某软中断占比高；bandersnatch同步慢用flamegraph找序列化/IO瓶颈。
- 方法论：先量化(基线→目标)→profile定位top热点→改→再测。避免过早优化。

================================================================================
五、月之暗面 SRE/系统软件 ——线上稳定性/故障定位/热补丁
================================================================================

Q1：线上内核panic怎么定位？(同智谱Q4，重点强化)
答题要点：
- kdump+crash是标配。crash bt看栈，先分清是硬件(mce/edac报错)、驱动(某.ko栈)、还是核心内核(调度/内存)。
- 简历三案例可讲：bit翻转(硬件)、io_uring架构bug(核心)、ebt锁竞争(子系统)——体现能定位不同层。
- 线上实操：保留vmcore→先恢复(重启/切备机)再分析；如果是已知bug用kpatch热修避免重启。
- 时效：线上要求快，所以要有monitor告警+dmesg实时采集+vmcore自动上传分析。

Q2：kpatch灰度回滚怎么做？
答题要点（简历产品化亮点）：
- 灰度：rpm包分发→先在测试机load→线上灰度N台观察→全量。
- 回滚：livepatch支持disable( echo > /sys/kernel/livepatch/<name>/disable )，瞬间切回旧函数。这是热回滚。
- kpatch局限：不能改数据结构布局(只改函数逻辑)、改不了init类已调用函数、依赖CONFIG_LIVEPATCH。
- 产品化：仿红帽rpm spec打包，把patch构建(kpatch-build)、签名、分发做成流水线；版本管理。
- 线上价值：避免内核重启导致的连接中断/业务抖动，对SRE是核心能力。

Q3：线上故障定位全流程？
答题要点：
1. 告警→确认影响面(单机/集群/全量)。
2. 现场保留：core dump、dmesg、perf snapshot、当时metric。
3. 分类：应用层(panic栈在业务so) / 内核层(栈在.ko或vmlinux) / 硬件(mce/dmesg有hardware error) / 网络(丢包/重传/中断)。
4. 临时恢复：重启/切流量/降级/回滚发布/热补丁。
5. 根因：crash/perf/ftrace/eBPF。
6. 复盘+预防(监控/限流/混沌演练)。
- 简历工具链：ftrace/perf/eBPF/crash/火焰图——SRE定位故障的完整武器库，强调都用过且解过真bug。

Q4：eBPF在稳定性/可观测的应用？
答题要点：
- 在线trace：kprobe/uprobe动态插桩，不重启不改码看内核/进程内部状态。适合线上"为什么会慢/卡"。
- 网络：tc/XDP做流量统计/限流；bcc的tcplife/connectsl统计连接。
- 安全审计：tracepoint trace execve/capable做行为审计。
- 可观测平台：bpftrace/pixie/kindling在k8s采集pod级网络/IO指标，无需instrumentation。
- 诚实：我用eBPF做trace定位(调优时)，没搭长驻可观测平台，但懂原理能评估选型。

Q5：内存管理调优线上实践？
答题要点：
- OOM：oom_score_adj调优先级；cgroup memory.limit保护关键服务；oom后看/proc/<pid>/oom_score定位谁被杀。
- 内存回收：vm.swappiness(数据库设低)、dirty_ratio防IO突刺；cgroup memory后台回收(memory.high)优于硬限(memory.max)触发OOM。
- SLAB/SLUB：/proc/slabinfo看内核对象占用，dentry/inode cache大时手动drop_caches(慎用)。
- 大页：透明大页THP对大内存进程省页表，但碎片化时可能反优化；数据库建议显式hugepage。
- 简历对应：memcg滑动平均统计vs测试、dim内存完整性页对齐——体现对内存统计和完整性的底层理解。

================================================================================
六、零一万物 AI工程效能 ——工程工具链/CI/CD
================================================================================

Q1：100T软件源重构和CI/CD有什么关系？
答题要点：
- 软件源/包仓库本质是"工程依赖供给链"，类似内网PyPI/npm镜像，是AI工程效能的基础设施。
- 价值：模型训练依赖几百个pip包，镜像源不稳/慢直接影响训练任务拉起速度和CI成功率。我做100T重构的经验直接迁移到"给AI平台搭高可用依赖源"。
- CI/CD角度：软件源同步要自动化(定时bandersnatch/pulp sync)、增量同步失败要重试告警、发布版本要可回滚——这些就是CI pipeline要考虑的。
- 诚实：简历偏"源/包仓库"，纯CI/CD流水线(GitLab CI/Jenkins)经验要说明是从软件源运维延伸，不能夸大。

Q2：CI/CD流水线怎么做？镜像构建加速？
答题要点（迁移经验，要诚实标注）：
- 流水线分层：lint→unit test→build→integration test→deploy(staging→prod灰度)。
- 加速：
  - 构建缓存：docker layer cache、pip cache(pulp/内网镜像)、ccache(c代码)。
  - 并行：矩阵构建(多python版本/多架构arm64+amd64并行)。
  - 增量：只build变更的layer；monorepo按包变更触发对应CI。
  - distroless/多阶段构建减小镜像。
- 镜像分发：内网registry多副本+pulp容器插件；大镜像用stargz/nydus懒加载。
- 简历迁移点：100T软件源的"多副本+cache+带宽压测"经验直接用于registry设计。

Q3：CI里怎么验证内核级改动？
答题要点：
- 内核改动CI：交叉编译多架构(arm64/x86/申威)→QEMU跑LTP/自研回归用例→部署到测试机跑perf基准对比。
- 简历对应：4.19回合高版本bpf/btf~1000补丁解决校验出错致近百用例失败——这就是CI回归的实战，补丁回合后用例全过才是完成标准。
- 工程化：补丁回合要自动化(patch系列apply+build+test+report)，可基于patchwork/gitolite搭。
- 可讲bpf/btf回合坑：BTF生成依赖pahole版本、CO-RE相关宏变更要批量改用例。

Q4：工程效能/开发者体验怎么做？
答题要点：
- 诚实：简历偏底层，DE/工程效能是从软件源、内核工具角度切入。
- 可讲：开发环境标准化(统一镜像+工具链)、本地开发与CI一致性(devcontainer)、慢操作前移到本地(本地跑lint/test避免CI排队)。
- 简历可迁移：内核开发用的ftrace/perf/eBPF可包装成"开发者性能分析自助工具"；crash分析经验做成"vmcore自动分析"脚本降低排障门槛。
- 强调：我懂底层痛点(内核调试慢、源同步不稳)，能从开发者真实痛点做工具，而不是堆工具。

Q5：线上稳定性/热补丁在工程效能里的位置？
答题要点：
- kpatch产品化经验可做成"热补丁即服务"：开发者提patch→CI构建kpatch rpm→灰度分发→监控→回滚，全流程自动化。这就是工程效能+稳定性的交集。
- 价值：把"重启机器打内核补丁"这个高成本操作变成"分钟级热补丁"，大幅降低内核bug修复对业务的影响——直接提升研发和运维效能。
- 诚实：这套流水线是简历kpatch产品化的自然延伸，落地程度要说清(我做了打包分发，全自动化流水线是设计层面)。

================================================================================
通用高频技术问题（所有岗位都会问）
================================================================================

G1：内核锁机制——读写锁/自旋锁/RCU
答题要点：
- 自旋锁(spinlock_t)：临界区短、不能睡眠、持锁时抢占关闭(UP)/多核自旋忙等。中断上下文要用spin_lock_irqsave/save关中断防死锁(中断里拿同锁会自死锁)。简历ebt_do_table就是读写锁版本。
- 读写锁(rwlock_t)：多读单写，读多写少场景比自旋锁并发高。但写者饥饿问题(读多时写拿不到)； reader-writer lock在某些实现里writer也starve。ebt_do_table读写锁在二层转发高并发下软中断拿不到锁→CPU打满，就是rwlock在极端读压力下的痛点，解决方案是改成更细粒度锁或RCU。
- RCU(Read-Copy-Update)：读路径几乎零开销(无锁，只是禁抢占/标记)，写者复制一份改完再原子替换指针，旧数据等所有读者退出(grace period)后释放。适合"读极多写极少"的数据结构(路由表、namespace)。关键概念：grace period(synchronize_rcu)、rcu_read_lock/unlock、rcu_assign_pointer/rcu_dereference。
- 互斥锁(mutex)：可睡眠，进程上下文用，比自旋锁开销大(调度)但不在临界区时让出CPU。
- 顺序锁(seqlock)：读时查sequence号，写时++，读后比对，不一致重读。适合写少读多且读容忍重试(如jiffies)。
- 简历迁移：ebt读写锁痛点→讲为什么rwlock在高并发读时会成瓶颈(写饥饿/缓存行竞争)→RCU如何解决(读无锁)。这是简历案例升华成的"锁选型"能力。

G2：进程调度/中断上下半部
答题要点：
- 进程调度：CFS(完全公平调度)用红黑树按vruntime排序，选最小vruntime进程运行；nice值影响vruntime增长速率；实时策略(SCHED_FIFO/RR)优先级高于CFS。调度延迟受sched_min_gran/sched_latency限制。
- 实时性：PREEMPT_RT让内核可抢占(自旋锁改rt_mutex、线程化中断)；普通内核只在preemption point抢占。isolcpus把核从调度器移除，独占给任务。
- 中断上下半部：
  - 上半部(硬中断/Top Half)：关中断、极快、只做紧急活(如从网卡FIFO拷到skb、ack硬件)，不能睡眠。
  - 下半部(Bottom Half)：延后处理，可开中断。三种机制：
    - 软中断(softirq)：静态定义(NET_RX/TX/TIMER等)，同类型可多核并发执行，性能最高但不能睡眠、不能阻塞。
    - tasklet：基于软中断，同类型串行(单核跑)，2.6后逐渐被弃用。
    - workqueue：进程上下文，可睡眠，适合要睡眠的延后工作(如IO)。
  - threaded_irq：把中断处理线程化，既可抢占又可睡眠，是现代推荐方式。
- 简历应用：
  - 15万并发软中断绑核就是针对NET_RX软中断；软中断在同核上不会重入但跨核会，绑核控制并发。
  - idle中断接收=上半部读FIFO+下半部分包(软中断或workqueue)。
  - 网络栈NAPI本质是软中断轮询，poll机制减轻中断风暴。
- 可追问"为什么不用tasklet"：tasklet串行性能差且社区deprecated，新代码用threaded_irq或workqueue。

G3：内存管理——伙伴系统/SLAB/页对齐
答题要点：
- 伙伴系统(Buddy Allocator)：管理物理页(order 0=4KB到order 10=4MB)，按order合并/拆分。外碎片问题(大块连续内存申请不到)→用/proc/buddyinfo看各order空闲。解决外碎片靠compaction/migrate_type(CMA/MOVABLE)。
- SLAB/SLUB/SLUB：伙伴系统粒度太粗(页级)，内核小对象(如task_struct/file/inode)用slab分配器——对象池，按size分级，per-CPU cache加速。/proc/slabinfo看对象数。SLUB是现代默认(比SLAB简单、调试好)。简历memcg相关统计和slab有关。
- 伙伴系统+slab关系：伙伴给页，slab在页上切小对象。kmalloc走slab，alloc_pages走伙伴。
- 页对齐(简历dim内存完整性)：
  - 物理页4KB对齐是伙伴系统基本单位。大页(2MB/1GB)走hugetlb或THP。
  - 内存完整性检测(如dim)要按页对齐：检测pattern要填满整页，跨页检测会因不同页状态干扰不准；对齐到页边界才能精确比对。
  - 简历dim内存完整性页对齐：dim工具校验时要求被测内存页对齐，否则校验范围与实际页边界不重合，会误报或漏报。
- 内存回收/压缩：kswapd后台回收；direct reclaim阻塞回收(慢)；compaction整理碎片腾连续页。OOM killer是最后手段。
- memcg(简历memcg滑动平均统计)：cgroup内存统计，滑动平均是统计负载方式(衰减历史值)。memcg统计per-cgroup的rss/cache，滑窗平均用于容量规划。
- 可追问"SLAB vs SLUB"：SLAB多级per-CPU数组队列复杂、对NUMA优化好但开销大；SLUB精简、单层per-CPU partial list、调试用/sys/kernel/slab/。性能SLUB略优，所以默认。

================================================================================
附：答题通用原则
================================================================================
1. 真实优先：简历没做过的(如PREEMPT_RT内核改、大集群SRE实战)坦承"理解原理但没做过项目"，不要编。
2. 案例支撑：每个技术点尽量挂到简历真实案例(15万并发、ebt锁、io_uring架构bug、kpatch产品化、100T软件源)。
3. 边界感：说明"我做了X，没做Y"——如kpatch做产品化不做框架开发，100T是调研分析不是已运维。
4. 可追问：预期面试官追问细节，准备好二级问题(如AXI HP burst长度、slab per-CPU cache结构、RCU grace period实现)。
5. 跨岗迁移：BSP经验可迁移到机器人(传感器bring-up)，网络调优经验可迁移到Infra/SRE(集群性能)，内核调试经验可迁移到工程效能(热补丁即服务)。
================================================================================
