#!/usr/bin/env python3
import os
import getpass

def configure():
    print("="*60)
    print("      小红书数据抓取工具 - 配置向导")
    print("="*60)
    print("\n请输入以下配置信息：")
    print("-"*60)
    
    # 获取飞书配置
    feishu_app_id = input("1. 飞书 APP ID: ").strip()
    while not feishu_app_id:
        print("❌ APP ID 不能为空")
        feishu_app_id = input("1. 飞书 APP ID: ").strip()
    
    feishu_app_secret = input("2. 飞书 APP Secret: ").strip()
    while not feishu_app_secret:
        print("❌ APP Secret 不能为空")
        feishu_app_secret = input("2. 飞书 APP Secret: ").strip()
    
    bitable_url = input("3. 飞书表格 URL: ").strip()
    while not bitable_url:
        print("❌ 表格 URL 不能为空")
        bitable_url = input("3. 飞书表格 URL: ").strip()
    
    # 创建 .env 文件
    env_content = f"""FEISHU_APP_ID={feishu_app_id}
FEISHU_APP_SECRET={feishu_app_secret}
BITABLE_URL={bitable_url}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("-"*60)
    print("✅ 配置完成！")
    print(f"\n配置文件已保存到: {os.path.abspath('.env')}")
    print("\n接下来运行：")
    print("  ./run.sh --keys <关键词> --sort <排序方式> --count <数量>")
    print("\n示例：")
    print("  ./run.sh --keys 针灸 --sort popular --count 10")

if __name__ == "__main__":
    configure()
