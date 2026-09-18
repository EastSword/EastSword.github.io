---
layout: article
title: "全量 Git 历史，是怎么被Zcode静默搬上云的"
subtitle: "ZCode 全量快照的链路还原：采集了什么、传给了谁、证据到哪里"
abstract: "ZCode 在登录状态下会把工作区连同完整 .git 历史打包加密直传阿里云 OSS，解密私钥只在服务端，用户侧两个开关都关不住。本文合并 ferstar 与老冯的独立取证，还原从凭证申请到 OSS 直传的完整链路，对照两个月前 Grok 的同类事件，并明确证据边界：传输是实锤，用途没有任何证据。"
date: 2026-09-18
updated: 2026-09-18
reading_time: 7
category: "AI安全"
tags: ["AI", "隐私", "数据主权", "AI Coding", "终端安全"]
toc:
  - id: ch01
    title: "从磁盘清理到 313MB 密文"
    children: []
  - id: ch02
    title: "上传链路是怎么工作的"
    children: []
  - id: ch03
    title: "快照里装了什么"
    children: []
  - id: ch04
    title: "密钥在谁手里"
    children: []
  - id: ch05
    title: "两个开关都关不住"
    children: []
  - id: ch06
    title: "只有ZCode犯这个错吗"
    children: []
  - id: ch07
    title: "企业和个人能做什么"
    children: []
  - id: ch08
    title: "总结"
    children: []
  - id: ch09
    title: "参考来源"
    children: []
---

9 月 18 日凌晨，独立开发者 ferstar 发了一篇博客《扒一扒 ZCode 静默上传全量 Git 历史的骚操作》。ZCode 是智谱官方的 AI 编程桌面客户端。

![图片](/assets/uploads/20260918-0f3b9da0a8.webp)

他最初只是在清理磁盘，发现 `~/.zcode` 目录占了七百多兆，其中 `v2/checkpoints/` 一个子目录就有 303MB。顺着这个目录往下查，最后查到的事实让人大跌眼镜。没想到，在登录状态下，客户端会在后台把整个工作区连同完整的 `.git` 历史、LFS 缓存、reflog 打包加密，直传阿里云 OSS，跨工作区的全局配置也在采集范围内。[1]

![图片](/assets/uploads/20260918-d004691485.webp)

博客发出后，安全研究者老冯按同样的路线在自己的 Mac 上做了独立复测，结论一致，并且补上了几个关键证据。[6] 

![图片](/assets/uploads/20260918-bcf41dba4b.webp)

这篇文章把两边的取证合在一起，先完整还原链路的技术细节，再讨论它越过了哪几条线，以及哪些指控是现有证据不支持的。

## 从磁盘清理到 313MB 密文
{: #ch01}

ferstar 在 `v2/checkpoints/pending/` 下发现了一个 313MB 的 `.enc` 文件，状态文件写明了来源，其中workspacePath 指向他本地打开的一个商业项目，workspaceSizeBytes 是 345MB，encryptedSizeBytes 是 313MB，kind 标记为 baseline。baseline这个标记意味着全量快照，不是增量。在.enc文件里面，还有一个failureCount 的变量，此时的值是 564。[1]

这几个数字是什么意思呢？解释一下，客户端扫描了他打开的商业项目，排除 `node_modules` 等少量目录后，把剩下的 345MB 打包加密成 313MB，标记为全量基线，然后尝试上传，且上传失败了 564 次，文件一直在 pending 目录里等重试。那个项目总共 10GB，排除依赖后剩下的 345MB 几乎全是核心资产。

需要说明的是，failureCount 为 564 只能证明这份快照采集了、并且在持续尝试上传，不能证明它传了出去。真正证明「传出去并被接受」的证据来自老冯的复测。他的机器上有四个工作区的快照，其中一份的状态文件里写入了 `lastAcceptedManifestHash`，按代码里这个字段的写入路径，它对应上传获得服务端确认之后的分支。两份取证合起来，采集和传输这两个环节都是实锤。[6]

![图片](/assets/uploads/20260918-9657a128d5.webp)


## 上传链路是怎么工作的
{: #ch02}

这一节是纯技术还原，材料来自 ferstar 对客户端代码的逆向。[1]

捕获挂在两个钩子上。一个叫 captureBeforePrompt，在用户每次发送 prompt 之前触发；另一个叫 repo-wiki-update，在任务结束后触发。ferstar 的日志显示，单个活跃会话最多记录了 62 次捕获。

捕获发生后，客户端向 zcode.z.ai 的 `/api/v1/snapshot/upload-credential` 接口申请上传凭证。服务端返回 snapshot_id、和一把 RSA 公钥，以及阿里云 OSS 的 PostObject 表单签名。而且从报告中可以看到，凭证由服务端决定发不发，发了客户端才采集，而且针对这个请求不缓存、不写日志、失败无提示，这也就意味着，当我们看到相关文章发布的时候，可能并不能复现。

打包和加密用的是标准做法。客户端把工作区打成 tar.gz，用随机生成的对称密钥做 AES-256-CTR 加密，再把这把对称密钥用服务端下发的 RSA 公钥以 RSA-OAEP-SHA256 方式包裹，也就是典型的信封加密。

上传过程中，密文以 PostObject 表单方式传到阿里云 OSS，不经过智谱自己的业务服务器。OSS 确认后回调智谱服务端登记，客户端收到回执才写入 `lastAcceptedManifestHash`。

ferstar 把 pending 目录里那个 313MB 的文件删掉，客户端检测到缺失后重新打包，failureCount 从 564 变成 565，接着走重试流程，这说明还具备重传逻辑。

你可能会说，反正工作区里的代码和各个文件，本来就是开放给Zcode，翻了下 ZCode 的隐私政策，里面明确写了会收集“对话中提交的文本、文件和代码”——这属于 AI 助手调模型推理的常规操作，各家都一样。

**那如果采集范围比工作区本身更大呢？**在分析中，发现客户端还会读取 repo_snapshot_extra_manifest 里登记的文件，这些是跨工作区的全局配置，比如 settings.behavior.json。也就是说，被上传的不只你当前打开的项目。

整条链路看下来，这套“获取数据”的工程步骤非常精密，值得给个“大拇指”，比如异常检测、重试、信封加密、对象存储直传，非常的成熟。

## 快照里装了什么
{: #ch03}

密文解不开，但打包时生成的 Manifest 清单是明文留在本地的。ferstar 统计了那份包含 42,411 个文件的清单，结果如下：

| 内容 | 体积 | 占比 |
|---|---|---|
| `.git/lfs/` | 196.1 MB | 56.8% |
| `.git/objects/` | 102.2 MB | 29.6% |
| `.git/logs/` | 0.6 MB | 0.2% |
| 其余源码与文档 | 46.2 MB | 13.4% |

`.git` 一个目录占了 86.6%。[1] 老冯复测的两个仓库更极端，`.git` 的字节占比分别是 93.9% 和 98.5%。[6]

所以这份快照的主体是仓库自创建以来的全部历史，当前工作区的文件反而是少数。两者的区别是实质性的。工作区文件是你此刻选择保留的东西，Git 历史里躺着的是你已经处理掉的东西：提交过又删除的密钥和配置、被覆盖的旧版本、本地未推送的分支名、`.git/config` 里配的内部 GitLab 域名和仓库路径。

老冯在复测里又补充，客户端的文件筛选是一条顺序判定链，`.git` 目录的放行排在所有排除规则之前，密钥过滤和单文件 1MB 上限对 `.git` 下的内容一律不生效。他仓库里一个 137MB 的 packfile 因此整包进入了快照。他的仓库里还有 `.git/filter-repo` 和 `.git/lost-found` 目录，前者是历史重写的残留，通常正是为了清除敏感数据才做的重写，后者存放悬空对象。刻意清理过的历史，原样躺在待上传的包里。[6]

## 密钥在谁手里
{: #ch04}

ferstar 拿本机所有私钥尝试解 envelope 里的密钥，全部失败。前面其实也有介绍，目前所使用的 **AES-256-CTR 加密内容，RSA-OAEP-SHA256 包裹对称密钥，** 这套算法和组合称得上是主流标准。[1] 并且，RSA 公钥是服务端在下发上传凭证时动态给的，配对的私钥从头到尾只在云端，只有持有私钥的智谱后端才能解开。

如果这个功能的目的是给用户做检查点回滚或者跨设备同步，密钥应该绑在用户侧。Git 的 bundle、Time Machine 的备份都是这么做的，备份的第一原则是所有者能恢复自己的数据。而Zcode现在的架构是服务端单方面持有恢复能力，在这样一个有能力做出规范信封加密的团队面前，为什么我们可以接受自己电脑上存着自己看不到的东西？

## 两个开关都关不住
{: #ch05}

出了这种事，多数人的第一反应是去设置里把开关关掉。ferstar 把两个设置项和代码逻辑逐一对照过，结果都关不住这条链路。[1]

| 开关 | 用户以为它管 | 实际管 |
|---|---|---|
| 优化体验（optimizeAgentExperienceEnabled） | 数据采集和上传 | 只管要不要拿数据去训练，关了照样采集上传 |
| 仓库快照索引（repoSnapshotIndexingEnabled） | 快照功能本身 | 只管服务端拿到快照后建不建索引，关了本地照常打包上传 |

为什么会这样，因为负责快照捕获和上传的 sidecar 在启动时无条件实例化，整个初始化路径上没有针对用户配置的判断，只需要 tokenProvider 能拿到登录态的 JWT，那么用户一旦登录，这条链路就开启了。前面我也提过，客户端回传文件的开关是服务端控制，因此本地配置在这套架构里起不到控制作用。

## 只有ZCode犯这个错吗
{: #ch06}

今年 7 月，研究者 cereblab 对 xAI 的 Grok Build 命令行做了 wire 级抓包分析。[3] 同样发现存在这个问题，Grok的推理走 `/v1/responses` 通道，快照走另一个存储通道，上传到 Google Cloud Storage 的 grok-code-session-traces 桶。他在提示词里明确写了「回复 OK，不要读任何文件」，快照通道照样把整个仓库打成 git bundle 传了上去，克隆回来能逐字节恢复一个模型从未读取过的文件和全部提交历史。

![图片](/assets/uploads/20260918-119ac744e9.webp)

为了防止误判，cereblab重新起了一个 12GB 的仓库，塞满模型从未读过的随机文件，结果推理通道只传出 192KB，快照通道传出 5.10 GiB，两者相差约 27,800 倍。这直接证明了Grok当时把上传范围扩大到整个代码库上，「模型上下文自然携带」这种解释就显得过于扯淡了。

后续是 xAI 在服务端关停了上传通道，增加了退出选项，马斯克公开承诺删除已上传的数据。[4]

![图片](/assets/uploads/20260918-14a884c718.webp)

Grok 事件的报告和复现仓库全网公开，任何一家做 AI 编程工具的公司做竞品调研都能看到，而同一类行为在舆论烧过一轮之后，仍然原样存在于一家头部国产厂商的官方客户端里，这已经不能再用技术疏忽来解释了。

## 企业和个人能做什么
{: #ch07}

如果团队里有人在使用 ZCode 或同类客户端，以下是我会采用的处置顺序。

第一步是盘点。这类工具真正的风险在于安全团队不知道谁在用。它不经过 GitLab，不触发堡垒机，不走 DLP 的审计通道，员工在终端登录个人账号，全量 Git 历史就从终端直接出去了。先搞清楚公司内安装了哪些 AI 编程工具、使用者在哪些部门，这个动作成本不高，价值最大。

第二步盯流量特征，内容解不开没关系。哪个进程在传、目的域名是什么、单次传了多少，这三样都看得见。全量快照的行为特征很好认：单次上载几百 MB、直连 OSS 或 GCS 这类对象存储域名、失败后周期性重试。EDR 和出口流量分析不需要解密就能识别这种行为。

第三步轮换历史凭据，这一步最容易被忽略。密钥过滤只看文件名，对 Git 历史无效，历史上提交过一次的私钥、数据库密码、AK/SK 都会随 `.git/objects` 出去。对可能已经被快照的仓库，删文件没有用，要把历史里出现过的凭据全部轮换，而且要趁早。轮换越早，已经出去的旧凭据贬值越快。

最后是分层隔离。敏感代码库不放在装有这类客户端的机器上，或者用企业自建的隔离环境跑 AI 编码，让外部客户端在技术上接触不到源码。个人用户可以用 ferstar 给的方案，macOS 上 `chflags uchg`，Linux 上 `chattr +i`，在文件系统层锁住 checkpoints 目录，代价是检查点回滚功能不可用，这个取舍值不值得由自己判断。[1]


```
#macOS
# 清空并锁定 checkpoints 目录
rm -rf ~/.zcode/v2/checkpoints
mkdir -p ~/.zcode/v2/checkpoints
chflags uchg ~/.zcode/v2/checkpoints

# 验证：应该输出 Operation not permitted
touch ~/.zcode/v2/checkpoints/test

#Linux
# 清空并锁定 checkpoints 目录
rm -rf ~/.zcode/v2/checkpoints
mkdir -p ~/.zcode/v2/checkpoints
sudo chattr +i ~/.zcode/v2/checkpoints

# 验证：应该输出 Operation not permitted
touch ~/.zcode/v2/checkpoints/test
```

## 总结
{: #ch08}

在公开文档的分析中，我们得知Zcode当前在用户登录状态下无条件采集工作区全量和 `.git` 历史，并把跨工作区的全局配置一并打包，且密文只有智谱服务端能解，该行为不受用户可见设置管控，隐私政策没有覆盖这个行为。

我始终对国内厂商怀有善意，所以关于智谱拿这些数据做了什么。训练、索引、跨设备同步、内部审查，目前都只是猜测，我并不希望这个让我半夜开心放开腿蹬的模型有啥负面信息，本文所引用ferstar 和老冯的取证只能证明存在数据有传输和接收，指控「上传就是为了训练」，是现有证据不支持的。

但对风险管理来说，意图从来不是必要输入。服务端具备读取全量历史的能力，这个能力由架构保证，不随意图波动，风险控制的对象是能力。一个默认全量采集、密钥只在服务端、开关全部失效、条款没有授权的数据出口，不管厂商此刻想做什么，对用户都已经构成实质风险。

判断一个工具是否越线，光看它声明的用途是不够的。

更可靠的依据是它**在你的机器上实际拿走了什么、交给了谁、你有没有拒绝的选项**。

很遗憾，目前都没有看到，所以我卸载了Zcode。

---

## 参考来源
{: #ch09}

- [1] ferstar《扒一扒 ZCode 静默上传全量 Git 历史的骚操作》：[https://blog.ferstar.org/posts/zcode-silent-workspace-snapshot-upload/](https://blog.ferstar.org/posts/zcode-silent-workspace-snapshot-upload/)
- [2] ZCode Privacy Policy：[https://zcode.z.ai/en/privacy](https://zcode.z.ai/en/privacy)
- [3] cereblab《What xAI's Grok Build CLI Actually Sends to xAI: A Wire-Level Analysis》：[https://gist.github.com/cereblab/dc9a40bc26120f4540e4e09b75ffb547](https://gist.github.com/cereblab/dc9a40bc26120f4540e4e09b75ffb547)
- [4] 同上，更新部分：xAI 服务端关停上传、增加 opt-out、承诺删除已上传数据
- [5] 老冯《本地 AI：算的是政治账，不是经济账》：[https://mp.weixin.qq.com/s?__biz=MzU5ODAyNTM5Ng==&mid=2247493186&idx=1&sn=d8570dcd325af4652dcd7e88264b79b4&scene=21#wechat_redirect](https://mp.weixin.qq.com/s?__biz=MzU5ODAyNTM5Ng==&mid=2247493186&idx=1&sn=d8570dcd325af4652dcd7e88264b79b4&scene=21#wechat_redirect)
- [6] 老冯就 ZCode 快照的独立复测文章：[https://mp.weixin.qq.com/s/LdXekkP-Yb2IQfoMV53uDw](https://mp.weixin.qq.com/s/LdXekkP-Yb2IQfoMV53uDw)
