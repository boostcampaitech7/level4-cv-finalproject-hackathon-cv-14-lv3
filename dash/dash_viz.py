import pandas as pd
import plotly.express as px
import dash
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go

# CSV 파일 로드
data = pd.read_csv("sales.csv")


# 날짜 열만 추출 (열 이름이 날짜 형식인 열만 선택)
date_columns = [col for col in data.columns if col.startswith('202')]

monthly_data = (
    data.melt(id_vars=['ID'], value_vars=date_columns, var_name='날짜', value_name='매출액')  # 데이터 변환
    .assign(월=lambda df: pd.to_datetime(df['날짜']).dt.to_period('M').astype(str))  # 월 추출
    .groupby(['ID', '월'], as_index=False)['매출액'].sum()  # ID와 월별로 매출 합계 계산
)

# ID를 행으로, 월을 열로 변환
result = monthly_data.pivot(index='ID', columns='월', values='매출액').reset_index()
result['ID'] = result['ID'].astype('str')
last_month = result.columns[-1]  # 가장 마지막 달을 선택

# 빨간색 계열 색상 10등분 (상위 10개에 사용)
reds = [
    '#D14B4B', '#E22B2B', '#E53A3A', '#F15D5D', '#F67878', 
    '#F99A9A', '#FBB6B6', '#FDC8C8', '#FEE0E0', '#FEEAEA'
]


# 파란색 계열 색상 10등분 (하위 10개에 사용)
blues = [
    '#0000FF', '#0000E6', '#0000CC', '#0000B3', '#000099', 
    '#00007F', '#000066', '#00004C', '#000033', '#00001A'
]

# 마지막 달에서 상위 5개 ID
top_10_last_month = result.nlargest(10, last_month, keep='all')
top_10_last_month["color"] = reds

# 마지막 달에서 하위 5개 ID
bottom_10_last_month = result.nsmallest(10, last_month)
bottom_10_last_month["color"] = blues


# 날짜별 합계 계산 (각 날짜에 대한 매출 합계)
daily_data = pd.DataFrame(data[date_columns].sum(axis=0), columns=['값']).reset_index()
daily_data.columns = ['날짜', '값']
daily_data['날짜'] = pd.to_datetime(daily_data['날짜'])

# 주간 데이터 계산 (7일 단위로 합계)
daily_data['주간'] = daily_data['날짜'].dt.to_period('W').apply(lambda r: r.start_time)
weekly_data = daily_data.groupby('주간')['값'].sum().reset_index()

# 월간 데이터 계산 (각 월에 대해 매출 합계)
daily_data['월간'] = daily_data['날짜'].dt.to_period('M').apply(lambda r: r.start_time)
monthly_data = daily_data.groupby('월간')['값'].sum().reset_index()

daily_data = daily_data[daily_data['날짜'] >= '2023-02-01']
weekly_data = weekly_data[weekly_data['주간'] >= '2022-11-01']

# 최근 12개월의 연간 매출 계산
recent_12_months = monthly_data.tail(12)
annual_sales = recent_12_months['값'].sum()

# KPI 데이터 (금액을 1,000,000원 형태로 쉼표 구분)
kpi_values = {
    "총 합계 (연간 매출)": annual_sales,  # 연간 매출
    "일간 평균": daily_data['값'].mean(),
    "주간 평균": weekly_data['값'].mean(),
    "월간 평균": monthly_data['값'].mean(),
    "일간 매출": daily_data['값'].iloc[-1],  # 최신 일간 매출
    "주간 매출": weekly_data['값'].iloc[-1],  # 최신 주간 매출
    "월간 매출": monthly_data['값'].iloc[-1]  # 최신 월간 매출
}

# 월간 매출 변화 계산
last_month_sales = monthly_data['값'].iloc[-1]  # 마지막 월 매출
second_last_month_sales = monthly_data['값'].iloc[-2]  # 마지막에서 두 번째 월 매출
monthly_change = ((last_month_sales - second_last_month_sales) / second_last_month_sales) * 100  # 매출 변화율

# KPI 항목에 월간 매출 변화 추가
kpi_values["월간 매출 변화"] = f"{monthly_change:.2f}%"

# 금액을 "₩1,000,000원" 형태로 표시하는 함수
def format_currency(value):
    return f"₩{value:,.0f}원"

# 금액을 억 원 단위로 변환하는 함수
def format_currency_in_units(value):
    if value >= 1e8:
        return f"{value/1e8:.0f}B"
    else:
        return f"{value/1e7:.0f}천만원"
    
# "소분류" 별 매출 변화 계산
data["소분류"] = data["소분류"].fillna('기타')  # NaN 값 처리

# 마지막 두 달의 매출 차이를 계산하여 상승폭 계산
last_month_sales = data[date_columns[-1]].sum()
second_last_month_sales = data[date_columns[-2]].sum()
data["매출 상승폭"] = (last_month_sales - second_last_month_sales) / second_last_month_sales * 100

# 상승폭이 큰 품목 상위 20개 선택
top_20_items = data.groupby('소분류')['매출 상승폭'].sum().nlargest(6).reset_index()

# 품목 이름만 리스트로 구성
item_sales = top_20_items[['소분류']].values.tolist()

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

# Dash 애플리케이션 생성
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

# 파스텔톤 색상 팔레트 적용
pastel_colors = px.colors.qualitative.Pastel



# 레이아웃 구성
# KPI 항목 레이아웃 변경
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

# 월간 매출 변화 색상 결정 함수
def get_monthly_change_color(value):
    if value > 0:
        return "red"  # 양수일 경우 빨강
    elif value < 0:
        return "blue"  # 음수일 경우 파랑
    else:
        return "#333"  # 0일 경우 기본 색상

# 월간 매출 변화 값
monthly_change_value = float(kpi_values["월간 매출 변화"].strip('%'))

# 월간 매출 변화 카드 스타일
KPI_MONTHLY_CHANGE_STYLE = {
    "text-align": "center",
    "font-size": "24px",
    "color": get_monthly_change_color(monthly_change_value),  # 동적으로 색상 변경
}


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

    html.Div([
        # 오른쪽 4개 KPI 카드
        html.Div([
            html.H3("월간 매출 변화", style=KPI_TITLE_STYLE),
            html.H2(kpi_values["월간 매출 변화"], style=KPI_MONTHLY_CHANGE_STYLE)
        ], style=KPI_CARD_STYLE_RIGHT),
        html.Div([
            html.H3("트렌드", style=KPI_TITLE_STYLE),
            html.H2("")  # 내용 없음
        ], style=KPI_CARD_STYLE_RIGHT),
        html.Div([
            html.H3("기타", style=KPI_TITLE_STYLE),
            html.H2("")  # 내용 없음
        ], style=KPI_CARD_STYLE_RIGHT),
        html.Div([
            html.H3("??", style=KPI_TITLE_STYLE),
            html.H2("")  # 내용 없음
        ], style=KPI_CARD_STYLE_RIGHT),
    ], style=ROW_STYLE),

    # 일간, 주간, 월간 그래프 섹션
    html.Div([  
    html.Div([  
        dcc.Graph(  
            id='daily-graph',  
            figure=px.line(  
                daily_data, x='날짜', y='값', title='일간 데이터',  
                template="plotly_white",  
                line_shape="linear",  
                color_discrete_sequence=[pastel_colors[0]]  # 파스텔톤 색상 적용  
            ).update_traces(
                line=dict(width=3),
                fill='tozeroy',  # 선 아래 영역을 채움
                fillcolor='rgba(187, 212, 255, 0.15)'  # 선 근처는 진하게, 멀어질수록 연하게 (rgba는 0~1로 투명도 설정)
            ).update_layout(  
                title_x=0.5,  
                yaxis_title='매출',  
                title_font=dict(size=18, color='#333', family="Arial, sans-serif", weight="bold"),  
                xaxis_title='일간', 
                xaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # x축 타이틀 굵게
                yaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # y축 타이틀 굵게 
                yaxis=dict(  
                    tickformat=",",  # 쉼표로 천 단위 구분  
                    ticksuffix="B",  # 억 단위로 표시  
                    showgrid=True,  
                    tickmode='array',  
                    tickvals=[i for i in range(0, int(daily_data['값'].max()), int(daily_data['값'].max() / 5))],  
                    ticktext=[f"{(i // 1e8) * 1e8 / 1e8:.0f}B" for i in range(0, int(daily_data['값'].max()), int(daily_data['값'].max() / 5))],  
                    tick0=0,  
                    dtick=int(daily_data['값'].max() / 5),  
                    zeroline=False  # 0.00 없애기  
                )  
            )  
        ) 
    ], style=GRAPH_STYLE),  

    html.Div([  
        dcc.Graph(  
            id='weekly-graph',  
            figure=px.line(  
                weekly_data, x='주간', y='값', title='주간 데이터',  
                template="plotly_white",  
                line_shape="linear",  
                color_discrete_sequence=[pastel_colors[1]]  # 파스텔톤 색상 적용  
            ).update_traces(
                line=dict(width=3),
                fill='tozeroy',  # 선 아래 영역을 채움
                fillcolor='rgba(179, 220, 179, 0.1)'  # 선 근처는 진하게, 멀어질수록 연하게 (rgba는 0~1로 투명도 설정)
            ).update_layout(  
                title_x=0.5,  
                yaxis_title='매출',  
                title_font=dict(size=18, color='#333', family="Arial, sans-serif", weight="bold"),  
                xaxis_title='주간',  
                xaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # x축 타이틀 굵게
                yaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # y축 타이틀 굵게
                yaxis=dict(  
                    tickformat=",",  # 쉼표로 천 단위 구분  
                    ticksuffix="B",  # 억 단위로 표시  
                    showgrid=True,  
                    tickmode='array',  
                    tickvals=[i for i in range(0, int(weekly_data['값'].max()), int(weekly_data['값'].max() / 5))],  
                    ticktext=[f"{(i // 1e8) * 1e8 / 1e8:.0f}B" for i in range(0, int(weekly_data['값'].max()), int(weekly_data['값'].max() / 5))],  
                    tick0=0,  
                    dtick=int(weekly_data['값'].max() / 5),  
                    zeroline=False  # 0.00 없애기  
                )  
            )  
        )  
    ], style=GRAPH_STYLE),  

    html.Div([  
        dcc.Graph(  
            id='monthly-graph',  
            figure=px.line(  
                monthly_data, x='월간', y='값', title='월간 데이터',  
                template="plotly_white",  
                line_shape="linear",  
                color_discrete_sequence=[pastel_colors[2]]  # 파스텔톤 색상 적용  
            ).update_traces(
                line=dict(width=3),
                fill='tozeroy',  # 선 아래 영역을 채움
                fillcolor='rgba(244, 178, 247, 0.1)'  # 선 근처는 진하게, 멀어질수록 연하게 (rgba는 0~1로 투명도 설정)
            ).update_layout(  
                title_x=0.5,  
                yaxis_title='매출',  
                title_font=dict(size=18, color='#333', family="Arial, sans-serif", weight="bold"),  
                xaxis_title='월간',  
                xaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # x축 타이틀 굵게
                yaxis_title_font=dict(size=14, family="Arial, sans-serif", weight="bold"),  # y축 타이틀 굵게
                yaxis=dict(  
                    tickformat=",",  # 쉼표로 천 단위 구분  
                    ticksuffix="B",  # 억 단위로 표시  
                    showgrid=True,  
                    tickmode='array',  
                    tickvals=[i for i in range(0, int(monthly_data['값'].max()), int(monthly_data['값'].max() / 5))],  
                    ticktext=[f"{(i // 1e8) * 1e8 / 1e8:.0f}B" for i in range(0, int(monthly_data['값'].max()), int(monthly_data['값'].max() / 5))],  
                    tick0=0,  
                    dtick=int(monthly_data['값'].max() / 5),  
                    zeroline=False  # 0.00 없애기  
                )  
            )  
        )  
    ], style=GRAPH_STYLE)  
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
                "justify-content": "center",  # 중앙 정렬
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
                    title=f'{last_month} 월 매출 상위 10개 ID',
                    template="plotly_white",
                ).update_layout(
                    title_x=0.5,
                    title_font=dict(size=18, family="Arial, sans-serif", color="black", weight='bold'),
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
                    title=f'{last_month} 월 매출 하위 10개 ID',
                    template="plotly_white",
                ).update_layout(
                    title_x=0.5,
                    title_font=dict(size=18, family="Arial, sans-serif", color="black", weight='bold'),
                    yaxis_title='ID',
                    xaxis_title='매출액',
                    margin=dict(l=50, r=50, t=200, b=100),
                    height=600,
                    plot_bgcolor='white'
                )
            )
        ], style=SECTION_STYLE),
    ], style=ROW_STYLE)
])





if __name__ == '__main__':
    app.run_server(debug=True)

