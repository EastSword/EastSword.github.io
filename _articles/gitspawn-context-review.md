---
layout: article
title: AI 助手还在问你是否信任项目，程序怎么已经跑起来了？
subtitle: 从 Claude Code、Qwen Code 和 Cursor 的公开案例说起
abstract: 让 AI 帮忙看代码，它却可能在准备材料时启动额外程序。GitSpawn 是怎么回事？这些程序从哪里来，确认框为什么没拦住？我们从几张演示截图讲起。
date: '2026-09-08'
author: 千里
category: AI安全
tags:
- GitSpawn
- Claude Code
- Cursor
- Qwen Code
- AI Agent 安全
reading_time: 8
---

最近整理[隐侠官网的 AI 安全资讯](https://eastsword.github.io/news/)时，我看到了一项叫 GitSpawn 的研究。它让我重新想了一个很日常的问题：AI 助手问“你信任这个项目吗”，是不是意味着，在我点同意之前，它还没有动手？

在研究者展示的部分旧版工具中，答案并非如此。有些程序在等待确认时，就已经运行了项目配置指定的命令。

GitSpawn 是研究者给这类问题起的名字。简单说，**AI 助手为了了解项目，先在后台调用 Git；Git 又照着项目里的配置，启动了额外的程序。** 而且这件事可能发生在模型开始分析之前。

![Manifold 发布的 GitSpawn 研究页面](/assets/uploads/20260909-db04209a4a.webp)

来源：Francisco Rosales，Manifold，[GitSpawn 原始研究](https://www.manifold.security/blog/ai-coding-agents-git-hijack)，2026 年 9 月 1 日。下文讨论的是公开研究中的版本，不是今天所有产品的现状；演示截图来自研究者，本文没有重新运行漏洞。

## 让 AI 看代码，怎么还会启动别的程序？

假设你收到一个项目，想让 AI 帮忙检查代码。聪明的 Agent 小助手得先知道项目有哪些文件、最近改过什么，才能把材料交给模型。这些准备工作，经常由 **Git** 完成。

Git 是开发者管理代码版本的工具。它有一个叫 `core.fsmonitor` 的配置，可以指定一个辅助程序，帮助判断哪些文件发生了变化，省去逐个检查的时间。可以参考[Git 官方文档](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corefsmonitor)

麻烦就出在这里：如果项目里的这项配置是别人安排的，而助手直接让 Git 按它执行，那么“帮我看看改了哪些文件”就可能变成“先运行项目指定的程序”。

可以把它想成：你请人检查一个文件夹，他还没开始看正文，就先照着文件夹里的说明做了一个动作。可那份说明，可能有问题，因为各方保持一种默认信任的原则，没人去怀疑。

可以发现，在这条链路里，不需要模型先相信一段恶意提示词。因为负责准备材料的软件，本身就能运行程序， Agent 只是用合法程序运行目标文件， Git 从来就没被设计要去怀疑下方工具的问题。

不过，**项目是怎么交到你手里的，非常重要。** 本文这条 Git 配置路径，需要相关的本地配置已经到达你的机器，例如收到包含 `.git` 目录的项目压缩包。普通 `git clone` 不会把远端的 `.git/config` 复制过来，不能读成“克隆任意仓库就会中招”。[原文对交付方式的说明](https://www.manifold.security/blog/ai-coding-agents-git-hijack)

## Claude Code 还在等确认，文件已经出现了

先看下面这张图。

![Claude Code 等待信任确认时，研究者检查到标记文件已出现](/assets/uploads/20260908-e976db66e3.webp)

上半屏是 Claude Code 的工作区信任确认界面，下半屏是研究者检查标记文件的结果。所谓标记文件，就是演示中用来判断某段程序是否运行过的文件。通过截图就可以看到，在确认可以运行所提示命令前，访问动作已经出现了。

这张图取自 [Manifold 原始录像](https://framerusercontent.com/assets/4UNqmarh1NuIh8S6TO0ey7vs.mp4)末尾前约 2 秒，具体先后顺序可以回看录像。这个问题目前已经修复了，按照作者所述，这条 fsmonitor 问题已在 Claude Code 2.1.196 修复。

但这并不意味着整个Agent生态厂商都已经修复了这个风险，这就好比我们传统安全所说的“存在任意代码执行风险”，当界面还在征求用户同意时，后台却已经读取了对应的文件夹，并可能按照文件里内置的文档进行读取甚至执行。

可见，把对文件夹的信任确认具像化为确认框是不够的，我们需要关注这个确认框究竟拦住了哪些动作，还有哪些并不受限制。就像不是所有牛奶都叫特仑苏，所有出军指令下发前，并不都要粮草先行，因为可能并不会出军。

然后，Qwen Code 的演示则把这个问题又往前推了一步。

![Qwen Code 演示中出现的计算器](/assets/uploads/20260908-b73bb52f98.webp)

![同一段 Qwen Code 演示中的模型服务连接界面](/assets/uploads/20260908-9c78625360.webp)

两张图来自[同一段研究录像](https://framerusercontent.com/assets/ZhYP2IV3ARAmVhs165ARFOhrMJo.mp4)，分别是约第 5 秒和末尾前约 1 秒：先能看到计算器，之后是连接模型服务的界面，这里和Claude Code有差异的是两者并不是同时发生的，执行命令比连接模型更快，好比午时三刻问斩，却刚到午时已经咔嚓，这是非常有风险的行为（毕竟刀下留人是影视剧经常有的桥段）。

在我们的意识里，账号还没登录、还没连上模型，助手怎么可能开始工作。但事实就是这样，本地软件启动后，已经能做不少事情。登录模型服务和运行本机程序，看起来确实是两回事。

<details markdown="1">
<summary>其他产品的记录与版本（按原文 2026 年 9 月 1 日状态）</summary>

| 产品 / 路径 | 原文记录的时机 | 当日记录 |
| --- | --- | --- |
| Claude Code / ultrareview | 审查开始前 | 2.1.252 仍存在，机制不同 |
| Qwen Code | 认证前 | 0.22.3 仍存在 |
| Grok Build | 首次键入时 | 1.0.13 仍存在 |
| Hermes | 首条消息时 | 0.21.0 仍存在 |
| Codex、Cursor | 未单列完整过程 | 已修复；Codex 变体机制有差异 |

这些是原作者的披露记录。原文没有提供 Codex、Cursor 的独立完整演示，不能把其他工具的截图当成它们的证据。
如果想验证是否还能复现这个问题，需要判断现在使用的版本和厂商更新情况。

</details>

## Cursor 的另一个案例：先准备项目，后询问信任

这里换一个类似但不同的案例：Manifold 在 8 月 10 日发表的 Cursor CLI 研究，CLI 指的是在Cursor终端中使用的版本。

Cursor 可以为任务创建一份独立的工作目录，Git 把这种目录叫作 worktree。新目录可能需要先做一些准备，例如配置开发环境，所以项目里可以带有相应的准备步骤。

研究者发现，所测旧版 Cursor 会先执行项目指定的准备步骤，再询问用户是否信任项目。作者对照记录显示，2026.07.23-e383d2b 把顺序改了过来：先确认信任，再执行准备步骤。[Cursor 专项研究](https://www.manifold.security/blog/cursor-cli-worktree-pre-trust-execution)

![Cursor 专项研究中的工作区信任确认界面](/assets/uploads/20260908-cfc5a78b3d.webp)

截图来源同上，展示的是确认界面；具体执行顺序来自作者的测试记录。

它与前面的 Git 配置案例有一个重要区别：Cursor 的这份项目配置可以随正常的代码克隆到达本机。因此，“clone 不会复制 `.git/config`”只解释了前面那条路径，不能用来排除所有项目配置带来的风险。

原作者还指出，在其所查版本中，这段准备过程并不受沙箱开关约束。沙箱可以理解为限制程序能访问哪些文件、能做哪些操作的隔离环境。产品有这个功能，仍要问清它究竟管到了哪些步骤。

这也解释了为什么安全问题会在同一产品的新功能里再次出现：某个功能修好了，不代表后来增加的准备步骤也经过了相同检查。Cursor 在 2025 年就披露过项目 MCP 配置未经提示便启动的问题，但那是另一个漏洞，编号为 CVE-2025-64109，不能套用到这里的 worktree 案例。[Cursor 官方公告](https://github.com/cursor/cursor/security/advisories/GHSA-4hwr-97q3-37w2)

## Goose 的修复，可以帮助我们看懂该改什么

Goose 也是一款开源 AI 开发助手，能连接大模型、调用本地工具。它不是大模型本身。这里用它举例，是因为它的公告和源码都公开，我们能具体看看修复改在哪里。

![Goose 项目标识](/assets/uploads/20260909-b1ede93483.webp)

用户执行 `goose review`，就是让 Goose 审查代码。它先调用 Git 收集改动，再交给模型。厂商公告描述的问题，就发生在前面的收集阶段：Git 受本地配置影响，启动了额外程序，而这段操作不经过模型工具审批。公告列出的修复版本为 1.44.0。[Goose 厂商公告](https://github.com/aaif-goose/goose/security/advisories/GHSA-r5pp-p5r8-466r)

看修复代码，可以用一句话概括其中与本文有关的变化：**创建 Git 进程时，就明确关闭 fsmonitor 功能。** 这样，相关调用不必等模型做判断，就已经带上了限制。

不过，还得检查其他地方调用 Git 时，是否也用了这套限制。写了一个安全函数，并不意味着整个程序都经过它。

<details markdown="1">
<summary>想看代码细节：Goose 两个版本的对照</summary>

我们对照的是公开源码，未做动态复现。

| 检查位置 | 1.41.0 | 1.44.0 |
| --- | --- | --- |
| review 创建 Git 进程 | 在当前模块直接创建 | 接入公共 Git 调用函数 |
| 收集文件及差异 | `touched_files`、`collect_diff` 使用原入口 | 相应函数使用新的包装入口 |
| 与 fsmonitor 有关的处理 | 该局部入口只设置 `core.quotePath=off` | 公共入口设置 `core.fsmonitor=false` |

修复版使用 `review_git_command` 调用 `goose::subprocess::git_command`。公共入口还设置了 `safe.bareRepository=explicit`，这是另一项限制，不等同于关闭 fsmonitor。以上仅说明所查 review 路径的变化。

源码：[1.41.0 review](https://github.com/aaif-goose/goose/blob/39c27c387d726ce4605108d2f974d4feec158ed5/crates/goose-cli/src/commands/review/handler.rs#L334) · [1.44.0 review](https://github.com/aaif-goose/goose/blob/876555f85b1bd0e15ed75eed7c5ac1163c1f097a/crates/goose-cli/src/commands/review/handler.rs#L335) · [公共 Git 调用函数](https://github.com/aaif-goose/goose/blob/876555f85b1bd0e15ed75eed7c5ac1163c1f097a/crates/goose/src/subprocess.rs#L29)

</details>

## 下次使用Agent，我会先问这几件事

先看项目从哪里来。从公网克隆的仓库，或者别人发来的完整项目压缩包，都要审慎再三。要看一下项目带了哪些配置，确认自己使用的Agent版本。

如果是在企业里引入工具，产品或开发团队需要讲清楚，如果他们使用AI来进行生产，那么从打开项目到模型开始回答，中间自动运行了哪些程序？哪些要等用户同意，哪些受到沙箱限制？出现问题时，日志能不能查到？

这些问题不一定能靠聊天记录回答。或许模型还没参与时发生的操作，需要到客户端和进程日志里找。而这种日志的记录和监控，可以参考https://eastsword.github.io/articles/ai-agent-governance/这篇文章。

因此，本文撰写的目的，是想引起大家对Agent底层行为的注意，就本文来说，**“你信任这个项目吗”这句话，必须要在该等用户同意的操作发生之前问**。

而就我的初心来说，我希望大家有意识去思考，**“你信任AI接下来的操作吗”这句话，要在行动中时刻保持警惕**。

---

本文由千里整理与分析。GitSpawn 的发现与跨产品演示来自 Manifold 的 Francisco Rosales，Cursor worktree 案例来自其另一篇研究；Goose 分析另参考厂商公告及固定版本源码。文中截图均保留来源，本文未进行漏洞复现。
