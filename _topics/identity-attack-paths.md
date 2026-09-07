---
published: true
layout: topic
title: 身份攻击七路径与ITDR
subtitle: 密码对，MFA通过，零告警——合法认证身份的攻击面全景与检测之道
date: 2026-08-25
updated: 2026-08-29
status: 已结题
keyword: ITDR
categories: [身份安全, 检测与响应]
tags: [身份安全, 企业安全, 检测工程]
dao_summary: "对手已经从“无凭证的入侵者”变成“持有有效凭证的冒用者”——认证链路全绿、告警为零，人已经进来了。凭证有 L1-L6 层级，攻击者永远打当前防护下最弱的一层；约 80% 的数据泄露源于凭证泄露或滥用，身份就是新的边界，防御重心必须转向凭证全生命周期的持续证明。"
fa_summary: "方法论按“枚举攻击面 → 关联检测 → 按卡点推进”三步走：AiTM、Infostealer、MFA 疲劳、SaaS 本地账号、签名密钥伪造、OAuth 恶意授权、恢复流程劫持七条路径全景枚举并逐一映射 ATT&CK；ITDR 用认证日志、特权访问、凭证暴露面、身份配置四类数据源关联九个信号；每条防御写清落地卡点，不给正确但不可执行的清单。"
shu_summary: "落地以可复现为标准：九信号检测规则里五条 KQL 可直接粘贴进 Microsoft Sentinel；AiTM 双 TLS 中继逐步拆解 Evilginx 如何拦截 Set-Cookie、为何 MFA 全程“本人”参与仍然失效；公众号三篇按“为何挡不住 → 不偷密码的入侵 → 零告警怎么抓”层层递进。"
qi_summary: "外部依据收行业事实标准：MITRE ATT&CK 是七条路径技术映射的坐标系，FIDO2 / WebAuthn 给出凭证 L6 层级的答案，Microsoft Sentinel 承载 KQL 检测落地，B站讲解视频完整讲 Uber 案与零告警原理。每条标注来源、原创或转载与推荐星级。"
dao:
  - title: MFA 挡住门口的小偷，挡不住拿钥匙的主人
    text: 身份安全的对手已从"无凭证的入侵者"变成"持有有效凭证的冒用者"——认证链路全绿、告警为零，攻击者已经进来了。防御重心必须从入口校验转向凭证全生命周期的持续证明。
    type: 原创
    platform: 本课题
  - title: 凭证是有层级的
    text: 从密码、OTP 种子、会话 Cookie、OAuth 令牌到签名密钥与设备身份秘密，L1 到 L6 层层向上——攻击者的目标永远是当前防护下最弱的一层，偷到哪层，MFA 就从哪层失效。
    type: 原创
    platform: 本课题
  - title: 身份就是新的边界
    text: Gartner 的结论：约 80% 的数据泄露源于凭证泄露或滥用。当边界防御默认存在，攻击者的最优策略就是直接成为"你"——身份治理的优先级因此高于绝大多数 perimeter 项目。
    type: 原创
    platform: 本课题
fa:
  - title: 七条攻击路径全景枚举
    text: AiTM 反向代理、Infostealer、MFA 疲劳与注册劫持、SaaS 本地账号、签名密钥伪造、OAuth 恶意授权、恢复流程劫持——每条带技术拆解与 ATT&CK 映射，构成合法认证身份攻击面的完整清单。
    type: 原创
    platform: 本课题
  - title: ITDR 检测方法论
    text: 四类数据源（认证日志、特权访问、凭证暴露面、身份配置变更）关联分析，用九个信号覆盖七条路径——检测的对象不是"入侵事件"而是"身份行为的异常"。
    type: 原创
    platform: 本课题
  - title: 落地卡点优先于正确清单
    text: 每条防御措施写清落地卡点与推进顺序——不给正确但不可执行的清单，能落一步是一步。
    type: 原创
    platform: 本课题
shu:
  - title: 九信号检测规则
    text: 覆盖七条攻击路径的九个检测信号，五条 KQL 查询可直接进 Microsoft Sentinel。
    type: 原创
    platform: 本课题
  - title: AiTM 双 TLS 中继拆解
    text: Evilginx 的反向代理如何拦截 Set-Cookie 拿到会话令牌、为何 MFA 全程"本人"参与仍然失效，附复现环境说明。
    type: 原创
    platform: 本课题
  - title: 公众号系列三篇
    text: 上篇讲 MFA 为何挡不住、中篇讲不偷密码的入侵、下篇讲零告警的入侵怎么抓。
    type: 原创
    platform: 公众号
    url: https://mp.weixin.qq.com/s/EM5qM81ApwvRTa8MtvNugA
    desc: 登录认证安全系列上篇：《MFA 能确保登录一定安全？未必》，2026-08-28 发布
qi:
  - title: MITRE ATT&CK
    text: 七条路径逐一映射的技术知识库，检测覆盖度评估的坐标系。
    type: 转载
    platform: MITRE
    url: https://attack.mitre.org/
    desc: MITRE ATT&CK 对抗战术与技术知识库，全球检测工程的事实标准
    stars: 5
  - title: FIDO2 / WebAuthn
    text: 凭证层级 L6 的答案：硬件绑定、源站验证、钓鱼免疫的身份认证标准。
    type: 转载
    platform: FIDO 联盟
    url: https://fidoalliance.org/
    desc: FIDO 联盟官方：FIDO2 与 WebAuthn 标准，抗钓鱼认证的规范出处
    stars: 5
  - title: Microsoft Sentinel
    text: KQL 检测规则的载体，本课题五条查询的落地平台。
    type: 转载
    platform: 微软
    url: https://learn.microsoft.com/azure/sentinel/
    desc: Microsoft Sentinel 官方文档：SIEM 与 UEBA 检测工程
    stars: 4
  - title: B站讲解视频
    text: 53 分钟视频：Uber 案例与零告警原理的完整讲解。
    type: 原创
    platform: B站
    url: https://www.bilibili.com/video/BV1SX416mE6g
    desc: 《身份认证问题讨论》53 分钟讲解：Uber 案 + 零告警原理
    stars: 4
links:
  - platform: 公众号
    form: 上篇《登录认证安全（上）MFA能确保登录一定安全？未必》
    url: https://mp.weixin.qq.com/s/EM5qM81ApwvRTa8MtvNugA
    note: 已发布 2026-08-28
  - platform: 公众号
    form: 中篇《登录认证安全（中）不偷密码的入侵》
    url: https://mp.weixin.qq.com/s/BEj1NBVVyH9YYG0K1U_EPg
    note: 已发布 2026-08-29
  - platform: 公众号
    form: 下篇《登录认证安全（下）零告警的入侵怎么抓》
    url: https://mp.weixin.qq.com/s/5nU_Qawj3rbfoApbzhI3Ew
    note: 已发布 2026-08-29
  - platform: CSDN
    form: 完整版《剖析合法认证身份攻击路径，ITDR有何应对效果》
    url: https://blog.csdn.net/qq_37865996/article/details/163982749
    note: 已发布（沿用原版）
videos:
  - platform: B站
    form: 53分钟讲解《身份认证问题讨论》（Uber案+零告警原理）
    url: https://www.bilibili.com/video/BV1SX416mE6g
    note: 已发布 2026-08-29
  - platform: 视频号
    form: 《身份认证安全问题探讨》
    url: https://weixin.qq.com/sph/AHY0zVteg
    note: 已发布 2026-08-29（微信内打开）
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
