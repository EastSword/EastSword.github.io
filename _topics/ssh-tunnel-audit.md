---
published: true
layout: topic
title: SSH隧道机中转与审计
subtitle: 运维没搞清原理就上线的中转方案——把 SSH 端口转发的机制、准入收敛与日志审计一次补齐
date: 2026-09-02
updated: 2026-09-03
status: 已结题
categories: [运维安全, 检测与响应]
tags: [运维安全, 安全审计, 检测工程]
dao_summary: "SSH 转发天然把证据拆成两半：登录日志只证明“谁连上了跳板机”，隧道流量由 sshd 重新发起，内网服务看到的来源永远是跳板机 IP。审计设计的第一性问题是把被协议拆开的证据重新缝起来；原则是只给用户一个 SSH 入口、不给内网通行证，一人一号是审计的前提。"
fa_summary: "方法论是用一个 ID 缝合两半证据：session.id = SHA1(主机|用户|sshd 父进程 PID|小时桶) 在认证侧与连接侧同公式生成、双向互查；四类最小审计事件只记元数据不抓业务内容，回答运维审计四问；匹配不到时按 PID → 父子进程 → 同 UID 时间窗逐级降级并标记置信度，把不完美变成可度量的。"
shu_summary: "落地从配置到采集全链路给齐：sshd 基线（VERBOSE 日志、local 转发、PermitOpen 白名单、nologin）含 ForceCommand 对纯转发不生效的坑；Tetragon eBPF 内核态全量观测内网连接，bcc tcplife 补字节数与时长；十秒窗口聚合防日志撑爆系统；8 章长文配 8 步执行手册（附 docx）。"
qi_summary: "外部依据收权威实现与采集引擎：OpenSSH 是转发机制与日志语义的出处，Tetragon 承担 eBPF 内核态采集核心，bcc tcplife 补齐连接生命周期观测，Elasticsearch + Filebeat 承载双索引与 Ingest Pipeline。每条标注来源与推荐星级。"
dao:
  - title: SSH 转发把证据拆成两半
    text: 登录日志只证明"谁连上了跳板机"；隧道里的流量由 sshd 重新发起 TCP 连接，内网服务看到的来源永远是跳板机 IP，身份归属就此断掉——审计设计的第一性问题是把被协议拆开的证据重新缝起来。
    type: 原创
    platform: 本课题
  - title: 只给入口，不给通行证
    text: 核心原则是给用户一个 SSH 入口，而不是一张内网通行证——`-D` 动态 SOCKS 一旦放开，跳板机就变成内网横向通道，便利性换来的边界崩塌不可逆。
    type: 原创
    platform: 本课题
  - title: 一人一号是审计的前提
    text: 共享账号问题是结构问题不是查询问题——多人共用一个账号时，补再多日志也追不到具体的人。权限模型先于日志模型。
    type: 原创
    platform: 本课题
fa:
  - title: session.id 关联方法论
    text: 用 session.id = SHA1(主机|用户|sshd 父进程 PID|小时桶) 把认证日志与连接日志重新缝合，auth 侧 Ingest Pipeline 与 flow 侧规整脚本同公式生成、双向互查——sshd 特权分离导致的 PID 差层是对齐关键。
    type: 原创
    platform: 本课题
  - title: 四类最小审计事件设计
    text: 登录成功/失败、会话开关、内网连接建立、连接关闭带字节数——只记元数据不抓业务内容，最小集合回答运维审计四问：谁登录、从哪登录、访问了哪些内网服务、访问规模是否异常。
    type: 原创
    platform: 本课题
  - title: 匹配降级策略
    text: session.id 匹配不到时按 PID → 父子进程 → 同 UID 加时间窗逐级降级，每级标记置信度——工程上承认不完美，但把不完美变成可度量的。
    type: 原创
    platform: 本课题
shu:
  - title: sshd 基线配置
    text: LogLevel VERBOSE、AllowTcpForwarding local、GatewayPorts no、Match Group tunnel-users 配 PermitOpen 白名单、nologin 拒绝交互请求——含 ForceCommand 对纯转发登录不生效的坑。
    type: 原创
    platform: 本课题
  - title: eBPF 内核态采集
    text: Tetragon tcp_v4_connect 全量内网观测（DAddr CIDR 内核态过滤，不限进程不限端口），bcc tcplife 补 close 侧收发字节数与连接时长，systemd 常驻 + logrotate 保采集可靠。
    type: 原创
    platform: 本课题
  - title: 十秒窗口聚合规整
    text: Python 规整脚本按 10 秒窗口合并同五元组连接，防止高并发下日志撑爆系统——采集的可持续性先于采集的完整性。
    type: 原创
    platform: 本课题
  - title: 官网长文与执行手册
    text: 完整版长文（8 章）+ 配套执行手册（8 步落地版，每步讲清证据链意义，附 docx 下载）。
    type: 原创
    platform: 官网
    url: /articles/ssh-tunnel-audit/
    desc: SSH 隧道机中转与审计完整版长文：机制拆解、准入收敛、审计设计与告警
qi:
  - title: Tetragon
    text: eBPF 安全观测引擎，内核态过滤 DAddr CIDR 的采集核心。
    type: 转载
    platform: GitHub
    url: https://github.com/cilium/tetragon
    desc: Cilium 出品的 eBPF 安全观测与执行引擎，实时内核事件采集
    stars: 5
  - title: OpenSSH
    text: 端口转发机制的权威实现，VERBOSE 日志语义的出处。
    type: 转载
    platform: 官方
    url: https://www.openssh.com/
    desc: OpenSSH 官方：SSH 协议参考实现，特权分离与转发日志语义
    stars: 5
  - title: Elasticsearch + Filebeat
    text: 双索引族（sshd.auth-* / ssh_tunnel.flow-*）与 Ingest Pipeline 的承载平台。
    type: 转载
    platform: Elastic
    url: https://www.elastic.co/
    desc: Elasticsearch 官方：搜索与分析引擎，Filebeat 双路采集与 Ingest Pipeline
    stars: 4
  - title: bcc tcplife
    text: 补齐连接关闭侧字节数与时长观测的 eBPF 工具。
    type: 转载
    platform: GitHub
    url: https://github.com/iovisor/bcc
    desc: BPF Compiler Collection：tcplife 工具观测 TCP 连接生命周期
    stars: 4
  - title: 配套执行手册 docx
    text: 手册离线版，含修订记录与每步意义说明，适合打印与内网分发。
    type: 原创
    platform: 官网
    url: /articles/ssh-tunnel-audit-manual/
    desc: SSH 隧道审计执行手册：8 步落地版，配置与验收成套
    stars: 4
links:
  - platform: 官网
    form: 完整版长文（8 章）
    url: /articles/ssh-tunnel-audit/
    note: 在线阅读完整版
  - platform: 官网
    form: 配套执行手册（8 步落地版）
    url: /articles/ssh-tunnel-audit-manual/
    note: 每步讲清证据链意义，配置与验收成套，附 docx 下载
assets:
  - name: sshd 基线配置与账号开通脚本
    desc: Match Group tunnel-users + PermitOpen 白名单、authorized_keys 逐用户 restrict,port-forwarding、账号开通脚本（含 pam_shells 边角检查），可直接套用
    location: 文章第 3 章，已随长文上线
  - name: Tetragon 观测策略与规整脚本
    desc: all-internal-connect.yaml（DAddr CIDR 内核态过滤，不限进程不限端口）、tunnel_flow_filter.py（10 秒窗口聚合 + session.id 同公式生成）、Filebeat 双路采集配置
    location: 文章第 6 章，已随长文上线
  - name: 日志审计执行手册 docx
    desc: 手册离线版，含修订记录与每步意义说明，适合打印与内网分发
    url: https://eastsword.github.io/assets/files/ssh-tunnel-audit-manual.docx
    location: docx 直接下载 · eastsword.github.io/assets/files/ssh-tunnel-audit-manual.docx
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
