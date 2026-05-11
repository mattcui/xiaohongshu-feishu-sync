import json
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

app_id = os.getenv('FEISHU_APP_ID')
app_secret = os.getenv('FEISHU_APP_SECRET')

# Get token
url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
payload = {'app_id': app_id, 'app_secret': app_secret}
response = requests.post(url, json=payload)
token = response.json().get('tenant_access_token')
print(f"获取Token成功")

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# Load data
data = []
with open('data/search_contents_2026-05-08.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            data.append(json.loads(line))

fields = list(data[0].keys())
print(f"检测到字段: {fields}")
print(f"数据条数: {len(data)}")

# Create bitable with org-wide access
url = 'https://open.feishu.cn/open-apis/bitable/v1/apps'
payload = {
    'name': '小红书数据_全员可查看',
    'share_to_org': True,
    'share_to_org_permission': 'view'
}
response = requests.post(url, headers=headers, json=payload)
result = response.json()
print(f"创建表格成功")

app_token = result.get('data', {}).get('app', {}).get('app_token')
table_id = result.get('data', {}).get('app', {}).get('default_table_id')
base_url = f"https://qcnytqlnrfst.feishu.cn/base/{app_token}"
print(f"表格链接: {base_url}")

# Add fields
for field_name in fields:
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields'
    payload = {'field_name': field_name, 'type': 1}
    requests.post(url, headers=headers, json=payload)

# Insert records
bitable_records = []
for row_data in data:
    record_fields = {}
    for field in fields:
        value = row_data.get(field, "")
        if isinstance(value, str):
            value = value.strip()
            value = re.sub(r'`', '', value)
        record_fields[field] = str(value) if value is not None else ""
    bitable_records.append({"fields": record_fields})

url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create'
payload = {"records": bitable_records}
response = requests.post(url, headers=headers, json=payload)
print(f"插入数据成功")

# Get share link using drive API
url = f'https://open.feishu.cn/open-apis/drive/explorer/v2/file/{app_token}/share_link'
response = requests.get(url, headers=headers)
print(f"\n获取分享链接: {response.status_code}")
try:
    result = response.json()
    share_url = result.get('data', {}).get('url')
    if share_url:
        print(f"🎉 分享链接: {share_url}")
    else:
        print(f"表格链接: {base_url}")
except:
    print(f"表格链接: {base_url}")
    
print("\n完成！")
