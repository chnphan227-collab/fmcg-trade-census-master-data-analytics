import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Cố định seed để kết quả tái lập được nếu cần
random.seed(42)
np.random.seed(42)

# 1. ĐỌC DỮ LIỆU GỐC & LẤY MẪU 800 OUTLET
df_raw = pd.read_csv('osm_raw.csv')
df_raw = df_raw.dropna(subset=['name', '@lat', '@lon']).drop_duplicates(subset=['name', '@lat', '@lon'])

# Lấy khoảng 756 dòng gốc (để sau khi nhân bản ~44 dòng trùng lặp sẽ ra đúng 800 dòng)
base_count = 756
df = df_raw.sample(n=min(base_count, len(df_raw)), random_state=42).reset_index(drop=True)

# 2. TẠO BẢNG LOOKUP (DIM_DISTRICT & DIM_CHANNEL)
valid_districts = [
    'Quận 1', 'Quận 3', 'Quận 4', 'Quận 5', 'Quận 7', 'Quận 10',
    'Quận Bình Thạnh', 'Quận Phú Nhuận', 'Quận Tân Bình', 'Thành phố Thủ Đức'
]
dim_district = pd.DataFrame({
    'District_ID': [f'DIST_{i+1:02d}' for i in range(len(valid_districts))],
    'District_Standard': valid_districts,
    'Region': ['Central', 'Central', 'South', 'West', 'South', 'West', 'East', 'Central', 'North', 'East']
})
dim_district.to_csv('Dim_District.csv', index=False, encoding='utf-8-sig')

valid_channels = ['Restaurant', 'Cafe', 'Bar', 'Pub']
dim_channel = pd.DataFrame({
    'Channel_ID': ['CH_01', 'CH_02', 'CH_03', 'CH_04'],
    'Channel_Standard': valid_channels,
    'Segment': ['Dining', 'Daytime', 'Nightlife', 'Nightlife']
})
dim_channel.to_csv('Dim_Channel.csv', index=False, encoding='utf-8-sig')

# 3. CHUẨN BỊ CÁC CỘT NỀN SẠCH BAN ĐẦU
outlets = pd.DataFrame()
outlets['Outlet_ID'] = [f'OUT_{i+1001}' for i in range(len(df))]
outlets['Outlet_Name'] = df['name'].str.strip()
outlets['Latitude'] = df['@lat']
outlets['Longitude'] = df['@lon']

# Chuẩn hóa Channel ban đầu từ OSM
outlets['Channel'] = df['amenity'].str.capitalize()
outlets.loc[~outlets['Channel'].isin(valid_channels), 'Channel'] = 'Restaurant'

# Xử lý District & Address ban đầu
outlets['District'] = df['addr:district'].apply(
    lambda x: x if pd.notna(x) and x in valid_districts else random.choice(valid_districts)
)
streets = df['addr:street'].fillna('Đường số ' + pd.Series([str(random.randint(1, 50)) for _ in range(len(df))]))
house_nums = [str(random.randint(1, 350)) for _ in range(len(df))]
outlets['Address'] = pd.Series(house_nums) + ' ' + streets
def gen_phone():
    return random.choice(['090', '091', '093', '097', '098', '032', '070', '083']) + ''.join([str(random.randint(0, 9)) for _ in range(7)])

outlets['Phone'] = [gen_phone() for _ in range(len(df))]
outlets['Status'] = 'Active'
outlets['Verification_Status'] = 'Verified'
outlets['Data_Source'] = np.random.choice(['Field Survey', 'Distributor Data', 'Sales Rep Audit'], size=len(df), p=[0.5, 0.3, 0.2])

# Thêm 3 cột bám sát JD
team_map = {
    'Quận 1': 'Team_Central_1', 'Quận 3': 'Team_Central_1', 'Quận Phú Nhuận': 'Team_Central_2',
    'Quận 4': 'Team_South', 'Quận 7': 'Team_South',
    'Quận 5': 'Team_West', 'Quận 10': 'Team_West', 'Quận Tân Bình': 'Team_North',
    'Quận Bình Thạnh': 'Team_East', 'Thành phố Thủ Đức': 'Team_East'
}
outlets['Surveyor_Team'] = outlets['District'].map(team_map)
outlets['Potential_Tier'] = np.random.choice(['Tier A', 'Tier B', 'Tier C'], size=len(df), p=[0.2, 0.5, 0.3])

# Ngày cập nhật trong vòng 180 ngày gần đây (tính đến 21/11/2026)
base_date = datetime(2026, 11, 21)
outlets['Last_Updated'] = [(base_date - timedelta(days=random.randint(0, 180))).strftime('%Y-%m-%d') for _ in range(len(df))]

# 4. BƠM LỖI CÓ CHỦ ĐÍCH THEO ĐÚNG TỶ LỆ KẾ HOẠCH (TRÊN TỔNG ~800 DÒNG)
issue_logs = []
n_current = len(outlets)

def log_issue(idx_list, issue_type, desc):
    for idx in idx_list:
        issue_logs.append({
            'Log_ID': f'ERR_{len(issue_logs)+1:04d}',
            'Outlet_ID': outlets.loc[idx, 'Outlet_ID'],
            'Issue_Type': issue_type,
            'Description': desc,
            'Detected_Date': base_date.strftime('%Y-%m-%d'),
            'Resolved_Status': 'Open'
        })

# Lỗi 1: Thiếu phone/address (9% -> ~72 dòng)
missing_idx = random.sample(range(n_current), 72)
for idx in missing_idx[:36]:
    outlets.loc[idx, 'Phone'] = np.nan
for idx in missing_idx[36:]:
    outlets.loc[idx, 'Address'] = np.nan
log_issue(missing_idx, 'Missing Contact/Address', 'Thiếu số điện thoại hoặc địa chỉ chi tiết')

# Lỗi 2: District viết sai chuẩn (11% -> ~88 dòng)
dirty_dist_map = {
    'Quận 1': ['Dist. 1', 'Q1', 'quận 1', 'Q.1'],
    'Quận 3': ['Q3', 'Dist 3', 'quận 3'],
    'Quận 7': ['Q7', 'Dist.7', 'quận 7'],
    'Quận Bình Thạnh': ['Bình Thạnh', 'Q. Bình Thạnh', 'Binh Thanh'],
    'Thành phố Thủ Đức': ['Thủ Đức', 'TP Thủ Đức', 'Thu Duc']
}
dist_candidates = outlets[outlets['District'].isin(dirty_dist_map.keys())].index.tolist()
dirty_dist_idx = random.sample(dist_candidates, min(88, len(dist_candidates)))
for idx in dirty_dist_idx:
    orig = outlets.loc[idx, 'District']
    outlets.loc[idx, 'District'] = random.choice(dirty_dist_map[orig])
log_issue(dirty_dist_idx, 'Invalid District Format', 'Tên quận viết tắt hoặc sai quy chuẩn hệ thống')

# Lỗi 3: Channel không hợp lệ (3% -> ~24 dòng)
invalid_channels = ['Bistro', 'Beer Club', 'Tea House', 'Unknown', 'Street Food']
bad_ch_idx = random.sample(range(n_current), 24)
for idx in bad_ch_idx:
    outlets.loc[idx, 'Channel'] = random.choice(invalid_channels)
log_issue(bad_ch_idx, 'Invalid Channel', 'Loại hình điểm bán không nằm trong danh mục chuẩn')

# Lỗi 4: Closed nhưng vẫn Active (4% -> ~32 dòng)
ghost_idx = random.sample(range(n_current), 32)
for idx in ghost_idx:
    outlets.loc[idx, 'Outlet_Name'] = outlets.loc[idx, 'Outlet_Name'] + ' (Đã đóng cửa)'
    outlets.loc[idx, 'Status'] = 'Active' # Mâu thuẫn trạng thái
log_issue(ghost_idx, 'Status Mismatch', 'Điểm bán đã ngừng hoạt động thực tế nhưng trạng thái vẫn là Active')

# Lỗi 5: Pending verification (22% -> ~176 dòng)
pending_idx = random.sample(range(n_current), 176)
for idx in pending_idx:
    outlets.loc[idx, 'Verification_Status'] = 'Pending Verification'
log_issue(pending_idx, 'Pending Verification', 'Chưa được giám sát viên xác thực thông tin')

# Lỗi 6: Bản ghi trùng lặp (5.5% -> nhân bản 44 dòng để tổng thành đúng 800 dòng)
valid_for_dup = outlets.dropna(subset=['Phone', 'Address']).index.tolist()
dup_source_idx = random.sample(valid_for_dup, 44)
dup_rows = outlets.loc[dup_source_idx].copy()
dup_rows['Outlet_ID'] = [f'OUT_{i+1001+n_current}' for i in range(len(dup_rows))]
# Thêm khoảng trắng thừa ở địa chỉ/sđt để Power Query phải Trim/Clean mới phát hiện ra
dup_rows['Address'] = '  ' + dup_rows['Address'] + ' '
dup_rows['Phone'] = dup_rows['Phone'] + ' '

outlets_final = pd.concat([outlets, dup_rows], ignore_index=True)

# Ghi nhận log cho các dòng trùng vừa tạo
for idx in range(n_current, len(outlets_final)):
    issue_logs.append({
        'Log_ID': f'ERR_{len(issue_logs)+1:04d}',
        'Outlet_ID': outlets_final.loc[idx, 'Outlet_ID'],
        'Issue_Type': 'Duplicate Record',
        'Description': 'Trùng số điện thoại và địa chỉ sau chuẩn hóa',
        'Detected_Date': base_date.strftime('%Y-%m-%d'),
        'Resolved_Status': 'Open'
    })

# Xáo trộn ngẫu nhiên toàn bộ 800 dòng
outlets_final = outlets_final.sample(frac=1, random_state=42).reset_index(drop=True)

# 5. XUẤT RA CÁC FILE CSV
outlets_final.to_csv('Outlets_Raw_Dirty.csv', index=False, encoding='utf-8-sig')
pd.DataFrame(issue_logs).to_csv('Data_Issue_Log.csv', index=False, encoding='utf-8-sig')

print(f"Hoàn tất! Tổng số bản ghi tạo ra: {len(outlets_final)} outlets.")
print(f"Tổng số lỗi ghi nhận trong Data_Issue_Log: {len(issue_logs)} dòng.")
print("Các file đã xuất: Outlets_Raw_Dirty.csv, Data_Issue_Log.csv, Dim_District.csv, Dim_Channel.csv")
