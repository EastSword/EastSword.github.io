# 东方隐侠安全团队 · 话题中枢站

以**研究主题**（而非时间流文章）组织的个人站点：每个话题一个页面，聚合该研究在公众号 / CSDN / FreeBuf /B站 / 视频号的全部形态入口与配套资产，地址持续修订。基于 GitHub Pages 原生 Jekyll，零依赖、零 CI。

**线上地址**：https://eastsword.github.io （仓库：EastSword/eastsword.github.io）

## 站点结构（多页面）

| 页面 | 文件 | 说明 |
|------|------|------|
| 首页 | `index.md` | Hero + 四大板块导航 + 课题/文章/资讯预览 |
| 研究话题 | `topics.md` | 全部课题，**领域分类**（`category` 字段）+ 标签双层筛选 + 搜索 + 分页 |
| 技术文章 | `articles.md` | 长文列表页，渲染 `_articles/` 集合 |
| 安全资讯 | `news.md` | 渲染 `_data/news.json`，分类筛选 + 搜索 + 分页 |
| 江湖留名 | `wall.md` | giscus 签名墙（GitHub Discussion #1） |
| 关于团队 | `about.md` | 团队介绍 + 联系方式卡片 |
| 话题详情 | `_topics/*.md` | 每课题一页，`layout: topic` |
| 文章详情 | `_articles/*.md` | 每篇一页，`layout: article`（自动目录 + 锚点 + 阅读版式） |

## 日常维护

**文章编辑器（推荐写作入口）**：`python3 scripts/edit_article.py` 后台启动并打开本地编辑器（仅绑定 127.0.0.1，默认端口 8917；命令执行完即返回，服务独立会话常驻，关闭终端不受影响，日志在系统临时目录）。服务已在运行时再执行该命令会直接开浏览器复用现有进程。`--stop` 停止、`--status` 查状态、`--no-open` 不开浏览器、`--foreground` 前台调试。编辑器内：左侧改主稿（工具栏支持标题/加粗/代码/链接/图片/表格），右侧实时预览与线上同渲染引擎（kramdown + GFM，需本地 `gem install kramdown kramdown-parser-gfm`）；`⌘S` 保存写回主稿；右上「发布上线」一键 保存→生成→git push（可选仅生成不推送）；「＋新建」登记新文章（自动建主稿文件 + 登记表条目）；「元信息」改标题/副题/摘要/分类/标签/关键词；底部图片库点击即插入；分隔条可拖动。文章登记表为 `scripts/articles.json`。

**发布/修订长文（命令行）**：主稿在本地改（如 `安全架构/公网大模型的密钥泄露：攻击面、提取手法与防御.md`），跑 `python3 scripts/publish_article.py`。脚本自动：剥 H1、给章节注入锚点并生成目录、把 `文章配图/` 图片搬运到 `assets/images/<slug>/` 并改写路径、计算阅读时长、更新 `updated` 日期（首发的 `date` 保持不变）→ commit + push，1 分钟后线上生效。加 `--no-push` 只生成不推送。新文章用编辑器「＋新建」或手改 `scripts/articles.json`（source 为相对 blog-site 的路径）。

**发布新平台后回填地址**：打开 `_topics/<话题>.md`，填 `url:`、改 `note` 和 `updated`。commit + push，1 分钟后自动生效。

**新增课题**：复制 `_topics/` 下任一文件，front-matter 里 `status` 三选一（`drafting` / `publishing` / `published`），`category` 填领域分类（身份安全 / AI安全 / 供应链安全 / 网络安全…，分类 chips 自动生成），`keyword` 填公众号关键词，`links` / `videos` / `assets` 数组按需增删。

**安全资讯同步**：`python3 scripts/sync_news.py`（每日 10:00 由定时任务自动执行）。拉取内网 EchoMind 情报聚合服务（默认 192.168.1.7:10010，多 IP 自动探测；收录 security + ai-security 共 83 源，脚本顶部 `CATEGORIES` 可改）→ 合并去重写入 `_data/news.json` → 有变化自动 commit + push。手动跑加 `--no-push` 只写文件。

**团队微信 / 公众号**：真实 ID 已填入 `_layouts/default.html` 的 `#modal-wechat`（DFYX_SEC_TEAM）和 `#modal-gzh`（dfyx_sec）两个弹窗，如需修改直接改 `<code>` 内容和 `data-copy` 属性。

## 签名墙管理（删除不当签名）

- **删除**：签名墙右上「签名管理」→ GitHub Discussion #1（仓库所有者权限）→ 评论卡片 `···` 菜单 → Delete。
- **软隐藏**（不删数据）：编辑 `assets/giscus-theme.css` 底部屏蔽名单，取消注释并替换 `BLOCKED_LOGIN` 为对方 GitHub 登录名，push 即生效。

## 目录结构

```
blog-site/
├── _config.yml          # 站点配置 + topics/articles collection 声明（scripts 目录不进产物）
├── index.md             # 首页
├── topics.md / articles.md / news.md / wall.md / about.md   # 各板块子页面
├── _layouts/
│   ├── default.html     # 页面骨架：导航/页脚/联系方式弹窗（视频号/微信/公众号）
│   ├── topic.html       # 话题页：资源矩阵表格渲染 + 评论区
│   └── article.html     # 文章页：自动目录 + 长文阅读版式 + 评论区
├── _includes/
│   └── comments.html    # giscus 评论区组件（pathname 映射，每页独立讨论串）
├── _topics/             # ★ 课题：一个话题一个 md
├── _articles/           # ★ 长文：publish_article.py 从主稿生成，勿手改
├── _data/news.json      # 安全资讯数据（脚本生成，勿手改）
├── scripts/sync_news.py        # 资讯同步脚本
├── scripts/publish_article.py  # 长文发布脚本（主稿 → 文章页 → push）
├── scripts/edit_article.py     # 本地文章编辑器服务（127.0.0.1:8917）
├── scripts/editor_ui.html      # 编辑器界面
├── scripts/_preview_render.rb  # 预览渲染（kramdown+GFM，与线上同引擎）
└── assets/              # 样式 / 图标 / 图片 / giscus 主题
```

## 本地预览（可选）

装过 Ruby 的前提下：`gem install jekyll && jekyll serve`，访问 http://127.0.0.1:4000。不装也行，直接 push 看线上效果。
