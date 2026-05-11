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
num_fields = len(fields)
print(f"检测到字段: {fields}")
print(f"数据条数: {len(data)}")

# Create spreadsheet with org-wide access
url = 'https://open.feishu.cn/open-apis/sheets/v3/spreadsheets'
payload = {
    'title': '小红书数据_全员可查看',
    'permission': {
        'org_wide_access': 'can_view'
    }
}
response = requests.post(url, headers=headers, json=payload)
result = response.json()
print(f"创建表格: {result}")

spreadsheet_token = result.get('data', {}).get('spreadsheet', {}).get('spreadsheet_token')
base_url = result.get('data', {}).get('spreadsheet', {}).get('url')
print(f"表格链接: {base_url}")

# Prepare all data (headers + rows)
rows = [fields]
for row_data in data:
    row = []
    for field in fields:
        value = row_data.get(field, "")
        if isinstance(value, str):
            value = value.strip()
            value = re.sub(r'`', '', value)
        row.append(str(value) if value is not None else "")
    rows.append(row)

# Write all data using append API
end_col = chr(64 + num_fields)
url = f'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/Sheet1!A1:{end_col}{len(rows)}'
payload = {'values': rows}
response = requests.put(url, headers=headers, json=payload)
print(f"写入数据: {response.status_code}")

# Get share link
url = f'https://open.feishu.cn/open-apis/drive/v1/permission/{spreadsheet_token}/link?type=sheet'
response = requests.get(url, headers=headers)
result = response.json()
print(f"获取分享链接: {result}")

share_url = result.get('data', {}).get('url')
if share_url:
    print(f"\n🎉 分享链接: {share_url}")
else:
    print(f"\n表格链接: {base_url}")
    
print("\n完成！")
