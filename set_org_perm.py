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

# Target app token
app_token = 'Q48XbwanGaGxD0sf04cciQFynDg'

# Try drive v1 permission API
url = f'https://open.feishu.cn/open-apis/drive/v1/permissions/{app_token}/members?type=bitable'
payload = {
    'member_type': 'org',
    'member_id': '',
    'perm': 'view'
}
response = requests.post(url, headers=headers, json=payload)
print(f"设置组织权限: {response.status_code}")
print(f"响应: {response.text}")

# Try setting public link
url = f'https://open.feishu.cn/open-apis/drive/v1/permissions/{app_token}/link?type=bitable'
response = requests.get(url, headers=headers)
print(f"\n获取分享链接: {response.status_code}")
print(f"响应: {response.text[:500]}")
