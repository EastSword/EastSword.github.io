---
layout: topic
title: Tag 即发布权
subtitle: GitLab / GitHub Tag 权限收敛与 CI 自动化管理实践
date: 2026-08-25
updated: 2026-08-25
status: drafting
keyword: tag
links:
  - platform: 公众号
    form: 上下两篇（东方隐侠安全团队）
    url:
    note: 稿件已备
  - platform: CSDN
    form: 自检避坑版
    url:
    note: 稿件已备
  - platform: B站
    form: 实操演示（一条命令绕过审核打 tag）
    url:
    note: 待录制
assets:
  - name: L0-L3 Tag 治理自评 checklist
    desc: 四级成熟度自评表，可打印
    location: 公众号回复 tag
    url:
  - name: 四平台 CI 自动打 tag 脚本包
    desc: GitLab Runner / TeamCity / Jenkins / GitHub Actions 最终版（含 TeamCity 五坑修复）
    location: 知识大陆「千里」
    url:
---

Git 的对象不可变，但贴在对象上的标签（ref）是可变的——这个被绝大多数团队忽略的事实，意味着 **tag 就是发布权**。

一条 `git tag` + `git push --tags` 就能把未经审核的代码推进生产：攻击者不需要入侵任何下游仓库，不需要碰 CI 配置，甚至不需要管理员权限（只要 Developer 角色能推 tag）。下游的部署系统、依赖解析器、镜像构建流水线全都无条件信任 tag 名。tj-actions 事件里，23,000 个什么都没做的仓库在一夜之间被打进恶意代码，攻击面正是这一层。

这个话题从 Git 对象模型的第一性原理讲起：六条攻击路径（含最阴的"tag 触发 CI 配置注入"）、五个供应链案例（tj-actions / xz / SolarWinds / Go proxy / Repo Jacking）、GitLab Protected Tags 与 GitHub Rulesets 的逐项收敛配置、NIST SSDF 与 SLSA 标准映射，以及四套可直接落地的 CI 自动打 tag 方案——TeamCity 那套是作者自己踩了五个坑换来的（VCS Trigger 分支过滤、`%` 参数替换吞字符、`sh` 非 bash、空 tag 列表误判……坑比配置本身值钱）。
