# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import sqlalchemy
import re
from dotenv import load_dotenv
import os
import requests
import json
from openai import OpenAI

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

# 2) DB 연결 (SQLite)
db_path = "../database/database.db"
engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")

# 환경 변수 로드
load_dotenv()
UPSTAGE_API_KEY = os.getenv('UPSTAGE_API_KEY')

# OpenAI 클라이언트 초기화
client = OpenAI(
    api_key=UPSTAGE_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

# ===== 데이터 로딩 =====
query_sales = """
SELECT
    d.ID,
    p.category AS 대분류,
    p.subsubcategory AS 소분류,
    d.date,
    d.value AS 매출액
FROM daily_sales_data d
JOIN product_info p ON d.ID = p.ID
"""
df_sales = pd.read_sql(query_sales, con=engine)

query_quantity = """
SELECT
    d.ID,
    d.date,
    d.value AS 판매수량
FROM daily_data d
"""
df_quantity = pd.read_sql(query_quantity, con=engine)

inventory_sql = """
SELECT
    p.ID,
    p.product,
    inv.value AS 재고수량
FROM product_inventory inv
JOIN product_info p ON inv.ID = p.ID
"""
inventory_df = pd.read_sql(inventory_sql, con=engine)
inventory_df = inventory_df.rename(columns={'id': 'ID'})

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
    daily_sales_quantity_last = data_quantity[data_quantity['날짜'] == last_date][['ID', '판매수량']]
    daily_sales_quantity_last = daily_sales_quantity_last.rename(columns={'판매수량': '일판매수량'})
else:
    daily_sales_quantity_last = pd.DataFrame(columns=['ID', '일판매수량'])

merged_df = pd.merge(inventory_df, daily_sales_quantity_last, on='ID', how='left')
merged_df['일판매수량'] = merged_df['일판매수량'].fillna(0)
merged_df['남은 재고'] = merged_df['재고수량'] - merged_df['일판매수량']
low_stock_df = merged_df[merged_df['남은 재고'] <= 20]

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
    .groupby(['ID', '월'], as_index=False)['매출액'].sum()
)

result = monthly_data.pivot(index='ID', columns='월', values='매출액').reset_index()
result['ID'] = result['ID'].astype(str)

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
    return daily_df.to_dict(orient="records")

@app.get("/api/weekly")
def get_weekly_data():
    return weekly_data.to_dict(orient="records")

@app.get("/api/monthly")
def get_monthly_data():
    return monthly_sum_df.to_dict(orient="records")

@app.get("/api/categorypie")
def get_category_pie():
    return df_category.to_dict(orient="records")

@app.get("/api/lowstock")
def get_low_stock():
    return low_stock_df.to_dict(orient="records")

@app.get("/api/rising-subcategories")
def get_rising_subcategories():
    return {
        "rise_rate": float(rise_rate),
        "subcat_list": list(subcat_list)  # 넘파이 Index -> list
    }


# (추가) 상·하위 10개 품목
@app.get("/api/topbottom")
def get_topbottom():
    """
    Dash 코드에서:
      if last_month_col:
          top_10_last_month = result.nlargest(10, last_month_col, keep='all').copy()
          top_10_last_month["color"] = reds
          ...
    """
    global result, last_month_col

    if last_month_col:
        top_10_df = result.nlargest(10, last_month_col, keep='all').copy()
        top_10_df["color"] = [reds] * len(top_10_df)

        non_zero_values = result[result[last_month_col] != 0]
        bottom_10_df = non_zero_values.nsmallest(10, last_month_col).copy()
        bottom_10_df["color"] = [blues] * len(bottom_10_df)
    else:
        top_10_df = pd.DataFrame(columns=result.columns)
        bottom_10_df = pd.DataFrame(columns=result.columns)

    top_10_list = top_10_df.to_dict(orient='records')
    bottom_10_list = bottom_10_df.to_dict(orient='records')

    return {
        "top_10": top_10_list,
        "bottom_10": bottom_10_list,
        "last_month_col": last_month_col
    }

# Solar 챗봇 엔드포인트 추가
@app.post("/api/chat")
async def chat_with_solar(message: dict):
    try:
        # KPI 데이터
        kpi_info = {
            "연간 매출": int(annual_sales),
            "일평균 매출": float(daily_avg),
            "주간 평균 매출": float(weekly_avg),
            "월간 평균 매출": float(monthly_avg),
            "전월 대비 변화율": float(monthly_change)
        }

        # 재고 부족 상품 정보
        low_stock_items = low_stock_df[['product', '재고수량', '일판매수량']].to_dict('records')

        # 카테고리별 매출
        category_sales = df_category.to_dict('records')

        # 월간 매출 데이터
        monthly_data = monthly_sum_df.to_dict('records')

        # 일간 매출 데이터
        daily_data = daily_df.tail(7).to_dict('records')  # 최근 7일

        system_message = f"""
        당신은 판매 데이터 분석 AI 어시스턴트입니다. 다음 정보를 기반으로 질문에 답변해주세요:

        1. KPI 현황:
        - 연간 매출: {kpi_info['연간 매출']:,}원
        - 일평균 매출: {kpi_info['일평균 매출']:,.0f}원
        - 주간 평균 매출: {kpi_info['주간 평균 매출']:,.0f}원
        - 월간 평균 매출: {kpi_info['월간 평균 매출']:,.0f}원
        - 전월 대비 변화율: {kpi_info['전월 대비 변화율']:.1f}%

        2. 재고 부족 상품 현황:
        {', '.join([f"{item['product']}(재고: {item['재고수량']}개, 일판매: {item['일판매수량']}개)" for item in low_stock_items])}

        3. 카테고리별 매출:
        {', '.join([f"{cat['대분류']}: {cat['매출액']:,}원" for cat in category_sales])}

        4. 상승률: {rise_rate:.1f}%
        주요 성장 카테고리: {', '.join(subcat_list[:5])}

        5. 최근 일별 매출 현황:
        {', '.join([f"{row['날짜'].strftime('%Y-%m-%d')}: {row['값']:,}원" for row in daily_data])}

        이 데이터를 기반으로 판매, 재고, 매출 관련 질문에 답변해주세요.
        답변할 때는 구체적인 숫자를 포함하고, 필요한 경우 추세나 패턴도 설명해주세요.
        """

        response = client.chat.completions.create(
            model="solar-pro",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": message["content"]}
            ],
            stream=False
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

# main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
