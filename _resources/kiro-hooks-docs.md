---
title: Kiro Hooks 官方文档（triggers / actions / exit codes）
source: kiro.dev
author: Kiro 官方文档
date: 2026-09-07
published: 持续更新
type: 官方文档
topics: [ai-agent-governance]
url: https://kiro.dev/docs/hooks/types/
reason: 用户态 Hook 的阻断与超时语义、IDE 与 CLI 的事件支持差异，评估插件类管控能力前先读这份。
---

Kiro Hook 机制的三份核心文档：triggers（事件类型与工具匹配，https://kiro.dev/docs/hooks/types/ ）、actions（Shell action 的执行与阻断语义，https://kiro.dev/docs/hooks/actions/ ）、exit codes（CLI Hook 的退出码契约，https://kiro.dev/docs/reference/exit-codes/ ）。我们在对 Kiro 安全插件安装包做静态源码分析时，以此核对插件声明的拦截能力与真实实现是否一致，并确认了两个边界：IDE 与 CLI 支持的事件集不同；用户态 Hook 对本机管理员攻击者不构成可靠边界。原文档只讲能力，不讲安全边界——这个缺口正是实测要补的。
