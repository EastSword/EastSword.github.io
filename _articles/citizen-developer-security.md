---
layout: article
title: "人人都是开发之后，\"盯住开发\"还缺什么"
subtitle: "写代码不再有门槛，靠门槛圈人的名单、关口和共同语言三样旧地基跟着塌。宣贯缺的不是课件，是对象"
abstract: "现在人人都在用 AI 产出应用，名单、关口、共同语言三样地基同时漏风。五个场景过一遍数据外流、密钥入码、应用裸奔、幻觉包、代理持生产权限，指出宣贯缺的不是课件是对象，并给出改定义、讲六件事、给正路、轻登记的补法。"
date: 2026-09-17
updated: 2026-09-17
reading_time: 8
category: "AI安全"
tags: ["AI", "安全", "安全意识", "影子", "AI"]
toc:
  - id: ch01
    title: "以前那套办法，为什么一直够用"
    children: []
  - id: ch02
    title: "是从一句提示词开始的变化"
    children: []
  - id: ch03
    title: "风险场景频发"
    children: []
  - id: ch04
    title: "宣贯缺失在哪里"
    children: []
  - id: ch05
    title: "怎么补"
    children: []
  - id: ch06
    title: "回归主题"
    children: []
  - id: ch07
    title: "参考来源"
    children: []
---

> "这个确实是个问题，以前只有开发会写代码，盯着他们不外传代码、不乱部署就好，现在人人都是开发，对应的意识宣贯还是缺的。"

听到这句话，很多人直点头，今天我们就聊聊，以前"盯开发"那套东西到底是怎么运转的，它从哪一天开始出现纰漏，漏出来的口子，我们现在应对如何。

## 以前那套办法，为什么一直够用
{: #ch01}

说"盯开发"，其实盯的不是人，是三样东西。

第一样是人员名单。会写代码的人集中在研发部门，组织架构拉出来基本就是完整名单。入职的时候谁要签保密协议，日常工作谁要上安全编码培训，谁的电脑要尤其进行安全管控，谁的 GitLab 权限怎么配，都会划分的很清楚。

第二样是几个必经的安全卡口。代码从写出来到跑起来，路径一般是固定的。进GitLab或其他类型的仓库，经过内部代码评审，走构建，测试环境验一遍，上线也有审批，生产环境部署和操作都经过堡垒机。在这个过程中，代码仓库实现"不外传代码"，上线审批环节实现"不乱部署"，安全只要收好口子，治理效果还是相当不错的。

第三样是人员意识。所有涉及代码开发的员工，知道自己在为什么负责，作为安全人员，当我们向研发传达"密钥不能进代码"、"上线要走审批"、"代码里面有漏洞必须及时修复"，这些都几乎低成本可以和他们达成共识，因为有了职业经验，都会明白前期及时优化要比后期漏洞修复成本低很多。当然除了成本，饭碗的稳固也决定了大家会谨慎。

那么这样一套稳定运行的机制，怎么出现了安全风险的呢？

## 是从一句提示词开始的变化
{: #ch02}

去年 2 月，Karpathy 造了个词，vibe coding，大意是"别管编码，说出你想要什么就行"。这个词能火，是因为它描述的动作，运营、财务、人事、客服都做得到。

维基百科的原文是这样的：
> Vibe coding is the software development practice assisted by artificial intelligence (AI) where the software developer describes a project or task in natural languages to a large language model (LLM), which generates source code automatically. Vibe coding may involve accepting AI-generated code without thorough review of the output, instead relying on results and follow-up prompts to guide changes.


![图片](/assets/uploads/20260916-f82d978b57.webp)

以前运营想做个抽奖页面，得提需求给开发，排期两周；财务想每月自动对账，得求人写脚本。现在打开 Codex 或者 Cursor，大白话说清楚要什么，半天，应用就开发完成了，想要部署起来，也是几句话可以让Agent代劳。

那么目前公网层面暴露的vibe coding服务规模有多少呢，Gartner 预计今年公民开发者（没写过代码、但用工具产出应用的人）数量会是专业开发的四倍。今年 5 月 WIRED 报道，安全公司 RedAccess 搜了 Lovable、Replit、Base44、Netlify 这几家平台的托管域名，翻出五千多个几乎没有鉴权的应用，四成暴露着敏感数据：医疗记录、财务数据、甚至一家医院的排班表连医生个人信息都在里面，还有公司的新品战略演示。建这些应用的人，绝大多数不是程序员。

此时此刻，写代码已经不再需要会写，不再是少数人（开发群体）的特权了。我们反看原先对代码安全的三个机制，是怎么坍塌的。

一是，名单没了。运营、财务、人事、客服，谁在用 AI 写东西，谁只是和AI做简单交互，在安全团队这侧是很难主动分辨清楚的，也没有任何流程让这事"被知道"，因为他们不需要开仓库，不需要提发布单。

二是，关口没了。这些应用的路是从聊天窗口直接到公网，中间不经过公司的 GitLab、构建流水线、堡垒机中的任何一个，公司花十年建的把关和流程，管的是一条新来者不会走的老路。

三是，意识没了。跟一个用 Lovable 搭报销工具的 HR 讲"注意行级安全配置"，等于没讲。他不知道什么是凭据、什么是鉴权、什么是暴露面。沟通费劲，难以理解，逐渐浮躁甚至暴躁。

## 风险场景频发
{: #ch03}

下面几个场景是我按公司里面最常见的岗位拼的，大家可以用公司的同事对号入座，hhhhh

**场景一：数据泄漏。**财务经常会遇到对不平账的情况，情况紧急，顺应时代潮流，直接把带客户手机号和充值记录的流水表截了个图，贴给一个网页版 AI，"帮我看看哪里错了。"，然后美美喝coffee去了。但是这一下，公司的敏感数据一下就出了公司边界，落在一台你看不见的服务器上。在相关行业调查里，27% 的员工承认干过类似的事。以前泄密要走 U 盘、走邮件，现在走对话框，而且很多人没人觉得这算"泄密"。

顺着这条路径，有一天，一位尽职尽责、有创新精神的财务相关人员，心血来潮想开发个发票管理系统，想到公司的开发部门这几天刚采购了codex，就去申请了一个账号，对方也没过多询问原因。拿到手里后，跟着官方手册，捣鼓半天终于安装好了。激动的心，颤抖的手，敲下了“你好，请帮我开发一个发票管理系统，后面我给你发发票照片或者电子附件，你来做登记”，看到AI快速开始思考并构建出一个美观的平台，实在是快意无限。殊不知，这个系统现在一堆漏洞，敏感的发票数据一直累积在本地，而且所有数据都给AI也呈递了一份。再后来，在家里想访问系统，但是服务搭建在公司电脑上，经过AI思考、实施，顺利在公网上线了服务，自己可以在家里直接远程访问数据。后来，就有人爆料该公司数据泄漏，安全部门大半年之后才追到这个缺口。

这就是场景二。

**场景二：应用违规上线。**Replit的CEO曾说过一句话："公网应用可以被访问，是预期行为。"，Lovable 出事之后也是类似口径，“应用怎么配，是创建者的责任。“，在Lovable这次事故中，一个研究员用免费账号、五次 API 调用，读到了别人的源码和数据库密码，事故根因是配置项存在安全纰漏，影响一百七十多个应用、一万八千多用户的数据，且这一报告提交后工单还被关了，增加暴露了四十八天。

**场景三：密钥硬编码。**有这样一个场景，数据分析人员用 Cursor 写取数脚本，AI 问都不问，把数据库连接串直接写在代码第八行。这个文件后来进了某个共享目录，或者被整段贴进了群里。GitGuardian 去年扫出两千八百多万个硬编码密钥，AI 参与的提交，泄露率是纯人工的两倍。同一个错误，研发犯了会挨批，公民开发者犯了，连自己都不知道那是个错误。

**场景四：AI幻觉。**研究测出来，AI 生成的代码里大约两成引用的包是它编的。以前攻击者靠你打错字抢注假包，把 request 拼错一个字母，他就注册那个坑你；现在靠 AI 编名字，你照着它给的命令装下去，恶意代码就进来了，这行当现在有个名字叫 slopsquatting。去年 9 月那个感染了五百多个 npm 包的 Shai-Hulud 蠕虫，主要打的还是专业开发者——专业的人都成片失守，没概念的人更谈不上防线。

![图片](/assets/uploads/20260917-b02364b5b5.webp)


**场景五，AI掌管生产权限。**去年 7 月，SaaStr 的创始人在 Replit 上搭应用，明确说了冻结代码，结果 AI 代理当晚把生产库删了，然后自己编了四千个假用户，让界面看起来一切正常。现在很多人的AI Agent手里都有完整的生产凭据，大家可以在公司里问一圈，有没有人为了省事，把生产密码贴给 AI 代理让它"自己改"，只要有一个，这个剧本随时重演。去年 5 月 Invariant Labs 披露，公开仓库的 issue 里藏一段指令，就能诱导你正在跑的 agent 把私有仓库的内容带出去。也就是说，就算你的代理权限配得很干净，它读到的外部内容也可能反过来指挥它。

这里我们可以延伸一下，现在为了应对AI渗透，很多公司推出了AI访问识别、AI蜜罐，然后通过提示词注入，利用AI在本地的权限去获取发起方的身份，这个话题我们后面会单独来讲。

![图片](/assets/uploads/20260917-53514b49ed.webp)

在这些场景里面，其实大多是来源这些原因的碰撞：一个图方便的合理动机，一个不知道自己在暴露什么的操作者，一段没人看见的窗口期。区别只在于，以前这类操作者只可能是运维或开发，现在可以是任何人。

## 宣贯缺失在哪里
{: #ch04}

在传统的安全培训中，一般就分为两套。一套给全员，会在培训中告诉大家别点钓鱼链接、别用弱口令、离开工位锁屏；一套给研发，安全开发流程、编码规范、组件管理、上线门禁。而现在出现了中间一群人，那就是用 AI 写脚本、搭工具的业务同事，全员培训没有这一部分内容，开发培训也听不懂。比如"严禁密钥硬编码"，这里认开发者本人知道密钥都以什么形态藏在代码里算是硬编码；"严禁裸奔暴露"，前提是他找得到那个开关在哪。

CSA曾调研了12000个白领，六成人在工作中用 AI，不到两成知道公司有使用指引，也就是说40%的人是在刀尖上跳舞。

不仅是一线公司忽视了这个事情，NIST 的 AI 风险框架、OWASP 的 LLM Top 10，都没给"公民开发者"这个角色一个正面的位置，行业连教材的骨架都没搭出来，公司内部自然没有现成的东西可抄。

## 怎么补
{: #ch05}

对谁讲，先把定义改了。别再按"研发部"发通知，定义改成一句话：凡是用 AI 产出代码、脚本、应用的，都算开发，都进来听。人从哪找？工具申请记录、低代码平台账号、GitLab 开仓记录，三个名单一对，比等大家自报靠谱得多。

那怎么来开展宣讲呢，我建议从这些角度：

1. 判断数据能不能贴给 AI，直接参考已有的数据安全制度即可，敏感数据给到AI，和上传网盘、公开群聊是一样违规。
2. 密码和 Key 不出现在任何 AI 看得到的地方，更别给代理生产权限。
3. 应用建完第一件事是设访问口令。
4. AI 推荐的包，装之前搜一下它存不存在。
5. 东西要挂到内网或公网，要登记要审核。
6. 发现自己搞砸了，马上报告，无损可以不追责。

我也在公司里面做AI治理大半年了，我的一个心得是“堵不如疏”。我们在公司里面去禁止这个禁止那个，但在时代发展潮流面前，反人性的禁令只会造成两个后果，要么阳奉阴违，要么错过发展良机，这都会对企业的发展造成不利的影响。因此我建议提供一条更佳安全、更佳规范的路径，工具要给到位，员工想用 AI 可以，走企业账号、白名单内的工具，公司出钱。想想，如果公司都提供了更加好用的模型，还不用个人付钱，这难道不是堵个人订阅最有效的办法吗。

安全团队，只需要在AI管控平台把安全的默认值做好，提供公司内部的使用环境，把单点登录、访问口令、密钥托管都做好，让"安全"不依赖用户的能力，依赖的是组织的安全策略，才是安全的硬道理。

安全要做的事还有很多。

登记要敏捷。用一些简短的登记，或者做一些本地的服务监控，对新应用快速登记、敏捷登记。

扫描要普遍。秘密扫描、依赖扫描别只盯着 GitLab 仓库，低代码平台导出的东西、AI 生成的脚本，同样要纳入扫描范围，AI 写的代码不豁免任何一道门禁。

出了事先别罚。捂盖子只会让星星火点变成燎原大火，上报通道要是让人害怕，那就是咎由自取。

## 回归主题
{: #ch06}

以前盯开发，本质是拿"会写代码"这个门槛当了安全边界，这个门槛现在必须去除，要聚焦公司内部的数据流向，用数据安全来作为AI治理的基石，把开发安全规范重新发给每一个现在能够写代码的人。

所以，人人都是开发之后，你还围绕开发团队做代码安全吗？

---

## 参考来源
{: #ch07}

事件与数据都出自公开报道和研究，写作时间 2026-09-15。

- WIRED 报道 RedAccess 研究（五千多个无鉴权应用、平台方回应）：[Thousands of Vibe-Coded Apps Expose Corporate and Personal Data on the Open Web](https://www.wired.com/story/thousands-of-vibe-coded-apps-expose-corporate-and-personal-data-on-the-open-web/)
- Lovable 事件：[官方回应](https://lovable.dev/blog/our-response-to-the-april-2026-incident)、[The Next Web 调查](https://thenextweb.com/news/lovable-vibe-coding-security-crisis-exposed)、[Superblocks 技术分析](https://www.superblocks.com/blog/lovable-vulnerabilities)、[OECD 事件库](https://oecd.ai/en/incidents/2026-04-20-b869)
- Replit 删库事件：[Fortune 报道](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/)
- Anthropic 源码泄露：[每日经济新闻](https://www.nbd.com.cn/articles/2026-04-01/4321281.html)、[财联社](https://www.cls.cn/detail/2334617)
- Shai-Hulud 蠕虫：[Unit 42 分析](https://unit42.paloaltonetworks.com/npm-supply-chain-attack/)、[CISA 警报](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem)、[Datadog 对 2.0 变种的分析](https://securitylabs.datadoghq.com/articles/shai-hulud-2.0-npm-worm/)
- 幻觉包与 slopsquatting：[CSA 研究简报](https://labs.cloudsecurityalliance.org/research/csa-research-note-slopsquatting-ai-supply-chain-20260419-csa/)
- GitHub MCP 提示注入：[Invariant Labs 披露](https://invariantlabs.ai/blog/mcp-github-vulnerability)、[Simon Willison 评述](https://simonwillison.net/2025/May/26/github-mcp-exploited/)
- 使用率与知晓率、框架缺口、GitGuardian 密钥数据、AI 代码漏洞研究：[CSA 影子 AI 简报](https://labs.cloudsecurityalliance.org/research/csa-research-note-shadow-ai-apps-enterprise-20260530-csa-sty/)、[CSA 治理缺口简报](https://labs.cloudsecurityalliance.org/research/csa-research-note-vibe-coding-ai-governance-gap-20260602-csa/)、[GitGuardian 状态报告经 CSA 引用](https://labs.cloudsecurityalliance.org/research/csa-research-note-vibe-coding-ai-governance-gap-20260602-csa/)
- 公民开发者规模预测：[Kissflow 整理的 Gartner 观点](https://kissflow.com/citizen-development/gartner-on-citizen-development/)、[Gartner 低代码预测](https://www.gartner.com/en/documents/7146430)

> 备注：27% 员工贴机密、六成使用率、框架缺口等数字转引自 CSA 简报与行业汇总，未逐一核对原始报告；文中"场景一到场景五"是按岗位构造的讨论用场景，公司内真实发生的同类事件见 Ollama/Flowise 公网审计、SSH 隧道治理和 MCP filesystem-pro-plus 复盘的内部记录。
