---
layout: article
title: "SSH 隧道机日志审计执行手册"
subtitle: "配套《SSH 隧道机运维与审计》的落地执行版——8 步配齐认证日志、eBPF 连接观测与 session.id 关联，每步先讲清意义，再给完整配置与验收命令"
abstract: "长文讲清楚了为什么，这本手册回答怎么落地。8 个步骤覆盖 sshd 日志与基线、Tetragon eBPF 内网连接观测、tcplife 字节数统计、事件规整脚本、systemd 常驻、Filebeat 双路采集、Ingest Pipeline 关联闭环。每一步开头说明它在证据链中的位置与缺失后果，配置与验收命令成套给出，跨小时 session.id 错配、容器重建、rsyslog 前提这些坑都有对应处理。"
date: 2026-09-03
updated: 2026-09-03
reading_time: 14
topic: ssh-tunnel-audit
category: "运维安全"
author: "千里"
tags: ["运维安全", "安全审计", "检测工程", "SSH"]
toc:
  - id: m00
    title: "0. 手册定位与落地顺序"
    children: []
  - id: m01
    title: "1. sshd 日志配置：人侧证据"
    children: []
  - id: m02
    title: "2. sshd 基线配置：控制面"
    children: []
  - id: m03
    title: "3. Tetragon 连接观测：目标侧证据"
    children:
      - id: m03-1
        title: "部署"
      - id: m03-2
        title: "加载观测策略"
      - id: m03-3
        title: "验证"
  - id: m04
    title: "4. tcplife：字节数与时长"
    children: []
  - id: m05
    title: "5. 事件规整脚本"
    children: []
  - id: m06
    title: "6. systemd 常驻与日志轮转"
    children: []
  - id: m07
    title: "7. Filebeat 采集入库"
    children: []
  - id: m08
    title: "8. session.id 关联闭环"
    children: []
  - id: m09
    title: "9. 已知局限与运维要点"
    children: []
---

这本手册是《[SSH 隧道机运维与审计：从中转便利到可审计访问](/articles/ssh-tunnel-audit/)》的落地执行版。长文回答"为什么要这么设计"，手册回答"具体怎么配、怎么验收、出问题怎么排查"。所有配置与长文保持同一基线，可以按顺序直接执行。需要离线版的话，[docx 全文在这里下载](https://eastsword.github.io/assets/files/ssh-tunnel-audit-manual.docx)：https://eastsword.github.io/assets/files/ssh-tunnel-audit-manual.docx

## 0. 手册定位与落地顺序
{: #m00}

审计要回答四个问题：谁登录、从哪登录、访问了哪些内网服务、访问规模是否异常。SSH 转发把证据天然拆成两半：认证日志证明"谁连上了跳板机"，内网目标看到的来源永远是跳板机 IP。全部 8 个步骤都在服务于把两半证据重新拼合。

| 步骤 | 证据贡献 | 性质 |
|---|---|---|
| 第 1 步 sshd 日志配置 | 人侧证据：谁、从哪登录、认证方式、密钥指纹 | 必选 |
| 第 2 步 sshd 基线配置 | 控制面：PermitOpen 白名单是告警判定依据，转发方向收敛 | 建议同步上线 |
| 第 3 步 Tetragon connect | 目标侧证据：访问了哪个内网目标，进程与父进程上下文 | 必选 |
| 第 4 步 tcplife close | 用量证据：收发字节数与连接时长 | 可后置 |
| 第 5 步 规整脚本 | 控量与结构化，生成 flow 侧 session.id | 必选 |
| 第 6 步 systemd 与轮转 | 常驻化、故障自愈、本地磁盘上限 | 必选 |
| 第 7 步 Filebeat | 双路日志入 ES，dataset 分流 | 必选 |
| 第 8 步 Ingest Pipeline | auth 侧补 session.id，关联闭环 | 必选 |

落地顺序按依赖关系排，不按章节号排：

1. **第 1 步先行**。改 VERBOSE 加 reload 五分钟完事，auth 侧证据从这一刻开始积累。
2. **第 3、5、6 步一批**。Tetragon 部署 + 策略 + 规整脚本 + systemd 常驻，观测链一次拉通。验收看两点：compact 模式能看到 connect 事件、flow.json 里有规整输出。
3. **第 7、8 步收口**。Filebeat 和 Ingest Pipeline 上线当天做一次 session.id 互查，flow 侧取一条反查 auth 能命中，闭环就算成立。
4. **第 2 步基线**跟运维同步排期。PermitOpen 白名单没就位之前，"白名单外目标"这类告警上不了；只采集不收敛，审计系统记录的是一个不受限的全网代理。
5. **第 4 步 tcplife** 按需手动跑，先不常驻。

上线前确认三个前置条件：目标机 rsyslog 在跑（纯 journald 且没装 rsyslog 的系统，认证日志只进 journal 不落文件，Filebeat 采不到）；Docker 可用且 `/sys/kernel/btf/vmlinux` 存在（Tetragon 依赖 BTF）；ES（10.0.0.10:9200）从隧道机可达。密码过渡期给一个明确的关闭时间点，不然会一直"过渡"下去。

## 1. sshd 日志配置：人侧证据
{: #m01}

这一步的意义：auth 日志是"谁登录"的唯一稳定证据源。隧道账号的 shell 是 nologin，纯端口转发登录不请求会话通道，ForceCommand 不触发，图形客户端也不执行远端命令，登录留痕只能依赖 sshd 自身的认证日志。VERBOSE 级别额外记录每次认证的密钥指纹（SHA256 摘要），密钥疑似失窃时靠它区分"同一账号换了一把钥匙"。没有这一步，session.id 关联和所有"谁"维度的查询都缺少数据基础。

```
# 日志增强
SyslogFacility AUTHPRIV
LogLevel VERBOSE
```

VERBOSE 够用，不要长期开 DEBUG，它会制造大量噪声并可能暴露敏感运行细节。

改完执行 `sudo sshd -t` 校验语法，再 `sudo systemctl reload sshd` 生效。这两条是独立命令，reload 必须在注释之外单独执行，否则整段被 shell 当注释跳过，配置不会生效也没有任何报错。

平台差异：认证日志路径 Debian 系是 `/var/log/auth.log`，RHEL 系是 `/var/log/secure`，第 7 步的 Filebeat 配置两条都覆盖了。

## 2. sshd 基线配置：控制面
{: #m02}

这一步的意义：它决定审计"管什么"，是后续告警规则的判定依据来源。PermitOpen 白名单定义"哪些目标合法"，"白名单外目标"告警就是拿连接事件与这份清单比对，没有白名单告警就没有基线。AllowTcpForwarding local 封死远程转发，GatewayPorts no 防止本地转发被绑定到对外网卡，这两项决定了隧道机不会从受控中转劣化为双向暴露面。Match Group 把隧道用户与普通运维分层，日志过滤和权限审查都按这个边界来。这一步可以后于日志采集部署，但告警上线前必须补齐。

把隧道用户放入独立用户组 tunnel-users，通过 Match Group 设置更严格的转发策略，普通运维登录和隧道访问就能分层管理：

```
# 日志增强，第 1 步中的配置保留
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

验收，正向建一条白名单内隧道应成功：

```
sudo sshd -t
sudo systemctl reload sshd
ssh -N -L 127.0.0.1:9200:10.0.0.10:9200 alice@tunnel-host
```

反向验证白名单外目标应失败，客户端会收到 administratively prohibited 错误。改 PermitOpen 加新目标时同样走 sshd -t 加 reload。

## 3. Tetragon 连接观测：目标侧证据
{: #m03}

这一步的意义：conntrack、防火墙日志这类网络侧工具只能给出五元组，结论止步于"跳板机 IP 访问了 10.0.0.10:9200"；eBPF 在内核态拿到发起连接的 PID、UID 与父进程链，才能回答"哪个 sshd 会话、哪个用户发起了这次访问"，这是 session.id 能关联的前提。选 connect 事件而不是抓包，是因为审计只需要连接元数据，CIDR 过滤在内核态完成，非内网流量零开销，日志量可控。

### 部署
{: #m03-1}

```
docker run -d --name tetragon --restart always \
  --pid=host --cgroupns=host --privileged \
  -v /sys/kernel/btf/vmlinux:/var/lib/tetragon/btf:ro \
  quay.io/cilium/tetragon:v1.7.0
```

### 加载观测策略
{: #m03-2}

策略文件 `all-internal-connect.yaml`：

```yaml
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

要点：没有 matchBinaries，任何进程的内网连接都记录；没有端口限制；网段按实际 VPC 裁剪。过滤在内核态完成，非内网连接零开销。

策略文件要挂载进容器才生效，而第一次部署时没挂策略目录，所以要把旧容器删掉重建，直接再跑一条 docker run 会报 container name already in use：

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

### 验证
{: #m03-3}

```
docker exec -ti tetragon tetra getevents -o compact
```

从办公网建一条隧道并访问目标，应看到：

```
🔌 connect /usr/sbin/sshd tcp 192.168.10.5:41234 -> 10.0.0.10:9200
```

看不到事件时按顺序排查：策略文件是否在挂载目录里（宿主机 `ls /etc/tetragon/policies`），隧道是否真的建立了（`ss -tnp | grep sshd`，能看到 sshd 到内网目标的连接），目的网段是否在策略 values 内。

## 4. tcplife：字节数与时长
{: #m04}

这一步的意义：第 3 步策略只挂了 tcp_v4_connect，connect 事件不含收发字节数，"过了多少流量、连了多久"拿不到。tcplife 在连接关闭时输出一条会话总结，补上用量证据，直接支撑"长连接""高流量"两类告警。缺这一步，审计能回答"谁访问了哪"，回答不了"量是否异常"。

```
# Ubuntu/Debian：apt install bpfcc-tools，工具名为 tcplife-bpfcc
# RHEL/CentOS：dnf install bcc-tools，工具在 /usr/share/bcc/tools/
sudo /usr/share/bcc/tools/tcplife | grep sshd
```

输出形如：

```
PID    COMM    LADDR           LPORT  RADDR           RPORT  TX_KB  RX_KB  MS
1201   sshd    10.0.0.5        51234  10.0.0.10       9200   3.5    93.2   360012
```

TX_KB 和 RX_KB 是这条连接的收发总量，MS 是连接存续毫秒数，数据读的是内核 socket 里现成的统计，不抓包。

为什么不用 Tetragon 顺手挂 tcp_close：它的 sock 参数默认只带地址和端口，收发字节数拿不到，要等上游支持或自己扩展策略，不如 bcc 现成。代价是 bcc 依赖内核头文件，内核小版本升级后要重新验证。

落地节奏：connect 侧全量常驻，close 侧平时按需手动跑，字节审计做深了再考虑常驻入库。

## 5. 事件规整脚本
{: #m05}

这一步的意义：Tetragon 原始输出是深层嵌套的 jsonl，单事件体积大、字段藏得深，直接入 ES 既难查询又撑索引。规整脚本承担三件事：把字段摊平为 ECS 风格路径（user.name、destination.ip、session.id），查询和告警规则才能直接引用；同五元组 10 秒窗口聚合，高频重连压缩成一条 flow_summary，控制日志量；按公式生成 flow 侧 session.id，为第 8 步的关联准备数据。

脚本里有两个关键实现。sshd 的转发连接由无特权子进程发起，auth 日志里的 PID 是它的父进程（[priv] 监控进程），session_id 取父进程 PID 才能对上 auth 侧。Tetragon 的 kprobe 参数按类型包装，sock 类型在 args[0].sock_arg 下，直接取 args[0] 的字段会静默拿到空值。

写入 `/usr/local/bin/tunnel_flow_filter.py` 并 `chmod +x`：

```python
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

手动验证：`docker exec tetragon tetra getevents -o json | /usr/local/bin/tunnel_flow_filter.py`，建一条隧道访问内网目标，应输出一条含 session.id 的 flow_summary。

## 6. systemd 常驻与日志轮转
{: #m06}

这一步的意义：docker exec 管道不是开机自启的，宿主机重启后观测静默中断，而审计最怕的就是"以为在记、其实没记"。systemd 托管提供常驻与自愈，容器重启导致管道断开时，Restart=always 在 3 秒内重新拉起。logrotate 限定本地磁盘上限，daily 滚动保留 14 天并压缩，防止 flow.json 无限增长先于 ES 把宿主机磁盘吃满。选 copytruncate 是为了不让轮转改名后 systemd 仍写旧文件句柄。

`/etc/systemd/system/ssh-tunnel-flow.service`：

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

`/etc/logrotate.d/ssh-tunnel-flow`：

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

启动：`sudo systemctl daemon-reload && sudo systemctl enable --now ssh-tunnel-flow`。验收：`systemctl status ssh-tunnel-flow` 显示 active (running)，`tail -f /var/log/ssh-tunnel/flow.json` 有输出。

## 7. Filebeat 采集入库
{: #m07}

这一步的意义：这是日志离开宿主机的一步，也是两类证据汇合的前置。两条输入对应两类证据：认证日志（谁登录）经 grok 解析为结构化字段，连接日志（去了哪）本身是 JSON，走 ndjson 直接解析。event.dataset 把两条流分开，后续才能对不同索引做不同的字段解析、保留周期和告警查询。没有这一步，前六步的产出只是宿主机本地文件，谈不上集中检索。

`/etc/filebeat/filebeat.yml`：

```yaml
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

执行 `sudo systemctl restart filebeat && sudo filebeat test output`，产出两个索引族：sshd.auth-YYYY.MM.DD 与 ssh_tunnel.flow-YYYY.MM.DD。

三个细节要留意。第一，认证日志的路径 Debian 系是 `/var/log/auth.log`、RHEL 系是 `/var/log/secure`，上面两条都写了；但纯 journald 且没装 rsyslog 的系统，认证日志只进 journal 不落文件，filestream 一行都采不到，先确认 rsyslog 在跑。第二，grok 里 event.outcome 的值是 Accepted/Failed 字面量，不是 ECS 标准的 success/failure，查询和告警按字面值写就行，要严格对齐 ECS 可以在 Ingest Pipeline 里补一段映射。第三，setup.ilm.enabled 关掉之后 ES 侧没有自动清理，本地有 logrotate 14 天兜底，ES 侧要么补索引模板和 ILM，要么加个定时任务删过期索引，比如 `curl -XDELETE "http://10.0.0.10:9200/sshd.auth-2026.07.*"` 这样按月清。

## 8. session.id 关联闭环
{: #m08}

这一步的意义：这是整个方案的闭环动作。flow 侧的 session.id 已由规整脚本算好，auth 侧要用同一公式在写入 ES 时补上，两边才能互查，"谁登录"与"访问了哪些内网目标"才算拼到同一会话。缺这一步，两类索引各自完整，但只能按用户名加时间窗模糊对齐，人证与行为证据仍是断的。实现上用 Ingest Pipeline：脚本拼出原始串，fingerprint 处理器做 SHA-1，避开在 painless 里直接调 MessageDigest 的白名单问题。

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

两个对齐细节。fingerprint 的输出是 base64 编码，不是常见的 hexdigest，所以规整脚本里 session_id 函数也返回 base64，两边格式才一致。公式里的 host，flow 侧来自 Tetragon 的 node_name，auth 侧来自 Filebeat 的 host.name，确认两边是同一个主机名（短名或 FQDN 要一致），不一致就统一改。

flow 事件同样会经过这条管道，脚本开头的 dataset 判断会直接跳过它们，不受影响。

验证闭环，先从 flow 侧任取一条：

```
GET ssh_tunnel.flow-*/_search
{ "size": 1, "query": { "exists": { "field": "session.id" } } }
```

拿返回的 session.id 反查 auth 侧：

```
GET sshd.auth-*/_search
{ "query": { "match_phrase": { "session.id": "替换成上一步拿到的值" } } }
```

能互相查到，"谁登录"和"访问了哪些内网目标"就真正拼到同一个会话上了。

## 9. 已知局限与运维要点
{: #m09}

**跨小时边界的 session.id 错配**。公式按小时分桶，登录与首条连接跨小时边界时（例如 12:59 登录、13:01 首连），两侧小时桶不同，session.id 对不上。排查查不到关联时先看时间是否跨整点，查询时对相邻小时桶再做一次兜底，或者接受这个精度损失。

**服务重启丢聚合窗口**。规整脚本的聚合窗口在内存里，服务重启会丢掉最后 10 秒内还没落盘的聚合结果，重启挑低峰做。丢了也能补救，Tetragon 默认把原始事件导出到容器 stdout，`docker logs tetragon` 可以回放核对。

**bcc 依赖内核头文件**。tcplife 这类 bcc 工具在内核小版本升级后可能失效，升级后重新跑一次验证。

**告警对 close 侧数据的依赖**。"长连接"和"高流量"两类告警依赖 tcplife 的输出，第 4 步没常驻之前这两条告警不上线。

**密码过渡期**。PasswordAuthentication yes 是给 Core Tunnel 存量账号的过渡配置，公钥铺完后改为 no 并 reload，给这个动作一个明确的截止时间。
