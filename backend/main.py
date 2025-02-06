from fastapi import FastAPI
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

# 1) FastAPI 앱 생성
app = FastAPI()

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
    base_url="https://api.upstage.ai/v1/solar"
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


# 데이터 로드
df_sales = load_sales_data()
reconnect_supabase()
inventory_df = load_inventory_data()
reconnect_supabase()
df_quantity = load_quantity_data()


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
        print(f"Error details: {str(e)}")
        return {
            "response": f"서버 오류가 발생했습니다: {str(e)}",
            "status": "error",
            "error": str(e)
        }

@app.post("/api/trend-chat")
async def chat_with_trend(message: dict):
    try:
        # n8n workflow 호출 후 트렌드 분석 응답 받기
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:5678/webhook/trend",
                json={
                    "query": "",
                    "chatInput": message.get("content", "")
                },
                timeout=30.0
            )

            print(f"n8n response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if "output" not in result:
                    return {
                        "response": "n8n workflow에서 올바른 응답을 받지 못했습니다.",
                        "status": "error"
                    }
                return {
                    "response": result["output"],
                    "status": "success"
                }
            elif response.status_code == 404:
                return {
                    "response": "n8n webhook URL을 찾을 수 없습니다.",
                    "status": "error"
                }
            else:
                return {
                    "response": f"트렌드 분석 처리 중 오류가 발생했습니다. (Status: {response.status_code})",
                    "status": "error"
                }

    except Exception as e:
        print(f"Error in trend-chat: {str(e)}")
        return {
            "status": "error",
            "error": f"서버 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/top-sales-items")
def get_top_sales_items():
    try:
        # 전역 변수로 이미 로드된 df_sales 사용
        global df_sales

        # date 컬럼을 datetime으로 변환
        df_sales['date'] = pd.to_datetime(df_sales['date'])

        # 최근 3개월 데이터 필터링
        latest_date = df_sales['date'].max()
        three_months_ago = latest_date - pd.DateOffset(months=3)
        recent_data = df_sales[df_sales['date'] >= three_months_ago]

        # ID별 총 매출액 계산 및 상위 5개 선택
        total_sales_by_id = recent_data.groupby(['id', '소분류'])['매출액'].sum().reset_index()
        top_5 = total_sales_by_id.nlargest(5, '매출액')

        # 최근 2일 날짜 구하기
        prev_date = df_sales[df_sales['date'] < latest_date]['date'].max()

        result = []
        for _, row in top_5.iterrows():
            item_id = row['id']
            item_data = df_sales[df_sales['id'] == item_id]

            # 최근 2일 매출액
            latest_sales = item_data[item_data['date'] == latest_date]['매출액'].sum()
            prev_sales = item_data[item_data['date'] == prev_date]['매출액'].sum()

            # 증감률 계산
            change_rate = ((latest_sales - prev_sales) / prev_sales * 100) if prev_sales != 0 else 0

            result.append({
                "id": item_id,
                "name": row['소분류'] if pd.notna(row['소분류']) else f"Product {item_id}",
                "sales": float(latest_sales),
                "change_rate": float(change_rate)
            })

        return result if result else []
    except Exception as e:
        print(f"Error in get_top_sales_items: {str(e)}")
        return []

@app.get("/api/daily-top-sales")
def get_daily_top_sales():
    try:
        # 이미 병합된 df_sales 사용 (대분류, 소분류 정보 포함)
        latest_date = df_sales['date'].max()
        latest_sales = df_sales[df_sales['date'] == latest_date].copy()
        
        # 제품별 매출액 합계 계산 및 상위 7개 선택
        daily_top_7 = latest_sales.groupby(['id', '대분류', '소분류'], as_index=False)['매출액'].sum()
        daily_top_7 = daily_top_7.nlargest(7, '매출액')
        
        # 결과 포맷팅
        result = [{
            'id': str(row['id']),
            'category': row['대분류'],  # 대분류
            'subcategory': row['소분류'],  # 소분류
            'sales': float(row['매출액']),
            'date': latest_date
        } for _, row in daily_top_7.iterrows()]
        
        return result
    except Exception as e:
        print(f"Error in get_daily_top_sales: {str(e)}")
        return []

# main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
