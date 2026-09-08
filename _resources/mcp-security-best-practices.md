---
title: MCP Security Best Practices（2025-11-25 版）
source: modelcontextprotocol.io
author: MCP 规范社区（Anthropic 发起）
published: "2025-11-25"
date: 2026-09-07
type: 官方规范
topics: [ai-agent-governance, mcp-supply-chain]
external_url: https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices
reason: 官方对令牌透传、混淆代理、SSRF、会话劫持等风险的防护要求，是 MCP 准入评审清单的一手依据。
---

MCP 官方安全最佳实践，逐条说明服务器实现者与运营方应满足的要求：不要混淆代理（混淆代理人问题）、不要向下游透传用户 token、校验重定向目标防 SSRF、会话标识的生命周期管理、DNS 解析的 TOCTOU 竞态等。我们的 MCP 准入与运行时控制设计（HTTP 与 stdio 分别设防、下游独立令牌、本地回环接口检查）以此为对齐基线，再叠加企业侧的网络出口管控。
