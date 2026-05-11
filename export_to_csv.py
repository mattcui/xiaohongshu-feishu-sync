import json

data = []
with open('data/search_contents_2026-05-08.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            data.append(json.loads(line))

fields = list(data[0].keys())

with open('xiaohongshu_data.csv', 'w', encoding='utf-8-sig') as f:
    f.write(','.join(fields) + '\n')
    for row in data:
        row_values = []
        for field in fields:
            value = row.get(field, '')
            if isinstance(value, str):
                value = value.replace('"', '""')
                if ',' in value or '"' in value or '\n' in value:
                    value = f'"{value}"'
            row_values.append(str(value))
        f.write(','.join(row_values) + '\n')

print(f"已导出 {len(data)} 条数据到 xiaohongshu_data.csv")
