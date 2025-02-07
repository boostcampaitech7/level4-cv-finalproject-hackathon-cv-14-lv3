from fastapi import FastAPI, WebSocket, WebSocketDisconnect,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from datetime import datetime
import pandas as pd
import sqlalchemy
import re
from dotenv import load_dotenv
import os
import requests
import json
from openai import OpenAI
from supabase import create_client
from supabase.lib.client_options import ClientOptions
import time
import sqlite3
from pydantic import BaseModel
from typing import List
import random
import numpy as np
import matplotlib.pyplot as plt
from tqdm.auto import tqdm
from sklearn.preprocessing import LabelEncoder

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
print(device)

CFG = {
    'TRAIN_WINDOW_SIZE':60,
    'PREDICT_SIZE':1,
    'EPOCHS':50,
    'LEARNING_RATE':1e-4,
    'BATCH_SIZE':1024,
    'SEED': 42
}

def seed_everything(seed):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True

seed_everything(CFG['SEED'])

train_cat = pd.read_csv('data/train.csv').drop(columns=['ID'])
train_num = pd.read_csv('data/train.csv').drop(columns=['ID'])

train_cat = train_cat.iloc[:,:4]
train_num = train_num.iloc[:, 4:-41]

train_data = pd.concat([train_cat, train_num], axis=1)

out_train = pd.read_csv('data/train.csv')
out_train = out_train.iloc[:, -7:]

train_data = pd.concat([train_data, out_train], axis=1)

# 숫자형 변수들의 min-max scaling을 수행하는 코드입니다. real_train
numeric_cols = train_data.columns[4:]

# 각 column의 min 및 max 계산
min_values = train_data[numeric_cols].min(axis = 1)
max_values = train_data[numeric_cols].max(axis = 1)

# 각 행의 범위(max-min)를 계산하고, 범위가 0인 경우 1로 대체
ranges = max_values - min_values
ranges[ranges == 0] = 1

# min-max scaling 수행
train_data[numeric_cols] = (train_data[numeric_cols].subtract(min_values, axis = 0)).div(ranges, axis = 0)

# max와 min 값을 dictionary 형태로 저장
scale_min_dict = min_values.to_dict()
scale_max_dict = max_values.to_dict()

# 1. 범주형 변수 레이블 인코딩
label_encoders = {}  # 각 컬럼별로 LabelEncoder를 저장
categorical_columns = ['Main', 'Sub1', 'Sub2', 'Sub3']

for col in categorical_columns:
    le = LabelEncoder()
    train_data[col] = le.fit_transform(train_data[col]).astype(int)
    label_encoders[col] = le

# 2. 임베딩 레이어 생성
class CategoricalEmbedding(nn.Module):
    def __init__(self, input_sizes, embedding_dims):
        super(CategoricalEmbedding, self).__init__()

        # 각 범주형 변수에 대한 임베딩 레이어를 생성
        self.embeddings = nn.ModuleList([
            nn.Embedding(input_size, dim) for input_size, dim in zip(input_sizes, embedding_dims)
        ])

    def forward(self, x):
        # x: [batch_size, num_categorical_features]
        embedded = [embedding(x[:, i]) for i, embedding in enumerate(self.embeddings)]
        return torch.cat(embedded, dim=1)  # 연결된 임베딩 벡터 반환

# 각 범주형 변수의 최대값 (레이블 인코딩된 값) + 1을 구함
input_sizes = [train_data[col].max() + 1 for col in categorical_columns]

# 임베딩 차원 설정
embedding_dims = [int(np.sqrt(size) // 2) for size in input_sizes]

model = CategoricalEmbedding(input_sizes, embedding_dims)

# 모든 행에 대한 범주형 데이터를 PyTorch 텐서로 변환
all_data_tensor = torch.tensor(train_data[categorical_columns].values, dtype = torch.long)

# 임베딩 모델에 텐서를 입력하여 임베딩된 값을 얻음
with torch.no_grad():
    all_embedded_values = model(all_data_tensor)

# 임베딩된 텐서를 numpy 배열로 변환
all_embedded_np = all_embedded_values.numpy()

# 임베딩된 값을 저장할 임시 데이터프레임 생성
embedded_df = pd.DataFrame()

start_idx = 0
# 각 범주형 변수에 대한 임베딩된 값을 새로운 컬럼으로 추가
for i, col in enumerate(categorical_columns):
    col_names = [f"{col}_{j}" for j in range(embedding_dims[i])]
    for idx, name in enumerate(col_names):
        embedded_df[name] = all_embedded_np[:, start_idx + idx]
    start_idx += embedding_dims[i]

# 레이블 인코딩된 컬럼 제거
train_data.drop(columns=categorical_columns, inplace = True)

# 임베딩된 데이터를 원본 데이터프레임의 앞 부분에 추가
train_data = pd.concat([embedded_df, train_data], axis = 1)

# 결과 확인
train_data.head()

def make_predict_data(data, train_size = CFG['TRAIN_WINDOW_SIZE']):
    num_rows = len(data)

    input_data = np.empty((num_rows, train_size, len(data.iloc[0, :33]) + 1))

    for i in tqdm(range(num_rows)):
        encode_info = np.array(data.iloc[i, :33])
        sales_data = np.array(data.iloc[i, -train_size:])

        window = sales_data[-train_size : ]
        temp_data = np.column_stack((np.tile(encode_info, (train_size, 1)), window[:train_size]))
        input_data[i] = temp_data

    return input_data

test_input = make_predict_data(train_data)

# Custom Dataset
class CustomDataset(Dataset):
    def __init__(self, X, Y):
        self.X = X
        self.Y = Y

    def __getitem__(self, index):
        if self.Y is not None:
            return torch.Tensor(self.X[index]), torch.Tensor(self.Y[index])
        return torch.Tensor(self.X[index])

    def __len__(self):
        return len(self.X)

test_dataset = CustomDataset(test_input, None)
test_loader = DataLoader(test_dataset, batch_size = CFG['BATCH_SIZE'], shuffle = False, num_workers = 0)

def inference(model, test_loader, device):
    predictions = []

    with torch.no_grad():
        for X in tqdm(iter(test_loader)):
            X = X.to(device)

            output = model(X)

            # 모델 출력인 output을 CPU로 이동하고 numpy 배열로 변환
            output = output.cpu().numpy()

            predictions.extend(output)

    return np.array(predictions)

class Mish(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x):
        return x * torch.tanh(nn.functional.softplus(x))

class StackedLSTMModel(nn.Module):
    def __init__(self, input_size = 34, hidden_size = 1024, output_size = CFG['PREDICT_SIZE'], num_layers = 3, dropout = 0.5):
        super(StackedLSTMModel, self).__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # LSTM 레이어 내부에 dropout 적용
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers=num_layers, dropout = (0 if num_layers == 1 else dropout), batch_first = True)

        self.fc = nn.Sequential(
            nn.Linear(hidden_size, hidden_size//2),
            Mish(),
            nn.Linear(hidden_size//2, output_size)
        )

        self.actv = Mish()

    def forward(self, x):
        # x shape: (B, TRAIN_WINDOW_SIZE, 5)
        batch_size = x.size(0)
        hidden = self.init_hidden(batch_size, x.device)

        # LSTM layers
        x, hidden = self.lstm(x, hidden)

        # Only use the last output sequence
        last_output = x[:, -1, :]

        # Fully connected layer
        output = self.actv(self.fc(last_output))

        return output.squeeze(1)

    def init_hidden(self, batch_size, device):
        # Initialize hidden state and cell state
        return (torch.zeros(self.num_layers, batch_size, self.hidden_size, device = device),
                torch.zeros(self.num_layers, batch_size, self.hidden_size, device = device))

# 1) FastAPI 앱 생성
app = FastAPI()

# WebSocket 연결 관리 
active_connections = []

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경 변수 로드
load_dotenv()
UPSTAGE_API_KEY = os.getenv('UPSTAGE_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Supabase 클라이언트 초기화
options = ClientOptions(postgrest_client_timeout=600)  # 타임아웃을 600초로 설정
supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options)

# OpenAI 클라이언트 초기화
client = OpenAI(
    api_key=UPSTAGE_API_KEY,
    base_url=UPSTAGE_API_BASE_URL
)

# ===== 데이터 로딩 =====
# Supabase 연결 재설정 함수
def reconnect_supabase():
    global supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Reconnected to Supabase.")

# Supabase에서 모든 레코드를 페이지네이션(Chunk) 방식으로 가져오는 공통 함수
def load_all_data(table_name):
    all_data = []
    chunk_size = 100000
    start = 0

    while True:
        response = (
            supabase
            .table(table_name)
            .select("*")
            .range(start, start + chunk_size - 1)
            .execute()
        )
        fetched_data = response.data

        # 각 사이클에서 가져온 데이터 개수 출력
        print(f"Fetched {len(fetched_data)} rows from {table_name} (range: {start}~{start + chunk_size - 1})")

        if not fetched_data:
            # 더 이상 데이터가 없으면 중단
            break

        all_data.extend(fetched_data)
        start += chunk_size

    return all_data

# daily_sales_data 테이블의 모든 데이터를 읽어와 DataFrame으로 변환
def load_sales_data():
    try:
        # 절대 경로 사용
        db_path = os.path.join(os.path.dirname(__file__), "../database/database.db")
        conn = sqlite3.connect(db_path)

        # id를 정수로 가져오도록 쿼리 수정
        df = pd.read_sql_query("SELECT CAST(id AS INTEGER) as id, date, value FROM daily_sales_data", conn)
        conn.close()

        # 열 이름을 소문자로 변환
        df.columns = df.columns.str.lower()

        # date 컬럼이 존재하면 datetime으로 변환
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        return df
    except Exception as e:
        print(f"Error loading sales data: {str(e)}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Database path: {db_path}")
        raise

# daily_data 테이블의 모든 데이터를 읽어와 DataFrame으로 변환
def load_quantity_data():
    try:
        # 절대 경로 사용
        db_path = os.path.join(os.path.dirname(__file__), "../database/database.db")
        conn = sqlite3.connect(db_path)

        # id를 정수로 가져오도록 쿼리 수정
        df = pd.read_sql_query("SELECT CAST(id AS INTEGER) as id, date, value FROM daily_data", conn)
        conn.close()

        # 열 이름을 소문자로 변환
        df.columns = df.columns.str.lower()

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except Exception as e:
        print(f"Error loading quantity data: {str(e)}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Database path: {db_path}")
        raise

# product_inventory 테이블의 모든 데이터를 읽어와 DataFrame으로 변환
def load_inventory_data():
    all_data = load_all_data("product_inventory")
    df = pd.DataFrame(all_data)
    return df

# trend_product 테이블의 데이터를 읽어오는 함수
def load_trend_data():
    try:
        response = supabase.table('trend_product') \
            .select('product_name, rank, category, id') \
            .eq('rank', 1) \
            .execute()

        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        print(f"Error loading trend data: {str(e)}")
        raise

# 데이터 로드
df_sales = load_sales_data()
reconnect_supabase()
inventory_df = load_inventory_data()
reconnect_supabase()
df_quantity = load_quantity_data()
reconnect_supabase()
trend_df = load_trend_data()  # 트렌드 데이터 로드 추가

# ===== 컬럼명 변경 =====
df_sales = df_sales.rename(columns={'value': '매출액'})
df_quantity = df_quantity.rename(columns={'value': '판매수량'})
inventory_df = inventory_df.rename(columns={'value': '재고수량'})

# 문자열 변환
df_sales['date'] = df_sales['date'].astype(str)
df_quantity['date'] = df_quantity['date'].astype(str)

# 만약 df_sales에 '대분류' 혹은 '소분류' 컬럼이 없다면 product_info 데이터를 불러와 병합
if '소분류' not in df_sales.columns or '대분류' not in df_sales.columns:
    # product_info 테이블에는 id, main, sub1, sub2, sub3가 있음 (여기서는 sub1: 대분류, sub3: 소분류로 사용)
    product_info_response = supabase.from_('product_info').select("id, sub1, sub3").execute()
    df_product_info = pd.DataFrame(product_info_response.data)
    # 필요한 컬럼명을 변경합니다.
    df_product_info = df_product_info.rename(columns={"sub1": "대분류", "sub3": "소분류"})

    # id 컬럼을 문자열로 변환
    df_sales['id'] = df_sales['id'].astype(str)
    df_product_info['id'] = df_product_info['id'].astype(str)

    # df_sales에 product_info를 id를 기준으로 병합 (left join)
    df_sales = df_sales.merge(df_product_info[["id", "대분류", "소분류"]], on="id", how="left")

# ===== Dash 코드에서 하던 전처리 로직 =====

data = df_sales.copy()
data_quantity = df_quantity.copy()

data['날짜'] = pd.to_datetime(data['date'])
data_quantity['날짜'] = pd.to_datetime(data_quantity['date'])

# 일간 합계
daily_df = data.groupby('날짜', as_index=False)['매출액'].sum()
daily_df = daily_df.rename(columns={'매출액': '값'})

# 주간 집계 (날짜를 주 시작일로 변환하여 그룹화)
daily_df['주간'] = daily_df['날짜'].dt.to_period('W').apply(lambda r: r.start_time)
weekly_data = daily_df.groupby('주간', as_index=False)['값'].sum()

# 월간 집계 (날짜를 월 시작일로 변환하여 그룹화)
daily_df['월간'] = daily_df['날짜'].dt.to_period('M').apply(lambda r: r.start_time)
monthly_sum_df = daily_df.groupby('월간', as_index=False)['값'].sum()

# 최근 12개월 합계를 "연간 매출"로 가정
recent_12_months = monthly_sum_df.tail(12)
annual_sales = recent_12_months['값'].sum()

# KPI 계산
daily_avg = daily_df['값'].mean() if not daily_df.empty else 0
weekly_avg = weekly_data['값'].mean() if not weekly_data.empty else 0
monthly_avg = monthly_sum_df['값'].mean() if not monthly_sum_df.empty else 0
last_daily = daily_df['값'].iloc[-1] if not daily_df.empty else 0
last_weekly = weekly_data['값'].iloc[-1] if not weekly_data.empty else 0
last_monthly = monthly_sum_df['값'].iloc[-1] if not monthly_sum_df.empty else 0

# 월간 변화율 계산
if len(monthly_sum_df) >= 2:
    lm_sales = monthly_sum_df['값'].iloc[-1]
    slm_sales = monthly_sum_df['값'].iloc[-2]
    monthly_change = ((lm_sales - slm_sales) / slm_sales) * 100 if slm_sales != 0 else 0
else:
    monthly_change = 0

# 카테고리별(대분류) 매출
df_category = df_sales.groupby('대분류', as_index=False)['매출액'].sum()

# 재고수량 및 일일판매수량 처리
data_quantity['날짜'] = pd.to_datetime(data_quantity['date'])
last_date = data_quantity['날짜'].max()
if last_date:
    daily_sales_quantity_last = data_quantity[data_quantity['날짜'] == last_date][['id', '판매수량']]
    daily_sales_quantity_last = daily_sales_quantity_last.rename(columns={'판매수량': '일판매수량'})
else:
    daily_sales_quantity_last = pd.DataFrame(columns=['id', '일판매수량'])

merged_df = pd.merge(inventory_df, daily_sales_quantity_last, on='id', how='left')
merged_df['일판매수량'] = merged_df['일판매수량'].fillna(0)
merged_df['남은 재고'] = merged_df['재고수량'] - merged_df['일판매수량']
low_stock_df = merged_df[(merged_df['남은 재고'] >= 0) & (merged_df['남은 재고'] <= 30)]

# 매출 상승폭(소분류)
# 만약 소분류 값이 없는 경우 "기타" 처리
data["소분류"] = data["소분류"].fillna('기타')
pivot_subcat = data.groupby(['소분류', '날짜'])['매출액'].sum().unstack().fillna(0)
all_dates = sorted(pivot_subcat.columns)
if len(all_dates) >= 2:
    last_date_val, second_last_date_val = all_dates[-1], all_dates[-2]
    last_sum = pivot_subcat[last_date_val].sum()
    second_sum = pivot_subcat[second_last_date_val].sum()
    rise_rate = ((last_sum - second_sum) / second_sum) * 100 if second_sum != 0 else 0
else:
    rise_rate = 0

subcat_list = pivot_subcat.sum(axis=1).sort_values(ascending=False).head(10).index.tolist()

# ---------- (추가) 상/하위 10개 계산 ----------
monthly_data = (
    data.assign(월=lambda df: df['날짜'].dt.to_period('M').astype(str))
    .groupby(['id', '월'], as_index=False)['매출액'].sum()
)
result = monthly_data.pivot(index='id', columns='월', values='매출액').reset_index()
result['id'] = result['id'].astype(str)
if len(result.columns) > 1:
    last_month_col = result.columns[-1]
else:
    last_month_col = None

reds = ['#D14B4B', '#E22B2B', '#E53A3A', '#F15D5D', '#F67878',
        '#F99A9A', '#FBB6B6', '#FDC8C8', '#FEE0E0', '#FEEAEA']
blues = ['#B0D6F1', '#A5C9E9', '#99BCE1', '#8DB0D9', '#81A4D1',
         '#7498C9', '#688BC1', '#5C7FB9', '#5073B1', '#4567A9']

# ===== 엔드포인트들 =====

@app.get("/")
def read_root():
    return {
        "status": "success",
    }

@app.get("/api/kpis")
def get_kpis():
    # 넘파이 정수/실수 -> 파이썬 int/float
    return {
        "annual_sales": int(annual_sales),
        "daily_avg": float(daily_avg),
        "weekly_avg": float(weekly_avg),
        "monthly_avg": float(monthly_avg),
        "last_daily": int(last_daily),
        "last_weekly": int(last_weekly),
        "last_monthly": int(last_monthly),
        "monthly_change": float(monthly_change),
    }

@app.get("/api/daily")
def get_daily_data():
    # 2023년 이후 데이터만 필터링
    filtered_daily = daily_df
    return filtered_daily.to_dict(orient="records")

@app.get("/api/weekly")
def get_weekly_data():
    # 2022년 10월 이후 데이터만 필터링
    filtered_weekly = weekly_data
    return filtered_weekly.to_dict(orient="records")

@app.get("/api/monthly")
def get_monthly_data():
    return monthly_sum_df.to_dict(orient="records")

@app.get("/api/categorypie")
def get_category_pie():
    # 매출액 기준으로 정렬하고 상위 5개만 선택
    top_5_categories = df_category.nlargest(5, '매출액')
    return top_5_categories.to_dict(orient="records")

@app.get("/api/lowstock")
def get_low_stock():
    # merged_df와 low_stock_df가 전역 변수로 정의되어 있는지 확인
    global merged_df, low_stock_df

    try:
        # product_info 테이블에서 sub3 정보 가져오기
        response = supabase.table('product_info').select("id", "sub3").execute()
        product_info = pd.DataFrame(response.data)
        product_info = product_info.rename(columns={'id': 'id', 'sub3': 'Sub3'})

        # low_stock_df와 product_info 병합
        merged_low_stock = pd.merge(low_stock_df, product_info, on='id', how='left')

        return merged_low_stock.to_dict(orient="records")
    except Exception as e:
        print(f"Error in get_low_stock: {str(e)}")
        return {"error": str(e)}

@app.get("/api/rising-subcategories")
def get_rising_subcategories():
    return {
        "rise_rate": float(rise_rate),
        "subcat_list": list(subcat_list)  # 넘파이 Index -> list
    }

# (수정) 판매수량 상위 10개 품목 반환 엔드포인트
@app.get("/api/topbottom")
def get_topbottom():
    try:
        # df_quantity는 이미 전역 변수로 로드되어 있음 (컬럼: id, date, 판매수량)
        # 전체 판매수량을 제품별로 집계
        sales_qty_total = df_quantity.groupby('id', as_index=False)['판매수량'].sum()

        # 판매수량 상위 10개 품목 선택
        top_10_df = sales_qty_total.nlargest(10, '판매수량').copy()
        top_10_df['id'] = top_10_df['id'].astype(str)
        top_10_df = top_10_df.rename(columns={'id': 'ID', '판매수량': '총판매수량'})

        # Supabase에서 product_info 데이터 (예: 제품명 또는 sub3 정보를 가져옴)
        response = supabase.table('product_info').select("id, sub3").execute()
        product_info = pd.DataFrame(response.data)
        product_info['id'] = product_info['id'].astype(str)
        product_info = product_info.rename(columns={'id': 'ID', 'sub3': 'Sub3'})

        # 집계 데이터와 product_info를 병합 (제품명 등 추가 정보 포함)
        top_10_df = pd.merge(top_10_df, product_info, on='ID', how='left')

        top_10_list = top_10_df.to_dict('records')
        return {
            "top_10": top_10_list
        }
    except Exception as e:
        print(f"Error in get_topbottom: {str(e)}")
        return {
            "top_10": [],
            "error": str(e)
        }

# 챗봇용 데이터 미리 준비
def prepare_chat_data():
    # 월별 매출 데이터
    monthly_sales_text = "월별 매출 데이터:\n" + "\n".join([
        f"{row['월간'].strftime('%Y-%m')}: {row['값']:,}원"
        for row in monthly_sum_df.to_dict('records')
    ])

    # 주간 매출 데이터
    weekly_sales_text = "주간 매출 데이터:\n" + "\n".join([
        f"{row['주간'].strftime('%Y-%m-%d')}: {row['값']:,}원"
        for row in weekly_data.tail(12).to_dict('records')
    ])

    # 일별 매출 데이터
    daily_sales_text = "최근 30일 일별 매출 데이터:\n" + "\n".join([
        f"{row['날짜'].strftime('%Y-%m-%d')}: {row['값']:,}원"
        for row in daily_df.tail(30).to_dict('records')
    ])

    # 카테고리별 매출 상세
    category_details = df_sales.groupby('대분류').agg({
        '매출액': ['sum', 'mean', 'count']
    }).reset_index()
    category_details.columns = ['대분류', '총매출', '평균매출', '판매건수']

    category_text = "카테고리별 매출 상세:\n" + "\n".join([
        f"{row['대분류']}: 총매출 {row['총매출']:,}원, 평균 {row['평균매출']:,.0f}원, {row['판매건수']}건"
        for _, row in category_details.iterrows()
    ])

    # 재고 현황 상세
    inventory_status = pd.merge(
        inventory_df,
        daily_sales_quantity_last,
        on='id',
        how='left'
    )

    # product_info 테이블에서 카테고리 정보 가져오기
    product_info_response = supabase.from_('product_info').select("id,main,sub3").execute()
    product_info_df = pd.DataFrame(product_info_response.data)

    # 데이터 병합
    inventory_status = pd.merge(
        inventory_status,
        product_info_df,
        left_on='id',
        right_on='id',
        how='left'
    )

    inventory_status['일판매수량'] = inventory_status['일판매수량'].fillna(0)
    inventory_status['남은재고'] = inventory_status['재고수량'] - inventory_status['일판매수량']

    inventory_text = "카테고리별 재고 현황:\n" + "\n".join([
        f"{row['main'] if pd.notna(row['main']) else '미분류'}({row['sub3'] if pd.notna(row['sub3']) else '미분류'}): "
        f"총재고 {row['재고수량']}개, 일판매량 {row['일판매수량']}개, 남은재고 {row['남은재고']}개"
        for _, row in inventory_status.iterrows()
    ])

    return {
        "monthly_sales": monthly_sales_text,
        "weekly_sales": weekly_sales_text,
        "daily_sales": daily_sales_text,
        "category_details": category_text,
        "inventory_status": inventory_text
    }

# 챗봇용 데이터 미리 준비
def prepare_chat_data():
    # 월별 매출 데이터
    monthly_sales_text = "월별 매출 데이터:\n" + "\n".join([
        f"{row['월간'].strftime('%Y-%m')}: {row['값']:,}원"
        for row in monthly_sum_df.to_dict('records')
    ])

    # 주간 매출 데이터
    weekly_sales_text = "주간 매출 데이터:\n" + "\n".join([
        f"{row['주간'].strftime('%Y-%m-%d')}: {row['값']:,}원"
        for row in weekly_data.tail(12).to_dict('records')
    ])

    # 일별 매출 데이터
    daily_sales_text = "최근 30일 일별 매출 데이터:\n" + "\n".join([
        f"{row['날짜'].strftime('%Y-%m-%d')}: {row['값']:,}원"
        for row in daily_df.tail(30).to_dict('records')
    ])

    # 카테고리별 매출 상세
    category_details = df_sales.groupby('대분류').agg({
        '매출액': ['sum', 'mean', 'count']
    }).reset_index()
    category_details.columns = ['대분류', '총매출', '평균매출', '판매건수']

    category_text = "카테고리별 매출 상세:\n" + "\n".join([
        f"{row['대분류']}: 총매출 {row['총매출']:,}원, 평균 {row['평균매출']:,.0f}원, {row['판매건수']}건"
        for _, row in category_details.iterrows()
    ])

    # 재고 현황 상세
    inventory_status = pd.merge(
        inventory_df,
        daily_sales_quantity_last,
        on='id',
        how='left'
    )

    # product_info 테이블에서 카테고리 정보 가져오기
    product_info_response = supabase.from_('product_info').select("id,main,sub3").execute()
    product_info_df = pd.DataFrame(product_info_response.data)

    # 데이터 병합
    inventory_status = pd.merge(
        inventory_status,
        product_info_df,
        left_on='id',
        right_on='id',
        how='left'
    )

    inventory_status['일판매수량'] = inventory_status['일판매수량'].fillna(0)
    inventory_status['남은재고'] = inventory_status['재고수량'] - inventory_status['일판매수량']

    inventory_text = "카테고리별 재고 현황:\n" + "\n".join([
        f"{row['main'] if pd.notna(row['main']) else '미분류'}({row['sub3'] if pd.notna(row['sub3']) else '미분류'}): "
        f"총재고 {row['재고수량']}개, 일판매량 {row['일판매수량']}개, 남은재고 {row['남은재고']}개"
        for _, row in inventory_status.iterrows()
    ])

    return {
        "monthly_sales": monthly_sales_text,
        "weekly_sales": weekly_sales_text,
        "daily_sales": daily_sales_text,
        "category_details": category_text,
        "inventory_status": inventory_text
    }

# 데이터 미리 준비
CHAT_DATA = prepare_chat_data()

@app.post("/api/chat")
async def chat_with_solar(message: dict):
    try:
        # product_info 테이블에서 sub3 정보 가져오기
        response = supabase.table('product_info').select("id, sub3").execute()
        product_info = pd.DataFrame(response.data)
        product_info = product_info.rename(columns={'id': 'id', 'sub3': 'Sub3'})

        # low_stock_df와 product_info 병합
        merged_low_stock = pd.merge(low_stock_df, product_info, on='id', how='left')
        total_low_stock = len(merged_low_stock)

        if total_low_stock > 0:
            low_stock_list = "\n".join([
                f"- {row['Sub3'] if pd.notna(row['Sub3']) else '미분류'}: {row['남은 재고']}개"
                for _, row in merged_low_stock.iterrows()
            ])
        else:
            low_stock_list = "현재 재고 부족 상품이 없습니다."

        system_message = f"""
        당신은 판매 데이터 분석 AI 어시스턴트입니다.

        1. 매출이나 재고 관련 질문이 모호한 경우:
        - "어떤 기간의 매출에 대해 알고 싶으신가요? 일간, 주간, 월간 등 구체적으로 말씀해 주시면 자세히 알려드리겠습니다."
        - "어떤 제품의 재고를 확인하고 싶으신가요? 특정 카테고리나 제품을 말씀해 주시면 정확한 정보를 알려드리겠습니다."

        2. 매출이나 재고와 관련 없는 질문인 경우:
        - "죄송합니다. 저는 매출과 재고 관련 문의만 답변 가능한 AI 어시스턴트입니다."

        3. 매출이나 재고에 대한 구체적인 질문인 경우에만 아래 데이터를 참고하여 답변하세요:

        === 매출 현황 ===
        - 연간 매출: {int(annual_sales):,}원
        - 일평균 매출: {float(daily_avg):,.0f}원
        - 주간 평균 매출: {float(weekly_avg):,.0f}원
        - 월간 평균 매출: {float(monthly_avg):,.0f}원
        - 최근 일일 매출: {int(last_daily):,}원
        - 최근 주간 매출: {int(last_weekly):,}원
        - 최근 월간 매출: {int(last_monthly):,}원
        - 전월 대비 변화율: {float(monthly_change):.1f}%

        === 카테고리 분석 ===
        - 매출 상승률: {float(rise_rate):.1f}%
        - 주요 성장 카테고리(소분류): {', '.join(subcat_list[:5])}

        === 재고 현황 ===
        - 재고 부족 상품 수: {total_low_stock}개
        - 재고 부족 상품 목록:
        {low_stock_list}

        답변 시 주의사항:
        1. 매출/재고 관련 구체적인 질문에만 관련 데이터를 활용하여 답변
        2. 매출/재고 관련 모호한 질문에는 더 구체적인 질문을 요청
        3. 매출/재고와 관련 없는 질문에는 매출/재고 관련 문의만 가능하다고 안내
        4. 친절하고 전문적인 어조 유지
        5. 불필요한 데이터는 제외하고 질문과 관련된 정보만 제공
        6. 답변할 때 불릿 포인트(-) 사용하지 말고 자연스러운 문장으로 표현
        """

        response = client.chat.completions.create(
            model="solar-pro",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": message["content"]}
            ],
            temperature=0.0,
            stream=False,
            response_format={"type": "text/html"}  # HTML 형식 응답 요청
        )

        if hasattr(response, 'error'):
            return {
                "response": f"API 오류: {response.error}",
                "status": "error",
                "error": str(response.error)
            }

        return {
            "response": response.choices[0].message.content,
            "status": "success"
        }

    except Exception as e:
        print(f"Error details: {e!s}")
        return {
            "response": f"서버 오류가 발생했습니다: {e!s}",
            "status": "error",
            "error": str(e)
        }

@app.get("/api/trend-categories")
async def get_trend_categories():
    try:
        # 단순히 trending_product 테이블에서 모든 카테고리 조회
        response = supabase.table('trend_product')\
            .select('category')\
            .execute()
        
        # 중복 제거 및 정렬
        categories = sorted(list(set([item['category'] for item in response.data])))
        
        return {
            "status": "success",
            "categories": categories
        }

    except Exception as e:
        print(f"Error in trend-chat: {e!s}")
        return {
            "status": "error",
            "error": f"서버 오류가 발생했습니다: {e!s}"
        }

@app.post("/api/trend-chat")
async def chat_with_trend(message: dict):
   try:
       # trend_product 테이블에서 모든 데이터 조회
       response = supabase.table('trend_product')\
           .select('*')\
           .order('rank')\
           .execute()

       trend_data = response.data

       # 트렌드 데이터를 카테고리별로 정리
       categorized_trends = {}
       for item in trend_data:
           category = item['category'].strip()  
           if category not in categorized_trends:
               categorized_trends[category] = []
           categorized_trends[category].append({
               'rank': item['rank'],
               'product_name': item['product_name'],
               'start_date': item['start_date'],
               'end_date': item['end_date']
           })

       # 사용자 메시지에서 카테고리 확인
       user_category = message["content"].strip()
       
       if user_category in categorized_trends:
           # 해당 카테고리의 상위 5개 순위 정보 구성
           trend_info = []
           category_data = sorted(categorized_trends[user_category], key=lambda x: x['rank'])[:5]
           
           # 기간 정보 추출
           period = f"{category_data[0]['start_date']} ~ {category_data[0]['end_date']}"
           
           # 순위 정보 구성
           for item in category_data:
               trend_info.append(f"{item['rank']}위: {item['product_name']}")
           
           trend_text = "\n".join(trend_info)
           
           # 시스템 메시지 구성
           system_message = f"""
            You are an AI retail trend analyst specializing in sales improvement.

            Let me show you how to analyze retail trends with multiple examples:

            Example 1:
            Input Data:
            Category: 디지털/가전
            Period: 2024-01-04 ~ 2024-02-04
            Rank 1: 무선이어폰
            Rank 2: 공기청정기
            Rank 3: 스마트워치
            Rank 4: 가습기
            Rank 5: 블루투스스피커

            Thought Process:
            1. Two out of top 5 are IoT/wearable devices (earphones, smartwatch)
            2. Winter season items (air purifier, humidifier) show seasonal demand
            3. Audio devices (earphones, speaker) indicate strong entertainment needs 
            4. Mix of health (air care) and lifestyle tech shows balanced consumption

            Analysis Result:
            ▶ [디지털/가전] 월간트렌드 TOP 5
            (2024-01-04 ~ 2024-02-04)
            1위: 무선이어폰
            2위: 공기청정기
            3위: 스마트워치
            4위: 가습기
            5위: 블루투스스피커

            ▶ 트렌드 분석
            웨어러블/IoT 기기에 대한 수요가 높게 나타났으며, 실내 공기질 관리 가전도 강세를 보이고 있습니다. 특히 무선이어폰과 스마트워치의 상위 랭크는 모바일 라이프스타일이 더욱 강화되고 있음을 시사합니다. 음향기기의 꾸준한 수요도 특징적입니다.

            ▶ 다음 달 트렌드 예측
            신학기를 앞두고 스마트기기 수요가 더욱 증가할 것으로 예상되며, 환절기 대비 공기질 관리 가전의 수요도 지속될 것으로 전망됩니다.

            Example 2:
            Input Data:
            Category: 의류/잡화
            Period: 2024-01-04 ~ 2024-02-04
            Rank 1: 여성 패딩
            Rank 2: 남성 운동화
            Rank 3: 여성 부츠
            Rank 4: 여성 운동화
            Rank 5: 여성 크로스백

            Thought Process:
            1. Winter apparel dominates with padding and boots
            2. Athletic shoes popular across genders suggests active lifestyle trend
            3. Women's fashion items show stronger presence in rankings
            4. Mix of practical (shoes) and fashion (crossbag) items indicates balanced consumer needs

            Analysis Result:
            ▶ [의류/잡화] 월간트렌드 TOP 5
            (2024-01-04 ~ 2024-02-04)
            1위: 여성 패딩
            2위: 남성 운동화
            3위: 여성 부츠
            4위: 여성 운동화
            5위: 여성 크로스백

            ▶ 트렌드 분석
            동절기 필수 아이템인 패딩과 부츠가 강세를 보이고 있으며, 특히 여성 의류/잡화의 수요가 두드러집니다. 운동화는 남녀 모두에게 인기가 높아 캐주얼/스포티한 스타일이 트렌드임을 알 수 있습니다.

            ▶ 다음 달 트렌드 예측
            환절기로 접어들며 가벼운 아우터와 운동화 수요가 지속될 것으로 예상되며, 봄 시즌 새로운 스타일의 잡화 수요가 증가할 것으로 전망됩니다.

            Now, please analyze the following data using the same thought process:
            Category: {category}
            Period: {period}
            {trend_text}

            Remember to:
            1. First analyze the patterns in the ranking data
            2. Consider seasonal and market factors
            3. Think about consumer behavior and preferences
            4. Make logical predictions based on these factors
            5. Present your analysis in Korean using the same format as the examples
            """

           # Solar ChatAPI 응답 생성
           response = client.chat.completions.create(
               model="solar-pro",
               messages=[
                   {"role": "system", "content": system_message},
                   {"role": "user", "content": f"Please analyze the trends for {category} category and provide the response in Korean."}
               ],
               temperature=0.3, 
               stream=False,
               response_format={"type": "text/html"}
           )

           if hasattr(response, 'error'):
               return {
                   "response": f"API 오류: {response.error}",
                   "status": "error",
                   "error": str(response.error)
               }

           return {
               "response": response.choices[0].message.content,
               "status": "success"
           }
       else:
           # 카테고리가 없는 경우 사용 가능한 카테고리 목록 반환
           available_categories = list(categorized_trends.keys())
           return {
               "response": f"죄송합니다. '{user_category}' 카테고리는 현재 트렌드 정보에 없습니다.\n\n조회 가능한 카테고리: {', '.join(available_categories)}",
               "status": "success"
           }

   except Exception as e:
       print(f"Error in trend-chat: {str(e)}")
       return {
           "status": "error",
           "error": f"서버 오류가 발생했습니다: {str(e)}"
       }


@app.get("/api/inventory")
def get_inventory(sort: str = None, main: str = None, sub1: str = None, sub2: str = None):
    try:
        response = supabase.from_('product_inventory').select("""
            id, value,
            product_info (
                main, sub1, sub2, sub3
            )
        """).execute()

        df_inventory = pd.DataFrame(response.data)

        # ✅ `id` 값을 유지하고 문자열로 변환 (프론트와 일관되게 매핑)
        df_inventory["id"] = df_inventory["id"].astype(str)

        # ✅ `product_info` 컬럼에서 필요한 값 추출
        df_inventory["main"] = df_inventory["product_info"].apply(lambda x: x.get("main", None) if isinstance(x, dict) else None)
        df_inventory["sub1"] = df_inventory["product_info"].apply(lambda x: x.get("sub1", None) if isinstance(x, dict) else None)
        df_inventory["sub2"] = df_inventory["product_info"].apply(lambda x: x.get("sub2", None) if isinstance(x, dict) else None)
        df_inventory["sub3"] = df_inventory["product_info"].apply(lambda x: x.get("sub3", None) if isinstance(x, dict) else None)

        # ✅ 불필요한 컬럼 제거 (`product_info`는 원본 JSON이므로 삭제)
        df_inventory = df_inventory.drop(columns=["product_info"])
        
        # ✅ 필터링 적용
        if main:
            df_inventory = df_inventory[df_inventory["main"] == main]
        if sub1:
            df_inventory = df_inventory[df_inventory["sub1"] == sub1]
        if sub2:
            df_inventory = df_inventory[df_inventory["sub2"] == sub2]

        # ✅ 정렬을 프론트엔드에서만 담당 (백엔드는 정렬 X)
        if sort:
            df_inventory = df_inventory.sort_values(by=["value"], ascending=(sort == "asc"))

        return df_inventory.to_dict(orient="records")
    
    
    except Exception as e:
        print(f"❌ Error fetching inventory: {e!s}")
        return {"error": str(e)}

# ✅ 카테고리 필터 엔드포인트
@app.get("/api/category_filters")
def get_category_filters(main: str = None, sub1: str = None, sub2: str = None):
    """
    선택된 main, sub1, sub2를 기반으로 가능한 sub1, sub2, sub3 목록 반환
    """
    try:
        response = supabase.from_('product_info').select("main, sub1, sub2, sub3").execute()
        df = pd.DataFrame(response.data)

        filters = {}

        if main and sub1 and sub2:
            filters["sub3"] = sorted(df[(df["main"] == main) & (df["sub1"] == sub1) & (df["sub2"] == sub2)]["sub3"].dropna().unique().tolist())
        elif main and sub1:
            filters["sub2"] = sorted(df[(df["main"] == main) & (df["sub1"] == sub1)]["sub2"].dropna().unique().tolist())
        elif main:
            filters["sub1"] = sorted(df[df["main"] == main]["sub1"].dropna().unique().tolist())
        else:
            filters["main"] = sorted(df["main"].dropna().unique().tolist())

        return {"status": "success", "filters": filters}

    except Exception as e:
        return {"error": str(e)}


# ✅ 최소 재고 기준(ROP) 계산 (서버 실행 시 한 번만 수행)
def compute_fixed_reorder_points():
    try:
        response = supabase.from_('monthly_sales').select("*").execute()
        df_sales = pd.DataFrame(response.data)

        # 모델 인스턴스 생성
        infer_model = StackedLSTMModel().to(device)

        # 저장된 가중치 로드
        infer_model.load_state_dict(torch.load("weight/best_model.pth", map_location=device))
        pred = inference(infer_model, test_loader, device)
        # 1️⃣ 🔹 Inverse Scaling 적용
        for idx in range(len(pred)):
            if isinstance(scale_min_dict, dict):  # ✅ 딕셔너리일 경우
                min_val = scale_min_dict.get(idx, 0)  # 기본값 0
                max_val = scale_max_dict.get(idx, 1)  # 기본값 1
            else:  # 리스트나 넘파이 배열일 경우
                min_val = scale_min_dict[idx]
                max_val = scale_max_dict[idx]

            pred[idx] = pred[idx] * (max_val - min_val) + min_val

        # 2️⃣ 🔹 예측 데이터 후처리 (반올림 및 정수 변환)
        pred = np.round(pred, 0).astype(int)

        # 3️⃣ 🔹 음수값을 0으로 변경
        pred[pred < 0] = 0

        # 4️⃣ 🔹 1차원 배열이면 (N, 1)로 변환
        if pred.ndim == 1:
            pred = pred.reshape(-1, 1)

        if df_sales.empty:
            return {}

        # ✅ 전체 데이터 기준으로 월 평균 판매량 계산
        valid_dates = [col for col in df_sales.columns if re.match(r"\d{2}_m\d{2}", col)]
        df_sales["monthly_avg_sales"] = df_sales[valid_dates].mean(axis=1).fillna(0)

        # ✅ 전체 데이터 기준으로 일 평균 판매량 계산 -> 여기를 모델 inference 결과
        df_sales["daily_avg_sales"] = pred

        # ✅ 최소 재고 기준(ROP) 계산: 일 평균 판매량의 2배 + 10
        df_sales["reorder_point"] = (df_sales["daily_avg_sales"] * 2 + 10).fillna(10)

        # ✅ `id`를 문자열로 변환하여 JSON 직렬화 오류 방지
        df_sales["id"] = df_sales["id"].astype(str)

        # ✅ 최소 재고 기준을 딕셔너리 형태로 저장
        reorder_points = df_sales.set_index("id")["reorder_point"].to_dict()

        return reorder_points

    except Exception as e:
        print(f"❌ 최소 재고 기준 계산 오류: {str(e)}")
        return {}

# ✅ 서버 실행 시 최초 계산하여 저장
FIXED_REORDER_POINTS = compute_fixed_reorder_points()

@app.get("/api/reorder_points")
def get_reorder_points(start: str, end: str):
    try:
        response = supabase.from_('monthly_sales').select("*").execute()
        df_sales = pd.DataFrame(response.data)

        if df_sales.empty:
            return {"error": "🚨 Supabase에서 데이터를 불러오지 못했습니다."}

        # ✅ 선택한 기간의 월별 판매량 데이터 가져오기
        valid_dates = [col for col in df_sales.columns if re.match(r"\d{2}_m\d{2}", col)]
        selected_dates = [col for col in valid_dates if start <= col <= end]

        if not selected_dates:
            return {"error": "🚨 선택한 기간의 데이터가 없습니다."}

        # ✅ 선택한 기간에 대한 월/일 평균 판매량 계산
        df_sales["monthly_avg_sales"] = df_sales[selected_dates].mean(axis=1).fillna(0)
        df_sales["daily_avg_sales"] = df_sales["monthly_avg_sales"] / 30

        # ✅ 최소 재고 기준(ROP)은 서버 시작 시 계산된 값 사용
        df_sales["reorder_point"] = df_sales["id"].map(lambda x: FIXED_REORDER_POINTS.get(str(x), 10))

        # ✅ ID를 문자열로 변환하여 JSON 직렬화 문제 방지
        df_sales["id"] = df_sales["id"].astype(str)

        # ✅ 필요한 데이터만 반환
        reorder_data = df_sales[["id", "monthly_avg_sales", "daily_avg_sales", "reorder_point"]].to_dict(orient="records")

        return reorder_data

    except Exception as e:
        print(f"❌ ROP 갱신 오류: {str(e)}")
        return {"error": str(e)}

active_connections = []
db_path = os.path.join(os.path.dirname(__file__), "../database/database.db")

def order_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 테이블 존재 여부 확인
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='auto_orders';"
    )
    table_exists = cursor.fetchone()

    # 테이블이 없으면 생성
    if not table_exists:
        cursor.execute(
            """CREATE TABLE auto_orders (
                id INTEGER PRIMARY KEY,
                value INTEGER,
                is_orderable BOOLEAN
            )"""
        )
        conn.commit()
        print("✅ 테이블 'auto_orders'가 생성되었습니다.")

    conn.close()

order_db()

# ✅ 주문 데이터 모델
class OrderItem(BaseModel):
    id: int
    value: int
    is_orderable: bool

class OrderData(BaseModel):
    items: List[OrderItem]

# ✅ WebSocket 핸들러 (프론트엔드와 실시간 연결)
@app.websocket("/ws/auto_orders")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # 클라이언트 메시지 수신 (필요 없으면 제거 가능)
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# ✅ 주문 데이터 저장 + WebSocket으로 프론트에 전송
@app.post("/api/auto_orders")
async def save_auto_order(order_data: OrderData):
    if not order_data.items:
        raise HTTPException(status_code=400, detail="잘못된 데이터 형식입니다.")
    db_path = os.path.join(os.path.dirname(__file__), "../database/database.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for item in order_data.items:
        cursor.execute(
            """INSERT INTO auto_orders (id, value, is_orderable)
               VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET value = ?, is_orderable = ?""",
            (item.id, item.value, item.is_orderable, item.value, item.is_orderable),
        )

    conn.commit()
    conn.close()

    # ✅ 주문 완료 이벤트를 WebSocket을 통해 프론트에 전송
    order_info = {"id": item.id, "value": item.value, "status": "✅ 주문 완료"}
    for connection in active_connections:
        await connection.send_json(order_info)  # 프론트엔드에 JSON 데이터 전송

    return {"status": "success", "message": "자동 주문 완료 리스트 저장됨"}

# main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False) 
