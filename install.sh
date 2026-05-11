#!/bin/bash

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 步骤计数器
step=1
total_steps=7

print_title() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║              小红书数据抓取工具 - 安装配置向导                  ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
}

print_step() {
    echo ""
    echo "================================================================"
    echo "  [$step/$total_steps] $1"
    echo "================================================================"
    step=$((step + 1))
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 主程序
print_title

# 步骤1: 检查 Python 环境
print_step "检查 Python 环境"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "当前 Python 版本: $PYTHON_VERSION"
else
    print_error "未找到 Python3，请先安装 Python"
    echo ""
    echo "安装 Python 方法："
    echo "  macOS: brew install python3"
    echo "  Ubuntu: sudo apt install python3 python3-pip"
    exit 1
fi

# 步骤2: 安装 uv 包管理器
print_step "安装 uv 包管理器"
if command -v uv &> /dev/null; then
    print_success "uv 已安装"
else
    echo "正在安装 uv..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        # 刷新 PATH
        export PATH="$HOME/.local/bin:$PATH"
        print_success "uv 安装成功"
    else
        print_error "uv 安装失败"
        exit 1
    fi
fi

# 步骤3: 创建虚拟环境
print_step "创建虚拟环境"
if [ -d ".venv" ]; then
    print_success "虚拟环境已存在，跳过创建"
else
    echo "正在创建虚拟环境..."
    if uv venv --python 3.11; then
        print_success "虚拟环境创建成功"
    else
        print_error "虚拟环境创建失败"
        exit 1
    fi
fi

# 步骤4: 安装项目依赖
print_step "安装项目依赖"
echo "正在安装项目依赖..."
if uv pip install -r requirements.txt; then
    print_success "项目依赖安装成功"
else
    print_error "项目依赖安装失败"
    exit 1
fi

echo "正在安装语音识别依赖..."
if uv pip install funasr modelscope torchaudio --quiet; then
    print_success "语音识别依赖安装成功"
else
    print_warning "语音识别依赖安装失败（可选）"
fi

# 步骤5: 克隆 MediaCrawler
print_step "克隆 MediaCrawler"
if [ -d "MediaCrawler" ]; then
    print_success "MediaCrawler 已存在，跳过克隆"
else
    echo "正在克隆 MediaCrawler..."
    if git clone https://github.com/NanmiCoder/MediaCrawler.git; then
        print_success "MediaCrawler 克隆成功"
        echo "正在安装 MediaCrawler 依赖..."
        if uv pip install -r MediaCrawler/requirements.txt; then
            print_success "MediaCrawler 依赖安装成功"
        else
            print_error "MediaCrawler 依赖安装失败"
            exit 1
        fi
    else
        print_error "MediaCrawler 克隆失败"
        exit 1
    fi
fi

# 步骤6: 配置飞书凭证
print_step "配置飞书凭证"

read -p "请输入飞书 APP ID: " FEISHU_APP_ID
while [ -z "$FEISHU_APP_ID" ]; do
    print_error "此项为必填项"
    read -p "请输入飞书 APP ID: " FEISHU_APP_ID
done

read -p "请输入飞书 APP Secret: " FEISHU_APP_SECRET
while [ -z "$FEISHU_APP_SECRET" ]; do
    print_error "此项为必填项"
    read -p "请输入飞书 APP Secret: " FEISHU_APP_SECRET
done

read -p "请输入飞书表格 URL: " BITABLE_URL
while [ -z "$BITABLE_URL" ]; do
    print_error "此项为必填项"
    read -p "请输入飞书表格 URL: " BITABLE_URL
done

# 写入 .env 文件
cat > .env << EOF
FEISHU_APP_ID=$FEISHU_APP_ID
FEISHU_APP_SECRET=$FEISHU_APP_SECRET
BITABLE_URL=$BITABLE_URL
EOF

print_success "配置文件已保存"

# 步骤7: 测试飞书连接
print_step "测试飞书连接"
echo "正在测试飞书连接..."
TEST_RESULT=$(uv run python3 -c "
import os
from dotenv import load_dotenv
import requests

load_dotenv()
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')

if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
    print('配置缺失')
    exit(1)

url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
response = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
result = response.json()
if result.get('code') == 0 and result.get('tenant_access_token'):
    print('连接成功')
else:
    print(f'连接失败: {result.get(\"msg\", \"未知错误\")}')
    exit(1)
")

if [ "$TEST_RESULT" == "连接成功" ]; then
    print_success "飞书连接测试成功"
else
    print_warning "飞书连接测试失败: $TEST_RESULT"
    print_warning "请检查配置信息是否正确"
fi

# 完成
echo ""
echo "================================================================"
echo -e "${GREEN}🎉 安装配置完成！${NC}"
echo "================================================================"
echo ""
echo "📖 使用方法："
echo "  cd /Users/mattcui/Downloads/workspace/sync_feishu"
echo "  ./run.sh --keys <关键词> --sort <排序方式> --count <数量>"
echo ""
echo "📊 排序方式："
echo "  general  - 综合排序"
echo "  popular  - 最多点赞"
echo "  latest   - 最新发布"
echo ""
echo "💡 示例："
echo "  ./run.sh --keys 针灸"
echo "  ./run.sh --keys 针灸,中医美容 --sort popular --count 10"
echo ""