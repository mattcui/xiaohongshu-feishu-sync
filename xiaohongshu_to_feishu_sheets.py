import json
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

class FeishuTableImporter:
    def __init__(self):
        self.app_id = os.getenv('FEISHU_APP_ID')
        self.app_secret = os.getenv('FEISHU_APP_SECRET')
        self.base_url = "https://open.feishu.cn/open-apis"
        
        if not self.app_id or not self.app_secret:
            raise ValueError("请在.env文件中配置FEISHU_APP_ID和FEISHU_APP_SECRET")
        
        self.access_token = None
        self._get_access_token()
    
    def _get_access_token(self):
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        response = requests.post(url, json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取access_token失败: {data.get('msg')}")
        
        self.access_token = data.get("tenant_access_token")
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def create_spreadsheet(self, title):
        url = f"{self.base_url}/sheets/v3/spreadsheets"
        payload = {"title": title}
        response = requests.post(url, headers=self._headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"创建表格失败: {data.get('msg')}")
        
        return data.get("data").get("spreadsheet")
    
    def add_permission(self, token, member_id, permission="edit"):
        url = f"{self.base_url}/drive/permission/grant"
        payload = {
            "token": token,
            "token_type": "spreadsheet_token",
            "members": [{
                "member_id": member_id,
                "member_type": "user",
                "permission": permission
            }],
            "notify": False
        }
        response = requests.post(url, headers=self._headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            print(f"添加权限失败: {data.get('msg')}")
        else:
            print(f"已添加用户 {member_id}，权限: {permission}")
    
    def import_json_to_table(self, json_data, table_name="小红书数据"):
        if isinstance(json_data, dict):
            data_list = [json_data]
        elif isinstance(json_data, list):
            data_list = json_data
        else:
            raise ValueError("JSON数据必须是dict或list类型")
        
        if not data_list:
            raise ValueError("JSON数据为空")
        
        fields = list(data_list[0].keys())
        num_fields = len(fields)
        
        print(f"检测到字段: {fields}")
        print(f"数据条数: {len(data_list)}")
        
        spreadsheet = self.create_spreadsheet(table_name)
        spreadsheet_token = spreadsheet.get("spreadsheet_token")
        url = spreadsheet.get("url")
        print(f"已创建表格: {table_name}")
        print(f"表格链接: {url}")
        
        end_col = chr(64 + num_fields)
        header_range = f"Sheet1!A1:{end_col}1"
        
        url = f"{self.base_url}/sheets/v2/spreadsheets/{spreadsheet_token}/values"
        payload = {
            "valueRange": {
                "range": header_range,
                "values": [fields]
            }
        }
        response = requests.put(url, headers=self._headers(), json=payload)
        if response.json().get("code") != 0:
            raise Exception(f"写入表头失败")
        
        rows = []
        for data in data_list:
            row = []
            for field in fields:
                value = data.get(field, "")
                if isinstance(value, str):
                    value = value.strip()
                    value = re.sub(r'`', '', value)
                row.append(str(value) if value is not None else "")
            rows.append(row)
        
        data_range = f"Sheet1!A2:{end_col}{len(rows) + 1}"
        payload = {
            "valueRange": {
                "range": data_range,
                "values": rows
            }
        }
        response = requests.put(url, headers=self._headers(), json=payload)
        if response.json().get("code") != 0:
            raise Exception(f"写入数据失败")
        
        print(f"已插入 {len(data_list)} 条数据")
        
        self.add_permission(spreadsheet_token, "user068934", "edit")
        
        return {"spreadsheet_token": spreadsheet_token, "url": url}

def load_json_from_file(file_path):
    if file_path.endswith('.jsonl'):
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
        return data
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='将小红书JSON数据导入飞书表格')
    parser.add_argument('--json-file', help='JSON文件路径')
    parser.add_argument('--table-name', default='小红书数据', help='表格名称')
    
    args = parser.parse_args()
    
    if args.json_file:
        json_data = load_json_from_file(args.json_file)
    else:
        json_data = {
            "note_id": "test",
            "title": "测试数据"
        }
    
    importer = FeishuTableImporter()
    result = importer.import_json_to_table(json_data, args.table_name)
    
    print(f"\n导入完成！")
    print(f"表格链接: {result['url']}")

if __name__ == "__main__":
    main()
