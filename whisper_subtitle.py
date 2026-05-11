import os
import re
import json
import requests
import whisper
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

app_id = os.getenv('FEISHU_APP_ID')
app_secret = os.getenv('FEISHU_APP_SECRET')

class FeishuVideoSubtitle:
    def __init__(self):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        self._get_access_token()
        self.model = whisper.load_model("base")

    def _get_access_token(self):
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {'app_id': self.app_id, 'app_secret': self.app_secret}
        response = requests.post(url, json=payload)
        self.token = response.json().get("tenant_access_token")
        print(f"获取Token成功")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def get_records_with_video(self, app_token, table_id):
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        response = requests.get(url, headers=self._headers())
        data = response.json()

        if data.get("code") != 0:
            print(f"获取记录失败: {data.get('msg')}")
            return []

        records = data.get("data", {}).get("items", [])
        result = []

        for record in records:
            fields = record.get("fields", {})
            video_url = fields.get("video_url", "")
            note_url = fields.get("note_url", "")
            title = fields.get("title", "")
            record_id = record.get("record_id", "")
            current_subtitle = fields.get("字幕", "")

            if video_url and not current_subtitle:
                result.append({
                    "record_id": record_id,
                    "video_url": video_url,
                    "note_url": note_url,
                    "title": title
                })

        return result

    def add_subtitle_field(self, app_token, table_id):
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        payload = {"field_name": "字幕", "type": 1}
        response = requests.post(url, headers=self._headers(), json=payload)
        return response.json().get("code") == 0 or "已存在" in str(response.json())

    def update_record(self, app_token, table_id, record_id, subtitle):
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        payload = {"fields": {"字幕": subtitle}}
        response = requests.put(url, headers=self._headers(), json=payload)
        return response.json().get("code") == 0

    def get_table_id(self, app_token):
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables"
        response = requests.get(url, headers=self._headers())
        data = response.json()
        if data.get("code") == 0:
            tables = data.get("data", {}).get("items", [])
            if tables:
                return tables[0].get("table_id")
        return None

def download_video(url, output_path="video.mp4"):
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
    except Exception as e:
        print(f"下载失败: {e}")
        return None

def generate_subtitle(video_path, model):
    try:
        result = model.transcribe(video_path, language="zh")
        return result["text"]
    except Exception as e:
        print(f"生成字幕失败: {e}")
        return None

def main():
    app_token = "EAt0b1cXHaRPEuseQUScrhFXnBb"

    feishu = FeishuVideoSubtitle()
    table_id = feishu.get_table_id(app_token)

    if not table_id:
        print("获取表格信息失败")
        return

    print(f"表格ID: {table_id}")
    print(f"Whisper模型加载成功")

    feishu.add_subtitle_field(app_token, table_id)
    records = feishu.get_records_with_video(app_token, table_id)

    print(f"找到 {len(records)} 条视频需要生成字幕\n")

    for i, record in enumerate(records):
        print(f"[{i+1}/{len(records)}] 处理: {record.get('title', '无标题')}")

        video_path = f"temp_video_{i}.mp4"
        downloaded = download_video(record.get('video_url', ''), video_path)

        if downloaded:
            subtitle = generate_subtitle(video_path, feishu.model)
            if subtitle:
                success = feishu.update_record(app_token, table_id, record.get('record_id'), subtitle)
                if success:
                    print(f"   ✅ 字幕已更新到飞书")
                else:
                    print(f"   ❌ 更新失败")
            else:
                print(f"   ❌ 生成字幕失败")
        else:
            print(f"   ❌ 下载视频失败")

        if os.path.exists(video_path):
            os.remove(video_path)

        print()

    print("全部处理完成！")

if __name__ == "__main__":
    main()
