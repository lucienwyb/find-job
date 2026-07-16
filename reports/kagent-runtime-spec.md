# kagent — 自研轻量Agent Runtime项目规格书

> 第30轮产出。这是转Agent编排架构岗的硬通货(前29轮论证确认:没自研runtime项目投了被当套壳用)。最大化复用候选人7年内核功底(eBPF/cgroup/调度),3月出MVP。

## 项目定位
`kagent` — 内核级可观测的轻量Agent Runtime。非套壳,自己设计"agent怎么可靠跑":状态机引擎+工具协议+调度+eBPF观测。Python主、Rust写调度核心。2-3月MVP。

## 核心模块(逐个:职责+技术选型+如何复用内核功底)

1. **图执行引擎**(类LangGraph,自实现)：节点=函数/LLM调用,边=条件路由。DAG+循环(ReAct),状态存SQLite做checkpoint。选型:纯Python dataclass+dict,不引框架。复用:把节点调度建模成内核调度器——优先级队列、抢占点、超时取消。

2. **工具调用协议**：实现简化MCP server+client(JSON-RPC over stdio)。工具注册schema,agent发tool_call,runtime校验+执行+超时。复用:工具进程隔离用namespace/subreaper管(他熟)。

3. **记忆与上下文压缩**：短期=对话窗口滑动,长期=SQLite向量(sqlite-vec)+摘要。超token触发摘要压缩。复用:类内存reclaim策略,LRU+工作集。

4. **规划算法**：ReAct(思考-行动-观察循环)起步,第二月加Plan-Execute(先拆步再执行)。输出结构化plan JSON。

5. **失败重试与回滚**：节点失败按策略重试(指数退避);checkpoint支持回退到上一个成功节点重跑。复用:事务/日志思路,像journal。

6. **并发与资源调度** ★杀手锏1：Rust写`ksched`核心——每agent一个task,限流(令牌桶)/超时熔断/并发数上限。**用cgroup v2给每个agent套CPU+内存限额**,OOM直接kill防失控。复用:他cgroup/调度/CFS直接迁移,这是别人做不到的硬隔离。

7. **可观测性** ★杀手锏2：**基于eBPF的agent行为trace**——用bcc/libbpf采集LLM调用延迟、工具调用次数、token消耗、系统调用,挂到trace span上。别人用OpenTelemetry埋点,他能看到syscall级。复用:他bpf回合+perf直接迁移。

8. **评估闭环**：offline跑测试集,记成功率/平均步数/成本/延迟,grid输出对比表。

## 技术栈
Python 3.11(主)+Rust(ksched/限流核心,PyO3绑定)。LLM:OpenAI兼容API(本地用qwen)。存储:SQLite+sqlite-vec。trace:eBPF+OpenTelemetry导出。**无LangChain/LangGraph依赖(体现非套壳)**。

## 杀手锏(差异化竞争力)
- **eBPF agent trace**：syscall级观测LLM调用链,定位"卡在哪"——别人埋点到函数,他到内核事件。面试直接demo火焰图。
- **cgroup硬隔离**：agent跑飞被OOM kill,不拖垮宿主。体现可靠性架构思维。

## 里程碑(10周)
- W1-2：图引擎+节点抽象+hello world agent跑通。博客1:《不用LangGraph,100行写个agent引擎》
- W3-4：MCP server/client+3个工具(exec/python/search)。博客2
- W5-6：Rust ksched限流+超时+checkpoint回滚。博客3:《把cgroup调度搬进agent runtime》
- W7-8：eBPF trace探针+成本/延迟面板。博客4 ★核心卖点
- W9-10：端到端demo+评估集+README。博客5
- GitHub:`kagent`,每2周tag,README放架构图+benchmark。

## 端到端demo场景
**自动化内核bug triage agent**：agent调3个工具——①`dmesg_parser` ②`crash_analyzer`(他crash经验) ③`ebpf_probe_gen`(动态生成bcc脚本采集现场)。输入一段panic log,agent规划→抓关键帧→匹配已知模式→给修复建议。工具本身就是他内核技能的封装,面试官秒懂壁垒。

## 简历bullet(3行,体现架构能力非coding)
- 设计并实现轻量Agent Runtime(状态机引擎+MCP工具协议+Rust调度核心),不依赖LangChain,支持checkpoint回滚与并发限流
- 用eBPF实现syscall级agent行为trace,LLM调用/工具/延迟全链路可观测,定位效率优于纯埋点方案
- 用cgroup v2对agent做CPU/内存硬隔离,单agent失控可被OOM kill而不影响宿主,保障多租户可靠性

## 为什么这是硬通货
照此做,3月出MVP,面试直接demo eBPF火焰图+cgroup隔离——这是内核背景转Agent架构岗的唯一硬通货路径。把"7年底层"从"要扔的包袱"变成"agent runtime的差异化壁垒",直接对冲第27轮"训推Infra是换皮底层"的担忧(这里底层是杀手锏不是日常活)。
