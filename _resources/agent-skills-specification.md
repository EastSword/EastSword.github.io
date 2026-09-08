---
title: Agent Skills Specification
source: agentskills.io
author: Anthropic
published: "2025"
date: 2026-09-07
type: 官方规范
topics: [ai-agent-governance]
external_url: https://agentskills.io/specification
reason: Skill 是行为与软件供应链的混合体；规范中 allowed-tools 是实验性元数据，不能当跨产品权限沙箱——这是实测验证过的关键差异点。
---

Agent Skill 的开放规范：SKILL.md 搭配脚本与渐进式披露的目录结构，让 Skill 成为可分发的"行为包"。安全视角的关键提醒：`allowed-tools` 属实验性元数据，各家客户端对它的强制程度不一，不能当作跨产品的权限沙箱来设计防线；Skill 的治理要按"软件供应链 + 行为定义"双重身份处理——准入审批、来源锁定、可撤销，与代码依赖管理同等级别。
