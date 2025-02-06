import React, { useEffect, useState, useRef, useMemo, Suspense, lazy } from 'react';
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
  width: "95%",
  maxWidth: "2100px",
  margin: "20px auto",
  display: "flex",
  justifyContent: "center",
  alignItems: "center"
};

const GRAPH_STYLE = {
  margin: "20px",
  padding: "20px",
  backgroundColor: "#ffffff",
  borderRadius: "10px",
  boxShadow: "0px 4px 10px rgba(0, 0, 0, 0.1)"
};

const KPI_ALL_STYLE = {
  width: "95%",  // KPI 카드들과 동일한 너비
  maxWidth: "2100px",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  padding: "10px 20px",  // 좌우 패딩 추가
  margin: "0 auto"  // 중앙 정렬
};

// 공통 박스 스타일
const BOX_CONTAINER_STYLE = {
  width: "400px",
  height: "600px",  // 동일한 높이 설정
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
  overflow: "auto"
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
  ...BOX_CONTAINER_STYLE,
  height: "600px"  // 매출 그래프와 동일한 높이
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
  padding: "15px 0",
  borderBottom: "1px solid #f0f0f0",
  fontSize: "16px"
};
const WATCHLIST_ITEM_LEFT_STYLE = {
  display: "flex",
  alignItems: "center"
};
const WATCHLIST_LOGO_STYLE = {
  width: "40px",
  height: "40px",
  borderRadius: "50%",
  marginRight: "12px",
  objectFit: "cover"
};
const WATCHLIST_ITEM_NAME_STYLE = {
  fontWeight: "bold",
  fontSize: "16px"
};
const WATCHLIST_ITEM_SUBNAME_STYLE = {
  fontSize: "14px",
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

// LazyPlot 컴포넌트 정의
const LazyPlot = lazy(() => import('react-plotly.js'));

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
  const [rising, setRising] = useState({ subcat_list: [] });

  // 상/하위 10 (이전 코드 그대로 사용)
  const [top10, setTop10] = useState([]);
  const [bottom10, setBottom10] = useState([]);
  const [lastMonthCol, setLastMonthCol] = useState("");

  // 예: 상위 5개 트렌드 상품 (Watchlist 용)
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
        // now risingRes.data is { subcategories: [ { name, rise_ratio }, ... ] }
        setRising(risingRes.data);

        const topBottomRes = await axios.get(`${API_BASE}/api/topbottom`);
        setTop10(topBottomRes.data.top_10 || []);
        setBottom10(topBottomRes.data.bottom_10 || []);
        setLastMonthCol(topBottomRes.data.last_month_col || "");

        const topSalesRes = await axios.get(`${API_BASE}/api/top-sales-items`);
        setTopSalesItems(topSalesRes.data);
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
  // 상/하위 10 -> 여기서는 Top3와 Bottom3로 수정
  ////////////////////////////////////////
  function getVal(obj) {
    return lastMonthCol ? (obj[lastMonthCol] || 0) : 0;
  }
  // 1) 매출 내림차순 정렬 후 상위 3개 추출
  const sortedTop3 = [...top10]
    .sort((a, b) => getVal(b) - getVal(a))
    .slice(0, 3);

  // 2) 포디엄 순서 [2등, 1등, 3등] 으로 재배치
  const bestPodiumOrder =
    sortedTop3.length === 3
      ? [sortedTop3[1], sortedTop3[0], sortedTop3[2]]
      : sortedTop3;

  // 3) 각 순위별 "블록 높이"를 다르게 설정
  //    (예: 1등이 가장 높고, 2등이 중간, 3등이 낮음)
  const bestHeightMap = {
    1: "200px", // 1등 크게
    2: "150px",
    3: "120px"
  };
  const bestColorMap = {
    1: "#ffef99",  // 1등
    2: "#cfcfcf",  // 2등
    3: "#ffd1a9"   // 3등
  };
  // 1) 매출 오름차순 정렬 후 하위 3개 추출
  //    => [0] = 가장 낮은 매출(=1등)
  const sortedBottom3 = [...bottom10]
    .sort((a, b) => getVal(a) - getVal(b))
    .slice(0, 3);

  // 2) 포디엄 순서 [2등, 1등, 3등] 으로 재배치
  const worstPodiumOrder =
    sortedBottom3.length === 3
      ? [sortedBottom3[1], sortedBottom3[0], sortedBottom3[2]]
      : sortedBottom3;

  // 3) 각 순위별 블록 높이 (이번에는 1등이 가장 낮게)
  const worstHeightMap = {
    1: "100px",  // 1등(최저)
    2: "140px",
    3: "180px"   // 3등(가장 높게)
  };
  const worstColorMap = {
    1: "#ffdce0", // 1등
    2: "#ffe6e9", // 2등
    3: "#fff0f2"  // 3등
  };
  // 상위/하위 Top3를 위한 트레이스 생성 (아래에서 사용)
  const top10Trace = {
    x: bestPodiumOrder.map(item => getVal(item)),
    y: bestPodiumOrder.map(item => item.ID),
    type: "bar",
    orientation: "h",
    marker: { color: bestPodiumOrder.map((_, i) => reds[reds.length - 1 - i] || "#FEEAEA") }
  };

  const bottom10Trace = {
    x: worstPodiumOrder.map(item => getVal(item)),
    y: worstPodiumOrder.map(item => item.ID),
    type: "bar",
    orientation: "h",
    marker: { color: worstPodiumOrder.map((_, i) => blues[i] || "#4567A9") }
  };

  const topTitle = lastMonthCol
    ? `${lastMonthCol} 월 매출 상위 3개 ID`
    : "상위 3개";
  const bottomTitle = lastMonthCol
    ? `${lastMonthCol} 월 매출 하위 3개 ID`
    : "하위 3개";

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
  const [selectedPeriod, setPeriod] = useState("일간");
  const [topSalesItems, setTopSalesItems] = useState([]);

  // 최다 매출 상품 데이터만 별도로 빠르게 fetch
  useEffect(() => {
    const fetchTopSales = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/top-sales-items`, {
          // timeout 설정 및 우선순위 높임
          timeout: 3000,
          headers: {
            'Priority': 'high'
          }
        });
        
        // 데이터 가공을 최소화
        const items = response.data.map(item => ({
          ...item,
          // 필요한 속성만 추출
          id: item.id,
          name: item.name,
          change_rate: item.change_rate
        }));
        
        setTopSalesItems(items);
      } catch (error) {
        console.error('Error fetching top sales items:', error);
        setTopSalesItems([]); // 에러 시 빈 배열로 설정
      }
    };

    fetchTopSales();
  }, []); // 독립적인 useEffect로 분리

  // TopSalesItem 컴포넌트 메모이제이션
  const MemoizedTopSalesItem = useMemo(() => React.memo(({ item }) => {
    const isPositive = item.change_rate >= 0;
    
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '25px',
        backgroundColor: 'white',
        borderRadius: '16px',
        boxShadow: '0 8px 16px rgba(0, 0, 0, 0.08)',
        margin: '10px',
        width: 'calc(20% - 30px)',
        minWidth: '300px',
        height: '140px'
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ 
            fontWeight: '600', 
            fontSize: '18px',
            marginBottom: '12px',
            color: '#2c3e50'
          }}>
            {item.name}
          </div>
          <div style={{
            color: isPositive ? '#dc3545' : '#007bff',
            fontWeight: '600',
            fontSize: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            {isPositive ? '↑' : '↓'} 
            {Math.abs(item.change_rate).toFixed(1)}%
          </div>
        </div>
        <div style={{ width: '150px', height: '80px' }}>
          <Suspense fallback={
            <div style={{ 
              width: '100%', 
              height: '100%', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              backgroundColor: '#f8f9fa',
              borderRadius: '8px'
            }}>
              <span>Loading...</span>
            </div>
          }>
            <LazyPlot 
              data={[{
                y: Array.from({ length: 20 }, (_, i) => {
                  const trend = item.change_rate >= 0 ? 1 : -1;
                  return 50 + trend * (Math.random() * 15 + Math.sin(i/3) * 10 + i * 2);
                }),
                type: 'scatter',
                mode: 'lines',
                fill: 'tonexty',
                line: {
                  color: isPositive ? '#dc3545' : '#007bff',
                  width: 2,
                  shape: 'spline'
                },
                fillcolor: isPositive ? 'rgba(220, 53, 69, 0.1)' : 'rgba(0, 123, 255, 0.1)'
              }]}
              layout={{
                width: 150,
                height: 80,
                margin: { l: 0, r: 0, t: 0, b: 0 },
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                xaxis: { visible: false, showgrid: false },
                yaxis: { visible: false, showgrid: false }
              }}
              config={{ displayModeBar: false }}
            />
          </Suspense>
        </div>
      </div>
    );
  }), []);

  // TopSalesItems를 감싸는 컨테이너 스타일
  const TOP_SALES_CONTAINER_STYLE = {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "nowrap",
    gap: "15px",
    overflowX: "auto",
    width: "100%",  // 전체 너비 사용
    padding: "15px 0"  // 좌우 패딩 제거
  };

  // 매출 그래프와 트렌드 리스트를 감싸는 컨테이너 스타일 수정
  const GRAPH_SECTION_STYLE = {
    ...SECTION_STYLE,
    display: "flex",
    justifyContent: "space-between",
    gap: "20px"
  };

  return (
    <div style={PAGE_STYLE}>
      <h1 style={TITLE_STYLE}>데이터 대시보드</h1>

      {/* KPI 카드 4개 가로 정렬 */}
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        width: "95%",
        maxWidth: "2100px",
        margin: "30px auto",
        gap: "15px"
      }}>
        {[
          { title: "연간 매출", value: kpis.annual_sales, diff: 0 }, // 연간 매출은 증감률 없음
          { title: "일간 매출", value: dailyVals.current, diff: dailyDiffPct },
          { title: "주간 매출", value: monthlyVals.current, diff: monthlyDiffPct },
          { title: "월간 매출", value: weeklyVals.current, diff: weeklyDiffPct }
        ].map(({ title, value, diff }, idx) => (
          <div key={idx} style={{
            backgroundColor: "#f8f9fa",
            borderRadius: "10px",
            boxShadow: "0px 4px 10px rgba(0, 0, 0, 0.1)",
            padding: "15px 20px",
            width: "calc(25% - 15px)",
            minWidth: "200px"
          }}>
            {/* 타이틀 */}
            <h3 style={{
              fontSize: "12px",
              fontWeight: "bold",
              color: "#777",
              marginBottom: "8px",
              letterSpacing: "1px",
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
                fontSize: "24px",
                fontWeight: "bold",
                color: "#222",
              }}>
                {formatCurrency(value)}
              </h2>

              {/* 증감률 표시 (연간 매출 제외) */}
              {diff !== null && (
                <p style={{
                  fontSize: "12px",
                  fontWeight: "bold",
                  color: diff >= 0 ? "#dc3545" : "#007bff",
                  marginLeft: "10px"
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
        <h2 style={TITLE_STYLE}>최근 3개월 최다 매출 상품</h2>
        <div style={TOP_SALES_CONTAINER_STYLE}>
          {topSalesItems.map((item, index) => (
            <MemoizedTopSalesItem 
              key={item.id || index} 
              item={item} 
            />
          ))}
        </div>
      </div>
      {/*
        (1) 일간/주간/월간 KPI 카드 3개
        (2) 오른쪽에 "Trend-list" 박스
        => 둘 다 BOX_CONTAINER_STYLE
      */}
      <div style={GRAPH_SECTION_STYLE}>
        {/* 왼쪽: 통합 KPI 카드 */}
        <div style={{
          ...KPI_CARD_CONTAINER_STYLE,
          width: "70%",
          marginRight: "20px",
          height: "600px",
          display: "flex",
          flexDirection: "column",
          position: "relative"
        }}>
          {/* 기간 선택 버튼 컨테이너 */}
          <div style={{
            display: "flex",
            gap: "15px",
            justifyContent: "center",
            position: "absolute",
            top: "20px",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 1,
            padding: "10px 20px",
            background: "rgba(250, 250, 250, 0.95)",
            borderRadius: "30px",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.06)",
            backdropFilter: "blur(8px)",
            border: "1px solid rgba(240, 240, 240, 0.8)"
          }}>
            {["일간", "주간", "월간"].map((period) => (
              <button
                key={period}
                onClick={() => setPeriod(period)}
                style={{
                  padding: "12px 28px",
                  borderRadius: "20px",
                  border: "none",
                  background: period === selectedPeriod
                    ? "linear-gradient(145deg, #505764, #6E7A8A)"
                    : "rgba(255, 255, 255, 0.9)",
                  color: period === selectedPeriod ? "white" : "#505764",
                  cursor: "pointer",
                  transition: "all 0.3s ease",
                  fontWeight: period === selectedPeriod ? "600" : "500",
                  fontSize: "14px",
                  letterSpacing: "0.5px",
                  boxShadow: period === selectedPeriod
                    ? "0 8px 16px rgba(80, 87, 100, 0.15)"
                    : "0 4px 12px rgba(0, 0, 0, 0.03)",
                  transform: period === selectedPeriod
                    ? "translateY(-1px)"
                    : "translateY(0)",
                  position: "relative",
                  overflow: "hidden",
                  minWidth: "110px",
                  border: period === selectedPeriod
                    ? "none"
                    : "1px solid rgba(80, 87, 100, 0.12)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "'Pretendard', sans-serif",
                  WebkitFontSmoothing: "antialiased",
                  MozOsxFontSmoothing: "grayscale",
                  "&:hover": {
                    transform: period === selectedPeriod
                      ? "translateY(-1px)"
                      : "translateY(-1px)",
                    boxShadow: period === selectedPeriod
                      ? "0 10px 20px rgba(80, 87, 100, 0.2)"
                      : "0 6px 16px rgba(0, 0, 0, 0.06)",
                    background: period === selectedPeriod
                      ? "linear-gradient(145deg, #576171, #6E7A8A)"
                      : "rgba(255, 255, 255, 1)",
                  },
                  "&:active": {
                    transform: "translateY(0)",
                    boxShadow: period === selectedPeriod
                      ? "0 5px 10px rgba(80, 87, 100, 0.1)"
                      : "0 2px 8px rgba(0, 0, 0, 0.04)",
                  }
                }}
              >
                {period}
              </button>
            ))}
          </div>

          <div style={KPI_CARD_TITLE_STYLE}>매출 현황</div>

          {/* 선택된 기간에 따른 KPI 값 표시 */}
          <h2 style={KPI_MAIN_VALUE_STYLE}>
            {formatCurrency(
              selectedPeriod === "일간" ? dailyVals.current :
                selectedPeriod === "주간" ? weeklyVals.current :
                  monthlyVals.current
            )}
          </h2>

          {/* 증감률 표시 */}
          <div style={KPI_DIFF_CONTAINER_STYLE}>
            <span style={KPI_DIFF_PERCENT_STYLE(
              selectedPeriod === "일간" ? dailyDiff >= 0 :
                selectedPeriod === "주간" ? weeklyDiff >= 0 :
                  monthlyDiff >= 0
            )}>
              {selectedPeriod === "일간" ? `${dailyDiffPct >= 0 ? '+' : ''}${dailyDiffPct.toFixed(2)}%` :
                selectedPeriod === "주간" ? `${weeklyDiffPct >= 0 ? '+' : ''}${weeklyDiffPct.toFixed(2)}%` :
                  `${monthlyDiffPct >= 0 ? '+' : ''}${monthlyDiffPct.toFixed(2)}%`}
            </span>
            <span style={KPI_DIFF_TEXT_STYLE}>
              {`${Math.abs(
                selectedPeriod === "일간" ? dailyDiff :
                  selectedPeriod === "주간" ? weeklyDiff :
                    monthlyDiff
              ).toLocaleString()} ${selectedPeriod === "일간" ? "than yesterday" :
                selectedPeriod === "주간" ? "than last week" :
                  "than last month"
                }`}
            </span>
          </div>

          {/* 그래프 */}
          <div style={{
            ...KPI_GRAPH_WRAPPER_STYLE,
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center"
          }}>
            <Plot
              data={
                selectedPeriod === "일간" ? dailyPlotData :
                  selectedPeriod === "주간" ? weeklyPlotData :
                    monthlyPlotData
              }
              layout={{
                ...dailyPlotLayout,
                width: undefined,
                height: 400,
                autosize: true,
                title: {
                  text: `${selectedPeriod} 매출 그래프`,
                  font: { size: 18, color: '#333', family: "Arial, sans-serif", weight: "bold" },
                  y: 0.95
                },
                xaxis: {
                  title: {
                    text: "매출액",
                    font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                  }
                },
                yaxis: {
                  title: {
                    text: "날짜",
                    font: { size: 14, family: "Arial, sans-serif", weight: "bold" }
                  }
                },
                margin: {
                  l: 80,
                  r: 50,
                  t: 50,
                  b: 50
                },
                paper_bgcolor: 'white',
                plot_bgcolor: 'white'
              }}
              style={{ width: "100%" }}
              useResizeHandler={true}
              config={{ displayModeBar: false, responsive: true }}
            />
          </div>
        </div>

        {/* 오른쪽: Trend-list (Watchlist) */}
        <div style={WATCHLIST_CONTAINER_STYLE}>
          <div style={WATCHLIST_HEADER_STYLE}>
            <div style={WATCHLIST_TITLE_STYLE}>Trend-list</div>
          </div>
          <div style={WATCHLIST_ITEMS_CONTAINER}>
            {topTrends.slice(0, 5).map((item, idx) => (
              <WatchListItem key={idx} item={item} />
            ))}
          </div>
        </div>
      </div>

      {/* Best Top 3 & Worst Top 3 중앙 정렬 */}
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: "40px",
        marginTop: "20px"
      }}>
        {/* Best Top 3 */}
        <div style={{
          ...SECTION_STYLE,
          flex: 1,
          maxWidth: "500px",
          height: "400px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center"
        }}>
          <h2 style={TITLE_STYLE}>매출 Best Top 3 🏆</h2>
          <div style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "flex-end",
            gap: "20px"
          }}>
            {bestPodiumOrder.map((item, idx) => {
              const rank = idx === 0 ? 2 : idx === 1 ? 1 : 3;
              return (
                <div key={item.ID} style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "flex-end",
                  width: "80px",
                  height: bestHeightMap[rank],
                  backgroundColor: bestColorMap[rank],
                  borderRadius: "10px",
                  padding: "10px",
                  boxShadow: rank === 1
                    ? "0 0 10px rgba(255,215,0,0.7)"
                    : "0 4px 10px rgba(0, 0, 0, 0.1)"
                }}>
                  <div style={{ fontSize: "16px", fontWeight: "bold", marginBottom: "5px" }}>
                    {item.ID}
                  </div>
                  <div style={{ fontSize: "14px", color: "#333", marginBottom: "5px" }}>
                    {formatCurrency(getVal(item))}
                  </div>
                  <div style={{
                    fontSize: "14px",
                    fontWeight: rank === 1 ? "bold" : "normal",
                    color: rank === 1 ? "#D17A00" : "#666"
                  }}>
                    {rank}등
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Worst Top 3 */}
        <div style={{
          ...SECTION_STYLE,
          flex: 1,
          maxWidth: "500px",
          height: "400px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center"
        }}>
          <h2 style={TITLE_STYLE}>매출 Worst Top 3 😭</h2>
          <div style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "flex-end",
            gap: "20px"
          }}>
            {worstPodiumOrder.map((item, idx) => {
              const rank = idx === 0 ? 2 : idx === 1 ? 1 : 3;
              return (
                <div key={item.ID} style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "flex-end",
                  width: "80px",
                  height: worstHeightMap[rank],
                  backgroundColor: worstColorMap[rank],
                  borderRadius: "10px",
                  padding: "10px",
                  boxShadow: rank === 1
                    ? "0 0 10px rgba(255,0,0,0.3)"
                    : "0 4px 10px rgba(0, 0, 0, 0.1)"
                }}>
                  <div style={{ fontSize: "16px", fontWeight: "bold", marginBottom: "5px" }}>
                    {item.ID}
                  </div>
                  <div style={{ fontSize: "14px", color: "#333", marginBottom: "5px" }}>
                    {formatCurrency(getVal(item))}
                  </div>
                  <div style={{
                    fontSize: "14px",
                    fontWeight: rank === 1 ? "bold" : "normal",
                    color: rank === 1 ? "#C40000" : "#666"
                  }}>
                    {rank}등
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DashPage;