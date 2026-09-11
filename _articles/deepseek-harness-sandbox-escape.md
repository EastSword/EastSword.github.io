---
title: 被沙箱关住的 AI 智能体，竟然实现了逃逸？
subtitle: CVE-2026-82533：DeepSeek Harness 沙箱逃逸的完整链条
abstract: DeepSeek Harness 用系统沙箱约束 AI 编码智能体的行为，CVE-2026-82533 却让沙箱里的智能体把会话切成完全访问模式，审批按规则不触发，沙箱被留在身后，凭据全部暴露。本文结合 OX Security
  报告与社区更早的 PoC，还原切模式、审批自答、密钥外送三条利用路径与修复遗留问题，给出从版本到凭据的自查清单。
date: 2026-09-11
author: 千里
layout: article
category: AI安全
tags:
- DeepSeek
- CVE-2026-82533
- 沙箱逃逸
- AI Agent 安全
- 提示注入
cover: ''
reading_time: 22
---

DeepSeek 八月开源了 AI 编码智能体运行框架 DeepSeek Harness（npm 包 `@deepseek-ai/dsh`，命令行 `dsh`），上线三周已经在 GitHub 拿下超过 22 万颗星。它的卖点是本地优先，浏览器界面加一个只监听 `127.0.0.1:3080` 的 HTTP 服务，插件化架构，智能体的命令跑在操作系统沙箱里，Linux 用 bubblewrap 或 Landlock，macOS 用 Seatbelt，Windows 用受限令牌加 ACL，写操作被限制在工作区目录内。

![图片](/assets/uploads/20260911-772cfd5dec.webp)

在设计中，沙箱存在的意义很明确。智能体经常要处理不可信内容，读来路不明的仓库、解析别人发来的文件，沙箱就是安全的硬边界，如果发生安全事件也限制在工作区里。

![图片](/assets/uploads/20260911-89387687d4.webp)

9 月 8 日，OX Security 的研究团队发布了 CVE-2026-82533，**被关在沙箱里的智能体，可以用一条 shell 命令把所在会话切成完全访问模式。** 此后它执行的每一条命令都不再受沙箱约束，也不再需要人点确认。

![图片](/assets/uploads/20260911-e27e35b8f4.webp)

| 项目 | 说明 |
|---|---|
| 漏洞编号 | CVE-2026-82533（VulnCheck 分配，2026-09-08 发布） |
| 评分 | CVSS 4.0 = 9.4，向量 AV:N/AC:L/AT:N/PR:N/UI:P；CVSS 3.1 = 9.6 |
| 缺陷类型 | CWE-807，在安全决策中依赖不可信输入 |
| 受影响版本 | 0.1.1-rc.2 及更早，默认安装即受影响 |
| 修复版本 | GitHub 0.1.2-alpha.1（8/27）；npm 上第一个带修复的是 0.1.2-alpha.2（8/30） |
| 触发条件 | 本地路径需要智能体读到攻击者可控文本；远程路径需要端口经隧道或转发暴露 |
| 报告方 | Nir Zadok、Moshe Siman Tov Bustan（OX Security） |

整个利用不要求网络暴露，不要求凭据，不要求改动任何配置。唯一的前提是智能体执行了一条被攻击者文本诱导的命令，沙箱本来要防的场景也在这一块，可以说这是在沙箱脸上挑衅的行为。

本文把三条利用路径放在一起还原，包括 OX 报告的切模式主链，以及社区更早报出的审批自答链和密钥外送链。技术细节整理自 [OX Security 的分析](https://www.ox.security/blog/cve-2026-82533-deepseek-harness-ai-agent-sandbox-escape/)、VulnCheck 的 CVE 公告、奇安信 QVD-2026-57410，以及项目自身的公开材料，包括讨论区 [#250](https://github.com/deepseek-ai/deepseek-harness/discussions/250) 与 [#853](https://github.com/deepseek-ai/deepseek-harness/discussions/853)、沙箱实现源码、修复提交 3e24087 与配套设计文档、npm 发布记录，核对时间为 9 月 11 日。OX 原文配图版权归原作者所有，引用仅作技术分析。

## 沙箱到底管什么：把三个平台的实现读一遍

要理解逃逸，先要看清沙箱的真实边界。项目自己的沙箱文档中写明，`SandboxMode` 只治理文件系统效果，网络和进程可见性不在它的管辖范围里，这是官方明确的能力说明（不做反向思考的话，其实真没人会觉得有什么缺失）。这句话在文档里出现了两次，是明确的边界声明，不是笔误。

实现在 `packages/sandbox/sandbox-local/src/profiles.ts`，三个平台的配置值得逐行读。先看 Linux 的 bubblewrap 实现。

```ts
export function bwrapProfileArgs(policy: SandboxPolicy): string[] {
  const args = ['--ro-bind', '/', '/', '--dev', '/dev',
    '--unshare-pid', '--proc', '/proc', '--die-with-parent']
  if (policy.mode === 'workspace-write') {
    args.push('--tmpfs', '/tmp')
    args.push('--bind', policy.workspaceRoot, policy.workspaceRoot)
  }
  return args
}
```

整个根文件系统以只读挂载，`--unshare-pid` 隔离了进程号空间，`workspace-write` 模式下把工作区目录以读写 bind 挂进来，外加一个全新的 `/tmp`。参数列表里没有 `--unshare-net`，也就是说网络命名空间和宿主机完全共享。

Landlock 是同一个策略的另一种写法。

```ts
export function landlockProfileArgs(policy: SandboxPolicy): string[] {
  const readWrite = ['/dev/null']
  if (policy.mode === 'workspace-write') {
    readWrite.push('/tmp', policy.workspaceRoot)
  }
  return landlockGrantArgs({ readOnly: ['/'], readWrite })
}
```

可写清单里只有 `/dev/null`、`/tmp` 和工作区，其余全部只读。macOS 的 Seatbelt 配置最能说明设计取向。

```ts
const forms = ['(version 1)', '(allow default)', '(deny file-write*)',
  '(allow file-write* (literal "/dev/null"))', /* 各可写根逐条放行 */]
```

`(allow default)` 打底，没被明确拒绝的一律放行，上面只叠一条 `(deny file-write*)`。翻译成人话，文件写入被拒绝，其余一切默认允许，网络就在「其余一切」里。

![图片](/assets/uploads/20260911-431a9ca82b.webp)

总的来说，三个平台殊途同归，**文件读权限是放开的，写权限被圈在工作区，网络从头到尾没人管。** 8 月 14 日腾讯安全团队针对 0.1.0-rc.5 发布的四漏洞评审里，第二个 PoC 实测**在 read-only 模式下读到了工作区外的凭据文件**。这种缺失不是无意疏漏，而是设计取向。但它和使用者对「沙箱」二字的默认理解之间，差着一整个威胁模型。

## 控制面分析

沙箱的安全设计缺陷还不足以直接逃逸，攻击成功的另一个更关键的因素是控制智能体的本地 HTTP 服务，有三个设计上的特点。

- **控制面监听在环回地址。** 浏览器界面需要一个本地 HTTP 服务来控制智能体，这个服务绑在 `127.0.0.1:3080`。绑环回是对的做法，但它对沙箱里的进程不构成任何屏障，因为智能体本来就在同一台机器上，环回地址对它和对你一样可达。

- **地址和会话身份是主动递过去的。** 每次 shell 调用都会带上一组托管的 `DSH_*` 环境变量，包括 `DSH_HOME`、`DSH_SHELL=1`、`DSH_SESSION_ID`，Web 模式下还有 `DSH_WEB_URL`。本意是给智能体提供环境常识，结果是接口地址和「我是哪个会话」两样东西都不用自己找。

- **接口的访问判断只读 Host 头。** 一个叫 `isTrustedApiRequest` 的函数承担了所有请求的信任判断。

```ts
export function isTrustedApiRequest(request: ApiTrustRequest,
    trustedHosts: readonly string[]): boolean {
  // Host fence (DNS-rebinding defense): the browser fills Host
  // from the URL it believes it is talking to, so a rebound page
  // carries the attacker's domain here even though the socket
  // lands on this server.
  const host = header(request.headers, 'host')
  if (host === undefined) return false
  const hostUrl = parseAuthority(host)
  if (hostUrl === undefined) return false
  // …命中环回地址或 trustedHosts 白名单即放行
}
```

![图片](/assets/uploads/20260911-ed2de9233a.webp)

它取请求头里的 Host 值，命中环回地址或者 `--trusted-host` 白名单就放行，从未核对过这个值与 TCP 连接的实际来源是否一致。

这个缺失非常致命。Host 检查本来防的是 DNS 重绑定，也就是攻击者把域名解析到 127.0.0.1，骗用户的浏览器去访问本地服务；对付浏览器这招有效，因为浏览器不允许脚本伪造 Host 头。但 `curl` 这类不受浏览器约束的客户端，或者沙箱里的智能体，可以随便写。#853 里报告者引用的代码注释自己就说「这不是认证层」，项目后来的修复设计文档也承认，HTTP 接口从请求头识别特权调用方，而 Host 值是客户端控制的。

沙箱不管网络、控制面在本机可达、地址和会话身份主动递过去、访问判断可以随意伪造，四个事实叠在一起，构成了完整链路。

![图片](/assets/uploads/20260911-6b457c49aa.webp)

接下来把三条逃逸链依次展开。

## 逃逸链一：一条命令实现逃逸

OX 报告的主链短得有点打人脸。沙箱里的智能体用一条普通 shell 命令调用相关接口，就可以把当前会话切成 `danger-full-access`，审批策略改成 `never`，最后实现逃逸。OX 发布的原图里，命令全文如下。

![图片](/assets/uploads/20260911-04eded9a1e.webp)

```bash
curl -s -X POST http://127.0.0.1:3080/api/commands/execute \
  -H 'Host: 127.0.0.1:3080' -H 'Content-Type: application/json' \
  -d '{"type":"client-request","rpcId":"esc","method":"commands/execute",
       "payload":{"args":{"agentId":"escape-poc",
                          "line":"/permission danger-full-access","images":[]}}}'
```

这条命令里看不到任何「逃逸」才需要的东西，它只是一个 HTTP POST，发往本机端口，Host 头写着环回地址，载荷里是一条斜杠命令。根据沙箱只管文件写入的特性（而它一个文件都没写），这完全是一条正常的命令。

然而这条命令运行完之后，智能体执行的每一条命令都在沙箱外，后续任何操作也不会再弹出确认框等人点头。

会话日志记录了策略被改写的全过程。

![图片](/assets/uploads/20260911-e395bc7303.webp)

`permission/preset` 从 `workspace-write` 变成 `danger-full-access`，`sandbox/mode` 跟着切换，`approval/policy` 从 `ask` 变成 `never`，最后 `command/done` 报告 success。这份日志里有两个细节值得单独看。

从日志里可以看到，整个过程中没有出现任何 `approval/request` 事件。审批机制的判定条件，是看「这条命令要的权限，是不是超过了会话已有的权限」。修改会话设置这个动作本身没有超出当前权限，所以不触发；改完之后，所有命令都在新的权限之内，也不触发。一切都是产品原本设计的「正常功能」，所以在当时的版本里不会产生任何有效告警。

另一个有意思的细节是，日志把这次策略变更记录为 `source: {kind: 'user'}`，这说明框架甚至分不清智能体自己的 shell 和键盘前的人。

为了排除「沙箱本来就没启用」的解释，研究者做了对照实验，在同一台机器上用同样的默认配置开两个会话，发同样的命令，区别只是一个会话先执行了那条切换模式的调用。

![图片](/assets/uploads/20260911-22c741c8bf.webp)

结果，先切换的会话成功写入了 `/home/ubuntu/ESCAPED-PROOF`，位置在工作区之外，进程还在 `sudo` 组里；另一个会话的同一命令被沙箱挡住，`CONTROL-DENIED` 没有写成。沙箱此前在正常工作。

## 逃逸链二：审批队列被智能体自己消费掉

切模式这条链有个显眼的破绽，会话状态从 `ask` 翻到 `never`，事后审计一眼就能看出来。社区更早挖出的第二条链没有这个问题，**它不动策略，而是把人在审批队列里的放行，自己替自己答掉。**

8 月 13 日，GitHub 仓库创建当天，用户 mxym 在讨论区发帖（#250），在默认的 `workspace-write` 加 `ask` 审批配置下复现了完整流程。机制分两步。

智能体请求提升权限时，框架往审批队列放一个 `approval/requested` 事件，等人在浏览器界面点确认。这个事件会经 `/api/events.mux` 的 WebSocket 流**广播给所有订阅者**，沙箱里的进程也在订阅者之列，它读一下 `$DSH_WEB_URL` 就知道去哪订阅。而审批的答复接口 `POST /api/respond` 同样不验证调用方身份，带上传回来的 `rpcId` 和 `outcome: "allowed-once"` 就能替人放行。

发帖人贴出的端到端验证输出里面，可以发现 Landlock 沙箱内的子进程连上 mux 流、收到广播的审批帧、自己回了 `allowed-once`，宿主侧待审批的 `danger-full-access` 命令随即以 `outcome: "allowed-once"` 放行，最终输出 `SANDBOX_APPROVAL_PROOF … {"accepted":true}`。

这样，整条逃逸链的过程里面，人没有点过任何确认框。

同一帖子里还单独验证了网络前提，Landlock 子进程直接访问宿主机环回端口，输出 `HTTP/1.0 200 OK` 和 `NETWORK_PROOF=CONFIRMED`。bubblewrap 没传 `--unshare-net`，Landlock 的授权清单里根本没有「网络」这个词。上一节读过的实现，在这里兑现成了攻击面。

这条链的隐蔽性在于会话表面上一切如常，审批策略还是 `ask`，界面还会弹确认框，审计日志里也是一次「正常」的放行，只是按确认键的不是人。报告者把根因总结成一句话，**环回可达不等于人类授权**。线协议只证明「谁知道这个请求存在」，不证明「按确认键的是谁」。他当时提出的修复建议，包括不可导出的浏览器专属能力、审批答复绑定到已认证的 UI 连接、把「沙箱子进程不能给自己批权限」做成产品级回归测试。这和两周后官方修复的思路几乎一致。

## 逃逸链三：改一个设置，密钥按次外送

前两条链的落点是命令执行，第三条链瞄准的是凭据，而且更安静。

`settings.update` 是一个特权方法，本来只有界面能调。在无认证的前提下，它可以把内置搜索工具 `web-search-deepseek` 的 `baseURL` 改成任意地址，比如攻击者控制的服务器。之后智能体每次发起搜索，请求都会带着 `x-api-key` 和 `Authorization: Bearer` 两套凭据头发向新地址。**密钥按次外送，持续到有人发现为止**，而会话里看起来只是搜索功能「坏了」。

#853 里独立报告了同族问题，`llm.discoverModels` 会把存储的供应商密钥发往调用方指定的 URL。两个入口一个思路，配置面里的敏感字段可以被无认证改写或指路，而配置面恰恰是权限最高的平面。对一个经常在会话里配着各家模型密钥的开发工具来说，这条链的杀伤不比命令执行小，被送出去的密钥，和你贴进对话里的 `.env` 文件，最终是同一批凭据。

## 端口一旦被转发，就是未授权远程接管

另外，同一个根因还有第二条利用路径，CVSS 评分里的 AV:N（网络可达）、PR:N（无需权限）来自这里。只要端口被转发出去，未授权访问就从理论变成了现实。

看下面这两个除了 Host 头之外完全相同的请求。

![图片](/assets/uploads/20260911-407cf051bc.webp)

`Host: evil.example` 得到 403，`Host: 127.0.0.1:3080` 得到 200。既然判断只看客户端自己填的 Host 头，请求从哪里发出就不重要，因为只要能到达那个端口，把 Host 写成 `localhost`，服务端就认。

暴露面在 8 月 14 日就被报告了，#853 指出 Web 服务对外提供约 60 个 RPC 方法，全部跑在无 token、无 Cookie、无 TLS 的明文 HTTP 上，唯一的防护手段就是这道 Host/Origin 栅栏。在报告中，报告者用三步完成远程利用，先在创建会话时指定工作目录，再切 `danger-full-access`，最后发提示词驱动 bash，大约 60 秒后标记文件就出现在磁盘上。

dsh 的命令行拒绝 `--host 0.0.0.0`，默认不会对外监听。但「端口被转发到别处」在开发场景里太常见了。VS Code 和 Cursor 的 Remote-SSH 会自动把检测到的端口转发到本地，`ssh -L` 手工转发，ngrok、Cloudflare Tunnel 这类工具做临时公网暴露，开发容器或跳板机前面挂反向代理。这些都不是异常操作。

那么这种远程路径的危害怎么样呢？不用讲也能想到，它比来自本地路径的攻击风险高多了，未认证的攻击者可以完全控制智能体。此外，同一个接口还能不带任何凭据下载全部会话日志。对话历史里有内部代码片段、报错栈里的路径和主机名、粘贴进去的配置，有的用户还会直接贴进去密钥。这部分损失即使升级了版本也无法追回，排查时应把它当作独立的「数据泄露事件」来评估，而不是顺带的影响。

## 反思：维护者说「不算安全问题」

| 时间 | 事件 |
|---|---|
| 8/10 | 首个版本 0.0.1-rc.1 发布到 npm |
| 8/13 | GitHub 仓库创建；同日，开发者 mxym 在讨论区报告审批自答逃逸路径，附完整 PoC（[讨论 #250](https://github.com/deepseek-ai/deepseek-harness/discussions/250)） |
| 8/14 | 开发者 OracleNep 报告接口无凭据接受请求、约 60 个 RPC 方法无认证，并指出项目没有安全策略文件和私下报告渠道（[讨论 #853](https://github.com/deepseek-ai/deepseek-harness/discussions/853)）；同日，腾讯安全团队发布针对 0.1.0-rc.5 的四漏洞评审 |
| 8/21 | 0.1.1-rc.2 发布到 npm，受影响的最后一个版本 |
| 8/24 | OX 复现确认，当天报告 VulnCheck；修复提交 3e24087 于同日落库；同日，奇安信以 QVD-2026-57410 独立披露，CVSS 3.0 = 9.8，评级「极危」，PoC 已公开 |
| 8/26 | 项目成员在 #853 回应，称行为「有意为之」，保持绑定 127.0.0.1 即可，这份报告「没有意义，只是一份风险评估」 |
| 8/27 | GitHub 打出 0.1.2-alpha.1 标签，未发布到 npm |
| 8/30 | 0.1.2-alpha.2 发布到 npm，npm 上第一个带修复的版本；OX 当天验证修复有效 |
| 9/3 | 0.1.2-rc.1 发布，成为 npm latest |
| 9/8 | VulnCheck 发布 CVE-2026-82533 |

其实出现安全问题，并没什么可怕的。可怕的是面对公开 PoC 时维护者表现出的态度，这说明未来再次翻车的概率很大。看上面的时间线，有三处值得注意。

社区在 8 月 13 日和 14 日就报出了完整的路径，比 OX 的报告早十天。项目当时没有 SECURITY.md，也没有私下报告渠道，这两份报告只能公开发在讨论区。8 月 24 日，奇安信还以 QVD-2026-57410 独立披露了同一问题，描述的机制相同，都是伪造请求头绕过对本地 API 的信任判断，可以说国内的披露比 VulnCheck 发布 CVE 早了两周。

有意思的是，**维护者在 8 月 26 日回应了。** 面对完整 PoC，官方立场是行为符合设计、绑环回就够了、报告「没有意义」。九天后，同一个接口被外部研究团队以 CVSS 9.4 报成 CVE。平心而论，「绑环回挡住浏览器远程攻击」作为设计取向说得通，问题在于把「默认配置下够用」当成了「安全边界」，这个威胁模型里没有同机的恶意进程，没有端口转发，也没有沙箱里的智能体，而这三个角色在真实使用里都存在。评估一个框架时，维护者对公开 PoC 的回应姿态，比单个漏洞更能说明修复会以什么质量到来。

修复也没有作为安全事项对外通报。0.1.2-rc.1 的发布说明把这次改动混在常规变更里，写成「移除旧传输层」和「网络访问要求一次性令牌认证」，没有安全提示，没提 CVE。到 9 月 10 日，仓库仍然没有 SECURITY.md，GitHub 安全公告列表仍然为空。对使用方的实际影响是，订阅这个仓库的公告不会告诉你该升级了，依赖扫描工具能不能命中，则取决于它有没有接入 VulnCheck 的数据源。修复版本还有一段分发滞后，GitHub 上的 0.1.2-alpha.1 从未发布到 npm，npm 上第一个带修复的版本是 8 月 30 日的 0.1.2-alpha.2。

## 修复思路

从根因上来说，给接口加上真正的认证，才能彻底修复。官方 8 月 24 日的提交 3e24087（115 个文件，+1615/−520 行）是本次修复的核心，新增了 `browser-auth.ts`。

进程启动时生成一个随机令牌，打印在启动 URL 的查询参数里。只有 `GET /?token=...` 这一条路径能把令牌换成签名 Cookie，然后跳回干净的 `/`。令牌在 API 路径上不被接受，也不能放进 Authorization 头。代理方法、远程调用、连接通道、WebSocket 流，所有 API 统一要求同一个浏览器会话。这取代了原来按方法划分特权清单的做法，那种清单总会漏掉新加的端点。

修复提交里有两个细节能看出设计者想清楚了。其一，测试明确断言**伪造的环回 Host 头不再能建立身份**，Host 和 Origin 被降级为「仅路由证据」，`--trusted-host` 从信任来源降级为只扩栅栏、不授身份。#853 里那句「这不是认证层」的注释，至此才被代码追认。其二，覆盖是全量的，`settings.describe`、`credentials.describe`、模型目录，每一个 Host 方法都要求同一个浏览器会话；同时配置面的密钥掩码独立于认证存在，即使认证层再出问题，密钥也不会明文回给调用方。

Host 和 Origin 检查保留下来，但降级为它本来该干的活，只防 DNS 重绑定和跨站请求，失败返回 403。Host 可信但没有有效会话，返回 401。两件事分开了。

为什么不直接核对 TCP 连接的对端地址？修复设计文档正面回答了这个多数人的第一反应，在有代理和端口转发的现实里，「连接来自本机」从来不等于「操作来自本机用户」。

Cookie 是 HMAC 签名的持有者凭据，`HttpOnly`、`SameSite=Strict`、绑定授权域、默认 30 天有效，不带 `Secure`，因为服务跑的是环回 HTTP。撤销的办法是删除 `$DSH_HOME/.credentials.yaml` 里的记录并重启进程，已发出的 Cookie 全部失效。

### 仍然没有解决的问题

修复解决的是「谁能调这个接口」，没有动「沙箱管什么」。当前版本的沙箱文档里，能力边界原封未动，依然只治理文件系统效果；智能体的 shell 依然拿到 `DSH_WEB_URL`，依然能访问那个端口，只是现在会拿到 401。「沙箱不限制读」这一点，已经从源码和实测两个方向得到证实。

而凭据的存放位置制造了一个新问题。撤销凭据要删的 `.credentials.yaml` 在 `$DSH_HOME` 下，`DSH_HOME` 的路径通过环境变量主动交给了智能体，沙箱对读不设防，沙箱一节里腾讯团队的 PoC 证实过这个事实。三者拼起来，**修复后的凭据文件，对沙箱内的智能体可读。** 读走之后能造成什么影响，公开材料里没有验证；这个事实本身，值得在下一轮修复里解决。

0.1.2-rc.1 的发布说明里有一句安全声明值得原样记住，DeepSeek Harness 未经过安全审计，沙箱、审批和权限机制不保证隔离性。

## 自查：从版本到凭据

作为使用者，先要确认版本，而且不能只看「我最近装的」。全局安装、npx 缓存、项目内依赖、第三方桌面应用打包的副本，是四个各自独立的位置。

```
# 全局安装
npm ls -g --depth=0 @deepseek-ai/dsh

# npx 缓存（很多人是 npx 直接跑的）
ls ~/.npm/_npx/*/node_modules/@deepseek-ai/dsh/package.json 2>/dev/null \
  | xargs -I{} grep -H '"version"' {}

# 项目内依赖
grep -rn '@deepseek-ai/dsh' . --include=package.json --include=package-lock.json \
  --include=pnpm-lock.yaml --include=yarn.lock

# 第三方桌面应用打包的副本（macOS 示例）
find /Applications ~/Library/Application\ Support -maxdepth 6 \
  -path '*@deepseek-ai/dsh/package.json' 2>/dev/null
```

判定标准是 0.1.1-rc.2 及更早都受影响，升级到 0.1.2-alpha.2 或更高。注意 CVE 记录里写的修复版本 0.1.2-alpha.1 在 npm 上装不到，不要照着它去指定版本。社区有个 Windows 桌面封装（[flaqai/open-deepseek-harness-desktop](https://github.com/flaqai/open-deepseek-harness-desktop)，非官方），8 月 27 日发布的版本对应上游 0.1.1-rc.2，正好是受影响的最后一个版本；8 月 30 日带修复的 0.1.2-alpha.1 进入它的预发布渠道，9 月 1 日转正。第三方打包的版本节奏由封装方决定，上面的命令查不到它，要到应用的关于页里单独确认。

接着查端口有没有被转发出去。这是判断「有没有被远程接管过」的关键。

```
# 确认监听只在 127.0.0.1
lsof -nP -iTCP -sTCP:LISTEN | grep -i node

# 存活的 SSH 端口转发
ps aux | grep -E 'ssh .*-[LR] ' | grep -v grep

# 隧道类工具
ps aux | grep -E 'ngrok|cloudflared|frpc|localtunnel' | grep -v grep
```

编辑器的 Remote 转发记录和反向代理配置也要看，它们不落在上面任何一条命令里。

然后查沙箱外的痕迹。如果曾在受影响版本上让智能体处理过外部仓库、issue 或网页内容，按「可能被执行过任意命令」来查。工作区之外的文件改动，重点是 `~/.ssh/`、`~/.zshrc`、`~/.bashrc`、`~/.gitconfig`、`~/Library/LaunchAgents/`、`~/.config/systemd/user/`；翻一遍 `$DSH_HOME`（默认 `~/.dsh`）下的会话记录，确认里面有多少敏感内容、有没有不认识的会话；有网关侧流量日志的话回溯异常外联。

凭据按「那台机器能碰到什么」轮换。开发机上通常没有足够的日志证明「没发生过」，只要满足过触发条件，比如处理过不可信内容或端口被转发过，就按已暴露处理，轮换 SSH 私钥、云 AK/SK、`.env`、各类 CLI 的本地 token、浏览器保存的凭据，以及 npm / PyPI / 容器仓库的发布 token。发布类凭据优先级最高，它是二次投毒的跳板。

暂时无法升级的话，不用的时候把 Web 界面关掉，清掉所有能到达这个端口的隧道、代理和端口转发，包括编辑器自动建立的那些，也不要用它处理不可信内容。最后这条是唯一能可靠断掉本地路径的办法。公开材料里没有任何方式能在默认本地安装、工具运行期间从沙箱内部阻止这次逃逸；8 月 13 日那份社区报告也明确指出，限制监听地址没有用，因为智能体本来就在同一台机器上。

## 五条反思

**被限制的主体不能同时是限制的管理者。** 智能体被沙箱约束，同时又能调用决定沙箱模式的接口，权限模型就成了一个环。做智能体框架可以直接拿这条自查，控制面对被控主体是否可达？可达的话，它有没有独立于被控主体的身份验证？

**审批机制要防「改规则」，不只是「破规则」。** 这次审批没有被绕过，它是被正确地没有触发，判定条件是「命令权限是否超出会话权限」，而攻击改的是会话权限本身。第二条链走得更远，审批事件广播给所有订阅者，答复接口不问身份，队列本身成了攻击面。任何「会话级策略 + 逐次审批」的设计都要同时回答这两个问题，修改策略的操作本身需不需要审批？审批的放行动作怎么证明是人做的？

**沙箱的边界要写清楚，用户才知道它挡不住什么。** 这个项目的文档其实写得很实在，「只治理文件效果」这句话反复出现过。问题在于，用户听到「沙箱」两个字，默认理解是完整隔离。文档的诚实和用户的理解之间的落差，会一直被利用。评估任何智能体产品的沙箱，第一个问题应该是它管哪几个维度，不管哪几个。

**本地接口不等于可信接口。** 「只绑 127.0.0.1 就不用做认证」这个假设在两个方向上同时失效。往内，同机的任何进程都能访问；往外，隧道和端口转发让「本机」这个概念变得模糊。用 Host 头判断来源，等于让调用方自己填身份。这个模式不是这个项目独有，本地起 HTTP 服务的开发工具都值得照着查一遍。

**提示注入现在有了完整的落点。** 过去讨论提示注入，危害往往停在「让模型说错话」。这次给出的完整链条，从不可信文本开始，到智能体执行一条命令，再到自身沙箱失效，最后是开发机上的凭据全部暴露。做安全评估时，「模型被诱导后能调用什么」比「模型会不会被诱导」更值得投入，前者可以工程化地收敛，后者目前还不能。

给智能体套上沙箱来对抗不可信内容，却把决定沙箱模式的控制面放在沙箱够得着的地方，还主动把它的地址和会话身份交到智能体手上，这非常荒谬。

被限制的主体不能同时是限制的管理者，这条在传统权限模型里是常识，真没想到，还要在智能体框架里重新证明一遍。人类什么时候能不在同一个坑里跌倒？或许，这就是历史轮回的必然。
