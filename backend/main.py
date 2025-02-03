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
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# OpenAI 클라이언트 초기화
client = OpenAI(
    api_key=UPSTAGE_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

# ===== 데이터 로딩 =====
def load_sales_data():
    response = supabase.from_('daily_sales_data').select("""
        id,
        date,
        value,
        product_info (
            sub1,
            sub3
        )
    """).execute()
    df = pd.DataFrame(response.data)
    
    # 중첩된 product_info 데이터를 풀어서 새로운 컬럼으로 만듦
    df['대분류'] = df['product_info'].apply(lambda x: x['sub1'] if x else None)
    df['소분류'] = df['product_info'].apply(lambda x: x['sub3'] if x else None)
    
    # product_info 컬럼 제거
    df = df.drop('product_info', axis=1)
    
    return df

def load_quantity_data():
    response = supabase.table('daily_data').select(
        "id",
        "date",
        "value"
    ).execute()
    return pd.DataFrame(response.data)

def load_inventory_data():
    response = supabase.from_('product_inventory').select("""
        id,
        value,
        product_info (
            main,
            sub3
        )
    """).execute()
    return pd.DataFrame(response.data)

# 데이터 로드
df_sales = load_sales_data()
df_quantity = load_quantity_data()
inventory_df = load_inventory_data()

# 컬럼명 변경
df_sales = df_sales.rename(columns={'value': '매출액'})
df_quantity = df_quantity.rename(columns={'value': '판매수량'})
inventory_df = inventory_df.rename(columns={'value': '재고수량'})

# 문자열 변환
df_sales['date'] = df_sales['date'].astype(str)
df_quantity['date'] = df_quantity['date'].astype(str)

# ===== Dash 코드에서 하던 전처리 로직 =====

data = df_sales.copy()
data_quantity = df_quantity.copy()

data['날짜'] = pd.to_datetime(data['date'])
data_quantity['날짜'] = pd.to_datetime(data_quantity['date'])

# 일간 합계
daily_df = data.groupby('날짜', as_index=False)['매출액'].sum()
daily_df.rename(columns={'매출액': '값'}, inplace=True)

# 주간 집계
daily_df['주간'] = daily_df['날짜'].dt.to_period('W').apply(lambda r: r.start_time)
weekly_data = daily_df.groupby('주간', as_index=False)['값'].sum()

# 월간 집계
daily_df['월간'] = daily_df['날짜'].dt.to_period('M').apply(lambda r: r.start_time)
monthly_sum_df = daily_df.groupby('월간', as_index=False)['값'].sum()

# 최근 12개월 합계를 "연간 매출"로 가정
recent_12_months = monthly_sum_df.tail(12)
annual_sales = recent_12_months['값'].sum()

# KPI
daily_avg = daily_df['값'].mean() if not daily_df.empty else 0
weekly_avg = weekly_data['값'].mean() if not weekly_data.empty else 0
monthly_avg = monthly_sum_df['값'].mean() if not monthly_sum_df.empty else 0
last_daily = daily_df['값'].iloc[-1] if not daily_df.empty else 0
last_weekly = weekly_data['값'].iloc[-1] if not weekly_data.empty else 0
last_monthly = monthly_sum_df['값'].iloc[-1] if not monthly_sum_df.empty else 0

# 월간 변화율
if len(monthly_sum_df) >= 2:
    lm_sales = monthly_sum_df['값'].iloc[-1]
    slm_sales = monthly_sum_df['값'].iloc[-2]
    if slm_sales != 0:
        monthly_change = ((lm_sales - slm_sales) / slm_sales) * 100
    else:
        monthly_change = 0
else:
    monthly_change = 0

# 카테고리별(대분류) 매출
df_category = df_sales.groupby('대분류', as_index=False)['매출액'].sum()

# 재고수량 및 일일판매수량
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
data["소분류"] = data["소분류"].fillna('기타')
pivot_subcat = data.groupby(['소분류', '날짜'])['매출액'].sum().unstack().fillna(0)

all_dates = sorted(pivot_subcat.columns)
if len(all_dates) >= 2:
    last_date, second_last_date = all_dates[-1], all_dates[-2]
    last_sum = pivot_subcat[last_date].sum()
    second_sum = pivot_subcat[second_last_date].sum()
    if second_sum != 0:
        rise_rate = ((last_sum - second_sum) / second_sum) * 100
    else:
        rise_rate = 0
else:
    rise_rate = 0

subcat_list = pivot_subcat.sum(axis=1).sort_values(ascending=False).head(10).index.tolist()


# ---------- (추가) 상위/하위 10개 계산 ----------
# Dash 코드에서:
# monthly_data -> result
# result = monthly_data.pivot(index='ID', columns='월', values='매출액').reset_index()
# last_month_col = result.columns[-1] ...
# top_10_last_month = result.nlargest(...)
# ...

# pivot
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

reds = [
    '#D14B4B', '#E22B2B', '#E53A3A', '#F15D5D', '#F67878',
    '#F99A9A', '#FBB6B6', '#FDC8C8', '#FEE0E0', '#FEEAEA'
]
blues = [
    '#B0D6F1', '#A5C9E9', '#99BCE1', '#8DB0D9', '#81A4D1',
    '#7498C9', '#688BC1', '#5C7FB9', '#5073B1', '#4567A9'
]

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
    filtered_daily = daily_df[daily_df['날짜'] >= '2023-01-01']
    return filtered_daily.to_dict(orient="records")

@app.get("/api/weekly")
def get_weekly_data():
    # 2022년 10월 이후 데이터만 필터링
    filtered_weekly = weekly_data[weekly_data['주간'] >= '2022-10-01']
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

# main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)