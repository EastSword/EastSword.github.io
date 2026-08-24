---
layout: topic
title: MCP 供应链攻击第一枪
subtitle: filesystem-pro-plus 事件复盘——当 AI Agent 的能力扩展层成为攻击面
date: 2026-08-22
updated: 2026-08-25
status: published
keyword: MCP
links:
  - platform: CSDN
    form: 完整版文章
    url: https://blog.csdn.net/qq_37865996/article/details/163958306
    note: 首发完整复盘
  - platform: 公众号
    form: 长文（东方隐侠安全团队）
    url:
    note: 待分发
  - platform: FreeBuf
    form: 投稿版
    url:
    note: 待投稿
assets:
  - name: MCP / Skills / MCP 安全扫描流程
    desc: 企业内 AI 客户端（Skills / MCP）的提交-扫描-准入工作流
    location: 工作实践，详见公众号相关文章
---

2026 年 8 月 13 日，首个大规模落地的 MCP 供应链攻击被确认：typosquat 手法伪装的恶意 MCP 服务器 `filesystem-pro-plus` 一周内被下载 14,300 次，加载后向外回传键盘记录、剪贴板内容、对话摘要与 OAuth token——47 个组织沦陷，其中包括某前沿模型实验室的内部 Agent。

最讽刺的是发现途径：某财富 500 强研究员在 pastebin 里看到了自己的凭证。

这个话题拆解了三个层面：**事件本身**的时间线与攻击链、**生态结构性缺陷**（11,400+ 个 MCP 服务器，无签名、默认无认证、无沙盒、无发布审核、无撤销机制）、以及**企业侧的应对**——如何对员工 AI 客户端做 Skills/MCP 的提交、扫描与准入管理。

后续研究：MCP 供应链话题与「身份攻击七路径」0x12 节的 AI Agent 身份问题相互印证——Agent 的认证就是它的配置文件，而配置文件是会被人偷换的。
