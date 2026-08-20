#!/usr/bin/env bash
# GNSS 文献调研 Agent — macOS/Linux 构建（验证 spec 可用；安装器需在 Windows 生成）
set -e
cd "$(dirname "$0")/.."
python3 packaging/build.py
