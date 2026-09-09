#!/bin/bash
# 安全资讯同步包装脚本（推荐入口）
# 用法：bash scripts/sync_news.sh [--no-push] [--backfill]
#
# 为什么需要包装：TRAE 沙箱会把 PYTHONHOME/PYTHONPATH 注入所有子进程，指向
# 沙箱自带的 Python 3.13 框架；系统 python3（CommandLineTools 3.9）启动时按该
# 路径找标准库会直接崩溃（ModuleNotFoundError: No module named 'encodings'）。
# 崩溃发生在解释器初始化阶段，脚本内代码无法拦截，只能在启动层面用 `-E`
# （忽略全部 PYTHON* 环境变量）规避。shebang 已带 -E，但显式 `python3 scripts/
# sync_news.py` 会绕过 shebang，故统一走本包装。

set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -E scripts/sync_news.py "$@"
