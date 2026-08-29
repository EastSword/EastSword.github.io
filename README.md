# 东方隐侠安全团队 · 话题中枢站

以**研究主题**（而非时间流文章）组织的个人站点：每个话题一个页面，聚合该研究在公众号 / CSDN / FreeBuf /B站 / 视频号的全部形态入口与配套资产，地址持续修订。基于 GitHub Pages 原生 Jekyll，零依赖、零 CI。

**线上地址**：https://eastsword.github.io （仓库：EastSword/eastsword.github.io）

## 站点结构（多页面）

| 页面 | 文件 | 说明 |
|------|------|------|
| 首页 | `index.md` | Hero + 四大板块导航 + 课题/资讯预览 |
| 研究话题 | `topics.md` | 全部课题，**领域分类**（`category` 字段）+ 标签双层筛选 + 搜索 + 分页 |
| 安全资讯 | `news.md` | 渲染 `_data/news.json`，分类筛选 + 搜索 + 分页 |
| 江湖留名 | `wall.md` | giscus 签名墙（GitHub Discussion #1） |
| 关于团队 | `about.md` | 团队介绍 + 联系方式卡片 |
| 话题详情 | `_topics/*.md` | 每课题一页，`layout: topic` |

## 日常维护

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
├── _config.yml          # 站点配置 + topics collection 声明
├── index.md             # 首页
├── topics.md / news.md / wall.md / about.md   # 各板块子页面
├── _layouts/
│   ├── default.html     # 页面骨架：导航/页脚/联系方式弹窗（视频号/微信/公众号）
│   └── topic.html       # 话题页：资源矩阵表格渲染
├── _topics/             # ★ 课题：一个话题一个 md
├── _data/news.json      # 安全资讯数据（脚本生成，勿手改）
├── scripts/sync_news.py # 资讯同步脚本
└── assets/              # 样式 / 图标 / giscus 主题
```

## 本地预览（可选）

装过 Ruby 的前提下：`gem install jekyll && jekyll serve`，访问 http://127.0.0.1:4000。不装也行，直接 push 看线上效果。
