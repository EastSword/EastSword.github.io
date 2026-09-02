---
published: true
layout: topic
title: SSH隧道机中转与审计
subtitle: 运维没搞清原理就上线的中转方案——把 SSH 端口转发的机制、准入收敛与日志审计一次补齐
date: 2026-09-02
updated: 2026-09-02
status: drafting
category: 运维安全
tags: [运维安全, 安全审计, 检测工程]
links:
  - platform: 官网
    form: 技术研究报告完整版（10 章：机制 / 运维 / 实现 / 风险 / 审计 / 采集 / ES / 分析 / 落地 / 演进）
    note: 报告已成稿（v2.1），整理为官网长文后上线
assets:
  - name: SSH 隧道机运维与审计技术研究报告（v2.1）
    desc: 10 章完整报告：转发机制拆解、具体实现方案（安全组 / sshd 基线 / 逐用户白名单 / 账号脚本 / 验收清单）、审计设计、日志采集与 ES 模型、分析方法与三阶段落地路线
    location: 课题主报告，随长文上线
  - name: sshd 基线配置与账号开通脚本
    desc: Match Group tunnel-users + PermitOpen 白名单 + ForceCommand、authorized_keys 逐用户 restrict,port-forwarding、nftables 兜底规则，可直接套用
    location: 随报告整理发布
research_notes: SSH隧道机运维与审计技术研究报告.html
---

## 核心问题

数据库、ES、管理后台这类内网服务不该暴露公网，但运维和研发又必须访问。在还没有完整远程接入体系时，最快的落地方式就是一台有公网 IP 的主机加 SSH 本地端口转发：用户用 Core Tunnel 登录，把本机 127.0.0.1 的端口映射到云内网服务，像访问本机端口一样访问内网。这套方案先以运维便利的形态上线了——当时运维并没有把原理搞清楚，直接结果是三个"不知道"：不知道谁连进来了、不知道他访问了哪个内网服务、不知道过了多少流量。

问题的根源是 SSH 转发天然把证据拆成两半。登录日志只证明"谁连上了跳板机"；而隧道里的流量由 sshd 在跳板机上重新发起 TCP 连接，内网服务看到的来源永远是跳板机 IP，身份归属就此断掉。sshd 默认日志不记录转发目标、时长和字节数；如果放任 `-D` 动态 SOCKS，跳板机直接变成内网横向通道；如果再多人共用一个账号，补再多日志也追不到具体的人。审计设计的核心，就是用 session.id（主机 + 用户 + sshd PID + 登录时间）把认证日志和连接日志重新缝起来，回答运维审计的四个问题：谁登录、从哪登录、访问了哪些内网服务、访问规模是否异常。

## 覆盖内容

- **机制拆解**：`ssh -L` 本地转发 / `-D` 动态 SOCKS / `-R` 远程转发三种模式对比与建议；Core Tunnel 本质是 OpenSSH 转发参数的图形化封装，没有创造新协议；与 frp 的异同——SSH 方案复用系统账号、密钥和 Linux 审计体系，边界清晰组件少，但缺统一控制台和细粒度审计，必须自行补安全方案
- **运维方案与具体实现**：云侧安全组（跳板机只开 SSH、目标服务只认跳板机私网 IP）、sshd 基线（`LogLevel VERBOSE` / `AllowTcpForwarding local` / `GatewayPorts no` / `Match Group tunnel-users` 配 `PermitOpen` 白名单 + `ForceCommand` 禁交互 shell）、authorized_keys 逐用户 `restrict,port-forwarding` 限制、账号开通脚本、Core Tunnel 客户端配置等价表、systemd 托管固定隧道、nftables 本地兜底、上线验收清单。核心原则：只给用户一个 SSH 入口，不给用户一张内网通行证
- **四大风险缺口**：目标服务看不到真实用户、sshd 默认日志不够、`-D` 动态代理扩大边界、日志量与隐私边界；关键判断是共享账号问题不是查询问题——一人一号是审计的前提
- **审计设计**：四类最小审计事件（登录成功/失败、会话开关、内网连接建立、连接关闭带字节数）；session.id 关联算法按优先级降级：PID 命中 → 父子进程命中 → 同 UID 加时间窗近似匹配并标记置信度
- **日志采集与控量**：Filebeat 双路输入（认证日志 filestream + 连接日志 ndjson）、Tetragon eBPF `tcp_v4_connect` 观测、Python 轻量过滤聚合脚本（只记 RFC1918 内网目标 + 白名单端口，10 秒窗口同五元组合并，防止日志撑爆系统）、systemd 常驻托管；只记元数据不抓业务内容
- **ES 模型**：ssh_auth / ssh_tunnel_connection 分索引、统一字段模型、索引模板、ILM hot-warm-delete 生命周期、Ingest Pipeline 字段规整，控量策略贯穿采集到存储
- **分析方法**：会话视图看板、按人按目标按来源的典型查询、告警规则（非工作时段登录、白名单外目标、异常数据量、同账号多源 IP）
- **落地路线**：三阶段推进——先把认证日志进 ES，再补连接级审计，最后做关联与告警；演进方向从"能用"走向逐用户白名单、公钥替换密码直至可信接入
