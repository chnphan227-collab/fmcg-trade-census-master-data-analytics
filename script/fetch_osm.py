import requests
import pandas as pd

# Tọa độ khu vực trung tâm & nội thành TP.HCM
bbox = "10.72,106.62,10.84,106.76"

query = f"""
[out:json][timeout:60];
(
  node["amenity"~"^(restaurant|bar|pub|cafe)$"]["name"]({bbox});
  way["amenity"~"^(restaurant|bar|pub|cafe)$"]["name"]({bbox});
);
out center;
"""

# Bắt buộc phải có User-Agent để không bị chặn lỗi 406
headers = {
    "User-Agent": "HCM-TradeCensus-Portfolio-Project/1.0 (Academic Research)",
    "Accept": "application/json"
}

# Danh sách các máy chủ Overpass đang hoạt động ổn định
servers = [
    "https://overpass.private.coffee/api/interpreter", # Máy chủ mới thay thế kumi.systems (không giới hạn)
    "https://ovp.dresel.systems/api-as/interpreter",   # Máy chủ chuyên biệt khu vực Châu Á
    "https://overpass-api.de/api/interpreter",         # Máy chủ chính tại Đức
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]

for url in servers:
    print(f"Đang kết nối tới: {url} ...")
    try:
        res = requests.post(url, data={'data': query}, headers=headers, timeout=65)
        if res.status_code == 200:
            data = res.json()
            elements = data.get('elements', [])
            if len(elements) > 0:
                rows = []
                for el in elements:
                    tags = el.get('tags', {})
                    lat = el.get('lat') or el.get('center', {}).get('lat')
                    lon = el.get('lon') or el.get('center', {}).get('lon')
                    rows.append({
                        '@id': el.get('id'),
                        'name': tags.get('name'),
                        'amenity': tags.get('amenity'),
                        'addr:street': tags.get('addr:street'),
                        'addr:district': tags.get('addr:district'),
                        '@lat': lat,
                        '@lon': lon
                    })
                pd.DataFrame(rows).to_csv('osm_raw.csv', index=False, encoding='utf-8-sig')
                print(f"THÀNH CÔNG! Đã tải được {len(rows)} địa điểm thật vào file 'osm_raw.csv'.")
                break
        else:
            print(f"Máy chủ báo bận (Mã {res.status_code}). Đang chuyển...")
    except Exception as e:
        print(f"Lỗi kết nối ({e}). Đang chuyển máy chủ khác...")
