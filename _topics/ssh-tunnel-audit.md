---
published: true
layout: topic
title: SSH隧道机中转与审计
subtitle: 运维没搞清原理就上线的中转方案——把 SSH 端口转发的机制、准入收敛与日志审计一次补齐
date: 2026-09-02
updated: 2026-09-03
status: published
category: 运维安全
tags: [运维安全, 安全审计, 检测工程]
links:
  - platform: 官网
    form: 完整版长文（8 章）
    url: /articles/ssh-tunnel-audit/
    note: 在线阅读完整版
assets:
  - name: sshd 基线配置与账号开通脚本
    desc: Match Group tunnel-users + PermitOpen 白名单、authorized_keys 逐用户 restrict,port-forwarding、账号开通脚本（含 pam_shells 边角检查），可直接套用
    location: 文章第 3 章，已随长文上线
  - name: Tetragon 观测策略与规整脚本
    desc: all-internal-connect.yaml（DAddr CIDR 内核态过滤，不限进程不限端口）、tunnel_flow_filter.py（10 秒窗口聚合 + session.id 同公式生成）、Filebeat 双路采集配置
    location: 文章第 6 章，已随长文上线
research_notes: SSH隧道机运维与审计技术研究报告.html
---

## 核心问题

数据库、ES、管理后台这类内网服务不该暴露公网，但运维和研发又必须访问。在还没有完整远程接入体系时，最快的落地方式就是一台有公网 IP 的主机加 SSH 本地端口转发：用户用 Core Tunnel 登录，把本机 127.0.0.1 的端口映射到云内网服务，像访问本机端口一样访问内网。这套方案先以运维便利的形态上线了——当时运维并没有把原理搞清楚，直接结果是三个"不知道"：不知道谁连进来了、不知道他访问了哪个内网服务、不知道过了多少流量。

问题的根源是 SSH 转发天然把证据拆成两半。登录日志只证明"谁连上了跳板机"；而隧道里的流量由 sshd 在跳板机上重新发起 TCP 连接，内网服务看到的来源永远是跳板机 IP，身份归属就此断掉。sshd 默认日志不记录转发目标、时长和字节数；如果放任 `-D` 动态 SOCKS，跳板机直接变成内网横向通道；如果再多人共用一个账号，补再多日志也追不到具体的人。审计设计的核心，就是用 session.id（主机 + 用户 + sshd 父进程 PID + 小时桶）把认证日志和连接日志重新缝起来，回答运维审计的四个问题：谁登录、从哪登录、访问了哪些内网服务、访问规模是否异常。

## 覆盖内容

- **机制拆解**：`ssh -L` 本地转发 / `-D` 动态 SOCKS / `-R` 远程转发三种模式对比与建议；Core Tunnel 本质是 OpenSSH 转发参数的图形化封装，没有创造新协议；核心难点是"用户到跳板机的 SSH 会话"与"跳板机到内网目标的新 TCP 连接"把证据拆成两半，目标服务看到的来源永远是跳板机 IP
- **运维方案与具体实现**：云侧安全组（跳板机只开 SSH、目标服务只认跳板机私网 IP）、sshd 基线（`LogLevel VERBOSE` / `AllowTcpForwarding local` / `GatewayPorts no` / `Match Group tunnel-users` 配 `PermitOpen` 白名单、nologin 拒绝交互请求——ForceCommand 对纯转发登录不生效，这个坑文章里讲透了）、authorized_keys 逐用户 `restrict,port-forwarding` 限制、账号开通脚本（含 pam_shells 边角检查）、Core Tunnel 客户端配置等价表、上线验收清单。核心原则：只给用户一个 SSH 入口，不给用户一张内网通行证
- **四大风险缺口**：目标服务看不到真实用户、sshd 默认日志不够、`-D` 动态代理扩大边界、日志量与隐私边界；关键判断是共享账号问题不是查询问题——一人一号是审计的前提
- **审计设计**：四类最小审计事件（登录成功/失败、会话开关、内网连接建立、连接关闭带字节数）；session.id = SHA1(主机|用户|sshd 父进程 PID|小时桶)，auth 侧 Ingest Pipeline 与 flow 侧规整脚本同公式生成、双向互查，sshd 特权分离导致的 PID 差层是对齐关键；匹配不到时按 PID → 父子进程 → 同 UID 加时间窗降级并标记置信度
- **日志采集**：Tetragon eBPF `tcp_v4_connect` 全量内网观测（DAddr CIDR 内核态过滤，不限进程不限端口）、bcc tcplife 补 close 侧收发字节数与连接时长、Python 规整脚本（10 秒窗口同五元组合并，防止日志撑爆系统）、systemd 常驻 + logrotate、Filebeat 双路输入（认证日志 grok 解析 + 连接日志 ndjson）；只记元数据不抓业务内容
- **ES 入库与告警**：sshd.auth-* / ssh_tunnel.flow-* 双索引族、Ingest Pipeline 按同公式补 session.id；告警规则覆盖白名单外目标、来源异常、访问扩散、长连接、高流量，后两条依赖 close 侧采集，落地节奏文章里给了取舍
