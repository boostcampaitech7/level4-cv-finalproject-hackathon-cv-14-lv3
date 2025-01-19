import pandas as pd
import plotly.express as px
import dash
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import sqlalchemy
import re


#####################
# 1) DB 연결 설정 (SQLite)
#####################
# SQLite DB 파일 경로를 지정합니다.
db_path = "D:/CV_Final_Hackarton/level4-cv-finalproject-hackathon-cv-14-lv3-1/database/database.db"

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

# ID별, 월별 피벗
result = monthly_data.pivot(index='ID', columns='월', values='매출액').reset_index()
result['ID'] = result['ID'].astype(str)

# 가장 마지막 달(컬럼) 찾기
if len(result.columns) > 1:
    last_month = result.columns[-1]  # 예: '2023-08'
else:
    # 만약 컬럼이 부족하면 임시 예외 처리
    last_month = None

# 빨간/파란 계열 색상
reds = [
    '#D14B4B', '#E22B2B', '#E53A3A', '#F15D5D', '#F67878',
    '#F99A9A', '#FBB6B6', '#FDC8C8', '#FEE0E0', '#FEEAEA'
]
blues = [
    '#0000FF', '#0000E6', '#0000CC', '#0000B3', '#000099',
    '#00007F', '#000066', '#00004C', '#000033', '#00001A'
]

if last_month:
    # 상위 10개
    top_10_last_month = result.nlargest(10, last_month, keep='all').copy()
    top_10_last_month["color"] = reds

    # 하위 10개
    bottom_10_last_month = result.nsmallest(10, last_month).copy()
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
    "width": "23%",  # 각 카드 크기 조정
    "margin": "10px",
    "padding": "15px",
    "text-align": "center",
    "border-radius": "10px",
    "background-color": "#ffffff",
    "box-shadow": "0px 4px 10px rgba(0, 0, 0, 0.1)"
}
KPI_CARD_STYLE_RIGHT = {
    "display": "inline-block",
    "width": "23%",  # 각 카드 크기 조정
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
                    yaxis_title='매출',
                    xaxis_title='일자'
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
                    yaxis_title='매출',
                    xaxis_title='주간'
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
                    yaxis_title='매출',
                    xaxis_title='월간'
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
                    yaxis_title='ID',
                    xaxis_title='매출액',
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
                    yaxis_title='ID',
                    xaxis_title='매출액',
                    margin=dict(l=50, r=50, t=200, b=100),
                    height=600,
                    plot_bgcolor='white'
                )
            )
        ], style=SECTION_STYLE),
    ], style=ROW_STYLE)
], style=PAGE_STYLE)


if __name__ == '__main__':
    app.run_server(debug=True)
