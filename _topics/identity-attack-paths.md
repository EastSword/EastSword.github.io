---
published: false
layout: topic
title: 身份攻击七路径与ITDR
subtitle: 密码对，MFA通过，零告警——合法认证身份的攻击面全景与检测之道
date: 2026-08-25
updated: 2026-08-26
status: drafting
keyword: ITDR
tags: [身份安全, 企业安全, 检测工程]
links:
  - platform: 公众号
    form: 上篇《七条路径与凭证层级（路径一至三）》
    url:
    note: 待发布
  - platform: 公众号
    form: 中篇《路径四至七与检测为何失明》
    url:
    note: 待发布
  - platform: 公众号
    form: 下篇《ITDR落地：九信号、五规则与十问》
    url:
    note: 待发布
  - platform: CSDN
    form: 完整版《密码对，MFA通过，零告警：七条身份攻击路径与ITDR检测指南》
    url:
    note: 待发布（替换旧文）
  - platform: FreeBuf
    form: 管理层视角版
    url:
    note: 投稿备选
videos:
  - platform: B站
    form: 10分钟讲解（Uber案+零告警原理）
    url:
    note: 脚本已备，待录制
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
- **七条攻击路径**：AiTM反向代理（Evilginx双TLS中继与Set-Cookie拦截）/ Infostealer（浏览器存储加密的信任根缺陷）/ MFA疲劳与注册劫持（Uber事件）/ SaaS本地账号（IdP目录外的盲区）/ 签名密钥伪造（Storm-0558伪造令牌）/ OAuth恶意授权 / 恢复流程劫持（MGM十亿美元事件）——每条带技术拆解与ATT&CK映射
- **传统检测为何失明**：暴力破解、异地登录、设备信任、进程检测四类思路对"合法登录"的集体失效分析
- **ITDR落地**：四类数据源、九个检测信号、五条可粘贴的KQL规则、响应闭环
- **NHI与AI Agent时代**：非人类身份五问，45:1的人机身份比例下的治理起点
- **管理层十问**：拿去开评审会的立项依据
