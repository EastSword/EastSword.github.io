---
title: MCP Authorization 规范（2025-11-25 版）
source: modelcontextprotocol.io
author: MCP 规范社区（Anthropic 发起）
published: "2025-11-25"
date: 2026-09-07
type: 官方规范
topics: [ai-agent-governance, mcp-supply-chain]
url: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
reason: 企业 MCP 准入的授权边界一手依据：token 面向本服务、不透传、动态客户端注册等约束都出自这里。
---

MCP 官方规范中定义 HTTP 传输授权流程的部分：授权服务器、动态客户端注册、token 的目标约束（面向本服务而非下游）、资源指示器等。企业落地时最关键的两条结论直接来自这份文本——授权 token 只对当前 MCP 服务有效，不能当万能凭据透传给下游；stdio 与 HTTP 两条通道的信任模型不同，需要分别设防。阅读建议：与 Security Best Practices 搭配，先读这份定边界，再读最佳实践补防护细节。
