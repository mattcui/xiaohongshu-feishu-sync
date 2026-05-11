import os
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

# Target bitable app token
app_token = 'AQcFbPWpYaeCpIsoJHmcjzoNnuf'

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# Try to get share link
url = f'https://open.feishu.cn/open-apis/drive/explorer/v2/file/{app_token}/share_link'
response = requests.get(url, headers=headers)
print(f"Get share link: {response.status_code}")
print(f"Response: {response.text[:1000]}")

# Try to create share link
url = f'https://open.feishu.cn/open-apis/drive/explorer/v2/file/{app_token}/share_link'
payload = {
    'share_mode': 'anyone_can_view',
    'allow_edit': True
}
response = requests.post(url, headers=headers, json=payload)
print(f"\nCreate share link: {response.status_code}")
print(f"Response: {response.text[:1000]}")
