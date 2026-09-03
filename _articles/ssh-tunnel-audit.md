---
layout: article
title: "SSH 隧道机运维与审计：从中转便利到可审计访问"
subtitle: "运维没搞清原理就上线的中转方案——把 SSH 端口转发的机制拆解、准入收敛与日志审计一次补齐"
abstract: "一台云主机加 SSH 本地端口转发，用 Core Tunnel 把本地端口映射到云内网服务——这套中转方案在运维还没搞清原理时就上线了。本文拆解转发机制的本质（会话与连接的证据被拆成两半），给出完整补齐方案：安全组与 sshd 基线、逐用户白名单、最小审计事件与 session.id 会话关联（sshd 特权分离的 PID 对齐是关键）、Tetragon eBPF 全量内网连接观测、tcplife 补字节数、Filebeat 采集与 ES 入库、告警规则与落地取舍。"
date: 2026-09-03
updated: 2026-09-03
reading_time: 13
topic: ssh-tunnel-audit
category: "运维安全"
author: "千里"
tags: ["运维安全", "安全审计", "检测工程", "SSH"]
toc:
  - id: ch01
    title: "1. SSH隧道机方案分析"
    children: []
  - id: ch02
    title: "2. 详解Core Tunnel背后的运行逻辑"
    children: []
  - id: ch03
    title: "3. 隧道机安全运维方案"
    children:
      - id: ch03-1
        title: "标准拓扑"
      - id: ch03-2
        title: "账号模型"
      - id: ch03-3
        title: "Core Tunnel 使用规范"
      - id: ch03-4
        title: "云侧网络与安全组"
      - id: ch03-5
        title: "服务端 sshd 基线配置"
      - id: ch03-6
        title: "更细粒度的逐用户白名单"
      - id: ch03-7
        title: "账号开通脚本"
      - id: ch03-8
        title: "Core Tunnel 客户端配置等价表"
      - id: ch03-9
        title: "上线验收清单"
  - id: ch04
    title: "4. 当前风险缺口分析"
    children: []
  - id: ch05
    title: "5. 审计机制建设"
    children:
      - id: ch05-1
        title: "最小审计事件"
      - id: ch05-2
        title: "关联逻辑"
  - id: ch06
    title: "6. 日志采集：工具、方法与取舍"
    children:
      - id: ch06-1
        title: "sshd 日志"
      - id: ch06-2
        title: "eBPF 连接观测"
      - id: ch06-3
        title: "close 侧：字节数与持续时长怎么拿"
      - id: ch06-4
        title: "规整脚本（事件 → flow.json）"
      - id: ch06-5
        title: "systemd 常驻 + 日志轮转"
      - id: ch06-6
        title: "Filebeat 采集配置"
      - id: ch06-7
        title: "session.id：auth 侧补齐"
  - id: ch07
    title: "7. 告警规则"
    children: []
  - id: ch08
    title: "8. 结论"
    children: []
---

数据库、ES、管理后台这类内网服务不该暴露公网，但运维和研发又必须访问，相信很多少侠都会遇到这种难题。在还没有完整远程接入体系时，圈内存在这样一种方式，可以使用一台有公网IP的主机加SSH本地端口转发，用户用Core Tunnel类似的隧道软件登录，将用户本机127.0.0.1的端口映射到云内网服务，像访问本机端口一样访问内网。但是很多团队使用这套方案时可能还没把原理搞清楚就直接上线了，等到出现安全告警或者安全事件的时候，只能回答三个"不知道"：不知道谁连进来了、不知道他访问了哪个内网服务、不知道过了多少流量。

这篇文章把这套中转方案的机制讲透，再给出完整的补齐路线：账号与准入收敛、sshd 与网络层配置、审计事件设计与会话关联、日志采集、ES 入库与告警规则。

## 1. SSH隧道机方案分析
{: #ch01}

这个方案的本质不是"搞一个代理"，而是在云上已有边界里，用最小组件成本解决内网服务访问问题。

云主机、数据库、搜索服务、管理后台、测试环境等内网服务通常不应该直接暴露到公网。但运维、研发、排障人员又需要临时或长期访问这些服务。传统做法要么开安全组白名单，要么上VPN，要么通过堡垒机或零信任平台。隐侠团队观察到，部分公司因为还没有完整的远程接入体系，就利用一台已有公网IP的主机加上 SSH转发，往往会成为最快落地的中转方式。

最小实现只需要三类配置：跳板机上运行 `sshd`；用户端配置本地端口转发；云安全组只开放 SSH 管理入口，不开放内网服务端口。这样，内网服务仍保持私网地址，用户不直接连内网，而是通过 SSH 会话让跳板机代为连接。

![描述](/assets/images/ssh-tunnel-audit/粘贴图-215708.png)

用户侧，Core Tunnel 这类工具把 OpenSSH 的端口转发能力图形化：用户填 SSH 地址、账号密码或私钥、本地监听端口、目标内网 IP 与端口，本机访问 `127.0.0.1:本地端口` 时，流量经 SSH 加密通道进入云主机，再由云主机转发到内网服务。
![描述](/assets/images/ssh-tunnel-audit/粘贴图-214204.png)

在这种情况下，SSH隧道机就实现了不把内网服务暴露公网，作为跳板机让已认证的SSH会话中转连接内网目标。

这个方案的价值是这样的：

| 维度 | 价值 | 说明 |
|:---: |:---:|---|
| 运维价值 | 上线快 | 无需改业务系统，也不要求目标服务支持额外认证插件。对研发来说，本地像访问本机端口一样访问云内网 |
| 网络价值 | 收敛暴露面 | 数据库、ES、管理后台不再开公网端口，只保留跳板机 SSH 入口，安全组变更更少 |
| 安全价值 | 可补齐审计 | 虽然 SSH 原生不是堡垒机，但可以通过 sshd 日志、进程级连接观测、ES 关联分析补齐留痕 |

## 2. 详解Core Tunnel背后的运行逻辑
{: #ch02}

因为很多少侠对这类工具比较陌生，所以单独介绍一下。

Core Tunnel 并没有创造新的隧道协议，它主要是在图形界面里封装 OpenSSH 的转发参数。理解机制的关键是区分"用户到跳板机的 SSH 会话"和"跳板机到内网目标的新 TCP 连接"。只要是中转，一般最终的目标服务看到的来源通常是跳板机，而不是用户电脑。

| 模式 | 命令等价 | 访问路径 | 建议 |
|---|---|---|---|
| 本地端口转发 | `ssh -L 9200:10.0.0.10:9200 user@jump` | 本机 9200 → jump:sshd → 10.0.0.10:9200 | 推荐作为标准访问方式 |
| 动态 SOCKS | `ssh -D 1080 user@jump` | 本机 SOCKS → jump:sshd → 任意目标 | 仅限少数排障场景，默认不建议 |
| 远程转发 | `ssh -R 8080:127.0.0.1:8080 user@jump` | jump 监听 → 回连用户本机 | 默认禁止，审计和暴露风险都高 |

实现短平快，就一定好吗，我肯定持否定态度。事实上，这种技术的存在有一定的合理性，但还是需要安全审计能力来做兜底。

分析当前场景，用户登录 SSH 只证明"谁连接了跳板机"。但当用户通过隧道访问内网 ES 或 DB 时，跳板机会新建一条到内网目标的 TCP 连接。这条连接在网络层只显示为"跳板机 → 内网服务"。此时，很难单纯通过单一日志来做跟踪记录，因为从目标服务日志，通常无法知道真实用户是谁，而只看隧道机的sshd登录日志，又不知道用户访问了哪个内网目标。

> **核心判断**：审计设计的本质，就是把这两类证据重新合并，实现认证日志负责识别人，连接级日志负责识别目标，进程 PID/UID/会话时间窗负责做关联。

## 3. 隧道机安全运维方案
{: #ch03}

### 标准拓扑
{: #ch03-1}

由于这套隧道方案基于 SSH 实现，我个人不建议将隧道机的入口直接暴露在公网，而应部署在企业内网。这样一来，它的主战场就是内网完成网络划分之后的场景，在办公网与生产网之间承担受控的访问中转。当然，即便部署在内网，日志分析的兜底也不能省略。

建议将跳板机放在与目标服务同 VPC 或可达子网内，在暴露面一侧，只开放 `22/tcp` 或企业自定义SSH端口；内网目标通过安全组只允许跳板机访问。用户侧只允许创建明确的本地转发，不把内网网段整体透给用户。

### 账号模型
{: #ch03-2}

每个自然人使用独立 Linux 账号或统一身份同步后的独立账号。不要多人共用 `ops`/`dev` 这类共享账号；一旦共享账号存在，审计只能落到"这个共享账号"，无法真正追到人。

| 控制点 | 推荐配置 | 原因 |
|---|---|---|
| 认证方式 | 公钥优先，逐步替换密码；关键人员用 FIDO2/硬件密钥 | 降低弱口令与撞库风险 |
| 转发方向 | `AllowTcpForwarding local` | 只允许本地转发，禁止反向暴露 |
| 目标白名单 | `PermitOpen ip:port` | 避免用户把跳板机变成全网代理 |
| 对外绑定 | `GatewayPorts no` | 防止本地转发被绑定到公网网卡 |
| 会话限制 | `MaxSessions`、`ClientAlive*` | 控制并发与僵尸连接 |

### Core Tunnel 使用规范
{: #ch03-3}

客户端侧约定命名规则：隧道名称包含业务、目标、端口，例如 `prod-es-9200`；本地端口固定分配，避免多人文档不一致；目标IP与端口只从批准清单中选择，这样做是为了让后续日志分析中的端口、目标和业务能对上。

### 云侧网络与安全组
{: #ch03-4}

如前面所说，跳板机建议单独放在运维子网，绑定公网 IP，只开放 SSH 入口；内网目标服务不开放公网，只允许跳板机私网 IP 访问。这样即便用户本地配置错误，也无法绕过跳板机直接访问目标服务。

```
# 安全组示例
# jump-host 入方向
允许 办公网出口IP/32 → jump-public-ip:22/tcp
拒绝 0.0.0.0/0 → jump-public-ip:22/tcp（如无固定出口，可先限国家/云 WAF/安全接入网关）

# 内网 ES / DB 入方向
允许 jump-private-ip → 10.0.0.10:9200/tcp
允许 jump-private-ip → 10.0.0.20:3306/tcp
拒绝 其他来源 → 目标服务端口
```

> **再次警示**：如果现在因为办公出口 IP 不固定而不得不临时开放 SSH 到公网，至少要叠加 Fail2ban、强密码过渡期、登录告警和尽快切公钥。公网 SSH + 用户名密码是隧道机最先需要收敛的风险。

### 服务端 sshd 基线配置
{: #ch03-5}

推荐把隧道用户放入独立用户组 `tunnel-users`，通过 `Match Group` 为这类用户设置更严格的转发策略。这样普通运维登录和隧道访问可以分层管理。

```
# 日志增强
SyslogFacility AUTHPRIV
LogLevel VERBOSE

# 全局收敛
PermitRootLogin no
GatewayPorts no
AllowAgentForwarding no
AllowStreamLocalForwarding no
X11Forwarding no
MaxAuthTries 3
MaxSessions 5
ClientAliveInterval 60
ClientAliveCountMax 3
LoginGraceTime 30

# 过渡期保留密码认证（Core Tunnel 现状），公钥铺完后改为 no
PasswordAuthentication yes
KbdInteractiveAuthentication no

# 隧道用户组：只给转发能力，不给 shell，目标白名单收敛
Match Group tunnel-users
    AllowTcpForwarding local
    PermitTTY no
    PermitTunnel no
    PermitOpen 10.0.0.10:9200 10.0.0.20:3306 10.0.0.30:6379
```

`Match` 块里几个关键项：`AllowTcpForwarding local` 只放行本地转发；`PermitTTY no` 禁止分配终端；`PermitOpen` 限定可转发的目标，按实际放通对象设置，也支持网段和通配端口，写法参考 sshd_config 手册。

这份配置特意不用 `ForceCommand`。它只在客户端请求会话通道（要 shell、执行命令）时才会执行，`ssh -N` 和 Core Tunnel 这类纯转发登录根本不请求会话通道，挂在它上面的脚本永远不会跑；而且账号 shell 是 nologin 时，强制命令要经由用户 shell 执行，同样跑不起来。拿 shell 的请求交给 nologin 自然拒绝（客户端会看到 This account is currently not available），登录留痕交给 auth 日志：VERBOSE 级别下，每次认证的账号、来源 IP、端口、认证方式、密钥指纹都会稳定落进 auth.log，后面日志采集一节就靠它做关联。

生效验证：
```bash
sudo sshd -t  # 语法校验
sudo systemctl reload sshd
# 正向：建立白名单内隧道，本地端口可访问目标
ssh -N -L 127.0.0.1:9200:10.0.0.10:9200 alice@tunnel-host
# 反向：转发白名单外目标应失败，客户端会收到 administratively prohibited 错误
```

### 更细粒度的逐用户白名单
{: #ch03-6}

如果不同用户能访问的内网服务不同，不建议只靠全局 `PermitOpen`。可以在 `authorized_keys` 里按 key 限制转发目标，并禁止 PTY、Agent、X11 与用户自定义命令。

```
# /home/alice/.ssh/authorized_keys
# alice 只能转发到 ES 和 Redis
restrict,port-forwarding,permitopen="10.0.0.10:9200",permitopen="10.0.0.30:6379" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... alice@company

# bob 只能转发到 MySQL
restrict,port-forwarding,permitopen="10.0.0.20:3306" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... bob@company
```

> **推荐做法**：全局 `Match Group tunnel-users` 先给一层最大边界，`authorized_keys permitopen` 再做逐用户最小权限。全局边界兜底，逐用户边界精细化。

### 账号开通脚本
{: #ch03-7}

隧道账号开通应脚本化，避免手工漏配家目录权限、用户组、密钥文件权限。下面是最小可用脚本，适合一人一号、公钥登录模式。

```bash
#!/usr/bin/env bash
# create_tunnel_user.sh
# 用法：sudo ./create_tunnel_user.sh alice 'ssh-ed25519 AAAA... alice@company'
set -euo pipefail

USER_NAME="$1"
PUB_KEY="$2"
GROUP_NAME="tunnel-users"

if ! getent group "$GROUP_NAME" >/dev/null; then
  groupadd "$GROUP_NAME"
fi

if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd -m -s /usr/sbin/nologin -G "$GROUP_NAME" "$USER_NAME"
fi

HOME_DIR="/home/$USER_NAME"
SSH_DIR="$HOME_DIR/.ssh"
install -d -m 700 -o "$USER_NAME" -g "$USER_NAME" "$SSH_DIR"

cat > "$SSH_DIR/authorized_keys" <<EOF
restrict,port-forwarding $PUB_KEY
EOF

chown "$USER_NAME:$USER_NAME" "$SSH_DIR/authorized_keys"
chmod 600 "$SSH_DIR/authorized_keys"

logger -p authpriv.notice "tunnel_user_created user=$USER_NAME group=$GROUP_NAME"
echo "created tunnel user: $USER_NAME"
```

一个边角：个别加固模板会给 sshd 的 PAM 栈加 pam_shells，如果 /usr/sbin/nologin 不在 /etc/shells 里，密钥验证通过了也登不进来。确认一下，不在就补一行：

```bash
grep nologin /etc/shells || echo /usr/sbin/nologin | sudo tee -a /etc/shells
```

如果暂时必须使用用户名密码登录，脚本也应强制设置到期时间、首次登录改密、失败锁定策略，并在迁移窗口结束后关闭密码认证。

```bash
# 密码过渡期控制示例
sudo passwd alice
sudo chage -M 30 -W 7 alice       # 密码 30 天过期，提前 7 天提醒
sudo faillock --user alice --reset # RHEL 系失败锁定管理示例
```

### Core Tunnel 客户端配置等价表
{: #ch03-8}

| Core Tunnel 字段 | 示例 | 等价 OpenSSH 参数 | 说明 |
|---|---|---|---|
| SSH Host | `jump.example.com` | `user@jump.example.com` | 跳板机公网域名或 IP |
| SSH Port | `22` | `-p 22` | 建议配合安全组限制来源 |
| Username | `alice` | `alice@jump` | 必须一人一号 |
| Authentication | Private Key | `-i ~/.ssh/id_ed25519` | 优先使用密钥，不建议长期密码 |
| Local Port | `9200` | `-L 127.0.0.1:9200:...` | 建议只绑定 127.0.0.1 |
| Remote Host | `10.0.0.10` | `...:10.0.0.10:...` | 目标内网 IP |
| Remote Port | `9200` | `...:9200` | 目标服务端口 |

这里配置完成之后，等价于在本地执行这样的命令：
```bash
# Core Tunnel 配置的命令行等价
ssh -N \
  -p 22 \
  -i ~/.ssh/id_ed25519 \
  -L 127.0.0.1:9200:10.0.0.10:9200 \
  alice@jump.example.com
```

然后curl [http://127.0.0.1:9200/](http://127.0.0.1:9200/) 就可以访问到对应的内网es

> **警示**：不要把本地监听写成 `0.0.0.0:9200`，否则用户电脑可能把这个本地隧道再次暴露给同网段其他人。标准写法应是 `127.0.0.1:本地端口`。


### 上线验收清单
{: #ch03-9}

| 验收项 | 命令/方法 | 期望结果 |
|---|---|---|
| sshd 配置合法 | `sshd -t` | 无错误输出 |
| 用户可建立指定隧道 | `ssh -N -L 127.0.0.1:9200:10.0.0.10:9200 alice@jump` | 本地端口可访问目标服务 |
| 白名单外目标被拒绝 | 尝试转发到未批准 IP/端口 | 连接失败，客户端报 administratively prohibited |
| 不能获取交互 shell | `ssh alice@jump` | 不进入 shell 或立即退出 |
| 日志可见 | 查看 ES 中 `sshd.auth-*` 和 `ssh_tunnel.flow-*` | 能看到用户、来源、目标、时间 |

## 4. 当前风险缺口分析
{: #ch04}

| 缺口 | 说明 |
|---|---|
| 目标服务看不到真实用户 | 内网 ES/DB 看到的是跳板机 IP。若目标服务本身也没有强认证，责任会被压缩成"跳板机访问了我" |
| sshd 默认日志不够 | 默认日志能记录登录成功/失败，但不足以稳定记录每个转发目标、持续时间和字节数 |
| -D 动态代理扩大边界 | SOCKS 模式允许用户访问更多目标，若无白名单和连接级审计，很容易变成内网横向通道 |
| 日志量与隐私边界 | 如果抓包或记录 HTTP 内容，容量和合规都会快速失控。应优先记录元数据 |

> **重要判断**：如果所有人共用一个 SSH 账号，再补日志也只能证明"共享账号访问过某服务"，不能证明"哪个人访问过"。这是账号体系问题，不是 ES 查询问题。

## 5. 审计机制建设
{: #ch05}

本方案满足运维审计最常见的四个问题：谁登录、从哪登录、访问了哪些内网服务、访问规模是否异常。

### 最小审计事件
{: #ch05-1}

| 事件 | 字段 | 来源 | 用途 |
|---|---|---|---|
| SSH 登录成功/失败 | 时间、账号、源 IP、端口、认证方式、密钥指纹 | sshd / auth.log | 定位人员与入口来源 |
| SSH 会话打开/关闭 | 账号、PID、TTY、PAM session、持续时间 | PAM / journald / auditd | 建立会话时间窗 |
| 内网连接建立 | PID、UID、目的 IP、目的端口、时间 | eBPF / conntrack / auditd | 识别访问目标 |
| 内网连接关闭 | PID、五元组、字节数、持续时间 | bcc tcplife（eBPF） | 识别用量与异常长连接 |

### 关联逻辑
{: #ch05-2}

认证日志拿到用户和源 IP，连接日志拿到目的 IP 和端口，中间靠一个统一的 `session.id` 把两类证据拼起来，公式固定为：

```
session.id = sha1(host.name | user.name | sshd.priv_pid | epoch_hour)

epoch_hour    = Unix 时间戳 ÷ 3600 取整（按小时分桶）
sshd.priv_pid = auth 日志行里的 sshd PID，即 [priv] 监控进程
```

公式里两个设计点，都是踩坑踩出来的：

一是时间不能取精确值。auth 行和第一条连接事件相差几秒到几分钟，拿精确登录时刻两边永远算不出同一个值，所以按小时分桶，同一小时内的登录与连接命中同一个 id。

二是 PID 差一层。sshd 特权分离后，auth 日志里的 PID（`sshd[1200]: Accepted ...`）是 [priv] 监控进程，而转发到内网的 TCP 连接由它的无特权子进程（PID 1201）发起。好在 eBPF 事件带父进程信息，flow 侧计算 session.id 时取父进程 PID，两边就一致了。

session.id 查不到时的兜底匹配，按顺序降级：

1. connection.pid == auth 侧 sshd PID（直接命中）
2. connection.ppid == auth 侧 sshd PID（父子进程，sshd 转发的默认情况）
3. connection.uid == session.uid 且 connection.time 在 session 时间窗内，命中后必须标 attribution.confidence = low

局限也要说清楚：登录和首条连接跨小时边界（比如 12:59 登录、13:01 才有第一条连接）时，两侧小时桶不同，session.id 对不上，查询时对相邻小时桶再做一次兜底，或者接受这个精度损失。

> **最有价值的产出**：不是单条日志，而是"认证事件 + 连接事件"拼出的会话视图——alice 从 1.2.3.4 登录，在 12:01–12:40 访问了 10.0.0.10:9200 与 10.0.0.20:3306，累计出向 93MB。

## 6. 日志采集：工具、方法与取舍
{: #ch06}

### sshd 日志
{: #ch06-1}

把 `LogLevel` 设置为 `VERBOSE`，可以拿到更完整的认证信息和密钥指纹。不要长期使用 `DEBUG`，它会制造大量噪声并可能暴露敏感运行细节。

sshd 不需要第二份配置，前面基线里的 `SyslogFacility AUTHPRIV` 和 `LogLevel VERBOSE` 已经覆盖，这里补充两点：`UsePAM` 保持发行版默认的 `yes`，密码过渡期的过期、锁定策略都挂在 PAM 上；VERBOSE 下 auth 日志能稳定给出每次认证的账号、来源 IP、端口、认证方式和密钥指纹，这些正是后面 grok 解析和 session.id 关联要用的字段。

### eBPF 连接观测
{: #ch06-2}

为什么是连接观测，而不是抓包。 审计要回答的是"谁在什么时间访问了哪个内网目标、量有多大"，这些都是连接元数据，和业务内容无关。

全量抓包有三个问题：一是容量失控，隧道里跑的是长连接业务流量，抓包日增量轻松过百 GB；二是合规风险，落到磁盘的报文里可能包含凭据、个人信息；三是没必要，内网目标看到的每条连接都由 sshd 发起，只要在跳板机上记录连接的建立和关闭，证据链就完整了。

所以只抓 **connect 与 close**  两个事件即可：
- connect（连接建立），主要记录时间戳、PID、UID、**进程名与父进程链**、源地址、目的 IP:Port，这样用于确定"谁（哪个 sshd 会话）发起了到哪去的访问"
- close（连接关闭），主要记录五元组、持续时长、收发字节数，可以确定"访问了多久、过了多少数据"，支撑长连接与高流量告警

为什么我上面着重加粗了进程上下文，这是使用eBPF的关键所在，一般的网络侧工具只能给出五元组，能得到的信息是"跳板机 IP 访问了 10.0.0.10:9200"，而eBPF在内核里能拿到发起连接的PID和UID，沿着进程树能对上具体的sshd: alice@pts会话，才能最终溯源到具体的人。

下面以tetragon为例进行部署

**第一步：部署（Docker 方式）**
```
docker run -d --name tetragon --restart always \
  --pid=host --cgroupns=host --privileged \
  -v /sys/kernel/btf/vmlinux:/var/lib/tetragon/btf \
  quay.io/cilium/tetragon:v1.7.0
```

**第二步：加载全量内网观测策略**
```yaml
# all-internal-connect.yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: all-internal-connect
spec:
  kprobes:
    - call: "tcp_v4_connect"
      syscall: false
      args:
        - index: 0
          type: "sock"
      selectors:
        - matchArgs:
            - index: 0
              operator: "DAddr"
              values:
                - "10.0.0.0/8"
                - "172.16.0.0/12"
                - "192.168.0.0/16"
          matchActions:
            - action: Post
```

要点：没有 matchBinaries，任何进程的内网连接都记录；没有端口限制；网段按实际 VPC 裁剪。过滤在内核态完成，非内网连接零开销。策略文件要挂载进容器才生效，而第一次部署时没挂策略目录，所以要把旧容器删掉重建，直接再跑一条 docker run 会报 container name already in use：
```
sudo mkdir -p /etc/tetragon/policies /var/log/ssh-tunnel
sudo chmod 750 /var/log/ssh-tunnel
# all-internal-connect.yaml 放进 /etc/tetragon/policies/ 后再执行下面两条
docker rm -f tetragon
docker run -d --name tetragon --restart always \
  --pid=host --cgroupns=host --privileged \
  -v /etc/tetragon/policies:/etc/tetragon/tetragon.tp.d:ro \
  -v /sys/kernel/btf/vmlinux:/var/lib/tetragon/btf:ro \
  quay.io/cilium/tetragon:v1.7.0
```

**第三步：验证**
```
docker exec -ti tetragon tetra getevents -o compact
```

从办公网建一条隧道并访问目标，应看到：
```
🔌 connect /usr/sbin/sshd tcp 192.168.10.5:41234 -> 10.0.0.10:9200
```

看不到事件时按顺序排查：策略文件是否在挂载目录里（宿主机 `ls /etc/tetragon/policies`）→ 隧道是否真的建立了（`ss -tnp | grep sshd`，能看到 sshd 到内网目标的连接）→ 目的网段是否在策略 values 内。

我这里就用一个简单的curl来展示流量是全记录的：
![描述](/assets/images/ssh-tunnel-audit/粘贴图-234844.png)


### close 侧：字节数与持续时长怎么拿
{: #ch06-3}

上面这套策略只挂了 `tcp_v4_connect`，connect 事件里没有收发字节数，"过了多少流量、连了多久"拿不到。补齐用 bcc 的 tcplife，它在连接关闭时输出一条会话总结，正好对应审计事件表里"内网连接关闭"那一行：

```bash
# Ubuntu/Debian：apt install bpfcc-tools，工具名 tcplife-bpfcc
# RHEL/CentOS：dnf install bcc-tools，工具在 /usr/share/bcc/tools/
sudo /usr/share/bcc/tools/tcplife | grep sshd
```

输出形如：

```
PID    COMM    LADDR           LPORT  RADDR           RPORT  TX_KB  RX_KB  MS
1201   sshd    10.0.0.5        51234  10.0.0.10       9200   3.5    93.2   360012
```

TX_KB/RX_KB 是这条连接的收发总量，MS 是连接存续毫秒数，数据读的是内核 socket 里现成的统计，不抓包。前面那个"alice 累计出向 93MB"的会话视图，就是拿 connect 侧的身份字段加上 close 侧的 TX_KB/RX_KB 拼出来的。

为什么不用 Tetragon 顺手挂 tcp_close：它的 sock 参数默认只带地址和端口，收发字节数拿不到，要等上游支持或自己扩展策略，不如 bcc 现成。代价是 bcc 依赖内核头文件，内核小版本升级后要重新验证。落地节奏建议：connect 侧先全量常驻，close 侧平时按需手动跑，字节审计做深了再考虑常驻入库。

### 规整脚本（事件 → flow.json）
{: #ch06-4}
/usr/local/bin/tunnel_flow_filter.py（chmod +x）：
```
#!/usr/bin/env python3
# 输入：tetra getevents -o json 行；输出：规整后的嵌套 JSON 行
# 规则：不限进程、不限端口；只保留内网网段目标；同五元组 10 秒窗口聚合
# session_id = sha1(host|user|sshd父进程PID|小时桶) 的 base64，与 auth 侧 Ingest Pipeline 同公式
import json, sys, time, ipaddress, hashlib, base64
from collections import defaultdict

INTERNAL_NETS = [ipaddress.ip_network(x) for x in ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]]
WINDOW = 10
bucket = defaultdict(lambda: {"count": 0, "first": None, "last": None})

def is_internal(ip):
    try:
        return any(ipaddress.ip_address(ip) in n for n in INTERNAL_NETS)
    except (ValueError, TypeError):
        return False

def get_user(proc):
    # Tetragon 各版本用户名字段位置不同：老版本在 process.user，新版本在 process.credentials.user
    cred = proc.get("credentials") or {}
    for v in (proc.get("user_name"), proc.get("user"), cred.get("user")):
        if isinstance(v, str) and v:
            return v
    return "unknown"

def session_id(host, user, pid, ts):
    # sha1 后取 base64：对齐 ES fingerprint 处理器的输出格式（base64 而非 hex）
    raw = f"{host}|{user}|{pid}|{int(ts)//3600}"
    return base64.b64encode(hashlib.sha1(raw.encode()).digest()).decode()

def flush(now):
    for k in list(bucket):
        v = bucket[k]
        if v["last"] and now - v["last"] >= WINDOW:
            comm, host, user, pid, session_pid, saddr, dst_ip, dst_port = k
            out = {
                "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(v["last"])),
                "event": {"dataset": "ssh_tunnel.flow", "action": "flow_summary", "count": int(v["count"])},
                "host": {"name": host},
                "user": {"name": user},
                "process": {"pid": int(pid), "name": comm},
                "source": {"ip": saddr},          # 隧道机出向地址；用户真实来源在 sshd.auth 侧
                "destination": {"ip": dst_ip, "port": int(dst_port)},
                "network": {"transport": "tcp"},
                "session": {"id": session_id(host, user, session_pid, v["first"])},
                "attribution": {
                    "kind": "sshd_session" if comm == "sshd" else "host_process",
                    "confidence": "high" if comm == "sshd" else "medium",
                },
            }
            print(json.dumps(out, ensure_ascii=False), flush=True)
            del bucket[k]

for line in sys.stdin:
    now = time.time()
    flush(now)
    try:
        e = json.loads(line)
    except Exception:
        continue
    pk = (e.get("event") or {}).get("process_kprobe")
    if not pk or pk.get("function_name") != "tcp_v4_connect":
        continue
    proc = pk.get("process") or {}
    args = pk.get("args") or []
    # Tetragon 的 kprobe 参数按类型包装，sock 类型在 args[0].sock_arg 下
    sock = (args[0].get("sock_arg") or {}) if args else {}
    dst_ip, dst_port = sock.get("daddr"), int(sock.get("dport") or 0)
    if not is_internal(dst_ip) or not dst_port:
        continue
    comm = (proc.get("binary") or "unknown").rsplit("/", 1)[-1]
    pid = proc.get("pid") or 0
    # sshd 的转发连接由无特权子进程发起，auth 日志里的 PID 是它的父进程（[priv] 监控进程），
    # session_id 必须用父进程 PID，才能和 sshd.auth 侧公式对上
    session_pid = ((proc.get("parent") or {}).get("pid") or pid) if comm == "sshd" else pid
    key = (
        comm,
        e.get("node_name") or "tunnel-host",
        get_user(proc),
        pid,
        session_pid,
        sock.get("saddr") or "unknown",
        dst_ip, dst_port,
    )
    bucket[key]["count"] += 1
    bucket[key]["first"] = bucket[key]["first"] or now
    bucket[key]["last"] = now
```

### systemd 常驻 + 日志轮转
{: #ch06-5}
/etc/systemd/system/ssh-tunnel-flow.service：
```
[Unit]
Description=Tetragon events -> normalize -> flow.json
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/bin/bash -lc 'docker exec tetragon tetra getevents -o json | /usr/local/bin/tunnel_flow_filter.py >> /var/log/ssh-tunnel/flow.json'
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

/etc/logrotate.d/ssh-tunnel-flow：
```
/var/log/ssh-tunnel/flow.json {
    daily
    rotate 14
    missingok
    notifempty
    copytruncate
    compress
    delaycompress
}
```

启动命令：`sudo systemctl daemon-reload && sudo systemctl enable --now ssh-tunnel-flow`

两个运维细节：规整脚本的聚合窗口在内存里，服务重启会丢掉最后 10 秒内还没落盘的聚合结果，重启挑低峰做；丢了也能补救，Tetragon 默认把原始事件导出到容器 stdout，`docker logs tetragon` 可以回放核对。


### Filebeat 采集配置
{: #ch06-6}

Filebeat 负责把认证日志和连接元数据推送到 ES。认证日志走系统日志路径，连接日志走 JSON 文件；两类日志用不同 dataset，后续才能做不同 ILM 和不同字段解析。

/etc/filebeat/filebeat.yml：
```
filebeat.inputs:
  # 谁登录：SSH 认证日志
  - type: filestream
    id: sshd-auth-log
    enabled: true
    paths:
      - /var/log/auth.log
      - /var/log/secure
    fields:
      event.dataset: sshd.auth
      service.name: sshd
      tunnel.role: tunnel_host
    fields_under_root: true
    processors:
      - grok:
          match:
            message:
              - "sshd\\[%{INT:process.pid}\\]: %{WORD:auth_result} %{WORD:auth_method} for (invalid user )?%{USER:user.name} from %{IP:source.ip} port %{INT:source.port}"
          ignore_missing: true
          ignore_failure: true
      - rename:
          fields:
            - from: "auth_result"
              to: "event.outcome"
          ignore_missing: true
          ignore_failure: true

  # 去了哪：内网连接日志（规整脚本输出）
  - type: filestream
    id: ssh-tunnel-flow
    enabled: true
    paths:
      - /var/log/ssh-tunnel/flow*.json
    parsers:
      - ndjson:
          target: ""
          add_error_key: true
    fields:
      tunnel.role: tunnel_host
    fields_under_root: true

processors:
  - add_host_metadata: ~
  - drop_fields:
      fields: ["agent.ephemeral_id", "ecs.version", "input.type", "log.offset"]
      ignore_missing: true

output.elasticsearch:
  hosts: ["http://10.0.0.10:9200"]
  index: "%{[event.dataset]}-%{+yyyy.MM.dd}"
  pipeline: "ssh-auth-session-id"

setup.template.enabled: false
setup.ilm.enabled: false
```

执行命令：`sudo systemctl restart filebeat && sudo filebeat test output`

执行后就可以把日志上传到es，产出两个索引族：sshd.auth-YYYY.MM.DD 与 ssh_tunnel.flow-YYYY.MM.DD。

这套配置还有三个细节要留意。第一，认证日志的路径 Debian 系是 `/var/log/auth.log`、RHEL 系是 `/var/log/secure`，上面两条都写了；但纯 journald 且没装 rsyslog 的系统，认证日志只进 journal 不落文件，filestream 一行都采不到，先确认 rsyslog 在跑。第二，grok 里 `event.outcome` 的值是 `Accepted`/`Failed` 字面量，不是 ECS 标准的 `success`/`failure`，查询和告警按字面值写就行，要严格对齐 ECS 可以在 Ingest Pipeline 里补一段映射。第三，`setup.ilm.enabled` 关掉之后 ES 侧没有自动清理，本地有 logrotate 14 天兜底，ES 侧要么补索引模板和 ILM，要么加个定时任务删过期索引，比如 `curl -XDELETE "http://10.0.0.10:9200/sshd.auth-2026.07.*"` 这样按月清。

### session.id：auth 侧补齐
{: #ch06-7}

flow 侧的 session.id 由规整脚本算好了，auth 侧要用同一个公式在写入 ES 时补上，两边才能互查。用 Ingest Pipeline 实现：一段脚本拼出原始串，再用 fingerprint 处理器做 SHA-1。

```json
PUT _ingest/pipeline/ssh-auth-session-id
{
  "processors": [
    {
      "script": {
        "if": "ctx.event?.dataset == 'sshd.auth' && ctx.user?.name != null && ctx.process?.pid != null && ctx.host?.name != null",
        "lang": "painless",
        "source": "long hour = Instant.parse(ctx['@timestamp']).getEpochSecond() / 3600; ctx.session_raw = ctx.host.name + '|' + ctx.user.name + '|' + ctx.process.pid + '|' + hour;"
      }
    },
    {
      "fingerprint": {
        "if": "ctx.session_raw != null",
        "fields": ["session_raw"],
        "target_field": "session.id",
        "method": "SHA-1"
      }
    },
    { "remove": { "field": "session_raw", "ignore_missing": true } }
  ]
}
```

注意 fingerprint 的输出是 base64 编码，不是常见的 hexdigest，所以规整脚本里 session_id 函数也返回 base64，两边格式才一致。flow 事件同样会经过这条管道，脚本开头的 dataset 判断会直接跳过它们，不受影响。

还有一个要对齐的细节：公式里的 host，flow 侧来自 Tetragon 的 node_name，auth 侧来自 Filebeat 的 host.name，确认两边是同一个主机名（短名或 FQDN 要一致），不一致就统一改。

验证闭环，先从 flow 侧任取一条：

```json
GET ssh_tunnel.flow-*/_search
{ "size": 1, "query": { "exists": { "field": "session.id" } } }
```

拿返回的 session.id 反查 auth 侧：

```json
GET sshd.auth-*/_search
{ "query": { "match_phrase": { "session.id": "替换成上一步拿到的值" } } }
```

能互相查到，"谁登录"和"访问了哪些内网目标"就真正拼到同一个会话上了。


## 7. 告警规则
{: #ch07}
这里给一些参考项，具体还是要看企业内网安全管理实际：

| 告警 | 规则 | 处理建议 |
|---|---|---|
| 白名单外目标 | 目的 IP/端口不在批准清单 | 先断会话，再核对 Core Tunnel 配置 |
| 来源异常 | 用户从新国家/ASN/非常用网段登录 | 二次确认账号是否被盗 |
| 访问扩散 | 单会话访问内网目标数超过阈值 | 排查是否启用 -D SOCKS |
| 长连接 | 连接持续超过 8 小时或空闲过久 | 清理僵尸隧道，收紧 ClientAlive |
| 高流量 | 用户或目标流量超历史基线 | 判断是否数据导出或异常爬取 |

表中"长连接"和"高流量"两条依赖 close 侧的持续时长与 TX/RX 字节数，close 侧没有常驻采集之前先不启用，或者退化为 connect 侧的近似信号：同一 session.id 短时间内新建连接数、访问目标数突增。


## 8. 结论
{: #ch08}

SSH 隧道机是一种合理的轻量运维方案，本方案解决的问题不在"用了SSH转发"，而在上线后是否把账号、目标白名单、会话审计和容量控制补齐。安全方案的重点不是记录更多内容，而是记录正确的元数据，并把认证与连接两类证据关联起来。

网络安全管理务必要注意细节，把风险控制在合理范围的最小级别，极致的安全往往无法实现，那就做有兜底的安全。

感谢各位的观看，再见～
