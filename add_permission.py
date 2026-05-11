#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data)
    return response.json().get("tenant_access_token")

def get_user_id(token, email_or_phone):
    url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {"emails": [email_or_phone]} if "@" in email_or_phone else {"mobiles": [email_or_phone]}
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    if result.get('code') == 0:
        users = result.get('data', {}).get('user_list', [])
        if users:
            return users[0].get('user_id')
    return None

def list_bitables(token):
    url = "https://open.feishu.cn/open-apis/bitable/v1/apps"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    result = response.json()
    if result.get('code') == 0:
        return result.get('data', {}).get('items', [])
    return []

def add_permission(token, app_token, user_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/permissions/members"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {
        "members": [
            {
                "member_id": user_id,
                "member_type": "user",
                "role": "editor"
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def main():
    import sys
    if len(sys.argv) < 2:
        print("用法: python add_permission.py <您的飞书邮箱>")
        print("示例: python add_permission.py xxx@xxx.com")
        sys.exit(1)
    
    email = sys.argv[1]
    
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    user_id = get_user_id(token, email)
    if not user_id:
        print(f"❌ 未找到用户: {email}")
        return
    print(f"✅ 找到用户ID: {user_id}")

    bitables = list_bitables(token)
    if not bitables:
        print("❌ 未找到应用创建的表格")
        return
    print(f"\n找到 {len(bitables)} 个表格:")
    
    success_count = 0
    fail_count = 0
    
    for i, bitable in enumerate(bitables, 1):
        app_token = bitable.get('app_token')
        name = bitable.get('name', '未命名表格')
        print(f"\n{i}. {name}")
        print(f"   App Token: {app_token}")
        
        result = add_permission(token, app_token, user_id)
        if result.get('code') == 0:
            print("   ✅ 添加编辑权限成功")
            success_count += 1
        else:
            print(f"   ❌ 添加权限失败: {result.get('msg')}")
            fail_count += 1
    
    print(f"\n========== 统计 ==========")
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")
    
    if success_count > 0:
        print("\n🎉 已为您添加以下表格的编辑权限:")
        print("您现在可以在飞书网页端编辑这些表格了！")

if __name__ == "__main__":
    main()