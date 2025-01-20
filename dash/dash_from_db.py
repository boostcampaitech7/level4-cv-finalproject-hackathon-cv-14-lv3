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
db_path = "database.db"
engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")

#####################
# 2) (매출) DB에서 데이터 불러오기
#####################
# daily_sales_data + product_info => (ID, 소분류, date, 매출액)
sales_query = """
SELECT
    d.ID,
    p.subsubcategory AS 소분류,
    d.date,
    d.value AS 매출액
FROM daily_sales_data d
JOIN product_info p ON d.ID = p.ID
"""
df = pd.read_sql(sales_query, con=engine)

#####################
# 3) 매출 Pivot → Melt
#####################
df['date'] = df['date'].astype(str)
pivoted = df.pivot_table(
    index=['ID', '소분류'],
    columns='date',
    values='매출액',
    aggfunc='sum'
).fillna(0).reset_index()

date_columns = [col for col in pivoted.columns if re.match(r'^20\d{2}-\d{2}-\d{2}$', col)]
data = pivoted.melt(
    id_vars=['ID', '소분류'],
    value_vars=date_columns,
    var_name='날짜',
    value_name='매출액'
)

#####################
# 4) 월별, 일별, 주별 집계 및 KPI 계산 (매출)
#####################
# (1) 월별 합계
monthly_data = (
    data.assign(월=lambda df: pd.to_datetime(df['날짜']).dt.to_period('M').astype(str))
    .groupby(['ID', '월'], as_index=False)['매출액'].sum()
)
result = monthly_data.pivot(index='ID', columns='월', values='매출액').reset_index()
result['ID'] = result['ID'].astype(str)

if len(result.columns) > 1:
    last_month = result.columns[-1]
else:
    last_month = None

reds = [
    '#D14B4B', '#E22B2B', '#E53A3A', '#F15D5D', '#F67878',
    '#F99A9A', '#FBB6B6', '#FDC8C8', '#FEE0E0', '#FEEAEA'
]
blues = [
    '#0000FF', '#0000E6', '#0000CC', '#0000B3', '#000099',
    '#00007F', '#000066', '#00004C', '#000033', '#00001A'
]

if last_month:
    top_10_last_month = result.nlargest(10, last_month, keep='all').copy()
    top_10_last_month["color"] = reds
    bottom_10_last_month = result.nsmallest(10, last_month).copy()
    bottom_10_last_month["color"] = blues
else:
    top_10_last_month = pd.DataFrame(columns=result.columns)
    bottom_10_last_month = pd.DataFrame(columns=result.columns)

# (2) 일별·주별·월별 합계
daily_df = (
    data.groupby('날짜', as_index=False)['매출액']
    .sum()
    .rename(columns={'매출액': '값'})
)
daily_df['날짜'] = pd.to_datetime(daily_df['날짜'])
daily_df['주간'] = daily_df['날짜'].dt.to_period('W').apply(lambda r: r.start_time)
daily_df['월간'] = daily_df['날짜'].dt.to_period('M').apply(lambda r: r.start_time)

weekly_data = daily_df.groupby('주간', as_index=False)['값'].sum()
monthly_sum_df = daily_df.groupby('월간', as_index=False)['값'].sum()

# 기간 필터 (예시)
daily_data = daily_df[daily_df['날짜'] >= '2023-02-01']
weekly_data = weekly_data[weekly_data['주간'] >= pd.to_datetime('2022-11-01')]

recent_12_months = monthly_sum_df.tail(12)
annual_sales = recent_12_months['값'].sum()

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


#####################
# (4) 재고 현황 추가
#####################
inventory_sql = """
SELECT
    p.ID,
    p.product,
    p.brand,
    inv.value as 재고수량
FROM product_inventory inv
JOIN product_info p ON inv.ID = p.ID
"""
inventory_df = pd.read_sql(inventory_sql, con=engine)

# 재고가 100 이하인 품목 중 가장 적은 순 (최대 10개)
low_stock_df = inventory_df[inventory_df['재고수량'] <= 100].copy()
low_stock_df = low_stock_df.sort_values(by='재고수량', ascending=True)
low_stock_top10 = low_stock_df.head(10)

low_stock_fig = px.bar(
    low_stock_top10,
    x='재고수량',
    y='product',
    orientation='h',
    title='주문이 필요한 품목',
    template="plotly_white",
    color='재고수량',
    color_continuous_scale='Reds'
).update_layout(
    title_x=0.5,
    xaxis_title='재고수량',
    yaxis_title='제품명',
    height=600
)


#####################
# (추가) (5) "판매수량" 기준 상/하위 10개
#####################
# 1) daily_data + product_info => (ID, 소분류, 날짜, 판매수량)
quantity_query = """
SELECT
    q.ID,
    p.subsubcategory AS 소분류,
    q.date,
    q.value AS 판매수량
FROM daily_data q
JOIN product_info p ON q.ID = p.ID
"""
df_qty = pd.read_sql(quantity_query, con=engine)
df_qty['date'] = df_qty['date'].astype(str)

# Pivot + melt
pivoted_qty = df_qty.pivot_table(
    index=['ID','소분류'],
    columns='date',
    values='판매수량',
    aggfunc='sum'
).fillna(0).reset_index()

date_cols_qty = [c for c in pivoted_qty.columns if re.match(r'^20\d{2}-\d{2}-\d{2}$', c)]
data_qty = pivoted_qty.melt(
    id_vars=['ID','소분류'],
    value_vars=date_cols_qty,
    var_name='날짜',
    value_name='판매수량'
)

# 월별 집계
monthly_data_qty = (
    data_qty.assign(월=lambda df: pd.to_datetime(df['날짜']).dt.to_period('M').astype(str))
    .groupby(['ID','월'], as_index=False)['판매수량'].sum()
)
result_qty = monthly_data_qty.pivot(index='ID', columns='월', values='판매수량').reset_index()
result_qty['ID'] = result_qty['ID'].astype(str)

if len(result_qty.columns) > 1:
    last_month_qty = result_qty.columns[-1]
else:
    last_month_qty = None

if last_month_qty:
    # 0이 아닌 항목만 필터링 => 의미 있는 하위 품목 추출
    nonzero_qty = result_qty[result_qty[last_month_qty] > 0].copy()

    # 상위 10개
    top_10_qty_last_month = nonzero_qty.nlargest(10, last_month_qty, keep='all').copy()
    top_10_qty_last_month["color"] = "#FFD700"  # 황금색 예시

    # 하위 10개
    bottom_10_qty_last_month = nonzero_qty.nsmallest(10, last_month_qty, keep='all').copy()
    bottom_10_qty_last_month["color"] = "#808080"  # 회색 예시
else:
    top_10_qty_last_month = pd.DataFrame()
    bottom_10_qty_last_month = pd.DataFrame()

top_10_qty_fig = px.bar(
    top_10_qty_last_month.sort_values(by=last_month_qty, ascending=True),
    x=last_month_qty,
    y='ID',
    orientation='h',
    color='color',
    color_discrete_map='identity',
    title=f'{last_month_qty} 월 판매수량 상위 10개' if last_month_qty else '판매수량 상위 10개 (데이터 부족)',
    template="plotly_white",
).update_layout(
    title_x=0.5,
    yaxis_title='ID',
    xaxis_title='판매수량',
    margin=dict(l=50, r=50, t=200, b=100),
    height=600,
)
bottom_10_qty_fig = px.bar(
    bottom_10_qty_last_month.sort_values(by=last_month_qty, ascending=True),
    x=last_month_qty,
    y='ID',
    orientation='h',
    color='color',
    color_discrete_map='identity',
    title=f'{last_month_qty} 월 판매수량 하위 10개(0 제외)' if last_month_qty else '판매수량 하위 10개 (데이터 부족)',
    template="plotly_white",
).update_layout(
    title_x=0.5,
    yaxis_title='ID',
    xaxis_title='판매수량',
    margin=dict(l=50, r=50, t=200, b=100),
    height=600,
)


##########################
# Dash 애플리케이션
##########################
app = Dash(__name__)

##########################
# 스타일 정의
##########################
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
ROW_STYLE = {
    "display": "flex",
    "flex-wrap": "wrap",
    "justify-content": "space-between"
}
KPI_CARD_STYLE = {
    "display": "inline-block",
    "width": "13%",
    "margin": "10px",
    "padding": "15px",
    "text-align": "center",
    "border-radius": "10px",
    "background-color": "#ffffff",
    "box-shadow": "0px 4px 10px rgba(0, 0, 0, 0.1)"
}
SECTION_STYLE = {
    "backgroundColor": "white",
    "borderRadius": "15px",
    "boxShadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
    "padding": "20px",
    "marginBottom": "20px",
    "border": "1px solid #e0e0e0",
    'width': '48%',
    'display': 'inline-block',
    'vertical-align': 'top'
}
GRAPH_STYLE = {
    "margin": "20px",
    "padding": "20px",
    "background-color": "#ffffff",
    "border-radius": "10px",
    "box-shadow": "0px 4px 10px rgba(0, 0, 0, 0.1)"
}
KPI_TITLE_STYLE = {
    "background-color": "#f4f4f4",
    "padding": "10px",
    "border-radius": "10px 10px 0 0",
    "text-align": "center",
    "color": "#333",
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

monthly_change_value = float(kpi_values["월간 매출 변화"].strip('%'))
KPI_MONTHLY_CHANGE_STYLE = {
    "text-align": "center",
    "font-size": "24px",
    "color": get_monthly_change_color(monthly_change_value),
}

item_style = {
    "width": "350px",
    "height": "160px",
    "display": "inline-flex",
    "justify-content": "center",
    "align-items": "center",
    "font-size": "20px",
    "font-weight": "bold",
    "color": "#fff",
    "background-color": "#FF7F50",
    "border-radius": "15px",
    "box-shadow": "0 8px 25px rgba(0, 0, 0, 0.2)",
    "margin-right": "30px",
}
KPI_ALL_STYLE = {
    "marginTop": "30px",
    "marginBottom": "30px",
    "border": "1px solid #e0e0e0",
    "borderRadius": "15px",
    "box-shadow": "0px 4px 10px rgba(0, 0, 0, 0.1)",
    'width': '96%',
    'display': 'flex',
    'flex-direction': 'column',
    'align-items': 'center',
    'justify-content': 'center',
    'padding': '20px',
    'margin-left': 'auto',
    'margin-right': 'auto',
}


##########################
# 레이아웃
##########################
app.layout = html.Div([
    html.H1("데이터 대시보드", style=TITLE_STYLE),

    # 1) KPI (첫 번째 줄)
    html.Div([
        html.Div([
            html.H3("연간 매출 (최근 12개월)", style=KPI_TITLE_STYLE),
            html.H2(format_currency(kpi_values['총 합계 (연간 매출)']), style=KPI_VALUE_STYLE)
        ], style=KPI_CARD_STYLE),
        html.Div([
            html.H3("일간 매출", style=KPI_TITLE_STYLE),
            html.H2(format_currency(kpi_values['일간 매출']), style=KPI_VALUE_STYLE)
        ], style=KPI_CARD_STYLE),
        html.Div([
            html.H3("주간 매출", style=KPI_TITLE_STYLE),
            html.H2(format_currency(kpi_values['주간 매출']), style=KPI_VALUE_STYLE)
        ], style=KPI_CARD_STYLE),
        html.Div([
            html.H3("월간 매출", style=KPI_TITLE_STYLE),
            html.H2(format_currency(kpi_values['월간 매출']), style=KPI_VALUE_STYLE)
        ], style=KPI_CARD_STYLE),
    ], style=ROW_STYLE),

    # 2) KPI (두 번째 줄)
    html.Div([
        html.Div([
            html.H3("월간 매출 변화", style=KPI_TITLE_STYLE),
            html.H2(kpi_values["월간 매출 변화"], style=KPI_MONTHLY_CHANGE_STYLE)
        ], style=KPI_CARD_STYLE),
        html.Div([
            html.H3("트렌드", style=KPI_TITLE_STYLE),
            html.H2("Chill guy", style=KPI_VALUE_STYLE)  # 필요시 내용
        ], style=KPI_CARD_STYLE),
        html.Div([
            html.H3("재고 없는 상품", style=KPI_TITLE_STYLE),
            html.H2("")  # 필요시 내용
        ], style=KPI_CARD_STYLE),
        html.Div([
            html.H3("??", style=KPI_TITLE_STYLE),
            html.H2("")  # 필요시 내용
        ], style=KPI_CARD_STYLE),
    ], style=ROW_STYLE),

    # 3) 일간 / 주간 / 월간 그래프 (매출)
    html.Div([
        # 일간 그래프
        html.Div([
            dcc.Graph(
                id='daily-graph',
                figure=px.line(
                    daily_data, x='날짜', y='값', title='일간 데이터',
                    template="plotly_white",
                    line_shape="linear"
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
                    line_shape="linear"
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
                    line_shape="linear"
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

    # 4) 매출 급상승 품목
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

    # 5) 매출액 상위/하위 10개 (기존)
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
                    height=600
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
                    height=600
                )
            )
        ], style=SECTION_STYLE),
    ], style=ROW_STYLE),

    # 7) "판매수량" 상위/하위 10개
    html.Div([
        html.Div([
            dcc.Graph(
                id='top-10-qty-graph',
                figure=top_10_qty_fig
            )
        ], style=SECTION_STYLE),

        html.Div([
            dcc.Graph(
                id='bottom-10-qty-graph',
                figure=bottom_10_qty_fig
            )
        ], style=SECTION_STYLE),
    ], style=ROW_STYLE),

    # 6) 재고가 적은 품목
    html.Div([
        html.Div([
            dcc.Graph(
                id='low-stock-graph',
                figure=low_stock_fig
            )
        ], style=SECTION_STYLE),
    ], style=ROW_STYLE)

], style=PAGE_STYLE)


if __name__ == '__main__':
    app.run_server(debug=True)
