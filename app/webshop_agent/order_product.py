import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client
from supabase.lib.client_options import ClientOptions

# Configure imports and environment
EMBEDDINGS_DIR = Path(__file__).parent.parent.parent / "database"
sys.path.append(str(EMBEDDINGS_DIR))

# Load environment variables from the embeddings directory
ENV_PATH = EMBEDDINGS_DIR / ".env"
load_dotenv(ENV_PATH)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


# Supabase 클라이언트 초기화
options = ClientOptions(postgrest_client_timeout=600)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options)

def load_all_sales_data(table_name, batch_size=1000):
    all_data = []
    offset = 0

    while True:
        response = supabase.from_(table_name).select("*").range(offset, offset + batch_size - 1).execute()

        if not response.data:  # 더 이상 데이터가 없으면 종료
            break

        all_data.extend(response.data)  # 데이터 추가
        offset += batch_size  # 다음 batch로 이동

    return pd.DataFrame(all_data) if all_data else None

def load_product_info(low_stock_ids):
    """
    재고가 부족한 id 리스트를 받아서 product_info를 넘겨주는 함수
    """
    response = supabase.table("product_info").select("*").in_("id", low_stock_ids).execute()
    return pd.DataFrame(response.data)



# 월간 구매 데이터 로드
month_df = load_all_sales_data('monthly_sales')
if month_df is not None:
    print(f"총 {len(month_df)}개 행을 가져왔습니다.")
    print(month_df.head())
else:
    print("데이터를 불러오지 못했습니다.")

# 최소 재고 기준 (Reorder Point, ROP): 일평균 판매량 * 리드타임(2일) + 안전재고
month_df["reorder_point"] = month_df.iloc[:, 1:].mean(axis=1) / 30 * 2 + 25
print(month_df[["id", "reorder_point"]])

inven_df = load_all_sales_data('product_inventory')
if inven_df is not None:
    print(f"총 {len(inven_df)}개 행을 가져왔습니다.")
    print(inven_df.head())
else:
    print("데이터를 불러오지 못했습니다.")

# 두 데이터프레임 병합 (id 기준)
merged_df = month_df[["id", "reorder_point"]].merge(inven_df, on="id", how="inner")

# 재고가 reorder_point보다 낮은 제품 필터링
low_stock_df = merged_df[merged_df["value"] < merged_df["reorder_point"]]

# 결과 출력
print("재고가 부족한 제품 목록:")
print(f"총 {len(low_stock_df)}개의 주문 목록이 있습니다.")
print(low_stock_df[["id", "value", "reorder_point"]])

# 재고 부족한 제품 ID 목록
low_stock_ids = low_stock_df["id"].tolist()
low_stock_df.rename(columns={'value': 'quantity'}, inplace=True) # 시연영상을 위한 코드
low_stock_df['quantity'] = (low_stock_df['quantity'] // 1).astype(int)

reorder_item_df = load_product_info(low_stock_ids)

if reorder_item_df is not None:
    print(f"총 {len(reorder_item_df)}개 행을 가져왔습니다.")
    print(reorder_item_df.head())
else:
    print("데이터를 불러오지 못했습니다.")

# 결과 출력
print("실제 주문 목록:")
print(f"총 {len(reorder_item_df)}개의 주문 목록이 있습니다.")
print(reorder_item_df)

# 두 데이터프레임을 id를 기준으로 병합
reorder_product_df = pd.merge(
    reorder_item_df[['id', 'main', 'sub1', 'sub2', 'sub3']],  # 필요한 열만 선택
    low_stock_df[['id', 'quantity']],  # id와 quantity 열만 선택
    on='id',  # 'id' 기준으로 병합
    how='inner'  # 공통된 id만 병합 (inner join)
)

# 결과 출력
print(reorder_product_df)

# DataFrame을 딕셔너리 리스트로 변환
data_to_insert = reorder_product_df.to_dict(orient="records")

# Supabase에 데이터 삽입 (이미 존재하는 id는 건너뜀)
if len(data_to_insert) != 0:
    response = supabase.table("order_product").upsert(
        data_to_insert,
        on_conflict=["id"]  # 'id'가 이미 존재하면 삽입을 건너뜀
    ).execute()
    # 결과 확인
    if response.data:
        print("데이터 업로드 성공!")
    else:
        print("업로드 실패:", response) 
