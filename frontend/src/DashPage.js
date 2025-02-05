import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';

////////////////////////////////////////
// 1) 스타일 상수
////////////////////////////////////////

const PAGE_STYLE = {
  backgroundColor: "#f4f4f9",
  padding: "20px",
  fontFamily: "Arial, sans-serif",
  fontSize: "18px"
};

const TITLE_STYLE = {
  textAlign: "center",
  fontSize: "24px",
  color: "#333",
  fontWeight: "bold",
  marginTop: "30px",
  marginBottom: "30px"
};

const ROW_STYLE = {
  display: "flex",
  flexWrap: "wrap",
  justifyContent: "space-evenly",
  gap: "10px",
  alignItems: "center"
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
const GRAPH_STYLE = {
  margin: "20px",
  padding: "20px",
  backgroundColor: "#ffffff",
  borderRadius: "10px",
  boxShadow: "0px 4px 10px rgba(0, 0, 0, 0.1)"
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

// 공통 박스 스타일
const BOX_CONTAINER_STYLE = {
  width: "400px",
  height: "400px",           // 원하는 동일 높이로 지정
  minWidth: "300px",
  backgroundColor: "#fff",
  borderRadius: "12px",
  boxShadow: "0 4px 10px rgba(0,0,0,0.1)",
  padding: "20px",
  textAlign: "left",
  margin: "10px",
  display: "flex",
  flexDirection: "column",
  justifyContent: "space-between",
  overflow: "auto"   // 내용이 넘칠 경우 자동 스크롤 (필요 시)
};


// 색상 배열 (reds, blues)
const reds = [
  "#D14B4B", "#E22B2B", "#E53A3A", "#F15D5D", "#F67878",
  "#F99A9A", "#FBB6B6", "#FDC8C8", "#FEE0E0", "#FEEAEA"
];
const blues = [
  '#B0D6F1', '#A5C9E9', '#99BCE1', '#8DB0D9', '#81A4D1',
  '#7498C9', '#688BC1', '#5C7FB9', '#5073B1', '#4567A9'
];

// 화폐 포맷
function formatCurrency(value) {
  if (typeof value !== "number") return "₩0원";
  return "₩" + value.toLocaleString() + "원";
}

////////////////////////////////////////
// Watchlist 스타일
////////////////////////////////////////

const WATCHLIST_CONTAINER_STYLE = {
  ...BOX_CONTAINER_STYLE  // 공통 스타일로 동일 크기 적용
};

const WATCHLIST_HEADER_STYLE = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "16px"
};

const WATCHLIST_TITLE_STYLE = {
  fontSize: "18px",
  fontWeight: "bold",
  color: "#333"
};

const WATCHLIST_ITEM_STYLE = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "8px 0",
  borderBottom: "1px solid #f0f0f0",
  fontSize: "15px"
};
const WATCHLIST_ITEM_LEFT_STYLE = {
  display: "flex",
  alignItems: "center"
};
const WATCHLIST_LOGO_STYLE = {
  width: "32px",
  height: "32px",
  borderRadius: "50%",
  marginRight: "8px",
  objectFit: "cover"
};
const WATCHLIST_ITEM_NAME_STYLE = {
  fontWeight: "bold"
};
const WATCHLIST_ITEM_SUBNAME_STYLE = {
  fontSize: "13px",
  color: "#999"
};
const WATCHLIST_ITEM_RIGHT_STYLE = {
  textAlign: "right"
};
const WATCHLIST_PRICE_STYLE = {
  fontWeight: "bold",
  color: "#333"
};
const WATCHLIST_DIFF_STYLE = (isPositive) => ({
  fontSize: "13px",
  color: isPositive ? "#28a745" : "#dc3545"
});

////////////////////////////////////////
// 2) KpiCard (그래프 포함) - 공통 박스
////////////////////////////////////////
const KPI_CARD_CONTAINER_STYLE = {
  ...BOX_CONTAINER_STYLE  // KPI 카드도 동일 크기
};

const KPI_CARD_TITLE_STYLE = {
  fontSize: "16px",
  color: "#666",
  marginBottom: "8px"
};
const KPI_MAIN_VALUE_STYLE = {
  fontSize: "28px",
  fontWeight: "bold",
  color: "#333",
  margin: 0
};
const KPI_DIFF_CONTAINER_STYLE = {
  display: "flex",
  alignItems: "center",
  marginTop: "4px",
  marginBottom: "8px"
};
const KPI_DIFF_PERCENT_STYLE = (isPositive) => ({
  color: isPositive ? "#28a745" : "#dc3545",
  fontWeight: "bold",
  fontSize: "16px",
  marginRight: "8px"
});
const KPI_DIFF_TEXT_STYLE = {
  fontSize: "14px",
  color: "#888"
};
const KPI_GRAPH_WRAPPER_STYLE = {
  width: "100%",
  height: "auto",
  marginTop: "10px"
};
// 아이템들을 감싸는 컨테이너
const WATCHLIST_ITEMS_CONTAINER = {
  flex: 1,
  display: "flex",
  flexDirection: "column"
};
function KpiCard({
  title,
  currentValue,
  diffValue,
  diffPercent,
  prevLabel,
  plotData,
  plotLayout
}) {
  const isPositive = diffValue >= 0;
  const diffPctStr = diffPercent >= 0
    ? `+${diffPercent.toFixed(2)}%`
    : `${diffPercent.toFixed(2)}%`;
  const diffAbs = Math.abs(diffValue).toLocaleString();
  const moreOrLess = isPositive ? "more" : "less";
  const diffText = `${diffAbs} ${moreOrLess} ${prevLabel}`;

  return (
    <div style={KPI_CARD_CONTAINER_STYLE}>
      <div style={KPI_CARD_TITLE_STYLE}>{title}</div>
      <h2 style={KPI_MAIN_VALUE_STYLE}>{formatCurrency(currentValue)}</h2>

      <div style={KPI_DIFF_CONTAINER_STYLE}>
        <span style={KPI_DIFF_PERCENT_STYLE(isPositive)}>
          {diffPctStr}
        </span>
        <span style={KPI_DIFF_TEXT_STYLE}>{diffText}</span>
      </div>

      <div style={KPI_GRAPH_WRAPPER_STYLE}>
        <Plot
          data={plotData}
          layout={plotLayout}
          config={{ displayModeBar: false }}
        />
      </div>
    </div>
  );
}

////////////////////////////////////////
// 3) WatchListItem
////////////////////////////////////////
function WatchListItem({ item }) {
  // 예: item = { icon, symbol, name, price, diff }
  const { icon, symbol, name, price, diff } = item;
  const isPositive = diff >= 0;
  const diffStr = diff >= 0 ? `+${diff.toFixed(2)}%` : `${diff.toFixed(2)}%`;

  return (
    <div style={WATCHLIST_ITEM_STYLE}>
      <div style={WATCHLIST_ITEM_LEFT_STYLE}>
        {icon && (
          <img
            src={icon}
            alt={symbol}
            style={WATCHLIST_LOGO_STYLE}
          />
        )}
        <div>
          <div style={WATCHLIST_ITEM_NAME_STYLE}>{symbol}</div>
          <div style={WATCHLIST_ITEM_SUBNAME_STYLE}>{name}</div>
        </div>
      </div>
      <div style={WATCHLIST_ITEM_RIGHT_STYLE}>
        <div style={WATCHLIST_PRICE_STYLE}>
          {formatCurrency(price)}
        </div>
        <div style={WATCHLIST_DIFF_STYLE(isPositive)}>
          {diffStr}
        </div>
      </div>
    </div>
  );
}

////////////////////////////////////////
// 4) AnimatedGraph
////////////////////////////////////////
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

////////////////////////////////////////
// 5) 메인 컴포넌트 (DashPage)
////////////////////////////////////////
function DashPage() {
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

  // 예: 상위 5개 트렌드 상품 (Watchlist 용)
  // 실제로는 서버 API 등에서 가져오거나, rising 등에서 가공해도 됨
  const [topTrends, setTopTrends] = useState([
    {
      icon: "https://img1.daumcdn.net/thumb/C500x500.fjpg/?fname=http://t1.daumcdn.net/brunch/service/user/c86j/image/MwGCP7OUtNBhaP4LtP1Xcebp3tM.heic",
      symbol: "Chii guy",
      name: "Chii guy",
      price: 310.4,
      diff: -1.10
    },
    {
      icon: "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTnhP--FPnVg3t9DG_HBf3CnzIzJotRvgvyhw&s",
      symbol: "햄부기햄북",
      name: "햄북어 햄북스딱스",
      price: 132.72,
      diff: -10.29
    },
    {
      icon: "https://i.namu.wiki/i/Fi8DbSs6wIjHBuahitiQFyVotJmhsO2TekpgBrNPmJK3zdMRrWii_itgMVL4Xo4Tnwou-pI-JzKWeBJ1h--tYA.webp",
      symbol: "부끄핑",
      name: "부끄부끄핑",
      price: 28.57,
      diff: -6.48
    },
    {
      icon: "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQpxqifC-I6Ir6463ZZvSIhIk44TUIf7odGhw&s",
      symbol: "CALM",
      name: "chimchackman",
      price: 71.86,
      diff: 0.98
    },
    {
      icon: "https://mblogthumb-phinf.pstatic.net/MjAyMTA4MjJfMTYw/MDAxNjI5NTYwODY2MjI0.Vco-WmnxXlIRj08eYipQIVjzvUgeAGrIKZDSPmwvcnog.yzwYknZ2eUK5ZnNyz4nRSxXNoyPYDRC_a8RgPeqRCA8g.JPEG.chooddingg/output_4182079403.jpg?type=w800",
      symbol: "MUDO",
      name: "mudo_myungsu",
      price: 87.66,
      diff: -3.86
    }
  ]);

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

  // (증감률 계산, 그래프 setup 등)--------------------------------------------
  // 예: 일/주/월 계산
  function getLatestAndPrevValue(arr, valKey = "값") {
    const len = arr.length;
    if (len < 2) return { current: 0, prev: 0 };
    return {
      current: arr[len - 1][valKey],
      prev: arr[len - 2][valKey]
    };
  }

  // 일간
  const dailyVals = getLatestAndPrevValue(dailyData);
  const dailyDiff = dailyVals.current - dailyVals.prev;
  const dailyDiffPct = dailyVals.prev ? (dailyDiff / dailyVals.prev) * 100 : 0;
  const dailyTrace = {
    x: dailyData.map(d => d.날짜),
    y: dailyData.map(d => d.값),
    type: "scatter",
    mode: "lines"
  };
  const dailyPlotData = [
    {
      ...dailyTrace,
      fill: 'tozeroy',
      fillcolor: 'rgba(64, 181, 246, 0.1)',
      line: { color: 'rgb(64, 181, 246)', width: 2 }
    }
  ];
  const dailyPlotLayout = {
    xaxis: { title: { text: "일간", font: { size: 14 } } },
    yaxis: { title: { text: "매출", font: { size: 14 } }, type: "linear" },
    width: 400,
    height: 300,
    margin: { t: 30, r: 20, l: 50, b: 40 },
    title: {
      text: "일간 매출 그래프",
      font: { size: 16, color: "#333" }
    }
  };

  // 주간
  const weeklyVals = getLatestAndPrevValue(weeklyData);
  const weeklyDiff = weeklyVals.current - weeklyVals.prev;
  const weeklyDiffPct = weeklyVals.prev ? (weeklyDiff / weeklyVals.prev) * 100 : 0;
  const weeklyTrace = {
    x: weeklyData.map(d => d.주간),
    y: weeklyData.map(d => d.값),
    type: "scatter",
    mode: "lines"
  };
  const weeklyPlotData = [
    {
      ...weeklyTrace,
      fill: 'tozeroy',
      fillcolor: 'rgba(129, 199, 132, 0.1)',
      line: { color: 'rgb(129, 199, 132)', width: 2 }
    }
  ];
  const weeklyPlotLayout = {
    xaxis: { title: { text: "주간", font: { size: 14 } } },
    yaxis: { title: { text: "매출", font: { size: 14 } }, type: "linear" },
    width: 400,
    height: 300,
    margin: { t: 30, r: 20, l: 50, b: 40 },
    title: {
      text: "주간 매출 그래프",
      font: { size: 16, color: "#333" }
    }
  };

  // 월간
  const monthlyVals = getLatestAndPrevValue(monthlyData);
  const monthlyDiff = monthlyVals.current - monthlyVals.prev;
  const monthlyDiffPct = monthlyVals.prev ? (monthlyDiff / monthlyVals.prev) * 100 : 0;
  const monthlyTrace = {
    x: monthlyData.map(d => d.월간),
    y: monthlyData.map(d => d.값),
    type: "scatter",
    mode: "lines"
  };
  const monthlyPlotData = [
    {
      ...monthlyTrace,
      fill: 'tozeroy',
      fillcolor: 'rgba(186, 104, 200, 0.1)',
      line: { color: 'rgb(186, 104, 200)', width: 2 }
    }
  ];
  const monthlyPlotLayout = {
    xaxis: { title: { text: "월간", font: { size: 14 } } },
    yaxis: { title: { text: "매출", font: { size: 14 } }, type: "linear" },
    width: 400,
    height: 300,
    margin: { t: 30, r: 20, l: 50, b: 40 },
    title: {
      text: "월간 매출 그래프",
      font: { size: 16, color: "#333" }
    }
  };

  ////////////////////////////////////////
  // 파이차트
  ////////////////////////////////////////
  const pieData = [
    {
      labels: categoryPie.map(c => c.대분류),
      values: categoryPie.map(c => c.매출액),
      type: "pie"
    }
  ];

  ////////////////////////////////////////
  // 상/하위 10
  ////////////////////////////////////////
  function getVal(obj) {
    return lastMonthCol ? (obj[lastMonthCol] || 0) : 0;
  }
  const sortedTop10 = [...top10].sort((a, b) => getVal(a) - getVal(b)).slice(0, 10);
  const sortedBottom10 = [...bottom10].sort((a, b) => getVal(b) - getVal(a)).slice(0, 10);

  const topIDs = sortedTop10.map(item => item.ID);
  const topVals = sortedTop10.map(item => getVal(item));
  const topColors = sortedTop10.map((item, i) => reds[reds.length - 1 - i] || "#FEEAEA");
  const bottomIDs = sortedBottom10.map(item => item.ID);
  const bottomVals = sortedBottom10.map(item => getVal(item));
  const bottomColors = sortedBottom10.map((item, i) => blues[i] || "#4567A9");

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

  // (급상승 품목) CSS
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
      0 20px 25px -5px rgba(255, 107, 107, 0.35),
      0 15px 15px -8px rgba(255, 160, 122, 0.25),
      0 8px 12px rgba(0,0,0,0.15),
      inset 0 -4px 8px rgba(0,0,0,0.2),
      inset 0 4px 8px rgba(255,255,255,0.3),
      inset 2px 0 4px rgba(255,255,255,0.1),
      inset -2px 0 4px rgba(0,0,0,0.1)
    `,
    transform: `
      translateY(-4px)
      perspective(1000px)
      rotateX(2deg)
    `,
    border: "1px solid rgba(255,255,255,0.3)",
    transition: "all 0.3s ease",
    marginRight: "15px",
    textShadow: "0 2px 4px rgba(0,0,0,0.2)",
    position: "relative",
    overflow: "hidden",
    backfaceVisibility: "hidden",
    transformStyle: "preserve-3d",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    padding: "10px",
    textAlign: "center",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center"
  };

  // CSS 키프레임
  const styles = `
    @keyframes shine {
      0% { left: -100%; }
      20% { left: 100%; }
      100% { left: 100%; }
    }
  `;
  document.head.appendChild(document.createElement('style')).textContent = styles;

  ////////////////////////////////////////
  // 렌더링
  ////////////////////////////////////////
  return (
    <div style={PAGE_STYLE}>
      <h1 style={TITLE_STYLE}>데이터 대시보드</h1>

      {/* KPI 카드 4개 가로 정렬 */}
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        width: "80%", // 🔹 가로 크기 조정 (너무 길지 않게)
        margin: "30px auto",
        gap: "15px"  // 🔹 카드 사이 여백 조정
      }}>
        {[
          { title: "연간 매출", value: kpis.annual_sales, diff: 0 }, // 연간 매출은 증감률 없음
          { title: "일간 매출", value: dailyVals.current, diff: dailyDiffPct },
          { title: "주간 매출", value: monthlyVals.current, diff: monthlyDiffPct },
          { title: "월간 매출", value: weeklyVals.current, diff: weeklyDiffPct }
        ].map(({ title, value, diff }, idx) => (
          <div key={idx} style={{
            backgroundColor: "#f8f9fa",  // 🔹 배경색 조정
            borderRadius: "10px",
            boxShadow: "0px 4px 10px rgba(0, 0, 0, 0.1)",
            padding: "15px 20px",
            width: "23%",  // 🔹 크기 고정
            minWidth: "180px",
            textAlign: "left"
          }}>
            {/* 타이틀 */}
            <h3 style={{
              fontSize: "12px",      // 🔹 글자 크기 조정
              fontWeight: "bold",
              color: "#777",
              marginBottom: "8px",
              letterSpacing: "1px",  // 🔹 대문자 간격 추가
              textTransform: "uppercase"
            }}>
              {title}
            </h3>

            {/* KPI 값 + 증감율을 한 줄에 배치 */}
            <div style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between"
            }}>
              {/* KPI 값 */}
              <h2 style={{
                fontSize: "24px",    // 🔹 숫자 크기 줄임
                fontWeight: "bold",
                color: "#222",
              }}>
                {formatCurrency(value)}
              </h2>

              {/* 증감률 표시 (연간 매출 제외) */}
              {diff !== null && (
                <p style={{
                  fontSize: "12px", // 🔹 증감률 폰트 크기 조정
                  fontWeight: "bold",
                  color: diff >= 0 ? "#dc3545" : "#007bff",
                  marginLeft: "10px" // 🔹 오른쪽 정렬을 위해 여백 추가
                }}>
                  {diff >= 0 ? `+${diff.toFixed(2)}% ↑` : `${diff.toFixed(2)}% ↓`}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* (급상승 품목 슬라이드) */}
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
          background: "linear-gradient(to right, rgba(244, 246, 248, 0.6), rgba(244, 246, 248, 0.4))",
          borderRadius: "25px",
          boxShadow: "inset 0 0 15px rgba(244, 246, 248, 0.8)",
          border: "1px solid rgba(244, 246, 248, 0.8)"
        }}>
          <div style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: "100px",
            height: "100%",
            background: "linear-gradient(to right, rgba(255,255,255,1), rgba(255,255,255,0))",
            zIndex: 1
          }} />
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
            animation: "slide 30s linear infinite",
            whiteSpace: "nowrap"
          }}>
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

      {/* 상/하위 10개 */}
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
                  '#FF8BA7',
                  '#7EC4CF',
                  '#FFB347',
                  '#98D8C1',
                  '#B5A8FF'
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
    </div>
  );
}

export default DashPage;
