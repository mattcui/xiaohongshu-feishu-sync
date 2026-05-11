#!/usr/bin/env python3
import os
import sys
import json
import io
import subprocess
import time
import requests
import re
import argparse
from datetime import datetime
from dotenv import load_dotenv
from funasr import AutoModel

load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')

def parse_bitable_url(url):
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
    "subtitle": "视频逐字稿"
}

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data)
    return response.json().get("tenant_access_token")

def set_xhs_sort_type(sort_type):
    config_path = os.path.join('MediaCrawler', 'config', 'xhs_config.py')
    if not os.path.exists(config_path):
        print(f"警告：未找到配置文件 {config_path}")
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_content = content

    sort_mapping = {
        "general": "general",
        "popular": "popularity_descending",
        "latest": "time_descending"
    }
    actual_sort = sort_mapping.get(sort_type, sort_type)

    content = re.sub(
        r"SORT_TYPE\s*=\s*[\"'][^\"']*[\"']",
        f"SORT_TYPE = \"{actual_sort}\"",
        content
    )

    if content != old_content:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已设置小红书排序类型为: {sort_type} ({actual_sort})")
        return old_content
    return None

def set_xhs_max_notes_count(max_count):
    config_path = os.path.join('MediaCrawler', 'config', 'base_config.py')
    if not os.path.exists(config_path):
        print(f"警告：未找到配置文件 {config_path}")
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_content = content

    content = re.sub(
        r"CRAWLER_MAX_NOTES_COUNT\s*=\s*\d+",
        f"CRAWLER_MAX_NOTES_COUNT = {max_count}",
        content
    )

    if content != old_content:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已设置小红书抓取数量为: {max_count}")
        return old_content
    return None

def crawl_xiaohongshu(keywords, sort_type="general", max_notes_count=15):
    print("\n===== 步骤1: 爬取小红书数据 =====")

    keyword_list = [k.strip() for k in keywords.split(',')]
    print(f"爬取关键字: {keyword_list}")
    print(f"排序方式: {sort_type}")
    print(f"抓取数量: {max_notes_count}")

    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    print(f"数据保存路径: {data_dir}")

    print("运行 MediaCrawler...")
    print("请在弹出的二维码页面扫码登录小红书")

    original_sort_config = set_xhs_sort_type(sort_type)
    original_count_config = set_xhs_max_notes_count(max_notes_count)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_data = []

    try:
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
                    if os.path.isdir(save_path):
                        import glob
                        jsonl_files = glob.glob(os.path.join(save_path, '**', '*.jsonl'), recursive=True)
                        # 优先读取笔记数据文件（search_contents）
                        content_files = [f for f in jsonl_files if 'search_contents' in f and 'search_comments' not in f]
                        if content_files:
                            for jsonl_file in content_files:
                                print(f"  读取文件: {jsonl_file}")
                                with open(jsonl_file, 'r', encoding='utf-8') as f:
                                    for line in f:
                                        line = line.strip()
                                        if line:
                                            data_item = json.loads(line)
                                            # 只保留有title字段的笔记数据，过滤掉评论数据
                                            if 'title' in data_item:
                                                all_data.append(data_item)
                        else:
                            print(f"  ⚠️ 未找到 search_contents.jsonl 文件")
                    else:
                        with open(save_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    data_item = json.loads(line)
                                    # 只保留有title字段的笔记数据
                                    if 'title' in data_item:
                                        all_data.append(data_item)
    finally:
        if original_sort_config is not None:
            config_path = os.path.join('MediaCrawler', 'config', 'xhs_config.py')
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(original_sort_config)
            print("已恢复排序配置")

        if original_count_config is not None:
            config_path = os.path.join('MediaCrawler', 'config', 'base_config.py')
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(original_count_config)
            print("已恢复抓取数量配置")

    print(f"\n爬取完成，共获取 {len(all_data)} 条数据")

    combined_file = os.path.join(data_dir, f'search_contents_all_{timestamp}.jsonl')
    with open(combined_file, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"合并后数据已保存到: {combined_file}")

    return combined_file

def load_json_data(file_path, max_count=None):
    print(f"\n===== 步骤2: 读取数据 =====")
    data = []

    if file_path.endswith('.jsonl'):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
                    if max_count and len(data) >= max_count:
                        break
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

    if max_count and len(data) > max_count:
        data = data[:max_count]

    print(f"加载了 {len(data)} 条数据 (限制为 {max_count} 条)")
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

    if not BITABLE_APP_TOKEN or not BITABLE_TABLE_ID:
        print("❌ 未配置飞书表格，请检查 .env 文件中的 BITABLE_URL")
        return None

    token = get_access_token()
    if not token:
        print("获取token失败")
        return None

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print(f"目标表格: BITABLE_APP_TOKEN={BITABLE_APP_TOKEN}, TABLE_ID={BITABLE_TABLE_ID}")

    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/fields'
    response = requests.get(url, headers=headers)
    result = response.json()

    if result.get('code') != 0:
        print(f"获取表格字段失败: {result.get('msg')}")
        return None

    existing_fields = result.get('data', {}).get('items', [])
    existing_field_names = {field.get('field_name') for field in existing_fields}
    existing_field_types = {field.get('field_name'): field.get('type') for field in existing_fields}
    print(f"表格已有字段: {existing_field_names}")

    all_fields = sorted(list(FIELD_MAPPING.keys()))
    print(f"数据字段 (仅导入FIELD_MAPPING中定义的字段): {all_fields}")

    for field_name in all_fields:
        chinese_name = FIELD_MAPPING.get(field_name, field_name)
        if chinese_name not in existing_field_names:
            url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/fields'
            payload = {'field_name': chinese_name, 'type': 1}
            response = requests.post(url, headers=headers, json=payload)
            print(f"添加新字段: {field_name} -> {chinese_name}")
            existing_field_names.add(chinese_name)
        else:
            print(f"字段已存在: {chinese_name}")

    filtered_data = []
    for row_data in data:
        if row_data.get('note_id'):
            filtered_data.append(row_data)

    print(f"过滤后数据行数: {len(filtered_data)}")

    success_count = 0
    fail_count = 0

    for row_idx, row_data in enumerate(filtered_data):
        record_fields = {}
        for field in all_fields:
            chinese_name = FIELD_MAPPING.get(field, field)

            if chinese_name not in existing_field_names:
                continue

            field_type = existing_field_types.get(chinese_name, 1)

            if field_type == 5:
                continue

            value = row_data.get(field, "")

            if isinstance(value, str):
                value = value.strip()
                value = re.sub(r'`', '', value)

            if field_type == 2:
                if value is None or value == "":
                    continue
                if isinstance(value, str):
                    value = value.replace('万', '0000').replace(',', '').replace('.', '')
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                elif not isinstance(value, int):
                    continue
            elif field_type == 3:
                if value is None:
                    value = ""
                else:
                    value = str(value)[:5000]
            elif field_type == 15:
                if isinstance(value, str) and value.startswith('http'):
                    value = {"link": value}
                else:
                    continue
            else:
                if value is None:
                    value = ""
                else:
                    value = str(value)[:5000]

            record_fields[chinese_name] = value

        url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/records'
        payload = {"fields": record_fields}
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()

        if result.get('code') == 0:
            success_count += 1
        else:
            fail_count += 1

    print(f"写入完成！成功: {success_count}, 失败: {fail_count}")

    return BITABLE_APP_TOKEN

def main():
    parser = argparse.ArgumentParser(description='小红书数据采集 + 字幕生成 + 飞书写入 自动化流程')

    parser.add_argument('--keys', required=True, help='搜索关键字，多个用逗号分隔，如: 针灸,中医美容')
    parser.add_argument('--sort', default='general', choices=['general', 'popular', 'latest'],
                        help='排序方式: general(综合) | popular(最多点赞) | latest(最新)')
    parser.add_argument('--count', type=int, default=15, help='抓取数量，默认15条')

    args = parser.parse_args()

    keywords = args.keys
    sort_type = args.sort
    max_notes_count = args.count

    print("="*50)
    print("小红书数据采集 + 字幕生成 + 飞书写入 自动化流程")
    print("="*50)
    print(f"关键字: {keywords}")
    print(f"排序方式: {sort_type}")
    print(f"抓取数量: {max_notes_count}")
    print("="*50)

    json_path = crawl_xiaohongshu(keywords, sort_type, max_notes_count)
    if not json_path:
        print("❌ 爬取失败")
        sys.exit(1)

    data = load_json_data(json_path, max_notes_count)
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
