#!/bin/bash

set -e

KEYWORDS=""
SORT_TYPE="general"
MAX_NOTES="15"

show_usage() {
    echo "用法: $0 --keys <关键字> [--sort <排序方式>] [--count <数量>]"
    echo ""
    echo "参数说明:"
    echo "  --keys      必填，搜索关键字，多个用逗号分隔，如: 针灸,中医美容"
    echo "  --sort      可选，排序方式，默认 general"
    echo "              general  - 综合排序"
    echo "              popular  - 最多点赞"
    echo "              latest   - 最新发布"
    echo "  --count     可选，抓取数量，默认15条"
    echo "  --help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --keys 针灸"
    echo "  $0 --keys 针灸,中医美容 --sort popular"
    echo "  $0 --keys 养生 --sort latest --count 20"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keys)
            KEYWORDS="$2"
            shift 2
            ;;
        --sort)
            SORT_TYPE="$2"
            shift 2
            ;;
        --count)
            MAX_NOTES="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "错误: 未知参数 $1"
            show_usage
            exit 1
            ;;
    esac
done

if [ -z "$KEYWORDS" ]; then
    echo "错误: --keys 参数是必填的"
    show_usage
    exit 1
fi

VALID_SORTS=("general" "popular" "latest")
if [[ ! " ${VALID_SORTS[@]} " =~ " ${SORT_TYPE} " ]]; then
    echo "错误: 无效的排序方式 '$SORT_TYPE'"
    echo "有效的排序方式: ${VALID_SORTS[*]}"
    exit 1
fi

if ! [[ "$MAX_NOTES" =~ ^[0-9]+$ ]]; then
    echo "错误: --count 参数必须是数字"
    exit 1
fi

echo "===== 开始自动化流程 ====="
echo "关键字: $KEYWORDS"
echo "排序方式: $SORT_TYPE"
echo "抓取数量: $MAX_NOTES"
echo ""

uv run python3 pipeline.py --keys "$KEYWORDS" --sort "$SORT_TYPE" --count "$MAX_NOTES"