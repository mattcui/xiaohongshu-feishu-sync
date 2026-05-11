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
    try:
        return response.json().get("tenant_access_token")
    except:
        print(f"获取token失败: {response.text[:200]}")
        return None

def search_files(token, keyword="小红书数据"):
    url = "https://open.feishu.cn/open-apis/drive/search/files"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "query": keyword,
        "page_size": 50,
        "type": "bitable"
    }
    response = requests.post(url, headers=headers, json=payload)
    try:
        result = response.json()
        if result.get('code') == 0:
            return result.get('data', {}).get('items', [])
        else:
            print(f"API错误: {result.get('msg')}")
            return []
    except Exception as e:
        print(f"解析JSON失败: {e}")
        print(f"响应内容: {response.text[:500]}")
        return []

def set_permission(token, file_token):
    url = "https://open.feishu.cn/open-apis/drive/permission/member/create"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "file_token": file_token,
        "member_type": "org",
        "member_id": "everyone",
        "perm": "edit"
    }
    response = requests.post(url, headers=headers, json=payload)
    try:
        return response.json()
    except:
        print(f"响应内容: {response.text[:200]}")
        return {"code": -1, "msg": "解析失败"}

def main():
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return

    bitables = search_files(token)
    if not bitables:
        print("❌ 未找到应用创建的表格")
        return
    
    print(f"找到 {len(bitables)} 个表格:")
    print("-" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i, item in enumerate(bitables, 1):
        file_token = item.get('file_token')
        name = item.get('name', '未命名表格')
        print(f"\n{i}. {name}")
        print(f"   File Token: {file_token}")
        
        result = set_permission(token, file_token)
        if result.get('code') == 0:
            print("   ✅ 已设置为组织内编辑权限")
            success_count += 1
        else:
            print(f"   ❌ 设置失败: {result.get('msg')}")
            fail_count += 1
    
    print(f"\n{'-' * 60}")
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")
    
    if success_count > 0:
        print("\n🎉 已为所有表格设置组织内编辑权限！")
        print("现在组织内所有成员都可以编辑这些表格了。")

if __name__ == "__main__":
    main()