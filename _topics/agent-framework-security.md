---
published: true
layout: topic
title: Agent 框架安全
subtitle: 从 CVE-2026-82533 DeepSeek Harness 沙箱逃逸出发，检验 Agent 框架的沙箱、审批与控制面设计
date: 2026-09-12
updated: 2026-09-12
status: 研讨中
keyword: AGENT
categories: [AI安全]
tags: [AI 安全, 沙箱逃逸, 提示注入, 权限边界]
dao_summary: "被限制的主体不能同时是限制的管理者——智能体被沙箱约束，却够得着决定沙箱模式的接口，权限模型就成了环。\n审批机制要防「改规则」，不只是「破规则」；沙箱的边界要写清楚，用户才知道它挡不住什么；本地接口不等于可信接口。\n提示注入现在有了完整的落点，「模型被诱导后能调用什么」比「模型会不会被诱导」更值得投入。"
fa_summary: "三条逃逸链共用一个根因。伪造 Host 头调用本地控制面，把会话切成 danger-full-access，审批按规则不触发；订阅审批事件流自答 allowed-once，人没有点过确认；改写工具 baseURL，让搜索密钥按次外送。\n端口一旦被转发，根因就长出未授权远程接管和无凭据下载会话日志的第二条路径。"
shu_summary: "自查按四步走。版本在全局安装、npx 缓存、项目依赖、第三方打包四个独立位置各查一遍；端口查监听地址、SSH 转发与隧道工具；处理过不可信内容就按任意命令已执行排查沙箱外痕迹；凭据按机器能碰到的范围轮换，发布类优先。\n无法升级时，关 Web 界面、清隧道、不喂不可信内容。"
qi_summary: "外部依据收 OX Security 的漏洞分析、讨论区 #250 与 #853 两份社区报告、沙箱实现源码与修复提交 3e24087，以及奇安信 QVD-2026-57410。\n来源以官方仓库和报告方原文为准，核对时间为 2026-09-11。"
dao:
  - title: 被限制的主体不能同时是限制的管理者
    text: 智能体被沙箱约束，同时又能调用决定沙箱模式的接口，权限模型就成了一个环。做智能体框架可以直接自查：控制面对被控主体是否可达？可达的话，它有没有独立于被控主体的身份验证？
    type: 原创
    platform: 本课题
  - title: 审批机制要防「改规则」，不只是「破规则」
    text: 判定条件是「命令权限是否超出会话权限」，而攻击改的是会话权限本身；审批事件广播给所有订阅者、答复接口不问身份时，队列本身成了攻击面。修改策略的操作本身需要审批，放行动作要能证明是人做的。
    type: 原创
    platform: 本课题
  - title: 沙箱的边界要写清楚，用户才知道它挡不住什么
    text: 用户听到「沙箱」默认理解是完整隔离，文档的诚实和用户的理解之间的落差会一直被利用。评估任何智能体产品的沙箱，第一个问题是它管哪几个维度，不管哪几个。
    type: 原创
    platform: 本课题
  - title: 本地接口不等于可信接口
    text: 「只绑 127.0.0.1 就不用做认证」往内对同机进程失效，往外被隧道和端口转发瓦解。用 Host 头判断来源，等于让调用方自己填身份。本地起 HTTP 服务的开发工具都值得照着查一遍。
    type: 原创
    platform: 本课题
  - title: 提示注入现在有了完整的落点
    text: 过去讨论提示注入，危害往往停在「让模型说错话」。这次给出的是完整链条，不可信文本到智能体执行命令、自身沙箱失效、开发机凭据全部暴露。「模型被诱导后能调用什么」可以工程化地收敛，「会不会被诱导」目前还不能。
    type: 原创
    platform: 本课题
fa:
  - title: 伪造 Host 头切换会话权限
    text: 沙箱内的智能体用一条普通 shell 命令调用 127.0.0.1:3080 的接口，把会话切成 danger-full-access、审批改成 never。审批判定的是「命令权限是否超出会话权限」，改会话设置的动作不触发审批，改完之后一切都在新权限之内。
    type: 原创
    platform: 本课题
  - title: 审批队列自答放行
    text: approval/requested 事件经 WebSocket 流广播给所有订阅者，沙箱内进程读 DSH_WEB_URL 订阅后，POST /api/respond 自己回 allowed-once。会话表面上一切如常，审计日志里是一次「正常」放行，按确认键的不是人。
    type: 原创
    platform: 本课题
  - title: 改写工具端点外送密钥
    text: 无认证调用 settings.update 把搜索工具 baseURL 改向攻击者服务器，此后每次搜索都带着 x-api-key 和 Bearer 凭据发往新地址；llm.discoverModels 同样会把存储的供应商密钥发往调用方指定 URL。密钥按次外送，持续到被发现为止。
    type: 原创
    platform: 本课题
  - title: 端口转发后的远程接管
    text: 信任判断只看客户端填的 Host 头，请求从哪里发出就不再重要。约 60 个 RPC 方法跑在无 token、无 Cookie、无 TLS 的明文 HTTP 上，三步完成远程利用；同一个接口还能无凭据下载全部会话日志，应按独立数据泄露事件评估。
    type: 原创
    platform: 本课题
shu:
  - title: 版本四位置核查
    text: 全局安装、npx 缓存、项目内依赖、第三方桌面应用打包的副本是四个独立位置，逐一查版本。0.1.1-rc.2 及更早受影响，升级到 0.1.2-alpha.2 或更高；CVE 里写的 0.1.2-alpha.1 在 npm 上装不到，不要照抄。
    type: 原创
    platform: 本课题
  - title: 端口与隧道排查
    text: 确认监听只在 127.0.0.1，排查存活的 SSH 端口转发与 ngrok、cloudflared、frpc、localtunnel 等隧道进程，编辑器的 Remote 转发记录和反向代理配置单独看，它们不落在通用命令里。
    type: 原创
    platform: 本课题
  - title: 沙箱外痕迹与凭据轮换
    text: 处理过不可信内容或端口被转发过，就按可能执行过任意命令排查：工作区外的文件改动重点看 .ssh、shell 配置、LaunchAgents、systemd user；翻 $DSH_HOME 会话记录。凭据按机器能碰到的范围轮换，发布类 token 优先，它是二次投毒的跳板。
    type: 原创
    platform: 本课题
  - title: 无法升级时的临时缓解
    text: 不用时关掉 Web 界面，清掉所有能到达端口的隧道、代理和转发，包括编辑器自动建立的，不用它处理不可信内容。最后这条是唯一能可靠断掉本地路径的办法，限制监听地址没有用。
    type: 原创
    platform: 本课题
qi:
  - title: OX Security 漏洞分析
    text: CVE-2026-82533 的首发技术分析，含逃逸链、会话日志与对照实验证据。
    type: 转载
    platform: 报告方原文
    url: https://www.ox.security/blog/cve-2026-82533-deepseek-harness-ai-agent-sandbox-escape/
    desc: Nir Zadok、Moshe Siman Tov Bustan，OX Security Research
    stars: 5
  - title: 社区报告 讨论区 #250
    text: 8 月 13 日 mxym 报告审批自答逃逸路径，附端到端 PoC 与修复建议，早于 OX 十天。
    type: 转载
    platform: 项目讨论区
    url: https://github.com/deepseek-ai/deepseek-harness/discussions/250
    desc: 含 NETWORK_PROOF 与 SANDBOX_APPROVAL_PROOF 两组验证输出
    stars: 4
  - title: 社区报告 讨论区 #853
    text: 8 月 14 日 OracleNep 报告约 60 个 RPC 方法无认证，三步远程 RCE，并指出缺少安全策略；8 月 26 日维护者在此回应「不算安全问题」。
    type: 转载
    platform: 项目讨论区
    url: https://github.com/deepseek-ai/deepseek-harness/discussions/853
    desc: 披露过程与维护者态度的一手记录
    stars: 4
  - title: 沙箱实现与修复提交
    text: profiles.ts 三个平台的沙箱配置，与修复提交 3e24087（115 文件，+1615/−520）的 browser-auth.ts 统一认证。
    type: 转载
    platform: 项目源码
    url: https://github.com/deepseek-ai/deepseek-harness/commit/3e24087
    desc: 测试断言伪造环回 Host 头不再能建立身份
    stars: 4
  - title: 奇安信 QVD-2026-57410
    text: 8 月 24 日独立披露同一问题，CVSS 3.0 = 9.8 评级极危，PoC 已公开，早于 CVE 两周。
    type: 转载
    platform: 情报中心
    url: https://qvd.qianxin.com/detail/QVD-2026-57410
    desc: 国内独立披露口径，与 VulnCheck CVE-2026-82533 对照
    stars: 3
links:
  - platform: 官网
    form: 完整版长文
    url: /articles/deepseek-harness-sandbox-escape/
    note: 被沙箱关住的 AI 智能体，竟然实现了逃逸？三条逃逸链、修复设计与从版本到凭据的自查清单
assets:
  - name: 受影响版本与凭据自查命令清单
    desc: 版本四位置核查、端口转发排查、沙箱外痕迹与凭据轮换的完整命令
    location: 官网文章，随长文发布
reading_path:
- 先读「逃逸链分析」：四个设计决定怎么叠成完整链路，为什么沙箱只治理文件效果
- 再看三条逃逸链的递进：切模式最显眼，审批自答最隐蔽，密钥外送最安静
- 然后读「时间线」：社区早十天报出、维护者回应「不算安全问题」、修复未作安全通报，披露过程和漏洞本身同样值得研究
- 最后过一遍「自查」：从版本的四个独立位置到凭据轮换，满足过触发条件就按已暴露处理
findings:
  known:
  - 沙箱三平台实现全部只约束写：读敞开、写圈在工作区、网络无人管，「沙箱不限制读」已从源码和实测两个方向证实
  - 审批机制判定「命令权限是否超出会话权限」，修改会话权限的动作本身不触发审批；审批事件广播加无身份答复接口，队列可被沙箱内进程自答
  - 接口信任判断只读客户端可控的 Host 头，官方代码注释自己写明「这不是认证层」；修复以启动令牌换签名 Cookie 建立统一浏览器会话身份
  - 修复后遗留：撤销凭据要删的 .credentials.yaml 在 $DSH_HOME 下，而 DSH_HOME 经环境变量主动交给智能体，凭据文件对沙箱内进程可读
  open:
  - 修复后凭据文件被沙箱内进程读取的实际影响，公开材料没有验证，等待下一轮修复或独立实测
  - 其他主流 Agent 框架（同类沙箱加审批结构）的控制面认证覆盖情况，待逐个审计
  - 审批交互的防御设计（不可导出的浏览器能力、审批绑定已认证 UI 连接）在真实产品中的落地效果，待跟踪
changelog:
- date: '2026-09-12'
  action: 课题立项。首发长文《被沙箱关住的 AI 智能体，竟然实现了逃逸？》完成定稿，与课题页同批发布上线。
---

## 核心问题

Agent 框架用沙箱、审批和权限模式来约束智能体行为，这套约束体系自己是否成立。课题从 CVE-2026-82533（DeepSeek Harness 沙箱逃逸）出发，回答三个问题。沙箱的边界到底声明到哪里，实现是否与声明一致。审批和权限模型会不会被被控主体改写，队列会不会被自答。控制面的认证怎么才算做对了，为什么「绑环回就不用认证」在内外两个方向同时失效。

研究对象是 2026 年 8 月开源、三周拿下 22 万星、默认安装即受影响的 DeepSeek Harness，攻击侧证据来自 OX Security 的分析与社区更早的报告，防御侧证据来自修复提交与设计文档。

## 覆盖内容

- **沙箱边界**：bubblewrap、Landlock、Seatbelt 三平台实现逐行读，「只治理文件效果」的官方声明与源码对照，读不设防的实测证据
- **控制面信任模型**：isTrustedApiRequest 只读 Host 头、DSH_* 环境变量主动递地址和会话身份、DNS 重绑定防护为什么不是认证
- **逃逸链一**：一条命令把会话切成 danger-full-access，审批被「正确地没有触发」，对照实验证明沙箱此前正常工作
- **逃逸链二**：审批事件广播与自答 allowed-once，人没有点过确认，会话表面一切如常
- **逃逸链三**：settings.update 改写工具 baseURL，搜索密钥按次外送；discoverModels 同族问题
- **远程路径**：端口转发后的未授权接管，无凭据下载会话日志，按独立数据泄露事件评估
- **披露过程**：社区早十天报告、维护者「不算安全问题」的回应、修复混在常规变更里没有安全通报
- **修复评估**：token 换签名 Cookie 的统一认证为什么对，以及修复后凭据文件对沙箱可读的遗留问题
- **自查**：版本四位置、端口与隧道、沙箱外痕迹、凭据轮换，附临时缓解措施

## 素材时间线

- 2026-08-13 讨论区 #250，mxym 报告审批自答逃逸路径，附端到端 PoC
- 2026-08-14 讨论区 #853，OracleNep 报告 60 个 RPC 方法无认证与三步远程 RCE；同日腾讯安全团队发布针对 0.1.0-rc.5 的四漏洞评审
- 2026-08-24 OX 复现确认并报告 VulnCheck，修复提交 3e24087 落库；同日奇安信以 QVD-2026-57410 独立披露
- 2026-08-26 项目成员在 #853 回应，称行为「有意为之」、报告「没有意义」
- 2026-09-08 VulnCheck 发布 CVE-2026-82533，CVSS 4.0 = 9.4
- 2026-09-11 本课题对全部来源完成核对（源码、讨论帖、修复提交、披露口径）
