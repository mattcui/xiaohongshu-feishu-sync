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

# Get current user info
url = 'https://open.feishu.cn/open-apis/contact/v3/users/me'
headers = {'Authorization': f'Bearer {token}'}
response = requests.get(url, headers=headers)
print(f"Current user info: {response.json()}")
