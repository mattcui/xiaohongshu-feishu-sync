# 小红书数据导入飞书表格工具

## 功能说明

该工具可以将 MediaCrawler 抓取的小红书 JSON 数据导入到飞书表格中。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置飞书

1. 在飞书开发者平台创建企业自建应用
2. 获取 App ID 和 App Secret
3. 给应用添加「云文档」权限（至少需要「创建、编辑文档/表格」权限）
4. 在 `.env` 文件中配置：

```env
FEISHU_APP_ID=your_app_id_here
FEISHU_APP_SECRET=your_app_secret_here
```

## 获取飞书文件夹 Token

打开飞书云文档，进入目标文件夹，URL 格式如下：
```
https://www.feishu.cn/drive/folder/fldxxxxxxxxxxxxxxxxxxxxxx
```
`fld` 后面的部分就是文件夹 Token。

## 使用方法

### 方法一：从 JSON 文件导入

```bash
python xiaohongshu_to_feishu.py --folder-token fldxxxxxxxxxxxxxxxxxxxxxx --json-file data.json
```

### 方法二：直接传入 JSON 字符串

```bash
python xiaohongshu_to_feishu.py --folder-token fldxxxxxxxxxxxxxxxxxxxxxx --json-string '{"note_id":"xxx","title":"xxx"}'
```

### 指定表格名称

```bash
python xiaohongshu_to_feishu.py --folder-token fldxxxxxxxxxxxxxxxxxxxxxx --json-file data.json --table-name "我的小红书数据"
```

## 注意事项

1. 确保飞书应用有足够的权限创建表格
2. JSON 数据可以是单个对象或对象数组
3. 工具会自动根据 JSON 的 key 创建表格列
4. 支持的数据量取决于飞书表格的限制
