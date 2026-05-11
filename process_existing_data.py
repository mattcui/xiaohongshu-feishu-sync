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

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data)
    return response.json().get("tenant_access_token")

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
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    try:
                        data = json.loads(content)
                    except:
                        lines = content.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line:
                                try:
                                    data.append(json.loads(line))
                                except:
                                    pass

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

def write_to_feishu(data):
    print("\n===== 步骤3: 写入飞书 =====")

    token = get_access_token()
    if not token:
        print("获取token失败")
        return None

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    all_fields = set()
    for row in data:
        for key, value in row.items():
            if value and str(value).strip():
                all_fields.add(key)
    
    fields = sorted(list(all_fields))
    print(f"有效字段数: {len(fields)}")
    print(f"字段列表: {fields}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    table_name = f"小红书数据_{timestamp}"

    url = 'https://open.feishu.cn/open-apis/bitable/v1/apps'
    payload = {
        'name': table_name,
        'share_to_org': True,
        'share_to_org_permission': 'view'
    }
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()

    if result.get('code') != 0:
        print(f"创建表格失败: {result.get('msg')}")
        return None

    app_token = result.get('data', {}).get('app', {}).get('app_token')
    table_id = result.get('data', {}).get('app', {}).get('default_table_id')

    print(f"创建表格成功: {table_name}")

    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields'
    response = requests.get(url, headers=headers)
    default_fields = response.json().get('data', {}).get('items', [])
    
    print(f"获取到 {len(default_fields)} 个默认字段:")
    for field in default_fields:
        field_id = field.get('field_id')
        field_name = field.get('field_name')
        print(f"  - {field_name}")
        delete_url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}'
        requests.delete(delete_url, headers=headers)
        print(f"    已删除字段: {field_name}")

    for field_name in fields:
        url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields'
        payload = {'field_name': field_name, 'type': 1}
        response = requests.post(url, headers=headers, json=payload)

    print("添加字段完成")

    print("删除默认空行...")
    records_url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records'
    response = requests.get(records_url, headers=headers)
    records = response.json().get('data', {}).get('items', [])
    
    record_ids_to_delete = []
    for record in records:
        record_ids_to_delete.append(record.get('record_id'))
    
    if record_ids_to_delete:
        delete_url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete'
        delete_payload = {"records": record_ids_to_delete}
        requests.post(delete_url, headers=headers, json=delete_payload)
        print(f"已删除 {len(record_ids_to_delete)} 条默认空行")

    filtered_data = []
    for row_data in data:
        if row_data.get('note_id'):
            filtered_data.append(row_data)
    
    print(f"过滤后数据行数: {len(filtered_data)}")

    bitable_records = []
    for row_data in filtered_data:
        record_fields = {}
        for field in fields:
            value = row_data.get(field, "")
            if isinstance(value, str):
                value = value.strip()
                value = re.sub(r'`', '', value)
            record_fields[field] = str(value)[:5000] if value is not None else ""
        bitable_records.append({"fields": record_fields})

    batch_size = 20
    for i in range(0, len(bitable_records), batch_size):
        batch = bitable_records[i:i+batch_size]
        url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create'
        payload = {"records": batch}
        requests.post(url, headers=headers, json=payload)
        print(f"写入数据 {i+1} - {i+len(batch)}")

    print("数据写入完成")

    return app_token

def main():
    data_dir = '/Users/mattcui/Downloads/workspace/sync_feishu/data'
    
    print("===== 查找已爬取的数据 =====")
    jsonl_files = glob.glob(os.path.join(data_dir, '**', '*search_contents*jsonl'), recursive=True)
    content_files = sorted([f for f in jsonl_files if 'comments' not in f], key=os.path.getmtime, reverse=True)
    
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

    app_token = write_to_feishu(data)

    print("\n" + "="*50)
    if app_token:
        url = f"https://qcnytqlnrfst.feishu.cn/base/{app_token}"
        print(f"🎉 完成！飞书表格链接: {url}")
    else:
        print("❌ 飞书写入失败")
    print("="*50)

if __name__ == "__main__":
    main()