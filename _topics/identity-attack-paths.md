---
published: true
layout: topic
title: 身份攻击七路径与ITDR
subtitle: 密码对，MFA通过，零告警——合法认证身份的攻击面全景与检测之道
date: 2026-08-25
updated: 2026-08-26
status: publishing
keyword: ITDR
tags: [身份安全, 企业安全, 检测工程]
links:
  - platform: 公众号
    form: 上篇《登录认证安全（上）MFA能确保登录一定安全？未必》
    url:
    note: 待发布（D0上午，三篇一次推送）
  - platform: 公众号
    form: 中篇《登录认证安全（中）不偷密码的入侵》
    url:
    note: 待发布（与上篇同批）
  - platform: 公众号
    form: 下篇《登录认证安全（下）零告警的入侵怎么抓》
    url:
    note: 待发布（与上中篇同批）
  - platform: CSDN
    form: 完整版《剖析合法认证身份攻击路径，ITDR有何应对效果》
    url: https://blog.csdn.net/qq_37865996/article/details/163982749
    note: 已发布（沿用原版）
  - platform: FreeBuf
    form: 管理层视角版《登录零告警：七条身份攻击路径复盘与ITDR建设优先级》
    url:
    note: 待投稿（审核3-7天不受控）
videos:
  - platform: B站
    form: 10分钟讲解（Uber案+零告警原理）
    url:
    note: 脚本已备，待录制（D0晚间8-10点，可延1-2天）
  - platform: 视频号
    form: B站片60-90s切片
    url:
    note: 与B站同素材，间隔1-2小时
assets:
  - name: ITDR检测基线速查
    desc: 九信号表+管理层十问，公众号回复ITDR获取
    location: 公众号（回复ITDR）
    url:
  - name: ITDR检测基线矩阵完整资产包（v1.1）
    desc: 五条KQL规则、七路径防御速查、带验收标准的路线图、泄露凭证情报源清单、NHI检查项
    location: 知识星球
    url:
---

## 核心问题

密码是对的，MFA是本人点的，登录来自合法设备——认证链路全绿放行，告警数量为零，但攻击者已经进来了。Gartner的结论：约80%的数据泄露源于凭证泄露或滥用，ITDR品类因此建立。Healsecurity对泄露infostealer日志的统计更直接：约117万条日志同时包含登录凭证与活体会话Cookie，重放即入，MFA连出场机会都没有。

MFA挡住的是门口的小偷，挡不住拿着钥匙的主人。

## 覆盖内容

- **凭证层级L1-L6**：从密码、OTP种子、会话Cookie、OAuth令牌到签名密钥与设备身份秘密——攻击者偷到哪一层，MFA就从哪一层失效
- **七条攻击路径**：AiTM反向代理（Evilginx双TLS中继与Set-Cookie拦截）/ Infostealer（浏览器存储加密的信任根缺陷）/ MFA疲劳与注册劫持（Uber事件）/ SaaS本地账号（Snowflake检索即瞄准）/ 签名密钥伪造（Storm-0558伪造令牌）/ OAuth恶意授权（GiftedOutlaws行动）/ 恢复流程劫持（MGM十亿美元事件）——每条带技术拆解与ATT&CK映射，防御段落写落地卡点与推进顺序，不给正确但不可执行的清单
- **传统检测为何失明**：暴力破解、异地登录、设备信任、进程检测四类思路对"合法登录"的集体失效分析
- **ITDR落地**：四类数据源、九个检测信号、五条可粘贴的KQL规则、响应闭环
- **NHI与AI Agent时代**：结合AI安全治理一线实践（VPN出口识别AI客户端、Skills与MCP配置扫描）观察非人类身份的真实风险，而非只引用行业报告数字
- **管理层十问**：拿去开评审会的立项依据
