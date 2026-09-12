---
published: true
layout: topic
title: MCP 与扩展层供应链安全
subtitle: 当 AI Agent 的能力扩展层成为攻击面——准入治理、事件复盘与持续观测
date: 2026-08-22
updated: 2026-09-12
status: 待开始
keyword: MCP
categories: [AI安全, 供应链安全]
tags: [AI 安全, 供应链安全]
dao_summary: "MCP 让 Agent 获得工具，也让外部代码获得进入企业内网的通道。\n扩展能力的信任模型如果不重建，Agent 的每一个新能力，都是一条新的入侵路径。\n课题待开始——此为初步思考，随研究推进持续修订。"
fa_summary: "拟按五步构建企业内 AI 客户端（Skills / MCP）的准入治理工作流：提交登记 → 静态扫描 → 动态行为观测 → 准入评审 → 撤销通道。\n框架整理中，细节随课题推进完善。"
qi_summary: "外部依据暂收 MCP 官方安全最佳实践一处权威来源。\n更多工具、规范与研究样本，随课题推进陆续补充。"
dao:
  - title: 能力扩展层即攻击面
    text: MCP 让 Agent 获得工具的同时，也让外部代码获得了进入企业内网的通道——扩展能力的信任模型如果不重建，Agent 的每一个新能力都是一条新的入侵路径。（初步思考，随研究推进持续修订）
    type: 原创
    platform: 本课题
fa:
  - title: 提交-扫描-准入工作流
    text: 企业内 AI 客户端（Skills / MCP）的准入治理框架：提交登记、静态扫描、动态行为观测、准入评审与撤销通道。（整理中）
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
links:
  - platform: 公众号
    form: 完整版长文 · 第一个案例（filesystem-pro-plus 事件复盘）
    url:
    note: 待发布，完成事件来源核查后上线
assets:
  - name: MCP / Skills 安全扫描流程
    desc: 企业内 AI 客户端（Skills / MCP）的提交-扫描-准入工作流
    location: 工作实践，待整理
findings:
  known: []
  open:
  - filesystem-pro-plus 事件的完整时间线与来源核查——立项后的第一项工作，核查完成前不发布事件结论
  - 企业内 AI 客户端（Skills / MCP）提交-扫描-准入治理工作流的实际有效性验证
  - 扩展层漏洞向框架层迁移的路径测绘，与「Agent 框架安全」课题交叉（该课题已证实控制面与凭据维度的方法论）
  - MCP 生态的持续观测：新增 CVE、恶意服务器样本与官方规范演化的跟踪机制
changelog:
- date: '2026-09-12'
  action: 课题定位调整：标题从单一事件命名（MCP 供应链攻击第一枪）改为问题域命名（MCP 与扩展层供应链安全），filesystem-pro-plus 复盘调整为第一个案例，补研究议程。
---

研究进行中，本页为占位。正式内容随首发同步上线。
