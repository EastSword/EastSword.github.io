# 东方隐侠安全团队 · 话题中枢站

以**研究主题**（而非时间流文章）组织的个人站点：每个话题一个页面，聚合该研究在公众号 / CSDN / FreeBuf / B站 / 知识大陆的全部形态入口与配套资产，地址持续修订。基于 GitHub Pages 原生 Jekyll，零依赖、零 CI。

**线上地址**：https://eastsword.github.io （仓库：EastSword/eastsword.github.io）
**鼠标悬停 favicon 显示**：东方隐侠安全团队（浏览器标题栏 / 书签名，取自 `_config.yml` 的 `title`）

## 日常维护（这就是全部）

**发布新平台后，更新话题页的资源地址**：打开 `_topics/<话题>.md`，把对应条目的 `url:` 从空填上，`note` 从"待上线"改成实际说明，`updated` 字段改成当天日期。commit + push，1 分钟后站点自动更新。

**新增一个研究话题**：复制任意 `_topics/` 下的文件改名，front-matter 里 `status` 三选一（`drafting` 撰写中 / `publishing` 发布中 / `published` 已发布，控制首页徽章颜色），`keyword` 填公众号关键词，`links` / `videos` / `assets` 数组按需增删——url 留空的条目自动显示"待上线"。正文区写话题摘要。首页话题卡片自动生成，无需改首页。

**绑定自定义域名**（可选）：仓库根加 `CNAME` 文件写域名，DNS 加 CNAME 指向 `<用户名>.github.io`。

## 目录结构

```
blog-site/
├── _config.yml          # 站点配置 + topics collection 声明
├── index.md             # 首页（话题卡片自动遍历生成）
├── _layouts/
│   ├── default.html     # 页面骨架（header/footer）
│   └── topic.html       # 话题页：资源矩阵表格渲染
├── _topics/             # ★ 日常只动这里：一个话题一个 md
└── assets/style.css     # 深色冷色调样式
```

## 本地预览（可选）

装过 Ruby 的前提下：`gem install jekyll && jekyll serve`，访问 http://127.0.0.1:4000。不装也行，直接 push 看线上效果。
