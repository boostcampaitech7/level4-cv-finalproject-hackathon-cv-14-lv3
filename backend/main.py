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
UPSTAGE_API_BASE_URL = os.getenv('UPSTAGE_API_BASE_URL')
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
    all_data = load_all_data("daily_sales_data")
    df = pd.DataFrame(all_data)

    # date 컬럼이 존재하면 datetime으로 변환
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df

# daily_data 테이블의 모든 데이터를 읽어와 DataFrame으로 변환
def load_quantity_data():
    all_data = load_all_data("daily_data")
    df = pd.DataFrame(all_data)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

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
        print(f"Error in get_low_stock: {e!s}")
        return {"error": str(e)}

@app.get("/api/rising-subcategories")
def get_rising_subcategories():
    return {
        "rise_rate": float(rise_rate),
        "subcat_list": list(subcat_list)  # 넘파이 Index -> list
    }

# (추가) 상·하위 10개 품목
@app.get("/api/topbottom")
def get_topbottom():
    if last_month_col:
        # Supabase에서 product_info 데이터 가져오기
        response = supabase.table('product_info').select("id", "sub3").execute()
        product_info = pd.DataFrame(response.data)

        # ID 컬럼을 문자열로 변환
        product_info['id'] = product_info['id'].astype(str)
        product_info = product_info.rename(columns={'id': 'ID', 'sub3': 'Sub3'})

        # top 10
        top_10_df = result.nlargest(10, last_month_col, keep='all').copy()
        top_10_df = top_10_df.rename(columns={'id': 'ID'})
        top_10_df['ID'] = top_10_df['ID'].astype(str)
        top_10_df = pd.merge(top_10_df, product_info, on='ID', how='left')
        top_10_list = top_10_df.to_dict('records')  # DataFrame을 리스트로 변환

        # bottom 10
        non_zero_values = result[result[last_month_col] != 0]
        bottom_10_df = non_zero_values.nsmallest(10, last_month_col).copy()
        bottom_10_df = bottom_10_df.rename(columns={'id': 'ID'})
        bottom_10_df['ID'] = bottom_10_df['ID'].astype(str)
        bottom_10_df = pd.merge(bottom_10_df, product_info, on='ID', how='left')
        bottom_10_list = bottom_10_df.to_dict('records')  # DataFrame을 리스트로 변환
    else:
        top_10_list = []
        bottom_10_list = []

    return {
        "top_10": top_10_list,
        "bottom_10": bottom_10_list,
        "last_month_col": last_month_col
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
           당신은 쇼핑 트렌드 분석 AI 어시스턴트입니다.
           
           다음은 {user_category} 카테고리의 {period} 기간 동안의 월간 트렌드 데이터입니다:
           
           {trend_text}
           
           위 정보를 바탕으로 다음과 같이 응답해주세요:
           1. 카테고리명 명시
           2. 상위 5개 제품의 순위와 이름 나열
           3. 전문적이고 친절한 어조 유지
           """

           # Solar ChatAPI 응답 생성
           response = client.chat.completions.create(
               model="solar-pro",
               messages=[
                   {"role": "system", "content": system_message},
                   {"role": "user", "content": f"{user_category} 카테고리의 트렌드를 알려주세요."}
               ],
               temperature=0.0, 
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
        

@app.get("/api/inventory")
def get_inventory(sort: str = "asc", main: str = None, sub1: str = None, sub2: str = None):
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

        # ✅ 재고 수량(value) 기준 정렬
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

        if df_sales.empty:
            return {}

        # ✅ 전체 데이터 기준으로 월 평균 판매량 계산
        valid_dates = [col for col in df_sales.columns if re.match(r"\d{2}_m\d{2}", col)]
        df_sales["monthly_avg_sales"] = df_sales[valid_dates].mean(axis=1).fillna(0)

        # ✅ 전체 데이터 기준으로 일 평균 판매량 계산
        df_sales["daily_avg_sales"] = df_sales["monthly_avg_sales"] / 30

        # ✅ 최소 재고 기준(ROP) 계산: 일 평균 판매량의 2배 + 10
        df_sales["reorder_point"] = (df_sales["daily_avg_sales"] * 2 + 25).fillna(25)

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