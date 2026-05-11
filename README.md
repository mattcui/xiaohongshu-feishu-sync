# 小红书数据抓取工具

自动化爬取小红书数据并写入飞书表格的工具，支持自定义关键词、排序方式和抓取数量。

## ✨ 功能特性

- 📕 **小红书数据爬取** - 支持关键词搜索、多种排序方式
- 🎬 **视频字幕生成** - 自动生成视频逐字稿（使用 FunASR）
- ✍️ **飞书表格写入** - 自动将数据追加到飞书表格
- 🔑 **中英文字段映射** - 支持自定义中文列名
- 🧪 **环境检查** - 自动检测和配置运行环境
- 🔄 **浏览器集成** - 使用用户已登录的 Chrome 浏览器

## 📋 前置条件

- Python 3.9+
- macOS / Linux / Windows
- 飞书开放平台账号（用于创建应用获取 API 凭证）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/mattcui/xiaohongshu-feishu-sync.git
cd xiaohongshu-feishu-sync
```

### 2. 一键安装

运行安装脚本，自动完成依赖安装和环境配置：

```bash
chmod +x install.sh
./install.sh
```

安装过程中会提示输入飞书配置信息：
- **飞书 APP ID** - 从飞书开放平台获取
- **飞书 APP Secret** - 从飞书开放平台获取  
- **飞书表格 URL** - 目标表格的完整链接

### 3. 开始抓取

```bash
./run.sh --keys 针灸 --sort popular --count 10
```

## 📖 使用说明

### 安装脚本 (`install.sh`)

一键完成所有安装和配置：

```bash
./install.sh
```

**安装流程：**
1. 检查 Python 环境
2. 安装 uv 包管理器
3. 创建虚拟环境
4. 安装项目依赖
5. 克隆 MediaCrawler
6. 配置飞书凭证（交互式输入）
7. 测试飞书连接

### 运行脚本 (`run.sh`)

```bash
./run.sh --keys <关键词> --sort <排序方式> --count <数量>
```

**参数说明：**

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `--keys` | 搜索关键词，多个用逗号分隔 | 任意关键词 | 必填 |
| `--sort` | 排序方式 | `general`, `popular`, `latest` | `general` |
| `--count` | 抓取数量 | 1-100 | 15 |
| `--help` | 显示帮助信息 | - | - |

**排序方式说明：**
- `general` - 综合排序
- `popular` - 最多点赞
- `latest` - 最新发布

**示例：**

```bash
# 抓取针灸相关笔记，使用默认配置
./run.sh --keys 针灸

# 抓取多个关键词，按最多点赞排序，抓取20条
./run.sh --keys 针灸,中医美容 --sort popular --count 20

# 抓取最新发布的养生笔记
./run.sh --keys 养生 --sort latest --count 15
```

### 配置文件 (`.env`)

安装脚本会自动生成 `.env` 文件，也可以手动创建：

```env
# 飞书应用凭证
FEISHU_APP_ID=your_app_id_here
FEISHU_APP_SECRET=your_app_secret_here

# 飞书表格 URL
BITABLE_URL=https://xxx.feishu.cn/base/your_app_token?table=your_table_id
```

**获取飞书凭证步骤：**
1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 在「凭证与基础信息」中获取 APP ID 和 APP Secret
4. 在「权限管理」中添加以下权限：
   - `bitable:app:readonly`
   - `bitable:table:readonly`
   - `bitable:record:create`
5. 启用应用并获取表格 URL

## 📊 输出字段

抓取的数据包含以下字段（支持中英文字段映射）：

| 英文字段 | 中文列名 | 说明 |
|----------|----------|------|
| note_id | 笔记ID | 小红书笔记唯一标识 |
| note_url | 笔记链接 | 笔记详情页链接 |
| title | 笔记标题 | 笔记标题 |
| type | 笔记类型 | 图文/视频 |
| desc | 笔记正文 | 笔记内容 |
| video_url | 视频链接 | 视频文件链接 |
| time | 发布时间 | 笔记发布时间 |
| last_update_time | 更新时间 | 笔记更新时间 |
| user_id | 用户ID | 发布者ID |
| nickname | 账号昵称 | 发布者昵称 |
| avatar | 封面图 | 笔记封面图片链接 |
| liked_count | 点赞数 | 点赞数量 |
| collected_count | 收藏数 | 收藏数量 |
| comment_count | 评论数 | 评论数量 |
| share_count | 分享数 | 分享数量 |
| ip_location | 地理位置 | 发布者IP位置 |
| image_list | 图片列表 | 图片链接列表 |
| tag_list | 标签 | 笔记标签 |
| last_modify_ts | 采集时间 | 数据采集时间 |
| source_keyword | 搜索关键词 | 搜索使用的关键词 |
| subtitle | 视频逐字稿 | 视频语音转文字内容 |

## 🛠️ 项目结构

```
xiaohongshu-feishu-sync/
├── pipeline.py          # 核心流程脚本
├── run.sh               # 运行脚本
├── install.sh           # 一键安装脚本
├── check_env.py         # 环境检查脚本
├── configure.py         # 配置向导
├── clean_table.py       # 清空表格脚本
├── append_to_bitable.py # 飞书表格操作
├── requirements.txt     # Python 依赖
├── .env.sample          # 环境变量模板
├── SKILL.md             # Trae Skill 定义
├── README.md            # 项目说明
└── MediaCrawler/        # 数据爬取模块（自动克隆）
```

## 🧪 环境检查

运行环境检查脚本验证配置：

```bash
uv run python3 check_env.py
```

**检查内容：**
- 项目目录是否存在
- `.env` 配置文件是否完整
- 虚拟环境是否创建
- 核心脚本是否齐全

## 📝 常见问题

### Q1: 为什么需要扫码登录小红书？

首次运行需要扫码登录小红书账号，后续会使用 Chrome 的登录状态，无需重复登录。

### Q2: 飞书连接失败怎么办？

请检查：
- APP ID 和 APP Secret 是否正确
- 应用是否已启用
- 是否已添加必要的权限
- 网络连接是否正常

### Q3: 数据写入失败？

请检查：
- 飞书表格字段类型是否匹配
- 是否有写入权限
- 字段内容是否超过长度限制

### Q4: 如何清空飞书表格？

```bash
uv run python3 clean_table.py
```

## 🔒 安全注意事项

- 请勿将 `.env` 文件提交到版本控制
- 定期轮换飞书 APP Secret
- 仅授予应用最小必要权限

## 📄 许可证

本项目仅供学习和研究目的使用。使用时应遵守目标平台的使用条款和 robots.txt 规则。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**使用提示**：如果您是第一次使用，请先运行 `./install.sh` 完成安装配置，然后使用 `./run.sh` 开始抓取数据。