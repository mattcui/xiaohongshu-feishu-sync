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
    
    def create_bitable_app(self, app_name):
        url = f"{self.base_url}/bitable/v1/apps"
        payload = {"name": app_name}
        response = requests.post(url, headers=self._headers(), json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"创建多维表格失败: {data.get('msg')}")
        
        app_info = data.get("data").get("app")
        return app_info
    
    def delete_default_fields(self, app_token, table_id):
        url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        response = requests.get(url, headers=self._headers())
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取字段失败: {data.get('msg')}")
        
        default_fields = data.get("data", {}).get("items", [])
        for field in default_fields:
            field_id = field.get("field_id")
            field_name = field.get("field_name")
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
            response = requests.delete(url, headers=self._headers())
            print(f"删除默认字段: {field_name} (ID: {field_id})")
    
    def add_fields_to_table(self, app_token, table_id, fields):
        for field_name in fields:
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
            payload = {
                "field_name": field_name,
                "type": 1
            }
            response = requests.post(url, headers=self._headers(), json=payload)
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"添加字段失败 {field_name}: {data.get('msg')}")
    
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
    
    def set_permissions(self, app_token, org_view=True, org_edit=True):
        try:
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/acl"
            payload = {
                "organization_wide_permission": {
                    "can_view": org_view,
                    "can_edit": org_edit
                }
            }
            response = requests.patch(url, headers=self._headers(), json=payload)
            try:
                data = response.json()
                if data.get("code") != 0:
                    print(f"设置权限时警告: {data.get('msg')}")
                else:
                    print("已设置组织内权限")
            except:
                print(f"权限设置API响应非JSON格式: {response.status_code}")
        except Exception as e:
            print(f"设置权限时出错: {str(e)}")
    
    def add_member(self, app_token, member_id, permission="edit"):
        try:
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/members"
            payload = {
                "member_id": member_id,
                "member_type": "user",
                "permission": permission
            }
            response = requests.post(url, headers=self._headers(), json=payload)
            try:
                data = response.json()
                if data.get("code") != 0:
                    print(f"添加成员失败: {data.get('msg')}")
                else:
                    print(f"已添加成员 {member_id}，权限: {permission}")
            except:
                print(f"添加成员API响应非JSON格式: {response.status_code}")
        except Exception as e:
            print(f"添加成员时出错: {str(e)}")
    
    def import_json_to_table(self, json_data, app_name="小红书数据"):
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
        
        app_info = self.create_bitable_app(app_name)
        app_token = app_info.get("app_token")
        table_id = app_info.get("default_table_id")
        url = app_info.get("url")
        print(f"已创建多维表格: {app_name}")
        print(f"表格链接: {url}")
        
        self.delete_default_fields(app_token, table_id)
        print("已删除默认字段")
        
        self.add_fields_to_table(app_token, table_id, fields)
        print(f"已添加字段: {fields}")
        
        record_ids = self.batch_create_records(app_token, table_id, data_list)
        print(f"已插入 {len(record_ids)} 条数据")
        
        self.set_permissions(app_token, org_view=True)
        
        self.add_member(app_token, "user068934", "edit")
        
        return {"app_token": app_token, "table_id": table_id, "url": url}

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

def clean_json_string(json_str):
    json_str = re.sub(r'`', '', json_str)
    json_str = re.sub(r'\s+', ' ', json_str)
    return json_str

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='将小红书JSON数据导入飞书多维表格')
    parser.add_argument('--json-file', help='JSON文件路径')
    parser.add_argument('--json-string', help='JSON字符串')
    parser.add_argument('--app-name', default='小红书数据', help='多维表格名称')
    
    args = parser.parse_args()
    
    if args.json_file:
        json_data = load_json_from_file(args.json_file)
    elif args.json_string:
        cleaned_str = clean_json_string(args.json_string)
        json_data = json.loads(cleaned_str)
    else:
        sample_data = {
            "note_id": "69eb57cc000000001a0363b8",
            "type": "video",
            "title": "海岛旅游的终极奥义就是“一岛一酒店”",
            "desc": "#海景[话题]# #三亚[话题]# #五星级酒店[话题]#",
            "video_url": "http://sns-video-hs.xhscdn.com/stream/79/110/259/01e9eb57a813ccd4010370039dbf4fb395_259.mp4",
            "time": 1777031116000,
            "last_update_time": 1777031116000,
            "user_id": "67f0b6a7000000000e01f7f1",
            "nickname": "碎嘴豆粒瓜",
            "avatar": "https://sns-avatar-qc.xhscdn.com/avatar/1040g2jo31lks8f7m5o005pvgmqjjjtvhd641128",
            "liked_count": "3.8万",
            "collected_count": "9784",
            "comment_count": "646",
            "share_count": "9060",
            "ip_location": "江苏",
            "image_list": "http://sns-webpic-qc.xhscdn.com/202605081749/c1a9a619230148e32a5fbaf3f9862b00/spectrum/1040g0k031vbgmckm1m005pvgmqjjjtvhbga58rg",
            "tag_list": "海景,三亚,五星级酒店,沙滩,旅游",
            "last_modify_ts": 1778233890409,
            "note_url": "https://www.xiaohongshu.com/explore/69eb57cc000000001a0363b8",
            "source_keyword": "三亚度假",
            "xsec_token": "ABMK0Ne4fEd5t3EnCv-RTxDlYVX43CuDsl8grHbzDsP04="
        }
        json_data = sample_data
        print("未提供JSON数据，使用示例数据")
    
    importer = FeishuTableImporter()
    result = importer.import_json_to_table(json_data, args.app_name)
    
    print(f"\n导入完成！")
    print(f"多维表格链接: {result['url']}")

if __name__ == "__main__":
    main()
