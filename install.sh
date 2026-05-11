#!/bin/bash

set -e

echo "===== 开始安装所有依赖 ====="
echo ""

echo "1. 安装 uv 包管理器..."
if ! command -v uv &> /dev/null; then
    echo "安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.cargo/env" 2>/dev/null || true
    source "$HOME/.local/share/uv/env" 2>/dev/null || true
else
    echo "✅ uv 已安装"
fi

echo ""
echo "2. 创建 Python 3.11 虚拟环境..."
uv python install 3.11
uv venv --python 3.11

echo ""
echo "3. 安装系统依赖..."
if ! command -v brew &> /dev/null; then
    echo "Homebrew 未安装，跳过"
else
    if ! command -v ffmpeg &> /dev/null; then
        echo "安装 ffmpeg..."
        brew install ffmpeg
    else
        echo "✅ ffmpeg 已安装"
    fi
fi

echo ""
echo "4. 克隆 MediaCrawler..."
if [ -d "MediaCrawler" ]; then
    echo "MediaCrawler 已存在，跳过克隆"
else
    git clone https://github.com/NanmiCoder/MediaCrawler.git
fi

echo ""
echo "5. 安装 Python 依赖..."
uv pip install -r requirements.txt
uv pip install funasr
uv pip install -U modelscope
uv pip install torchaudio

echo ""
echo "6. 安装 MediaCrawler 依赖..."
cd MediaCrawler
uv pip install -r requirements.txt
cd ..

echo ""
echo "7. 配置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || echo "FEISHU_APP_ID=your_app_id" > .env
    echo "FEISHU_APP_SECRET=your_app_secret" >> .env
    echo "请编辑 .env 文件填入你的飞书配置"
fi

echo ""
echo "===== 安装完成 ====="
echo ""
echo "下一步："
echo "1. 编辑 .env 文件，填入你的飞书 FEISHU_APP_ID 和 FEISHU_APP_SECRET"
echo "2. 运行 ./run.sh 关键字"
