#!/usr/bin/env python3
import os
import sys
import json
import io
import time
import requests
import re
import glob
from datetime import datetime
from dotenv import load_dotenv
from funasr import AutoModel

load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')

def parse_bitable_url(url):
    import re
    match = re.search(r'/base/([a-zA-Z0-9]+)', url)
    app_token = match.group(1) if match else None
    
    table_match = re.search(r'table=([a-zA-Z0-9]+)', url)
    table_id = table_match.group(1) if table_match else None
    
    return app_token, table_id

BITABLE_URL = os.getenv('BITABLE_URL')
if BITABLE_URL:
    BITABLE_APP_TOKEN, BITABLE_TABLE_ID = parse_bitable_url(BITABLE_URL)
    print(f"从URL解析: APP_TOKEN={BITABLE_APP_TOKEN}, TABLE_ID={BITABLE_TABLE_ID}")
else:
    BITABLE_APP_TOKEN = os.getenv('BITABLE_APP_TOKEN')
    BITABLE_TABLE_ID = os.getenv('BITABLE_TABLE_ID')

FIELD_MAPPING = {
    "note_id": "笔记ID",
    "note_url": "笔记链接",
    "title": "笔记标题",
    "type": "笔记类型",
    "desc": "笔记正文",
    "video_url": "视频链接",
    "time": "发布时间",
    "last_update_time": "更新时间",
    "user_id": "用户ID",
    "nickname": "账号昵称",
    "avatar": "封面图",
    "liked_count": "点赞数",
    "collected_count": "收藏数",
    "comment_count": "评论数",
    "share_count": "分享数",
    "ip_location": "地理位置",
    "image_list": "图片列表",
    "tag_list": "标签",
    "last_modify_ts": "采集时间",
    "source_keyword": "搜索关键词",
    "subtitle": "视频字幕"
}

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data)
    return response.json().get("tenant_access_token")

def get_table_fields(token, app_token, table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    result = response.json()
    if result.get('code') == 0:
        return result.get('data', {}).get('items', [])
    return []

def load_json_data(file_path):
    print(f"\n===== 读取数据: {file_path} =====")
    data = []

    if os.path.isdir(file_path):
        jsonl_files = glob.glob(os.path.join(file_path, '**', '*.jsonl'), recursive=True)
        content_files = [f for f in jsonl_files if 'search_contents' in f and 'comments' not in f]
        if content_files:
            for jsonl_file in content_files:
                print(f"  读取文件: {jsonl_file}")
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data.append(json.loads(line))
        else:
            print(f"  ⚠️ 未找到 search_contents.jsonl 文件")
    else:
        if file_path.endswith('.jsonl'):
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))

    if isinstance(data, dict):
        data = list(data.values())
    elif not isinstance(data, list):
        data = [data]

    print(f"加载了 {len(data)} 条数据")
    return data

def download_video_to_memory(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=1024*1024):
            if chunk:
                buffer.write(chunk)

        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"下载失败: {str(e)[:80]}")
        return None

def save_temp_video(video_buffer, path="temp_video.mp4"):
    try:
        with open(path, 'wb') as f:
            f.write(video_buffer.getvalue())
        return path
    except Exception as e:
        print(f"保存失败: {e}")
        return None

def generate_subtitle_funasr(video_path, model):
    try:
        result = model.generate(input=video_path, language="zh", use_itn=True)
        subtitle = result[0]["text"]
        subtitle = subtitle.replace("<|zh|>", "").replace("<|HAPPY|>", "").replace("<|BGM|>", "").replace("<|withitn|>", "")
        return subtitle.strip()
    except Exception as e:
        print(f"字幕生成失败: {e}")
        return ""

def generate_subtitles(data):
    print("\n===== 步骤2: 生成字幕 =====")

    print("加载 FunASR 模型...")
    model = AutoModel(model="iic/SenseVoiceSmall", vad_model="fsmn-vad", device="cpu")
    print("模型加载成功")

    video_count = sum(1 for item in data if item.get('video_url', '').strip().startswith('http'))
    print(f"共有 {video_count} 个视频需要处理")

    for i, item in enumerate(data):
        video_url = item.get('video_url', '').strip()
        title = item.get('title', '')[:30]

        if not video_url or not video_url.startswith('http'):
            print(f"跳过 {i+1}/{len(data)}: 无有效视频URL")
            item['subtitle'] = ''
            continue

        print(f"处理 {i+1}/{len(data)}: {title}")

        video_buffer = download_video_to_memory(video_url)
        if not video_buffer:
            item['subtitle'] = ''
            continue

        video_path = save_temp_video(video_buffer)
        if not video_path:
            item['subtitle'] = ''
            continue

        subtitle = generate_subtitle_funasr(video_path, model)
        item['subtitle'] = subtitle

        if os.path.exists(video_path):
            os.remove(video_path)

        if subtitle:
            print(f"  ✅ 字幕长度: {len(subtitle)} 字")

        time.sleep(0.5)

    return data

def append_to_bitable(data):
    print("\n===== 步骤3: 追加数据到飞书 =====")

    if not BITABLE_APP_TOKEN:
        print("❌ 错误: .env 中未设置 BITABLE_APP_TOKEN")
        print("请在 .env 文件中添加: BITABLE_APP_TOKEN=您的表格AppToken")
        return None

    token = get_access_token()
    if not token:
        print("获取token失败")
        return None

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if BITABLE_TABLE_ID:
        table_id = BITABLE_TABLE_ID
        print(f"使用指定的表格ID: {table_id}")
    else:
        url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables'
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get('code') != 0:
            print(f"获取表格信息失败: {result.get('msg')}")
            return None

        tables = result.get('data', {}).get('items', [])
        if not tables:
            print("❌ 表格中没有数据表")
            return None
        
        table_id = tables[0].get('table_id')
        print(f"获取到表格ID: {table_id}")

    existing_fields = get_table_fields(token, BITABLE_APP_TOKEN, table_id)
    existing_field_names = {field.get('field_name') for field in existing_fields}
    print(f"表格已有字段: {existing_field_names}")

    all_fields = set()
    all_fields = sorted(list(FIELD_MAPPING.keys()))
    print(f"数据字段 (仅导入FIELD_MAPPING中定义的字段): {all_fields}")

    for field_name in all_fields:
        chinese_name = FIELD_MAPPING.get(field_name, field_name)
        if chinese_name not in existing_field_names:
            url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/fields'
            payload = {'field_name': chinese_name, 'type': 1}
            response = requests.post(url, headers=headers, json=payload)
            print(f"添加新字段: {field_name} -> {chinese_name}")
            existing_field_names.add(chinese_name)

    filtered_data = []
    for row_data in data:
        if row_data.get('note_id'):
            filtered_data.append(row_data)
    
    print(f"过滤后数据行数: {len(filtered_data)}")

    bitable_records = []
    for row_data in filtered_data:
        record_fields = {}
        for field in all_fields:
            chinese_name = FIELD_MAPPING.get(field, field)
            value = row_data.get(field, "")
            if isinstance(value, str):
                value = value.strip()
                value = re.sub(r'`', '', value)
            record_fields[chinese_name] = str(value)[:5000] if value is not None else ""
        bitable_records.append({"fields": record_fields})

    batch_size = 20
    for i in range(0, len(bitable_records), batch_size):
        batch = bitable_records[i:i+batch_size]
        url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/records/batch_create'
        payload = {"records": batch}
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        if result.get('code') == 0:
            print(f"写入数据 {i+1} - {i+len(batch)}")
        else:
            print(f"写入失败: {result.get('msg')}")

    print("数据追加完成")

    return BITABLE_APP_TOKEN

def main():
    data_dir = '/Users/mattcui/Downloads/workspace/sync_feishu/data'
    
    print("===== 查找已爬取的数据 =====")
    jsonl_files = glob.glob(os.path.join(data_dir, '**', '*search_contents*jsonl'), recursive=True)
    content_files = sorted([f for f in jsonl_files if 'comments' not in f and 'with_subtitle' not in f], key=os.path.getmtime, reverse=True)
    
    if not content_files:
        print("未找到已爬取的数据文件")
        sys.exit(1)
    
    print("找到以下数据文件:")
    for i, file in enumerate(content_files[:5], 1):
        size = os.path.getsize(file)
        mtime = os.path.getmtime(file)
        mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{i}. {file}")
        print(f"   大小: {size} bytes, 修改时间: {mtime_str}")
    
    latest_file = content_files[0]
    print(f"\n使用最新文件: {latest_file}")
    
    data = load_json_data(latest_file)
    if not data:
        print("❌ 无数据")
        sys.exit(1)

    data = generate_subtitles(data)

    output_dir = 'data'
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f'search_contents_{timestamp}_with_subtitle.jsonl')
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"\n✅ 带字幕数据已保存: {output_path}")

    app_token = append_to_bitable(data)

    print("\n" + "="*50)
    if app_token:
        print(f"🎉 数据已追加到飞书表格!")
        print(f"表格链接: https://qcnytqlnrfst.feishu.cn/base/{app_token}")
    else:
        print("❌ 飞书写入失败")
    print("="*50)

if __name__ == "__main__":
    main()