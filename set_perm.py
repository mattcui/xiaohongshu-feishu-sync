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

# Target app token from the created table
app_token = 'G8MnboRzBagKZnstMPXcO0ZNnde'

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# Try bitable acl API
url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/acl'
payload = {
    'organization_wide_permission': {
        'can_view': True,
        'can_edit': True
    }
}
response = requests.patch(url, headers=headers, json=payload)
print(f"Bitable ACL API: {response.status_code}")
print(f"Response: {response.text[:1000]}")

# Try drive permission API  
url = 'https://open.feishu.cn/open-apis/drive/v2/permission/members/batch_add'
payload = {
    'token': app_token,
    'token_type': 'app_token',
    'members': [{
        'type': 'org',
        'role': 'viewer'
    }]
}
response = requests.post(url, headers=headers, json=payload)
print(f"\nDrive permission API: {response.status_code}")
print(f"Response: {response.text[:1000]}")
