---
title: How we contain Claude（Anthropic 工程博客）
source: anthropic.com/engineering
author: Anthropic 工程团队
date: 2026-09-07
published: "2026-05-25"
type: 工程实践
topics: [ai-agent-governance]
external_url: https://www.anthropic.com/engineering/how-we-contain-claude
reason: 一线厂商公开的 Agent 遏制机制工程叙述：隔离层级、权限边界与失效假设，适合与我们的实测结果交叉验证。
---

Anthropic 工程团队撰写的 Claude 遏制（containment）机制说明，讲清了多层隔离的思路：每层边界各自能挡什么、挡不住什么，以及当模型输出不可信时系统如何兜底。对我们的价值有二：其一，它是"模型说'不做'不等于系统'做不了'"这一判断的最佳官方注脚——强制防护必须依赖沙箱、凭据代理与服务端授权，而非模型自觉；其二，作为持续的官方技术讨论来源，适合长期追踪版本变化，并与我们的插件实测结果交叉验证。属于"官方声明"级证据，引用时注明。
