import pandas as pd
import plotly.express as px
import dash
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import sqlalchemy
import re
from dash import dash_table


#####################
# 1) DB 연결 설정 (SQLite)
#####################
# SQLite DB 파일 경로를 지정합니다.
db_path = "database.db"

# SQLAlchemy 엔진 생성 (SQLite의 경우 'sqlite:///[파일경로]')
engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")


#####################
# 2) DB에서 데이터 불러오기
#####################
# daily_sales_data (일자별 매출액)
# product_info (제품 정보: 여기서는 소분류 subsubcategory 예시)
# -> (ID, 소분류, date, 매출액) 형태로 추출
query = """
SELECT
    d.ID,
    p.subsubcategory AS 소분류,  -- product_info 테이블의 소분류 컬럼 (예시)
    d.date,                      -- daily_sales_data 테이블의 날짜
    d.value AS 매출액            -- daily_sales_data 테이블의 매출액
FROM daily_sales_data d
JOIN product_info p ON d.ID = p.ID
"""
df = pd.read_sql(query, con=engine)

# daily_data 테이블에서 판매 수량을 가져오는 쿼리
query_quantity = """
SELECT
    d.ID,
    d.date,
    d.value AS 판매수량  -- 'value'는 판매 수량을 나타냄
FROM daily_data d
"""
df_quantity = pd.read_sql(query_quantity, con=engine)

# 재고 수량 가져오기
inventory_sql = """
SELECT
    p.ID,
    p.product,
    inv.value AS 재고수량
FROM product_inventory inv
JOIN product_info p ON inv.ID = p.ID
"""
inventory_df = pd.read_sql(inventory_sql, con=engine)

#####################
# 3) Pivot (가로형 변환)
#####################
# 현재 df는 (ID, 소분류, date, 매출액) 형태의 '세로형(long)' 데이터.
# 원본 CSV 기반 코드는 "각 날짜가 컬럼으로" 있는 가로형(wide) 형태를 가정하므로
# pivot_table → wide 포맷 → melt → groupby(월별/주별) 등 동일 작업

df['date'] = df['date'].astype(str)  # 날짜를 문자열로 변환
pivoted = df.pivot_table(
    index=['ID', '소분류'],    # 행
    columns='date',           # 열(날짜)
    values='매출액',          # 값
    aggfunc='sum'
).fillna(0).reset_index()

# '2023-01-01' 처럼 날짜 형식으로 된 컬럼만 추출
date_columns = [col for col in pivoted.columns if re.match(r'^20\d{2}-\d{2}-\d{2}$', col)]

# melt를 통해 다시 (ID, 소분류, 날짜, 매출액) 세로형으로 변환
data = pivoted.melt(
    id_vars=['ID', '소분류'],
    value_vars=date_columns,
    var_name='날짜',
    value_name='매출액'
)

# 판매 수량 데이터에 대해 pivot_table을 사용하여 가로형 데이터로 변환
df_quantity['date'] = df_quantity['date'].astype(str)  # 날짜를 문자열로 변환
pivoted_quantity = df_quantity.pivot_table(
    index=['ID'],  # ID별로 그룹화
    columns='date',  # 날짜를 열로
    values='판매수량',  # 판매 수량을 값으로
    aggfunc='sum'
).fillna(0).reset_index()

# '2023-01-01' 처럼 날짜 형식으로 된 컬럼만 추출
date_columns = [col for col in pivoted_quantity.columns if col.startswith('20')]

# melt를 통해 다시 (ID, 날짜, 판매수량) 형태로 변환
data_quantity = pivoted_quantity.melt(
    id_vars=['ID'],
    value_vars=date_columns,
    var_name='날짜',
    value_name='판매수량'
)

#####################
# 4) 월별, 일별, 주별 집계 및 KPI 계산
#####################
# - (1) 월별로 sum → pivot → 상/하위 10개
# - (2) 일별 합계, 주별 합계, 월별 합계 → KPI 계산
# - (3) 매출 급상승 품목 계산

# (1) 월별 합계
monthly_data = (
    data.assign(월=lambda df: pd.to_datetime(df['날짜']).dt.to_period('M').astype(str))
    .groupby(['ID', '월'], as_index=False)['매출액'].sum()
)

# 월별 판매수량 계산
monthly_sales_quantity = (
    data_quantity.assign(월=lambda df: pd.to_datetime(df['날짜']).dt.to_period('M').astype(str))
    .groupby(['ID', '월'], as_index=False)['판매수량'].sum()
)

# 가장 최근 월의 판매 수량을 추출
last_month = monthly_sales_quantity['월'].max()
monthly_sales_quantity_last = monthly_sales_quantity[monthly_sales_quantity['월'] == last_month][['ID', '판매수량']]
monthly_sales_quantity_last = monthly_sales_quantity_last.rename(columns={'판매수량': '월판매수량'})

# ID별, 월별 피벗
result = monthly_data.pivot(index='ID', columns='월', values='매출액').reset_index()
result['ID'] = result['ID'].astype(str)

# 가장 마지막 달(컬럼) 찾기
if len(result.columns) > 1:
    last_month = result.columns[-1]  # 예: '2023-08'
else:
    # 만약 컬럼이 부족하면 임시 예외 처리
    last_month = None

#####################
# 월별 판매 수량과 재고 수량 병합
#####################

# 월 판매 수량 데이터와 재고 수량 데이터를 병합
merged_df = pd.merge(inventory_df, monthly_sales_quantity_last, on='ID', how='left')

# 7) 남은 재고 계산 (재고수량 - 월판매수량)
merged_df['남은 재고'] = merged_df['재고수량'] - merged_df['월판매수량']
low_stock_df = merged_df[merged_df['남은 재고'] <= 20]

# 빨간/파란 계열 색상
reds = [
    '#D14B4B', '#E22B2B', '#E53A3A', '#F15D5D', '#F67878',
    '#F99A9A', '#FBB6B6', '#FDC8C8', '#FEE0E0', '#FEEAEA'
]
blues = [
    '#B0D6F1', '#A5C9E9', '#99BCE1', '#8DB0D9', '#81A4D1',
    '#7498C9', '#688BC1', '#5C7FB9', '#5073B1', '#4567A9'
]

if last_month:
    # 상위 10개
    top_10_last_month = result.nlargest(10, last_month, keep='all').copy()
    top_10_last_month["color"] = reds

    # 하위 10개
    non_zero_values = result[result[last_month] != 0]  # 0이 아닌 값만 필터링
    bottom_10_last_month = non_zero_values.nsmallest(10, last_month).copy()
    bottom_10_last_month["color"] = blues
else:
    # last_month가 없으면 빈 데이터프레임
    top_10_last_month = pd.DataFrame(columns=result.columns)
    bottom_10_last_month = pd.DataFrame(columns=result.columns)

# (2) 일별, 주별, 월별 합계
daily_df = (
    data.groupby('날짜', as_index=False)['매출액']
    .sum()
    .rename(columns={'매출액': '값'})
)
daily_df['날짜'] = pd.to_datetime(daily_df['날짜'])

# 주간, 월간 계산
daily_df['주간'] = daily_df['날짜'].dt.to_period('W').apply(lambda r: r.start_time)
daily_df['월간'] = daily_df['날짜'].dt.to_period('M').apply(lambda r: r.start_time)

weekly_data = daily_df.groupby('주간', as_index=False)['값'].sum()
monthly_sum_df = daily_df.groupby('월간', as_index=False)['값'].sum()

# (필요시) 날짜 필터링
daily_data = daily_df[daily_df['날짜'] >= '2023-02-01']
weekly_data = weekly_data[weekly_data['주간'] >= pd.to_datetime('2022-11-01')]

# 최근 12개월의 연간 매출
recent_12_months = monthly_sum_df.tail(12)
annual_sales = recent_12_months['값'].sum()

# KPI 계산
kpi_values = {
    "총 합계 (연간 매출)": annual_sales,
    "일간 평균": daily_data['값'].mean() if not daily_data.empty else 0,
    "주간 평균": weekly_data['값'].mean() if not weekly_data.empty else 0,
    "월간 평균": monthly_sum_df['값'].mean() if not monthly_sum_df.empty else 0,
    "일간 매출": daily_data['값'].iloc[-1] if not daily_data.empty else 0,
    "주간 매출": weekly_data['값'].iloc[-1] if not weekly_data.empty else 0,
    "월간 매출": monthly_sum_df['값'].iloc[-1] if not monthly_sum_df.empty else 0
}

# 월간 매출 변화율
if len(monthly_sum_df) >= 2:
    last_month_sales = monthly_sum_df['값'].iloc[-1]
    second_last_month_sales = monthly_sum_df['값'].iloc[-2]
    if second_last_month_sales != 0:
        monthly_change = ((last_month_sales - second_last_month_sales) / second_last_month_sales) * 100
    else:
        monthly_change = 0
else:
    monthly_change = 0
kpi_values["월간 매출 변화"] = f"{monthly_change:.2f}%"


# (3) 매출 급상승 품목 (소분류 기준)
data["소분류"] = data["소분류"].fillna('기타')
pivot_subcat = data.pivot_table(
    index='소분류',
    columns='날짜',
    values='매출액',
    aggfunc='sum'
).fillna(0)

all_dates = sorted(pivot_subcat.columns)
if len(all_dates) >= 2:
    last_date, second_last_date = all_dates[-1], all_dates[-2]
    last_sum = pivot_subcat[last_date].sum()
    second_sum = pivot_subcat[second_last_date].sum()
    if second_sum != 0:
        pivot_subcat["매출 상승폭"] = ((last_sum - second_sum) / second_sum) * 100
    else:
        pivot_subcat["매출 상승폭"] = 0
else:
    pivot_subcat["매출 상승폭"] = 0

top_20_items = pivot_subcat["매출 상승폭"].nlargest(6).reset_index()
top_20_items.columns = ['소분류', '매출 상승폭']
item_sales = top_20_items[['소분류']].values.tolist()

##########################
# Dash 애플리케이션
##########################
app = Dash(__name__)

# 스타일 정의
PAGE_STYLE = {
    "background-color": "#f4f4f9",
    "padding": "20px",
    "font-family": "Arial, sans-serif"
}
TITLE_STYLE = {
    "text-align": "center",
    "font-size": "28px",
    "margin-bottom": "40px",
    "color": "#333",
    "font-weight": "bold",
    "margin-top": "50px",
    "margin-bottom": "50px"
}
KPI_CARD_STYLE = {
    "display": "inline-block",
    "width": "13%",  # 각 카드 크기 조정
    "margin": "10px",
    "padding": "15px",
    "text-align": "center",
    "border-radius": "10px",
    "background-color": "#ffffff",
    "box-shadow": "0px 4px 10px rgba(0, 0, 0, 0.1)"
}
ROW_STYLE = {
    "display": "flex",
    "flex-wrap": "wrap",
    "justify-content": "space-between"
}
GRAPH_STYLE = {
    "margin": "20px",
    "padding": "20px",
    "background-color": "#ffffff",
    "border-radius": "10px",
    "box-shadow": "0px 4px 10px rgba(0, 0, 0, 0.1)"
}
SECTION_STYLE = {
    "backgroundColor": "white",  # 흰색 배경
    "borderRadius": "15px",  # 둥근 테두리
    "boxShadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",  # 부드러운 그림자 효과
    "padding": "20px",  # 내부 여백
    "marginBottom": "20px",  # 각 섹션 간 여백
    "border": "1px solid #e0e0e0",  # 연한 회색 테두리
    'width': '48%',
    'display': 'inline-block',
    'vertical-align': 'top'
}
KPI_ALL_STYLE = {
    "marginTop":"30px",
    "marginBottom": "30px",  # 각 섹션 간 여백
    "border": "1px solid #e0e0e0",  # 연한 회색 테두리
    "borderRadius": "15px",
    "box-shadow": "0px 4px 10px rgba(0, 0, 0, 0.1)",
    'width': '96%',  # 가로 크기 조정
    'display': 'flex',  # 부모 div를 flex로 설정
    'flex-direction': 'column',  # 세로 정렬을 위한 flex 방향 설정
    'align-items': 'center',  # 세로 중앙 정렬
    'justify-content': 'center',  # 수평 중앙 정렬
    'padding': '20px',  # 내부 여백 추가
    'margin-left': 'auto',  # 중앙 정렬
    'margin-right': 'auto',  # 중앙 정렬
}

# 추가로 사용되는 스타일
KPI_CARD_STYLE_LEFT = {
    "display": "inline-block",
    "width": "22%",  # 각 카드 크기 조정
    "margin": "10px",
    "padding": "15px",
    "text-align": "center",
    "border-radius": "10px",
    "background-color": "#ffffff",
    "box-shadow": "0px 4px 10px rgba(0, 0, 0, 0.1)"
}
KPI_CARD_STYLE_RIGHT = {
    "display": "inline-block",
    "width": "22%",  # 각 카드 크기 조정
    "margin": "10px",
    "padding": "15px",
    "text-align": "center",
    "border-radius": "10px",
    "background-color": "#ffffff",
    "box-shadow": "0px 4px 10px rgba(0, 0, 0, 0.1)"
}

KPI_TITLE_STYLE = {
    "background-color": "#f4f4f4",  # 연한 회색 배경
    "padding": "10px",
    "border-radius": "10px 10px 0 0",  # 위쪽 모서리만 둥글게
    "text-align": "center",
    "color": "#333",  # 제목 텍스트 색상
    "font-size": "18px",
    "font-weight": "bold"
}

KPI_VALUE_STYLE = {
    "text-align": "center",
    "font-size": "24px",
    "color": "#333",
}

def format_currency(value):
    return f"₩{value:,.0f}원"

def get_monthly_change_color(value):
    if value > 0:
        return "red"
    elif value < 0:
        return "blue"
    else:
        return "#333"

# 월간 매출 변화
monthly_change_value = float(kpi_values["월간 매출 변화"].strip('%'))
KPI_MONTHLY_CHANGE_STYLE = {
    "text-align": "center",
    "font-size": "24px",
    "color": get_monthly_change_color(monthly_change_value),
}

# 매출 급상승 품목 배너 스타일
item_style = {
    "width": "350px",  # 아이템 가로 크기 늘리기
    "height": "160px",  # 아이템 세로 크기
    "display": "inline-flex",
    "justify-content": "center",
    "align-items": "center",
    "font-size": "20px",
    "font-weight": "bold",
    "color": "#fff",
    "background-color": "#FF7F50",
    "border-radius": "15px",  # 둥근 모서리
    "box-shadow": "0 8px 25px rgba(0, 0, 0, 0.2)",  # 부드럽고 강한 그림자 효과
    "margin-right": "30px",  # 간격 늘림
}

# 그래프 그리기용 파스텔 색상
pastel_colors = px.colors.qualitative.Pastel

###################
# 레이아웃 구성
###################
app.layout = html.Div([
    html.H1("데이터 대시보드", style=TITLE_STYLE),

    # KPI 영역 (첫 번째 줄)
    html.Div([
        html.Div([
            html.H3("연간 매출 (최근 12개월)", style=KPI_TITLE_STYLE),
            html.H2(format_currency(kpi_values['총 합계 (연간 매출)']), style=KPI_VALUE_STYLE)
        ], style=KPI_CARD_STYLE_LEFT),
        html.Div([
            html.H3("일간 매출", style=KPI_TITLE_STYLE),
            html.H2(format_currency(kpi_values['일간 매출']), style=KPI_VALUE_STYLE)
        ], style=KPI_CARD_STYLE_LEFT),
        html.Div([
            html.H3("주간 매출", style=KPI_TITLE_STYLE),
            html.H2(format_currency(kpi_values['주간 매출']), style=KPI_VALUE_STYLE)
        ], style=KPI_CARD_STYLE_LEFT),
        html.Div([
            html.H3("월간 매출", style=KPI_TITLE_STYLE),
            html.H2(format_currency(kpi_values['월간 매출']), style=KPI_VALUE_STYLE)
        ], style=KPI_CARD_STYLE_LEFT),
    ], style=ROW_STYLE),

    # KPI 영역 (두 번째 줄)
    html.Div([
        html.Div([
            html.H3("월간 매출 변화", style=KPI_TITLE_STYLE),
            html.H2(kpi_values["월간 매출 변화"], style=KPI_MONTHLY_CHANGE_STYLE)
        ], style=KPI_CARD_STYLE_RIGHT),
        html.Div([
            html.H3("트렌드", style=KPI_TITLE_STYLE),
            html.H2("")  # 실제 내용은 필요시 추가
        ], style=KPI_CARD_STYLE_RIGHT),
        html.Div([
            html.H3("기타", style=KPI_TITLE_STYLE),
            html.H2("")  # 실제 내용은 필요시 추가
        ], style=KPI_CARD_STYLE_RIGHT),
        html.Div([
            html.H3("??", style=KPI_TITLE_STYLE),
            html.H2("")  # 실제 내용은 필요시 추가
        ], style=KPI_CARD_STYLE_RIGHT),
    ], style=ROW_STYLE),

    # 일간, 주간, 월간 그래프 섹션
    html.Div([
        # 일간 그래프
        html.Div([
            dcc.Graph(
                id='daily-graph',
                figure=px.line(
                    daily_data, x='날짜', y='값', title='일간 데이터',
                    template="plotly_white",
                    line_shape="linear",
                    color_discrete_sequence=[pastel_colors[0]]
                ).update_traces(
                    line=dict(width=3),
                    fill='tozeroy',
                    fillcolor='rgba(187, 212, 255, 0.15)'
                ).update_layout(
                    title_x=0.5,
                    title_font=dict(size=18, color='#333', family="Arial, sans-serif", weight="bold"),
                    yaxis_title='매출', 
                    xaxis_title='일자',
                    xaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # x축 타이틀 굵게
                    yaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold")  # y축 타이틀 굵게 
                )
            )
        ], style=GRAPH_STYLE),

        # 주간 그래프
        html.Div([
            dcc.Graph(
                id='weekly-graph',
                figure=px.line(
                    weekly_data, x='주간', y='값', title='주간 데이터',
                    template="plotly_white",
                    line_shape="linear",
                    color_discrete_sequence=[pastel_colors[1]]
                ).update_traces(
                    line=dict(width=3),
                    fill='tozeroy',
                    fillcolor='rgba(179, 220, 179, 0.1)'
                ).update_layout(
                    title_x=0.5,
                    title_font=dict(size=18, color='#333', family="Arial, sans-serif", weight="bold"),
                    yaxis_title='매출',
                    xaxis_title='주간',
                    xaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # x축 타이틀 굵게
                    yaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold")  # y축 타이틀 굵게 
                )
            )
        ], style=GRAPH_STYLE),

        # 월간 그래프
        html.Div([
            dcc.Graph(
                id='monthly-graph',
                figure=px.line(
                    monthly_sum_df, x='월간', y='값', title='월간 데이터',
                    template="plotly_white",
                    line_shape="linear",
                    color_discrete_sequence=[pastel_colors[2]]
                ).update_traces(
                    line=dict(width=3),
                    fill='tozeroy',
                    fillcolor='rgba(244, 178, 247, 0.1)'
                ).update_layout(
                    title_x=0.5,
                    title_font=dict(size=18, color='#333', family="Arial, sans-serif", weight="bold"),
                    yaxis_title='매출',
                    xaxis_title='월간',
                    xaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # x축 타이틀 굵게
                    yaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold")  # y축 타이틀 굵게 
                )
            )
        ], style=GRAPH_STYLE),
    ], style=ROW_STYLE),

    # 매출 급상승 품목 섹션
    html.Div(
        children=[
            html.H1("매출 급상승 품목 ⚡", style=TITLE_STYLE),
            html.Div(
                children=[html.Div(f"{item[0]}", style={**item_style, "margin": "5px 10px 20px"}) for item in item_sales],
                style={
                    "display": "flex",
                    "flex-direction": "row",
                    "overflow": "hidden",
                    "width": "70%",
                    "margin-left": "auto",
                    "margin-right": "auto",
                    "justify-content": "center",
                }
            )
        ],
        style=KPI_ALL_STYLE
    ),

    # 상위/하위 10개 ID 섹션
    html.Div([
        html.Div([
            dcc.Graph(
                id='top-10-graph',
                figure=px.bar(
                    top_10_last_month.sort_values(by=last_month, ascending=True),
                    x=last_month,
                    y='ID',
                    orientation='h',
                    color='color',
                    color_discrete_map='identity',
                    title=f'{last_month} 월 매출 상위 10개 ID' if last_month else '상위 10개 (데이터 부족)',
                    template="plotly_white",
                ).update_layout(
                    title_x=0.5,
                    title_font=dict(size=18, color='#333', family="Arial, sans-serif", weight="bold"),
                    yaxis_title='ID',
                    xaxis_title='매출액',
                    xaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # x축 타이틀 굵게
                    yaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # y축 타이틀 굵게 
                    margin=dict(l=50, r=50, t=200, b=100),
                    height=600,
                    plot_bgcolor='white'
                )
            )
        ], style=SECTION_STYLE),

        html.Div([
            dcc.Graph(
                id='bottom-10-graph',
                figure=px.bar(
                    bottom_10_last_month.sort_values(by=last_month, ascending=True),
                    x=last_month,
                    y='ID',
                    orientation='h',
                    color='color',
                    color_discrete_map='identity',
                    title=f'{last_month} 월 매출 하위 10개 ID' if last_month else '하위 10개 (데이터 부족)',
                    template="plotly_white",
                ).update_layout(
                    title_x=0.5,
                    title_font=dict(size=18, color='#333', family="Arial, sans-serif", weight="bold"),
                    yaxis_title='ID',
                    xaxis_title='매출액',
                    xaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # x축 타이틀 굵게
                    yaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # y축 타이틀 굵게 
                    margin=dict(l=50, r=50, t=200, b=100),
                    height=600,
                    plot_bgcolor='white'
                )
            )
        ], style=SECTION_STYLE),
    ], style=ROW_STYLE),
    # 트렌드 상품 및 리콜 상품 섹션
    html.Div([
        html.Div(
            children=[
                html.H2("트렌드 상품", style={"text-align": "center", "font-weight": "bold"}),
                html.Div(
                    children=[
                    html.Img(
                        src="https://img1.daumcdn.net/thumb/R720x0.q80/?scode=mtistory2&fname=https%3A%2F%2Ft1.daumcdn.net%2Fcfile%2Ftistory%2F9994274C5AE78D7305",  # 이미지 URL (예: 대체 이미지 URL)
                        style={
                            "width": "400px",  # 이미지 너비
                            "height": "400px",  # 이미지 높이
                            "object-fit": "contain",  # 이미지 비율 유지하며 공간 맞춤
                            "margin": "auto",  # 가운데 정렬
                            "display": "block",  # 블록 요소로 설정하여 중앙 정렬
                        }
                    )
                ],
                    style={  # 내용 없는 박스
                    "height": "600px",
                    "display": "flex",
                    "justify-content": "center",
                    "align-items": "center",
                }),
            ],
            style=SECTION_STYLE
        ),
        html.Div(
            children=[
                html.H2("리콜 상품", style={"text-align": "center", "font-weight": "bold"}),
                html.Div(
                    children=[
                    html.Img(
                        src="https://i.pinimg.com/originals/af/51/13/af5113b12c2e068f9f675dfbed16e4ad.gif",
                        style={
                            "width": "400px",  # 이미지 너비
                            "height": "400px",  # 이미지 높이
                            "object-fit": "contain",  # 이미지 비율 유지하며 공간 맞춤
                            "margin": "auto",  # 가운데 정렬
                            "display": "block",  # 블록 요소로 설정하여 중앙 정렬
                        }
                    )
                ],
                    style={  # 내용 없는 박스
                    "height": "600px",
                    "display": "flex",
                    "justify-content": "center",
                    "align-items": "center",
                }),
            ],
            style=SECTION_STYLE
        ),
    ], style=ROW_STYLE),
        html.Div([
            # 왼쪽 칸 (40%)
            html.Div(
                children=[
                    html.H2("파이그래프 추가 예정?", style={"text-align": "center", "font-weight": "bold"}),
                    # 원하는 내용 추가 가능
                    
                ],
                style={**SECTION_STYLE, "width": "38%", "padding": "20px", "border": "1px solid #e0e0e0", "margin": "0", "height": "600px"}  # 40% 크기, SECTION_STYLE을 확장
            ),
            
            # 오른쪽 칸에 테이블을 표시하는 부분
            html.Div(
                children=[
                    html.H2("재고수량", style={"text-align": "center", "font-weight": "bold"}),
                    
                    # Dash 테이블을 사용하여 필터링된 데이터 표로 출력
                    dash_table.DataTable(
                        id='low-stock-table',
                        columns=[
                            {"name": "ID", "id": "ID"},
                            {"name": "상품명", "id": "product"},
                            {"name": "재고수량", "id": "재고수량"},
                            {"name": "월판매수량", "id": "월판매수량"},
                            {"name": "남은 재고", "id": "남은 재고"},
                        ],
                        data=low_stock_df.to_dict('records'),  # DataFrame을 dict 형태로 변환하여 표에 표시
                        style_table={'height': '350px', 'overflowY': 'auto'},  # 테이블 크기 조정
                        style_cell={
                            'textAlign': 'center',
                            'minWidth': '100px', 'width': '150px', 'maxWidth': '200px',
                        },
                    ),
                ],
                style={**SECTION_STYLE, "width": "58%", "padding": "20px", "border": "1px solid #e0e0e0", "margin": "0", "height": "600px"}  # 60% 크기, SECTION_STYLE을 확장
                        ),
                    ], style=ROW_STYLE)  # 두 칸을 가로로 나열
            ], style=PAGE_STYLE)


if __name__ == '__main__':
    app.run_server(debug=True)
