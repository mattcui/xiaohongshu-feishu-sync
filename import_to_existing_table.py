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
        print(f"获取Token成功")
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def list_tables(self, app_token):
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables"
        response = requests.get(url, headers=self._headers())
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取表格列表失败: {data.get('msg')}")
        
        return data.get("data", {}).get("items", [])
    
    def add_fields_to_table(self, app_token, table_id, fields):
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        response = requests.get(url, headers=self._headers())
        data = response.json()
        
        if data.get("code") != 0:
            print(f"获取现有字段失败: {data.get('msg')}")
            existing_names = set()
        else:
            existing_fields = data.get("data", {}).get("items", [])
            existing_names = {f.get("field_name") for f in existing_fields}
        
        for field_name in fields:
            if field_name in existing_names:
                print(f"字段已存在: {field_name}")
                continue
            
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
            payload = {
                "field_name": field_name,
                "type": 1
            }
            response = requests.post(url, headers=self._headers(), json=payload)
            data = response.json()
            
            if data.get("code") != 0:
                print(f"添加字段失败 {field_name}: {data.get('msg')}")
            else:
                print(f"已添加字段: {field_name}")
    
    def batch_create_records(self, app_token, table_id, records):
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
        
        bitable_records = []
        for record in records:
            fields = {}
            for key, value in record.items():
                if isinstance(value, str):
                    value = value.strip()
                    value = re.sub(r'`', '', value)
                fields[key] = str(value) if value is not None else ""
            bitable_records.append({"fields": fields})
        
        payload = {"records": bitable_records}
        response = requests.post(url, headers=self._headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"插入记录失败: {data.get('msg')}")
        
        records = data.get("data").get("records", [])
        return [r.get("record_id") for r in records]
    
    def import_to_existing_table(self, json_data, app_token, table_id):
        if isinstance(json_data, dict):
            data_list = [json_data]
        elif isinstance(json_data, list):
            data_list = json_data
        else:
            raise ValueError("JSON数据必须是dict或list类型")
        
        if not data_list:
            raise ValueError("JSON数据为空")
        
        fields = list(data_list[0].keys())
        
        print(f"检测到字段: {fields}")
        print(f"数据条数: {len(data_list)}")
        
        self.add_fields_to_table(app_token, table_id, fields)
        
        record_ids = self.batch_create_records(app_token, table_id, data_list)
        print(f"已插入 {len(record_ids)} 条数据")
        
        return record_ids

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
    app_token = "bllaKmV5B8AZ33z"
    table_id = "tbllaKmV5B8AZ33z"
    
    importer = FeishuTableImporter()
    
    json_data = load_json_from_file("data/search_contents_2026-05-08.jsonl")
    importer.import_to_existing_table(json_data, app_token, table_id)
    print("\n导入完成！")

if __name__ == "__main__":
    main()
