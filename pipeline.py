#!/usr/bin/env python3
import os
import sys
import json
import io
import subprocess
import time
import requests
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

def crawl_xiaohongshu(keywords):
    print("\n===== 步骤1: 爬取小红书数据 =====")

    keyword_list = [k.strip() for k in keywords.split(',')]
    print(f"爬取关键字: {keyword_list}")

    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    print(f"数据保存路径: {data_dir}")

    print("运行 MediaCrawler...")
    print("请在弹出的二维码页面扫码登录小红书")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_data = []

    for keyword in keyword_list:
        output_file = f'search_contents_{keyword}_{timestamp}.jsonl'
        save_path = os.path.join(data_dir, output_file)

        command = [
            'uv', 'run', 'main.py',
            '--platform', 'xhs',
            '--lt', 'qrcode',
            '--type', 'search',
            '--keywords', keyword,
            '--save_data_option', 'jsonl',
            '--save_data_path', save_path
        ]

        print(f"\n执行命令: {' '.join(command)}")
        result = subprocess.run(command, cwd='MediaCrawler', capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ 爬取失败: {result.stderr[:200]}")
        else:
            print(f"✅ 爬取成功，数据已保存到: {save_path}")

            if os.path.exists(save_path):
                with open(save_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            all_data.append(json.loads(line))

    print(f"\n爬取完成，共获取 {len(all_data)} 条数据")

    combined_file = os.path.join(data_dir, f'search_contents_all_{timestamp}.jsonl')
    with open(combined_file, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"合并后数据已保存到: {combined_file}")

    return combined_file

def load_json_data(file_path):
    print(f"\n===== 步骤2: 读取数据 =====")
    data = []

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
    print("\n===== 步骤3: 生成字幕 =====")

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
    print("\n===== 步骤4: 写入飞书 =====")

    token = get_access_token()
    if not token:
        print("获取token失败")
        return None

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    fields = list(data[0].keys())
    print(f"字段数: {len(fields)}")

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

    for field_name in fields:
        url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields'
        payload = {'field_name': field_name, 'type': 1}
        requests.post(url, headers=headers, json=payload)

    print("添加字段完成")

    bitable_records = []
    for row_data in data:
        record_fields = {}
        for field in fields:
            value = row_data.get(field, "")
            if isinstance(value, str):
                value = value.strip()
                import re
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
    if len(sys.argv) < 2:
        print("用法: python pipeline.py <关键字>")
        print("示例: python pipeline.py 针灸")
        print("       python pipeline.py 针灸,中医美容,养生")
        sys.exit(1)

    keywords = sys.argv[1]

    print("="*50)
    print("小红书数据采集 + 字幕生成 + 飞书写入 自动化流程")
    print("="*50)

    json_path = crawl_xiaohongshu(keywords)
    if not json_path:
        print("❌ 爬取失败")
        sys.exit(1)

    data = load_json_data(json_path)
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
