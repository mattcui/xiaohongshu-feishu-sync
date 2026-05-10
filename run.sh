#!/bin/bash

set -e

if [ -z "$1" ]; then
    echo "用法: ./run.sh <关键字>"
    echo "示例: ./run.sh 针灸"
    echo "       ./run.sh 针灸,中医美容,养生"
    exit 1
fi

KEYWORDS="$1"

echo "===== 开始自动化流程 ====="
echo "关键字: $KEYWORDS"
echo ""

uv run python3 pipeline.py "$KEYWORDS"
