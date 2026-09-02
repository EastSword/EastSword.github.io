---
layout: article
title: "SSH 隧道机运维与审计：从中转便利到可审计访问"
subtitle: "运维没搞清原理就上线的中转方案——把 SSH 端口转发的机制拆解、准入收敛与日志审计一次补齐"
abstract: "一台云主机加 SSH 本地端口转发，用 Core Tunnel 把本地端口映射到云内网服务——这套中转方案在运维还没搞清原理时就上线了。本文拆解转发机制的本质（会话与连接的证据被拆成两半），给出完整补齐方案：安全组与 sshd 基线、逐用户白名单、最小审计事件与 session.id 关联、Filebeat/Tetragon 采集控量、ES 索引与 ILM 模型、分析查询与告警规则、三阶段落地路线。"
date: 2026-09-03
updated: 2026-09-03
reading_time: 11
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
    title: "当前风险缺口分析"
    children: []
  - id: ch05
    title: "审计机制建设"
    children:
      - id: ch05-1
        title: "最小审计事件"
      - id: ch05-2
        title: "关联逻辑"
  - id: ch06
    title: "日志采集：工具、方法与取舍"
    children:
      - id: ch06-1
        title: "sshd 日志"
      - id: ch06-2
        title: "eBPF 连接观测"
      - id: ch06-3
        title: "规整脚本（事件 → flow.json）"
      - id: ch06-4
        title: "systemd 常驻 + 日志轮转"
      - id: ch06-5
        title: "Filebeat 采集配置"
      - id: ch06-6
        title: "告警规则"
  - id: ch07
    title: "结论"
    children: []
---

数据库、ES、管理后台这类内网服务不该暴露公网，但运维和研发又必须访问，相信很多少侠都会遇到这种难题。在还没有完整远程接入体系时，圈内存在这样一种方式，可以使用一台有公网IP的主机加SSH本地端口转发，用户用Core Tunnel类似的隧道软件登录，将用户本机127.0.0.1的端口映射到云内网服务，像访问本机端口一样访问内网。但是很多团队使用这套方案时可能还没把原理搞清楚就直接上线了，等到出现安全告警或者安全事件的时候，只能回答三个"不知道"：不知道谁连进来了、不知道他访问了哪个内网服务、不知道过了多少流量。

这篇文章把这套中转方案的机制讲透，再给出完整的补齐路线：账号与准入收敛、具体实现配置、审计事件设计、日志采集与控量、ES 模型、分析方法落地。

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
    ForceCommand /usr/local/sbin/tunnel-login-banner.sh
```

其中，`ForceCommand` 的作用是禁止隧道用户拿到交互式 shell，同时给出使用提示。
需要注意：OpenSSH 的 `ForceCommand` 与纯端口转发场景要结合实际版本验证。如果发现客户端建立转发后被立即关闭，可以改为 `PermitTTY no` + 受限 shell，或使用 `authorized_keys` 的 key option 做逐用户限制。最后的`PermitOpen`根据具体放通对象进行设置，当然也可以选择C段和全端口，具体设置参考sshd官方配置即可。


关于配置中的/usr/local/sbin/tunnel-login-banner.sh，在这里设置，作用是登录提示，需要chmod +x增加权限：
```bash
#!/usr/bin/env bash
logger -p authpriv.notice "tunnel_login user=${USER} src=${SSH_CONNECTION} cmd=${SSH_ORIGINAL_COMMAND:-none}"
echo "This account is only allowed for SSH local port forwarding."
sleep 2
exit 0
```

生效验证：
```bash
sudo sshd -t  # 语法校验
sudo systemctl reload sshd
# 正向：建立白名单内隧道，本地端口可访问目标
ssh -N -L 127.0.0.1:9200:10.0.0.10:9200 alice@tunnel-host
# 反向：转发白名单外目标应失败，且 auth 日志出现拒绝记录
grep "refused" /var/log/auth.log | tail
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

然后curl [http://127.0.0.1:9200/就可以访问到对应的内网es](http://127.0.0.1:9200/就可以访问到对应的内网es)

> **警示**：不要把本地监听写成 `0.0.0.0:9200`，否则用户电脑可能把这个本地隧道再次暴露给同网段其他人。标准写法应是 `127.0.0.1:本地端口`。


### 上线验收清单
{: #ch03-9}

| 验收项 | 命令/方法 | 期望结果 |
|---|---|---|
| sshd 配置合法 | `sshd -t` | 无错误输出 |
| 用户可建立指定隧道 | `ssh -N -L 127.0.0.1:9200:10.0.0.10:9200 alice@jump` | 本地端口可访问目标服务 |
| 白名单外目标被拒绝 | 尝试转发到未批准 IP/端口 | 连接失败，auth 日志有拒绝记录 |
| 不能获取交互 shell | `ssh alice@jump` | 不进入 shell 或立即退出 |
| 日志可见 | 查看 ES 中 `sshd-auth-*` 和 `ssh-tunnel-flow-*` | 能看到用户、来源、目标、时间 |

## 当前风险缺口分析
{: #ch04}

| 缺口 | 说明 |
|---|---|
| 目标服务看不到真实用户 | 内网 ES/DB 看到的是跳板机 IP。若目标服务本身也没有强认证，责任会被压缩成"跳板机访问了我" |
| sshd 默认日志不够 | 默认日志能记录登录成功/失败，但不足以稳定记录每个转发目标、持续时间和字节数 |
| -D 动态代理扩大边界 | SOCKS 模式允许用户访问更多目标，若无白名单和连接级审计，很容易变成内网横向通道 |
| 日志量与隐私边界 | 如果抓包或记录 HTTP 内容，容量和合规都会快速失控。应优先记录元数据 |

> **重要判断**：如果所有人共用一个 SSH 账号，再补日志也只能证明"共享账号访问过某服务"，不能证明"哪个人访问过"。这是账号体系问题，不是 ES 查询问题。

## 审计机制建设
{: #ch05}

本方案满足运维审计最常见的四个问题：谁登录、从哪登录、访问了哪些内网服务、访问规模是否异常。

### 最小审计事件
{: #ch05-1}

| 事件 | 字段 | 来源 | 用途 |
|---|---|---|---|
| SSH 登录成功/失败 | 时间、账号、源 IP、端口、认证方式、密钥指纹 | sshd / auth.log | 定位人员与入口来源 |
| SSH 会话打开/关闭 | 账号、PID、TTY、PAM session、持续时间 | PAM / journald / auditd | 建立会话时间窗 |
| 内网连接建立 | PID、UID、目的 IP、目的端口、时间 | eBPF / conntrack / auditd | 识别访问目标 |
| 内网连接关闭 | PID、五元组、字节数、持续时间 | eBPF tcpclose / flow log | 识别用量与异常长连接 |

### 关联逻辑
{: #ch05-2}

推荐生成一个 `session.id`：`jump-host + user + sshd_pid + login_time`。认证日志拿到用户和源 IP，连接日志拿到目的 IP 和端口，再通过 PID、UID、时间窗匹配到同一会话。匹配规则可以先简单后复杂：优先 PID 命中；PID 不一致时用父子进程；仍不一致时用同 UID + 时间窗 + 端口白名单做近似关联，并标记置信度。

```
session.id = sha1(host.name + user.name + sshd.pid + login.timestamp)

关联优先级：
1. connection.pid == sshd_session.pid
2. connection.ppid / ancestor_pid 命中 sshd_session.pid
3. connection.uid == session.uid 且 connection.time 在 session.time_window 内
4. 近似匹配必须加字段 attribution.confidence = low
```

> **最有价值的产出**：不是单条日志，而是"认证事件 + 连接事件"拼出的会话视图——alice 从 1.2.3.4 登录，在 12:01–12:40 访问了 10.0.0.10:9200 与 10.0.0.20:3306，累计出向 93MB。

## 日志采集：工具、方法与取舍
{: #ch06}

### sshd 日志
{: #ch06-1}

把 `LogLevel` 设置为 `VERBOSE`，可以拿到更完整的认证信息和密钥指纹。不要长期使用 `DEBUG`，它会制造大量噪声并可能暴露敏感运行细节。

```
# /etc/ssh/sshd_config
SyslogFacility AUTHPRIV
LogLevel VERBOSE
UsePAM yes
PubkeyAuthentication yes
PasswordAuthentication no
AllowTcpForwarding local
GatewayPorts no
PermitOpen 10.0.0.10:9200 10.0.0.20:3306
MaxSessions 5
ClientAliveInterval 60
ClientAliveCountMax 3
```

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

要点：没有 matchBinaries，任何进程的内网连接都记录；没有端口限制；网段按实际 VPC 裁剪。过滤在内核态完成，非内网连接零开销。挂载后重启容器生效：
```
sudo mkdir -p /var/log/ssh-tunnel && sudo chmod 750 /var/log/ssh-tunnel
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
看不到事件时按顺序排查：策略文件是否挂载成功 → sshd -T | grep permitopen 隧道是否真建立 → 目的网段是否在策略 values 内。
```
我这里就用一个简单的curl来展示流量是全记录的：
![描述](/assets/images/ssh-tunnel-audit/粘贴图-234844.png)


### 规整脚本（事件 → flow.json）
{: #ch06-3}
/usr/local/bin/tunnel_flow_filter.py（chmod +x）：
```
#!/usr/bin/env python3
# 输入：tetra getevents -o json 行；输出：规整后的嵌套 JSON 行
# 规则：不限进程、不限端口；只保留内网网段目标；同五元组 10 秒窗口聚合
import json, sys, time, ipaddress, hashlib
from collections import defaultdict

INTERNAL_NETS = [ipaddress.ip_network(x) for x in ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]]
WINDOW = 10
bucket = defaultdict(lambda: {"count": 0, "first": None, "last": None})

def is_internal(ip):
    try:
        return any(ipaddress.ip_address(ip) in n for n in INTERNAL_NETS)
    except (ValueError, TypeError):
        return False

def session_id(host, user, pid, ts):
    # 与 sshd.auth 侧同一公式，用于两边关联
    raw = f"{host}|{user}|{pid}|{int(ts)//3600}"
    return hashlib.sha1(raw.encode()).hexdigest()

def flush(now):
    for k in list(bucket):
        v = bucket[k]
        if v["last"] and now - v["last"] >= WINDOW:
            comm, host, user, pid, saddr, dst_ip, dst_port = k
            out = {
                "@timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(v["last"])),
                "event": {"dataset": "ssh_tunnel.flow", "action": "flow_summary", "count": int(v["count"])},
                "host": {"name": host},
                "user": {"name": user},
                "process": {"pid": int(pid), "name": comm},
                "source": {"ip": saddr},          # 隧道机出向地址；用户真实来源在 sshd.auth 侧
                "destination": {"ip": dst_ip, "port": int(dst_port)},
                "network": {"transport": "tcp"},
                "session": {"id": session_id(host, user, pid, v["first"])},
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
    sock = args[0] if args else {}
    dst_ip, dst_port = sock.get("daddr"), int(sock.get("dport") or 0)
    if not is_internal(dst_ip) or not dst_port:
        continue
    key = (
        (proc.get("binary") or "unknown").rsplit("/", 1)[-1],
        e.get("node_name") or "tunnel-host",
        proc.get("user_name") or "unknown",
        proc.get("pid") or 0,
        sock.get("saddr") or "unknown",
        dst_ip, dst_port,
    )
    bucket[key]["count"] += 1
    bucket[key]["first"] = bucket[key]["first"] or now
    bucket[key]["last"] = now
```

### systemd 常驻 + 日志轮转
{: #ch06-4}
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


### Filebeat 采集配置
{: #ch06-5}

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
              - "sshd\$$%{INT:process.pid}\$$: %{WORD:auth_result} %{WORD:auth_method} for (invalid user )?%{USER:user.name} from %{IP:source.ip} port %{INT:source.port}"
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

setup.template.enabled: false
setup.ilm.enabled: false
```

执行命令：`sudo systemctl restart filebeat && sudo filebeat test output`

执行后就可以把日志上传到es，产出两个索引族：sshd.auth-YYYY.MM.DD 与 ssh_tunnel.flow-YYYY.MM.DD。


### 告警规则
{: #ch06-6}
这里给一些参考项，具体还是要看企业内网安全管理实际：

| 告警 | 规则 | 处理建议 |
|---|---|---|
| 白名单外目标 | 目的 IP/端口不在批准清单 | 先断会话，再核对 Core Tunnel 配置 |
| 来源异常 | 用户从新国家/ASN/非常用网段登录 | 二次确认账号是否被盗 |
| 访问扩散 | 单会话访问内网目标数超过阈值 | 排查是否启用 -D SOCKS |
| 长连接 | 连接持续超过 8 小时或空闲过久 | 清理僵尸隧道，收紧 ClientAlive |
| 高流量 | 用户或目标流量超历史基线 | 判断是否数据导出或异常爬取 |


## 结论
{: #ch07}

SSH 隧道机是一种合理的轻量运维方案，本方案解决的问题不在"用了SSH转发"，而在上线后是否把账号、目标白名单、会话审计和容量控制补齐。安全方案的重点不是记录更多内容，而是记录正确的元数据，并把认证与连接两类证据关联起来。

网络安全管理务必要注意细节，把风险控制在合理范围的最小级别，极致的安全往往无法实现，那就做有兜底的安全。

感谢各位的观看，再见～
