---
layout: topic
title: 身份攻击七路径与 ITDR
subtitle: 密码对，MFA 通过，零告警——合法认证身份的攻击面全景与检测之道
date: 2026-08-25
updated: 2026-08-25
status: publishing
keyword: ITDR
links:
  - platform: 公众号
    form: 上中下三篇（东方隐侠安全团队）
    url:
    note: 一次推送齐发
  - platform: CSDN
    form: 完整版（重制中）
    url:
    note: 新标题《密码对，MFA 通过，零告警》
  - platform: FreeBuf
    form: 管理层视角版（约 4500 字）
    url:
    note: 投稿审核中
videos:
  - platform: B站
    form: 10 分钟讲解（Uber 案 + 零告警原理）
    url:
    note: 待录制
  - platform: 视频号
    form: 75 秒切片
    url:
    note: 待剪辑
assets:
  - name: ITDR 检测基线矩阵
    desc: 九个检测信号 × 数据源 × 响应动作，持续更新
    location: 知识大陆「千里」
    url:
  - name: 五条 KQL 检测规则
    desc: MFA 疲劳 / 休眠账号 / 会话断层 / 因子重绑 / 资源侧画像
    location: 知识大陆资产包
    url:
  - name: 泄露凭证情报源监控清单
    desc: Russian Market / Hudson Rock / crt.sh 等自检渠道
    location: 知识大陆资产包
    url:
---

起源于 Reddit r/AskNetsec 的一个问题：**登录本身完全合法、零告警，怎么检出被攻陷的身份？**

答案的骨架是七条攻击路径——AiTM 反向代理、Infostealer 日志市场、MFA 疲劳、SaaS 陈年凭证、Storm-0558 签名密钥伪造、OAuth 恶意授权、MGM 帮助台劫持。每条都对应真实事件（Uber、Snowflake、微软、MGM），每条都绕过了"密码 + MFA"的认证防线。传统检测全线失明的原因是结构性的：摄像头全对着门（认证），攻击者走的是窗户（会话）、后门（恢复流程）、房本（密钥）、物业授权（OAuth）。

这个话题最终落在 ITDR（Gartner 2022 年品类）：以身份为主键，聚合认证、目录、端点、资源四类遥测，做行为的事中事后持续分析。九个检测信号、五条可直接抄走的规则、十个拿去问管理层的问题——检测"看起来合法"的攻击，靠的是行为画像，不是更严的登录。
