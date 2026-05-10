import os
import io
import requests
import json
import time
from dotenv import load_dotenv
from funasr import AutoModel

load_dotenv()

app_id = os.getenv('FEISHU_APP_ID')
app_secret = os.getenv('FEISHU_APP_SECRET')

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": app_id, "app_secret": app_secret}
    
    response = requests.post(url, headers=headers, json=data)
    return response.json().get("tenant_access_token")

def download_video_to_memory(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=1024*1024):
            if chunk:
                buffer.write(chunk)
        
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"❌ 下载失败: {str(e)[:100]}")
        return None

def save_temp_video(video_buffer, path="temp_video.mp4"):
    try:
        with open(path, 'wb') as f:
            f.write(video_buffer.getvalue())
        return path
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return None

def generate_subtitle_funasr(video_path, model):
    try:
        result = model.generate(input=video_path, language="zh", use_itn=True)
        subtitle = result[0]["text"]
        subtitle = subtitle.replace("<|zh|>", "").replace("<|HAPPY|>", "").replace("<|BGM|>", "").replace("<|withitn|>", "")
        return subtitle.strip()
    except Exception as e:
        print(f"❌ 字幕生成失败: {e}")
        return ""

def get_app_tables(token, app_token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    return response.json()

def get_records(token, app_token, table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    return response.json().get("data", {}).get("items", [])

def add_subtitle_field(token, app_token, table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"field_name": "subtitle", "type": 1}
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def update_record(token, app_token, table_id, record_id, subtitle):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {"fields": {"subtitle": subtitle[:5000]}}
    
    response = requests.put(url, headers=headers, json=data)
    return response.json()

def main():
    app_token = "EAt0b1cXHaRPEuseQUScrhFXnBb"
    
    print("===== 加载FunASR模型 =====")
    model = AutoModel(model="iic/SenseVoiceSmall", vad_model="fsmn-vad", device="cpu")
    print("✅ 模型加载成功")
    
    print("\n===== 获取飞书数据 =====")
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    tables = get_app_tables(token, app_token)
    table_id = tables.get("data", {}).get("items", [{}])[0].get("table_id")
    
    if not table_id:
        print("❌ 获取表格ID失败")
        return
    
    print(f"✅ 表格ID: {table_id}")
    
    add_subtitle_field(token, app_token, table_id)
    print("✅ 已添加subtitle字段")
    
    records = get_records(token, app_token, table_id)
    print(f"✅ 获取到 {len(records)} 条记录")
    
    print("\n===== 开始生成字幕 =====")
    success_count = 0
    fail_count = 0
    
    for i, record in enumerate(records, 1):
        video_url = record.get("fields", {}).get("video_url", "").strip()
        record_id = record.get("record_id")
        title = record.get("fields", {}).get("title", "")[:30]
        
        if not video_url or not video_url.startswith("http"):
            print(f"⏭️ 第{i}条: 无有效视频URL - {title}")
            continue
        
        print(f"\n📹 处理第{i}条: {title}")
        
        video_buffer = download_video_to_memory(video_url)
        if not video_buffer:
            fail_count += 1
            continue
        
        video_path = save_temp_video(video_buffer)
        if not video_path:
            fail_count += 1
            continue
        
        subtitle = generate_subtitle_funasr(video_path, model)
        
        if os.path.exists(video_path):
            os.remove(video_path)
        
        if subtitle:
            print(f"📝 字幕长度: {len(subtitle)} 字")
            update_result = update_record(token, app_token, table_id, record_id, subtitle)
            if update_result.get("code") == 0:
                print("✅ 写入飞书成功")
                success_count += 1
            else:
                print(f"❌ 写入失败: {update_result.get('msg', '未知错误')}")
                fail_count += 1
        else:
            print("❌ 字幕生成失败")
            fail_count += 1
        
        time.sleep(1)
    
    print(f"\n===== 完成 =====")
    print(f"✅ 成功: {success_count} 条")
    print(f"❌ 失败: {fail_count} 条")
    print(f"📊 表格链接: https://qcnytqlnrfst.feishu.cn/base/{app_token}")

if __name__ == "__main__":
    main()
