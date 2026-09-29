---
published: true
layout: topic
title: MCP 与扩展层供应链安全
subtitle: AI Agent 能力扩展层的供应链安全：准入治理、事件复盘与持续观测
date: 2026-08-22
updated: 2026-09-29
status: 研讨中
keyword: MCP
categories:
- AI安全
- 供应链安全
tags:
- AI 安全
- 供应链安全
- Agent 记忆
- 发布管道
dao_summary: '扩展组件既处理 Agent 的上下文，也在宿主环境中执行代码。研究范围包括 MCP、Skills、插件及记忆库。

  首个已发布案例为 MemTensor 投毒复盘：从发布链路、运行时加载和记忆数据三个方面分析风险。该案例属于扩展层供应链事件，不作为 MCP 协议漏洞定性。'
fa_summary: '把版本来源核对、构建与发布脚本审查、运行时行为观测连成一条检查路径。

  准入流程仍按提交登记、静态扫描、动态观测、评审与撤销组织；MemTensor 案例用于补充检查项，流程有效性仍需实践验证。'
qi_summary: 保留 MCP 官方规范入口，新增本站 MemTensor 完整复盘。事件资料与证据争议集中在文章参考来源及文末说明中，后续按原始材料继续核对。
dao:
- title: 扩展代码与宿主权限
  text: 插件或记忆库接入后，其代码可能使用宿主进程的文件、网络与环境变量权限。组件来自官方发布渠道，不等于其代码和发布链路未经篡改。
  type: 原创
  platform: 本课题
- title: 安装与使用是不同的执行阶段
  text: MemTensor 文章梳理了导入、网关启动和记忆调用时的载荷启动路径。围绕安装脚本的检查不能代替使用阶段的行为观测。
  type: 原创
  platform: 本课题
- title: 记忆组件的数据边界
  text: 记忆组件同时接触用户输入、历史上下文和运行环境。应区分提示注入造成的行为偏转与组件代码投毒，两者的入口、证据和排查方式不同。
  type: 原创
  platform: 本课题
fa:
- title: 提交、扫描、准入与撤销
  text: 为 MCP、Skills 和插件登记来源、版本、宿主权限与负责人；结合静态审查和动态行为观测做准入评审，并保留版本撤销与替换路径。此工作流仍待企业环境验证。
  type: 原创
  platform: 本课题
- title: 发布版本与源码对应性核对
  text: 把 registry 版本、包内容、仓库 commit、tag 和发布记录一起核对。对不一致项保留证据并调查，不能只依赖版本号、官方账号或构建来源标识作出信任判断。
  type: 原创
  platform: 本课题
- title: 发布脚本与凭据使用审查
  text: 依据文章中的攻击链分析，将构建后端变更、发布校验脚本、环境变量跨步骤传递及凭据使用位置纳入审查。PyPI CI helper 的实际触发存在争议，不能把代码存在直接当作执行证据。
  type: 原创
  platform: 本课题
- title: 使用阶段的行为观测
  text: 把观测窗口延伸到库导入、插件启动和记忆调用，关联子进程、凭据文件访问与出网行为，并结合基线判断异常。
  type: 原创
  platform: 本课题
qi:
- title: MCP 官方安全最佳实践
  text: MCP 官方的安全实践文档，供应链风险的权威参考。
  type: 转载
  platform: 官方文档
  url: https://modelcontextprotocol.io/
  desc: Model Context Protocol 官方规范与 Security Best Practices
  stars: 5
- title: MemTensor 案例资料索引
  text: 本站文章末尾集中列出事件分析、预警与证据限定；CI helper 触发、后续载荷和再发布是否发生需继续核对。
  platform: 本站复盘
  url: /articles/memtensor/
  desc: 参考来源与文末证据说明
links:
- platform: 官网
  form: 完整复盘 · MemTensor 记忆工具链投毒
  url: /articles/memtensor/
  note: 已发布 2026-09-29：发布管道、import 时执行与记忆组件风险
- platform: 公众号
  form: 待核查案例 · filesystem-pro-plus 事件复盘
  url: null
  note: 待发布，完成事件来源核查后上线
assets:
- name: MCP / Skills 安全扫描流程
  desc: 企业内 AI 客户端（Skills / MCP）的提交-扫描-准入工作流
  location: 工作实践，待整理
findings:
  known:
  - 本文归档的 MemTensor 案例覆盖 npm 插件与 PyPI 记忆库，研究对象是 Agent 扩展组件供应链，不是 MCP 协议漏洞。
  - 据文章所引样本分析，载荷启动点包括 Python 导入和插件运行路径；安装阶段的检查不能覆盖全部执行路径。
  - 据文章分析，记忆调用路径把 prompt 文本传入子进程环境。该行为需要纳入数据影响评估，但不等同于已证明全部 prompt 均被外传。
  - 版本、源码与发布记录的对应关系是调查入口；官方发布身份和版本锁定不能单独证明包内容安全。
  open:
  - MemTensor PyPI CI helper 的实际触发路径：文章记录了 register() 调用方面的分析分歧，需要进一步取证。
  - sckit 后续载荷的具体行为及再发布是否实际发生；文章中的静态字符串证据不能替代运行证据。
  - 记忆调用中的 prompt 传递实际造成多大范围的数据外泄，仍需受影响环境的日志和取证材料。
  - filesystem-pro-plus 事件的完整时间线与来源核查；保留为待核查案例，未据此发布事件结论
  - 企业内 AI 客户端（Skills / MCP）提交-扫描-准入治理工作流的实际有效性验证
  - 扩展层漏洞向框架层迁移的路径测绘，与「Agent 框架安全」课题交叉（该课题已证实控制面与凭据维度的方法论）
  - MCP 生态的持续观测：新增 CVE、恶意服务器样本与官方规范演化的跟踪机制
changelog:
- date: '2026-09-29'
  action: 归档 MemTensor 完整复盘为首个已发布案例，状态改为研讨中；补道法术器、阅读路径与证据边界，保留 filesystem-pro-plus 待核查议程。
- date: '2026-09-12'
  action: 课题定位调整：标题从单一事件命名（MCP 供应链攻击第一枪）改为问题域命名（MCP 与扩展层供应链安全），filesystem-pro-plus 复盘调整为第一个案例，补研究议程。
shu_summary: '从 MemTensor 复盘提炼三组检查：版本与源码是否对应；安装之后的导入、网关启动和记忆调用是否拉起异常进程；组件能读到哪些凭据与业务上下文。

  以下是基于文章整理的审查与排查要点，不表示已完成独立复现或企业环境验收。'
shu:
- title: MemTensor 投毒全链路拆解：import 即执行，发布管道即入口
  publication: true
  text: 首个已发布案例。梳理发布凭据与管道、运行时载荷启动，以及 Agent 记忆组件的数据与权限风险；文章对 CI helper 和再发布能力保留证据限定。
  type: 原创
  platform: 官网
  url: /articles/memtensor/
  desc: 2026-09-29 发布，完整复盘与分角色建议
- title: 版本与执行路径检查
  text: 依据文章整理版本清单和包差异，再分别观察安装、导入、插件启动和记忆调用。记录新进程、文件访问及网络连接，不以安装正常代替运行时检查。
  type: 原创
  platform: 本课题
- title: 受影响范围排查
  text: 核对组件实际运行位置、宿主可读凭据、用户输入与记忆数据的可达范围。结合进程和网络证据判断影响，不能仅由样本具备能力推定所有环境均已发生泄露。
  type: 原创
  platform: 本课题
reading_path:
- 先读 MemTensor 完整复盘，区分发布链路、运行时启动与记忆数据三部分。
- 按本页“法”和“术”的检查项梳理在用扩展组件的版本、权限与行为。
- 发布身份与 tag 治理接着读「Tag 即发布权」；未证实的触发与后续载荷见下方待验证事项。
---

## 研究范围

本课题研究 MCP、Skills、插件及记忆库接入 Agent 时带来的供应链风险，覆盖组件来源、发布身份、运行时权限与数据访问。

## 已发布案例：MemTensor

[阅读完整复盘：MemTensor 投毒全链路拆解](/articles/memtensor/)。文章于 2026-09-29 发布，本页从中整理发布链路审查、运行时观测和记忆数据影响评估三个方向。技术细节与参考来源保留在原文，未在本次归档中重新开展独立取证。

这个案例属于记忆库与插件供应链风险，不能据此推定 MCP 协议存在相同漏洞。原计划中的 filesystem-pro-plus 复盘仍待来源核查。

## 与其他课题的关系

- [Tag 即发布权](/topics/tag-release-power/)：讨论谁能触发发布，以及 tag、源码、产物和发布身份如何对应。
- [Agent 框架安全](/topics/agent-framework-security/)：讨论扩展组件获得的宿主权限是否受沙箱、审批和控制面约束。
- [企业员工使用 AI Agent 的安全管控与监控技术](/topics/ai-agent-governance/)：将扩展准入、运行观测和撤销要求放入企业管理流程。
