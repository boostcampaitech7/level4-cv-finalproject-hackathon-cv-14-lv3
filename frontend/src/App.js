import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import ChatPage from './ChatPage';

////////////////////////////////////////
// 1) 스타일 상수 (질문 코드 그대로 유지)
////////////////////////////////////////

const PAGE_STYLE = {
  backgroundColor: "#f4f4f9",
  padding: "20px", // 패딩 크기 증가
  fontFamily: "Arial, sans-serif",
  fontSize: "18px", // 기본 글꼴 크기 증가
};

const TITLE_STYLE = {
  textAlign: "center",
  fontSize: "24px",
  color: "#333",
  fontWeight: "bold",
  marginTop: "30px",
  marginBottom: "30px"
};
const KPI_CARD_STYLE = {
  display: "inline-block",
  width: "15%", // 너비 증가
  margin: "10px", // 간격 증가
  padding: "16px", // 내부 여백 증가
  textAlign: "center",
  borderRadius: "10px",
  backgroundColor: "#ffffff",
  boxShadow: "0px 6px 12px rgba(0, 0, 0, 0.2)" // 그림자 강조
};

const ROW_STYLE = {
  display: "flex",
  flexWrap: "wrap", // 여러 줄로 감싸기 허용
  justifyContent: "space-evenly", // 블록 간 균등 간격 유지
  gap: "10px", // 블록 간 간격 추가
  alignItems: "center", // 세로 정렬
};

const GRAPH_STYLE = {
  margin: "20px",
  padding: "20px",
  backgroundColor: "#ffffff",
  borderRadius: "10px",
  boxShadow: "0px 4px 10px rgba(0, 0, 0, 0.1)"
};
const SECTION_STYLE = {
  backgroundColor: "white",  
  borderRadius: "15px",  
  boxShadow: "0px 4px 6px rgba(0, 0, 0, 0.1)",  
  padding: "20px",  
  marginBottom: "20px",  
  border: "1px solid #e0e0e0",  
  width: '48%',
  display: 'inline-block',
  verticalAlign: 'top'
};
const KPI_ALL_STYLE = {
  marginTop: "20px",
  marginBottom: "20px",
  border: "1px solid #e0e0e0",
  borderRadius: "10px",
  boxShadow: "0px 4px 10px rgba(0, 0, 0, 0.1)",
  width: "95%",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  padding: "10px",
  marginLeft: "auto",
  marginRight: "auto"
};
const KPI_CARD_STYLE_LEFT = {
  display: "inline-block",
  width: "20%",
  margin: "5px",
  padding: "8px",
  textAlign: "center",
  borderRadius: "10px",
  backgroundColor: "#ffffff",
  boxShadow: "0px 4px 10px rgba(0, 0, 0, 0.1)"
};
const KPI_CARD_STYLE_RIGHT = {
  display: "inline-block",
  width: "20%",
  margin: "5px",
  padding: "8px",
  textAlign: "center",
  borderRadius: "10px",
  backgroundColor: "#ffffff",
  boxShadow: "0px 4px 10px rgba(0, 0, 0, 0.1)"
};

const KPI_TITLE_STYLE = {
  backgroundColor: "#f4f4f4",
  padding: "5px",
  borderRadius: "10px 10px 0 0",
  textAlign: "center",
  color: "#333",
  fontSize: "14px",
  fontWeight: "bold"
};
const KPI_VALUE_STYLE = {
  textAlign: "center",
  fontSize: "18px",
  color: "#333"
};

// 색상 배열(진한색→연한색), Dash 코드에서 reds/blues
const reds = [
  "#D14B4B", "#E22B2B", "#E53A3A", "#F15D5D", "#F67878",
  "#F99A9A", "#FBB6B6", "#FDC8C8", "#FEE0E0", "#FEEAEA"
];
const blues = [
  '#B0D6F1', '#A5C9E9', '#99BCE1', '#8DB0D9', '#81A4D1',
  '#7498C9', '#688BC1', '#5C7FB9', '#5073B1', '#4567A9'
];

function formatCurrency(value) {
  if (typeof value !== "number") return "₩0원";
  return "₩" + value.toLocaleString() + "원";
}

////////////////////////////////////////
// 2) 메인 컴포넌트
////////////////////////////////////////

// AnimatedGraph 컴포넌트 분리
const AnimatedGraph = ({ trace, title }) => {
  const graphRef = useRef(null);
  const [isVisible, setIsVisible] = useState(false);
  const [animatedData, setAnimatedData] = useState(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.3 }
    );

    if (graphRef.current) {
      observer.observe(graphRef.current);
    }

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (isVisible && trace) {
      const startData = {
        ...trace,
        x: trace.x.map(() => Math.random() * Math.max(...trace.x))
      };

      setAnimatedData(startData);

      const duration = 1500;
      const steps = 30;
      const interval = duration / steps;
      let step = 0;

      const animation = setInterval(() => {
        step++;
        const progress = step / steps;
        
        const newData = {
          ...trace,
          x: trace.x.map((targetValue, i) => {
            const startValue = startData.x[i];
            return startValue + (targetValue - startValue) * progress;
          })
        };

        setAnimatedData(newData);

        if (step >= steps) {
          clearInterval(animation);
          setAnimatedData(trace);
        }
      }, interval);

      return () => clearInterval(animation);
    }
  }, [isVisible, trace]);

  return (
    <div
      ref={graphRef}
      style={{
        ...SECTION_STYLE,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        opacity: isVisible ? 1 : 0,
        transition: 'opacity 0.5s ease-in'
      }}
    >
      <Plot
        data={[animatedData || trace]}
        layout={{
          title: {
            text: title,
            font: { size: 18, color: '#333', family: "Arial, sans-serif", weight: "bold" }
          },
          xaxis: { 
            title: {
              text: "매출액",
              font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
            }
          },
          yaxis: {
            title: {
              text: "ID",
              font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
            },
            type: "category"
          },
          title_x: 0.5,
          height: 600,
          margin: { l: 50, r: 50, t: 200, b: 100 }
        }}
      />
    </div>
  );
};

function App() {
  // KPI & 데이터
  const [kpis, setKpis] = useState({});
  const [dailyData, setDailyData] = useState([]);
  const [weeklyData, setWeeklyData] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [categoryPie, setCategoryPie] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [rising, setRising] = useState({ rise_rate: 0, subcat_list: [] });

  // 상/하위 10
  const [top10, setTop10] = useState([]);
  const [bottom10, setBottom10] = useState([]);
  const [lastMonthCol, setLastMonthCol] = useState("");

  const API_BASE = "http://localhost:8000";

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 여러 API 호출
        const kpiRes = await axios.get(`${API_BASE}/api/kpis`);
        setKpis(kpiRes.data);

        const dailyRes = await axios.get(`${API_BASE}/api/daily`);
        setDailyData(dailyRes.data);

        const weeklyRes = await axios.get(`${API_BASE}/api/weekly`);
        setWeeklyData(weeklyRes.data);

        const monthlyRes = await axios.get(`${API_BASE}/api/monthly`);
        setMonthlyData(monthlyRes.data);

        const catRes = await axios.get(`${API_BASE}/api/categorypie`);
        setCategoryPie(catRes.data);

        const lowRes = await axios.get(`${API_BASE}/api/lowstock`);
        setLowStock(lowRes.data);

        const risingRes = await axios.get(`${API_BASE}/api/rising-subcategories`);
        setRising(risingRes.data);

        // 상/하위 10개
        const topBottomRes = await axios.get(`${API_BASE}/api/topbottom`);
        setTop10(topBottomRes.data.top_10 || []);
        setBottom10(topBottomRes.data.bottom_10 || []);
        setLastMonthCol(topBottomRes.data.last_month_col || "");
      } catch (err) {
        console.error(err);
      }
    };
    fetchData();
  }, []);

  ////////////////////////////////////////
  // KPI 색상
  ////////////////////////////////////////
  let monthlyChangeColor = "#333";
  if (typeof kpis.monthly_change === "number") {
    monthlyChangeColor = kpis.monthly_change > 0 ? "red" : "blue";
  }

  ////////////////////////////////////////
  // 그래프: 일간/주간/월간
  ////////////////////////////////////////
  const dailyTrace = {
    x: dailyData.map(d => d.날짜),
    y: dailyData.map(d => d.값),
    type: "scatter",
    mode: "lines",
    fill: "tozeroy",
    fillcolor: "rgba(187,212,255,0.15)",
    line: { width: 2, color: "#aad1ff" }
  };
  const weeklyTrace = {
    x: weeklyData.map(d => d.주간),
    y: weeklyData.map(d => d.값),
    type: "scatter",
    mode: "lines",
    fill: "tozeroy",
    fillcolor: "rgba(179,220,179,0.1)",
    line: { width: 2, color: "#9bdf9b" }
  };
  const monthlyTrace = {
    x: monthlyData.map(d => d.월간),
    y: monthlyData.map(d => d.값),
    type: "scatter",
    mode: "lines",
    fill: "tozeroy",
    fillcolor: "rgba(244,178,247,0.1)",
    line: { width: 2, color: "#f4b2f7" }
  };

  ////////////////////////////////////////
  // 파이차트 (대분류)
  ////////////////////////////////////////
  const pieData = [
    {
      labels: categoryPie.map(c => c.대분류),
      values: categoryPie.map(c => c.매출액),
      type: "pie"
    }
  ];

  ////////////////////////////////////////
  // 상/하위 10: Y축에 "그 10개 ID"만
  ////////////////////////////////////////
  // 1) 상위 10: 내림차순 정렬 → slice(0,10)
  // 2) 하위 10: 오름차순 정렬 → slice(0,10)
  // Y축에 전달하는 것은 그 10개의 ID 문자열만

  function getVal(obj) {
    return lastMonthCol ? (obj[lastMonthCol] || 0) : 0;
  }

  // 상위 10: 내림차순
  const sortedTop10 = [...top10]
    .sort((a, b) => getVal(a) - getVal(b))
    .slice(0, 10);

  // 하위 10: 오름차순
  const sortedBottom10 = [...bottom10]
    .sort((a, b) => getVal(b) - getVal(a))
    .slice(0, 10);

  // 색상 할당
  // 상위 10: index 0(가장 큰) -> reds[0], index 9(작은) -> reds[9]
  // 하위 10: index 9(가장 큰 among bottom) -> blues[0], etc
  // 아래는 "가장 큰 값이 맨 위"로 표시하기 위해 reverse를 적용할 수도 있음
  // 여기서는 단순히 "내림차순 => reds, 오름차순 => blues"만 하되,
  // yaxis에 딱 그 10개 ID만 준다.
  const len = reds.length;
  const topIDs = sortedTop10.map(item => item.ID);   // 10개
  const topVals = sortedTop10.map(item => getVal(item));
  const topColors = sortedTop10.map((item, i) => {
    // len-1 - i
    return reds[reds.length - 1 - i] || "#FEEAEA";
  });

  const bottomIDs = sortedBottom10.map(item => item.ID);
  const bottomVals = sortedBottom10.map(item => getVal(item));
  // 하위 10개도, 가장 큰 값(인덱스=9) 쪽에 blues[0]을 주려면 뒤집을 수도 있지만,
  // 혹은 i => blues[blues.length -1 - i], etc. (선호하는 방식대로)
  // 여기서는 그냥 i->blues[i]
  const bottomColors = sortedBottom10.map((item, i) => blues[i] || "#4567A9");

  // 수평 바 차트
  // 최종 trace
  const top10Trace = {
    x: topVals,
    y: topIDs,
    type: "bar",
    orientation: "h",
    marker: { color: topColors }
  };

  const bottom10Trace = {
    x: bottomVals,
    y: bottomIDs,
    type: "bar",
    orientation: "h",
    marker: { color: bottomColors }
  };

  const topTitle = lastMonthCol
    ? `${lastMonthCol} 월 매출 상위 10개 ID`
    : "상위 10개";

  const bottomTitle = lastMonthCol
    ? `${lastMonthCol} 월 매출 하위 10개 ID`
    : "하위 10개";

  // "급상승 품목"
  const itemStyle = {
    width: "200px",
    height: "100px",
    display: "inline-flex",
    justifyContent: "center",
    alignItems: "center",
    fontSize: "14px",
    fontWeight: "bold",
    color: "#fff",
    background: "linear-gradient(135deg, #FF6B6B 0%, #FFA07A 100%)",
    borderRadius: "15px",
    boxShadow: `
      0 20px 25px -5px rgba(255, 107, 107, 0.35),  // 메인 외부 그림자 강화
      0 15px 15px -8px rgba(255, 160, 122, 0.25),  // 두 번째 외부 그림자 강화
      0 8px 12px rgba(0, 0, 0, 0.15),              // 바닥 그림자 추가
      inset 0 -4px 8px rgba(0,0,0,0.2),            // 하단 내부 그림자 강화
      inset 0 4px 8px rgba(255,255,255,0.3),       // 상단 하이라이트 강화
      inset 2px 0 4px rgba(255,255,255,0.1),       // 우측 내부 하이라이트
      inset -2px 0 4px rgba(0,0,0,0.1)             // 좌측 내부 그림자
    `,
    transform: `
      translateY(-4px)        // 더 많이 띄움
      perspective(1000px)     // 3D 효과를 위한 원근감
      rotateX(2deg)          // X축 회전
    `,
    border: "1px solid rgba(255,255,255,0.3)",  // 테두리 더 밝게
    transition: "all 0.3s ease",
    marginRight: "15px",
    textShadow: "0 2px 4px rgba(0,0,0,0.2)",
    position: "relative",
    overflow: "hidden",
    backfaceVisibility: "hidden",  // 3D 변환 시 뒷면 숨김
    transformStyle: "preserve-3d",  // 3D 공간에서의 변환 유지
    whiteSpace: "pre-wrap",        // 텍스트 줄바꿈 허용
    wordBreak: "break-word",       // 긴 단어 줄바꿈
    padding: "10px",               // 텍스트 여백 추가
    textAlign: "center",           // 텍스트 가운데 정렬
    display: "flex",               // Flexbox 사용
    flexDirection: "column",       // 세로 방향 정렬
    justifyContent: "center",      // 세로 중앙 정렬
    alignItems: "center"           // 가로 중앙 정렬
  };

  // 스타일 시트에 애니메이션 추가
  const styles = `
    @keyframes shine {
      0% {
        left: -100%;
      }
      20% {
        left: 100%;
      }
      100% {
        left: 100%;
      }
    }
  `;

  // App 컴포넌트 내에 스타일 시트 추가
  document.head.appendChild(document.createElement('style')).textContent = styles;

  return (
    <Router>
      <Routes>
        <Route path="/" element={
    <div style={PAGE_STYLE}>
      <h1 style={TITLE_STYLE}>데이터 대시보드</h1>

      {/* Add chat Link */}
      <div style={{textAlign: 'center', marginBottom: '20px'}}>
              <Link to="/chat" style={{
                padding: '10px 20px',
                backgroundColor: '#007bff',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '5px',
                fontWeight: 'bold'
              }}>
                AI 챗봇 상담 바로가기
              </Link>
            </div>

      {/* KPI 카드 */}
      <div style={ROW_STYLE}>
        <div style={KPI_CARD_STYLE_LEFT}>
          <h3 style={KPI_TITLE_STYLE}>연간 매출</h3>
          <h2 style={KPI_VALUE_STYLE}>{formatCurrency(kpis.annual_sales)}</h2>
        </div>
        <div style={KPI_CARD_STYLE_LEFT}>
          <h3 style={KPI_TITLE_STYLE}>일간 매출</h3>
          <h2 style={KPI_VALUE_STYLE}>{formatCurrency(kpis.last_daily)}</h2>
        </div>
        <div style={KPI_CARD_STYLE_LEFT}>
          <h3 style={KPI_TITLE_STYLE}>주간 매출</h3>
          <h2 style={KPI_VALUE_STYLE}>{formatCurrency(kpis.last_weekly)}</h2>
        </div>
        <div style={KPI_CARD_STYLE_LEFT}>
          <h3 style={KPI_TITLE_STYLE}>월간 매출</h3>
          <h2 style={KPI_VALUE_STYLE}>{formatCurrency(kpis.last_monthly)}</h2>
        </div>
      </div>

      <div style={ROW_STYLE}>
        <div style={KPI_CARD_STYLE_RIGHT}>
          <h3 style={KPI_TITLE_STYLE}>월간 매출 변화</h3>
          <h2 style={{
            textAlign: "center",
            fontSize: "18px",
            color: monthlyChangeColor
          }}>
            {typeof kpis.monthly_change === "number"
              ? kpis.monthly_change.toFixed(2) + "%"
              : "0%"}
          </h2>
        </div>
        <div style={KPI_CARD_STYLE_RIGHT}>
          <h3 style={KPI_TITLE_STYLE}>트렌드</h3>
          <h2 style={KPI_VALUE_STYLE}></h2>
        </div>
        <div style={KPI_CARD_STYLE_RIGHT}>
          <h3 style={KPI_TITLE_STYLE}>기타</h3>
          <h2 style={KPI_VALUE_STYLE}></h2>
        </div>
        <div style={KPI_CARD_STYLE_RIGHT}>
          <h3 style={KPI_TITLE_STYLE}>??</h3>
          <h2 style={KPI_VALUE_STYLE}></h2>
        </div>
      </div>

      {/* 일간/주간/월간 그래프 */}
      <div style={ROW_STYLE}>
        <div style={GRAPH_STYLE}>
          <div style={{
            width: "100%",
            backgroundColor: "#f8f9fa",
            padding: "15px 0 20px 0",
            marginBottom: "20px",
            borderTopLeftRadius: "8px",
            borderTopRightRadius: "8px"
          }}>
            <h3 style={{
              textAlign: "center",
              margin: 0,
              fontSize: "18px",
              fontWeight: "bold",
              color: "#333",
              fontFamily: "Arial, sans-serif"
            }}>일간 데이터</h3>
          </div>
          <Plot
            data={[{
              ...dailyTrace,
              fill: 'tozeroy',
              fillcolor: 'rgba(64, 181, 246, 0.1)',
              line: { color: 'rgb(64, 181, 246)' }
            }]}
            layout={{
              xaxis: { 
                title: {
                  text: "일간",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                }
              },
              yaxis: { 
                title: {
                  text: "매출",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                },
                type: "linear"
              },
              width: 600,
              height: 380,
              margin: { t: 20, r: 30, l: 60, b: 40 }
            }}
          />
        </div>
        <div style={GRAPH_STYLE}>
          <div style={{
            width: "100%",
            backgroundColor: "#f8f9fa",
            padding: "15px 0 20px 0",
            marginBottom: "20px",
            borderTopLeftRadius: "8px",
            borderTopRightRadius: "8px"
          }}>
            <h3 style={{
              textAlign: "center",
              margin: 0,
              fontSize: "18px",
              fontWeight: "bold",
              color: "#333",
              fontFamily: "Arial, sans-serif"
            }}>주간 데이터</h3>
          </div>
          <Plot
            data={[{
              ...weeklyTrace,
              fill: 'tozeroy',
              fillcolor: 'rgba(129, 199, 132, 0.1)',
              line: { color: 'rgb(129, 199, 132)' }
            }]}
            layout={{
              xaxis: { 
                title: {
                  text: "주간",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                }
              },
              yaxis: { 
                title: {
                  text: "매출",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                },
                type: "linear"
              },
              width: 600,
              height: 380,
              margin: { t: 20, r: 30, l: 60, b: 40 }
            }}
          />
        </div>
        <div style={GRAPH_STYLE}>
          <div style={{
            width: "100%",
            backgroundColor: "#f8f9fa",
            padding: "15px 0 20px 0",
            marginBottom: "20px",
            borderTopLeftRadius: "8px",
            borderTopRightRadius: "8px"
          }}>
            <h3 style={{
              textAlign: "center",
              margin: 0,
              fontSize: "18px",
              fontWeight: "bold",
              color: "#333",
              fontFamily: "Arial, sans-serif"
            }}>월간 데이터</h3>
          </div>
          <Plot
            data={[{
              ...monthlyTrace,
              fill: 'tozeroy',
              fillcolor: 'rgba(186, 104, 200, 0.1)',
              line: { color: 'rgb(186, 104, 200)' }
            }]}
            layout={{
              xaxis: { 
                title: {
                  text: "월간",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                }
              },
              yaxis: { 
                title: {
                  text: "매출",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                },
                type: "linear"
              },
              width: 600,
              height: 380,
              margin: { t: 20, r: 30, l: 60, b: 40 }
            }}
          />
        </div>
      </div>

      {/* 급상승 품목 */}
      <div style={KPI_ALL_STYLE}>
        <h2 style={TITLE_STYLE}>
          매출 급상승 품목 
          <svg 
            style={{
              width: "24px",
              height: "24px",
              marginLeft: "8px",
              verticalAlign: "middle"
            }}
            viewBox="0 0 24 24"
            fill="none"
            stroke="#FF6B6B"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M23 6L13.5 15.5L8.5 10.5L1 18" />
            <polyline points="17 6 23 6 23 12" />
          </svg>
        </h2>
        <div style={{
          display: "flex",
          flexDirection: "row",
          overflow: "hidden",
          width: "1350px",
          margin: "auto",
          justifyContent: "center",
          position: "relative",
          padding: "20px 0",
          // 더 연한 회색으로 변경
          background: "linear-gradient(to right, rgba(244, 246, 248, 0.6), rgba(244, 246, 248, 0.4))",
          borderRadius: "25px",
          boxShadow: "inset 0 0 15px rgba(244, 246, 248, 0.8)",
          border: "1px solid rgba(244, 246, 248, 0.8)"
        }}>
          {/* 왼쪽 페이드 효과 */}
          <div style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: "100px",
            height: "100%",
            background: "linear-gradient(to right, rgba(255,255,255,1), rgba(255,255,255,0))",
            zIndex: 1
          }} />
          
          {/* 오른쪽 페이드 효과 */}
          <div style={{
            position: "absolute",
            right: 0,
            top: 0,
            width: "100px",
            height: "100%",
            background: "linear-gradient(to left, rgba(255,255,255,1), rgba(255,255,255,0))",
            zIndex: 1
          }} />

          <div style={{
            display: "flex",
            animation: "slide 30s linear infinite",  // 시간 증가
            whiteSpace: "nowrap"
          }}>
            {/* 아이템을 3번 반복하여 더 자연스러운 루프 생성 */}
            {[...rising.subcat_list, ...rising.subcat_list, ...rising.subcat_list].map((subcat, idx) => (
              <div 
                key={idx} 
                style={{
                  ...itemStyle,
                  margin: "5px 10px"
                }}
              >
                {subcat}
              </div>
            ))}
          </div>
          <style>
            {`
              @keyframes slide {
                0% {
                  transform: translateX(0);
                }
                100% {
                  transform: translateX(calc(-225px * ${rising.subcat_list.length}));
                }
              }
            `}
          </style>
        </div>
      </div>

      {/* 상위/하위 10개 */}
      <div style={ROW_STYLE}>
        <div style={{
          ...SECTION_STYLE,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center'
        }}>
          <Plot
            data={[top10Trace]}
            layout={{
              title: {
                text: topTitle,
                font: { size: 18, color: '#333', family: "Arial, sans-serif", weight: "bold" }
              },
              xaxis: { 
                title: {
                  text: "매출액",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                }
              },
              yaxis: {
                title: {
                  text: "ID",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                },
                type: "category"
              },
              title_x: 0.5,
              height: 600,
              margin: { l: 50, r: 50, t: 200, b: 100 }
            }}
          />
        </div>
        <div style={{
          ...SECTION_STYLE,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center'
        }}>
          <Plot
            data={[bottom10Trace]}
            layout={{
              title: {
                text: bottomTitle,
                font: { size: 18, color: '#333', family: "Arial, sans-serif", weight: "bold" }
              },
              xaxis: { 
                title: {
                  text: "매출액",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                }
              },
              yaxis: {
                title: {
                  text: "ID",
                  font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                },
                type: "category"
              },
              title_x: 0.5,
              height: 600,
              margin: { l: 50, r: 50, t: 200, b: 100 }
            }}
          />
        </div>
      </div>

      {/* 트렌드/리콜 상품 */}
      <div style={ROW_STYLE}>
        <div style={SECTION_STYLE}>
          <h2 style={{ textAlign: "center", fontWeight: "bold" }}>트렌드 상품</h2>
          <div style={{
            height: "400px",
            display: "flex",
            justifyContent: "center",
            alignItems: "center"
          }}>
            <img
              src="https://img1.daumcdn.net/thumb/R720x0.q80/?scode=mtistory2&fname=https%3A%2F%2Ft1.daumcdn.net%2Fcfile%2Ftistory%2F9994274C5AE78D7305"
              alt="trend"
              style={{
                width: "200px",
                height: "200px",
                objectFit: "contain"
              }}
            />
          </div>
        </div>
        <div style={SECTION_STYLE}>
          <h2 style={{ textAlign: "center", fontWeight: "bold" }}>리콜 상품</h2>
          <div style={{
            height: "400px",
            display: "flex",
            justifyContent: "center",
            alignItems: "center"
          }}>
            <img
              src="https://i.pinimg.com/originals/af/51/13/af5113b12c2e068f9f675dfbed16e4ad.gif"
              alt="recall"
              style={{
                width: "200px",
                height: "200px",
                objectFit: "contain"
              }}
            />
          </div>
        </div>
      </div>

      {/* 파이차트 + 재고수량 */}
      <div style={ROW_STYLE}>
        <div style={{
          ...SECTION_STYLE,
          width: "38%",
          height: "400px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          position: "relative"
        }}>
          <h2 style={{ 
            textAlign: "center", 
            fontWeight: "bold",
            position: "absolute",
            top: "20px",
            width: "100%"
          }}>카테고리별 매출 파이차트</h2>
          <Plot
            data={[{
              ...pieData[0],
              hole: 0.4,
              pull: pieData[0].values.map((val, idx) => 
                idx === pieData[0].values.indexOf(Math.max(...pieData[0].values)) ? 0.1 : 0
              ),
              marker: {
                colors: [
                  '#FF8BA7',  // 부드러운 로즈
                  '#7EC4CF',  // 청록색
                  '#FFB347',  // 밝은 주황
                  '#98D8C1',  // 민트
                  '#B5A8FF'   // 라벤더
                ]
              },
              type: 'pie',
              shadow: 0.5,
              scalegroup: 1
            }]}
            layout={{
              width: 600,
              height: 500,
              showlegend: true,
              legend: {
                orientation: "v",
                xanchor: "left",
                yanchor: "middle",
                x: 1.2,
                y: 0.5
              },
              margin: { l: 50, r: 200, t: 50, b: 50 },
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              scene: {
                camera: {
                  eye: { x: 2, y: 2, z: 2 }
                }
              }
            }}
          />
        </div>
        <div style={{
          ...SECTION_STYLE,
          width: "58%",
          overflowY: "auto",
          height: "400px"
        }}>
          <h2 style={{ textAlign: "center", fontWeight: "bold" }}>재고수량</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "center" }}>
            <thead style={{ backgroundColor: "#f4f4f4" }}>
              <tr>
                <th style={{ border: "1px solid #ccc" }}>ID</th>
                <th style={{ border: "1px solid #ccc" }}>상품명</th>
                <th style={{ border: "1px solid #ccc" }}>재고수량</th>
                <th style={{ border: "1px solid #ccc" }}>일판매수량</th>
                <th style={{ border: "1px solid #ccc" }}>남은 재고</th>
              </tr>
            </thead>
            <tbody>
              {lowStock.map((item, idx) => (
                <tr key={idx}>
                  <td style={{ border: "1px solid #ccc" }}>{item.ID}</td>
                  <td style={{ border: "1px solid #ccc" }}>{item.Sub3}</td>
                  <td style={{ border: "1px solid #ccc" }}>{item.재고수량}</td>
                  <td style={{ border: "1px solid #ccc" }}>{item.일판매수량}</td>
                  <td style={{ border: "1px solid #ccc" }}>{item["남은 재고"]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div> } />
    <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </Router>
  );
}

export default App;