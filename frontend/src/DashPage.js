import React, { useEffect, useState, useRef, useMemo, Suspense, lazy } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { FaTrophy, FaMedal, FaTshirt, FaGem, FaHome, FaLeaf, FaRunning, FaBook, FaBaby, FaUmbrellaBeach, FaShoppingBag, FaSprayCan, FaUtensils, FaDumbbell, FaAppleAlt } from 'react-icons/fa';
import { IoMdMedal } from 'react-icons/io';

////////////////////////////////////////
// 1) 스타일 상수
////////////////////////////////////////

const PAGE_STYLE = {
  backgroundColor: '#f8f9fa',
  backgroundImage: 'linear-gradient(to bottom right, #f8f9fa, #e9ecef)',
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

// 테이블 관련 스타일
const TABLE_STYLE = {
  width: "100%",
  borderCollapse: "collapse",
  margin: "20px 0"
};

const TABLE_HEADER_STYLE = {
  backgroundColor: "#f2f2f2",
  textAlign: "left",
  padding: "12px",
  border: "1px solid #ddd"
};

const TABLE_CELL_STYLE = {
  padding: "12px",
  border: "1px solid #ddd"
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
  display: 'flex',
  alignItems: 'center',
  padding: '12px',
  borderBottom: '1px solid #eee',
  transition: 'background-color 0.2s',
  cursor: 'pointer',
  ':hover': {
    backgroundColor: '#f8f9fa'
  }
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
// LazyPlot 컴포넌트 정의
const LazyPlot = lazy(() => import('react-plotly.js'));
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

////////////////////////////////////////
// 3) WatchListItem
////////////////////////////////////////

// 스타일 정의 추가
const WATCHLIST_INFO_STYLE = {
  flex: 1,
  marginLeft: '12px'
};

const WATCHLIST_SYMBOL_STYLE = {
  fontSize: '14px',
  color: '#666',
  marginBottom: '4px'
};

const WATCHLIST_NAME_STYLE = {
  fontSize: '16px',
  fontWeight: '600',
  color: '#333'
};

// 카테고리별 아이콘 매핑 함수 수정
const getCategoryIcon = (category) => {
  // 아이콘 색상 정의
  const iconColors = {
    '여가/생활편의': '#FFB74D',  // 해변 파라솔 - 밝은 주황색
    '패션의류': '#E57373',       // 티셔츠 - 연한 빨간색
    '패션잡화': '#BA68C8',       // 쇼핑백 - 보라색
    '화장품/미용': '#F48FB1',    // 스프레이 - 분홍색
    '홈/리빙': '#81C784',        // 집 - 초록색
    '식품': '#E53935',           // 사과 - 빨간색
    '스포츠/레저': '#42A5F5',    // 달리는 사람 - 파란색
    '도서/음반': '#8D6E63',      // 책 - 갈색
    '유아동': '#4DD0E1'          // 아기 - 하늘색
  };

  const iconStyle = {
    fontSize: '24px',
    color: iconColors[category] || '#505764'
  };

  // WatchListItem 컴포넌트에서 사용할 정보 반환
  const icon = (() => {
    switch(category) {
      case '여가/생활편의':
        return <FaUmbrellaBeach style={iconStyle} />;
      case '패션의류':
        return <FaTshirt style={iconStyle} />;
      case '패션잡화':
        return <FaShoppingBag style={iconStyle} />;
      case '화장품/미용':
        return <FaSprayCan style={iconStyle} />;
      case '홈/리빙':
        return <FaHome style={iconStyle} />;
      case '식품':
        return <FaAppleAlt style={iconStyle} />;
      case '스포츠/레저':
        return <FaRunning style={iconStyle} />;
      case '도서/음반':
        return <FaBook style={iconStyle} />;
      case '유아동':
        return <FaBaby style={iconStyle} />;
      default:
        return <FaHome style={iconStyle} />;
    }
  })();

  return {
    icon,
    color: '#666' // 카테고리 배지 색상은 기존 회색으로 유지
  };
};

// WatchListItem 컴포넌트 수정
const WatchListItem = ({ item }) => {
  const iconData = getCategoryIcon(item.symbol);
  
  return (
    <div style={WATCHLIST_ITEM_STYLE}>
      <div style={{
        width: '40px',
        height: '40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f8f9fa', // 배경색은 기존 회색으로 유지
        borderRadius: '8px',
        marginRight: '12px'
      }}>
        {iconData.icon}
      </div>
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{
          fontSize: '16px',
          fontWeight: '600',
          color: '#333',
          marginBottom: '4px'
        }}>
          {item.name}
        </div>
        <div style={{
          fontSize: '14px',
          color: '#999'
        }}>
          ID: {item.id}
        </div>
      </div>
      <div style={{
        fontSize: '14px',
        color: '#666',
        backgroundColor: '#f5f5f5',
        padding: '4px 8px',
        borderRadius: '4px',
        alignSelf: 'center',
        fontWeight: '500'
      }}>
        {item.symbol}
      </div>
    </div>
  );
};

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

  // 상/하위 10 (판매수량 상위 10개 품목만 사용)
  const [top10, setTop10] = useState([]);
  // bottom10, lastMonthCol 등 기존 변수는 그대로 남겨두거나 필요에 따라 제거

  // 예: 상위 5개 트렌드 상품 (Watchlist 용)
  const [topTrends, setTopTrends] = useState([]);

  const API_BASE = "http://localhost:8000";

  // 새로운 상태 추가
  const [dailyTopSales, setDailyTopSales] = useState([]);

  // 상태 추가
  const [showAllItems, setShowAllItems] = useState(false);

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

        const [dailyTopRes, topBottomRes] = await Promise.all([
          axios.get(`${API_BASE}/api/daily-top-sales`),
          axios.get(`${API_BASE}/api/topbottom`)
        ]);
        
        setDailyTopSales(dailyTopRes.data);
        if (topBottomRes.data.top_10) {
          setTop10(topBottomRes.data.top_10);
        }

        // trend-products API 호출 추가
        const trendRes = await axios.get(`${API_BASE}/api/trend-products`);
        if (trendRes.data) {
          // 데이터 형식 변환
          const formattedTrends = trendRes.data.map(item => ({
            symbol: item.category,
            name: item.product_name,
            id: item.id,
            // 임시 아이콘 URL (카테고리별로 다른 이미지를 사용하려면 여기서 매핑)
            icon: "https://via.placeholder.com/50",
            // 추가 필드는 임시값 또는 실제 데이터에 맞게 조정
            price: 0,
            diff: 0
          }));
          setTopTrends(formattedTrends);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, []);

  // (증감률 계산, 그래프 setup 등)--------------------------------------------
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
  // 렌더링
  ////////////////////////////////////////
  const [selectedPeriod, setPeriod] = useState("일간");
  const [topSalesItems, setTopSalesItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // 데이터 페칭 최적화 (top-sales-items)
  useEffect(() => {
    const fetchTopSales = async () => {
      try {
        setIsLoading(true);
        const response = await axios.get(`${API_BASE}/api/top-sales-items`);
        if (response.data && Array.isArray(response.data)) {
          setTopSalesItems(response.data);
        }
      } catch (error) {
        console.error('Error fetching top sales items:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTopSales();
  }, []); // 의존성 배열 비움

  // TopSalesItem 컴포넌트 (기존 코드 그대로 사용)
  const MemoizedTopSalesItem = useMemo(() => React.memo(({ item }) => {
    const isPositive = item.change_rate >= 0;

    const graphData = useMemo(() => ({
      data: [{
        y: Array.from({ length: 20 }, (_, i) => {
          const trend = item.change_rate >= 0 ? 1 : -1;
          return 50 + trend * (Math.random() * 15 + Math.sin(i / 3) * 10 + i * 2);
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
      }],
      layout: {
        width: 150,
        height: 80,
        margin: { l: 0, r: 0, t: 0, b: 0 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        xaxis: { visible: false, showgrid: false },
        yaxis: { visible: false, showgrid: false }
      },
      config: {
        displayModeBar: false,
        responsive: true
      }
    }), [item.change_rate, isPositive]);

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
            <LazyPlot {...graphData} />
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
    width: "100%",
    padding: "15px 0"
  };

  // 매출 그래프와 트렌드 리스트를 감싸는 컨테이너 스타일 수정
  const GRAPH_SECTION_STYLE = {
    ...SECTION_STYLE,
    display: "flex",
    justifyContent: "space-between",
    gap: "20px",
    width: "95%",  // 전체 너비 설정
    maxWidth: "2100px",  // 최대 너비 설정
    margin: "20px auto"  // 중앙 정렬
  };

  // 거래 내역 컨테이너 스타일
  const TRANSACTIONS_CONTAINER_STYLE = {
    display: "flex",
    justifyContent: "space-between",
    width: "95%",
    maxWidth: "2100px",
    margin: "20px auto",
    gap: "20px",
    padding: "0",
    boxSizing: "border-box"
  };

  // 거래 카드 공통 스타일
  const TRANSACTION_CARD_STYLE = {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: "12px",
    boxShadow: "0 4px 10px rgba(0,0,0,0.1)",
    padding: "20px",
    height: "400px",
    overflow: "auto"
  };

  // 거래 항목 스타일
  const TRANSACTION_ITEM_STYLE = {
    display: "flex",
    alignItems: "center",
    padding: "12px 0",
    borderBottom: "1px solid #eee"
  };

  // 상태 표시 스타일
  const STATUS_STYLE = (status) => ({
    padding: "4px 8px",
    borderRadius: "12px",
    fontSize: "12px",
    backgroundColor: 
      status === "completed" ? "#e6f4ea" :
      status === "pending" ? "#fff3e0" : "#ffebee",
    color: 
      status === "completed" ? "#1e8e3e" :
      status === "pending" ? "#f57c00" : "#d32f2f",
    marginRight: "10px"
  });

  // 순위 아이콘 컴포넌트
  const RankIcon = ({ rank }) => {
    const iconStyle = {
      position: 'absolute',
      left: '20px',
      fontSize: '26px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    };

    const rankColors = {
      0: { color: '#FFD700', shadow: '0 0 10px rgba(255, 215, 0, 0.3)' },  // 금
      1: { color: '#C0C0C0', shadow: '0 0 10px rgba(192, 192, 192, 0.3)' }, // 은
      2: { color: '#CD7F32', shadow: '0 0 10px rgba(205, 127, 50, 0.3)' }   // 동
    };

    if (rank > 2) return null;

    return (
      <div style={{
        ...iconStyle,
        color: rankColors[rank].color,
        filter: `drop-shadow(${rankColors[rank].shadow})`
      }}>
        <FaMedal />
      </div>
    );
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
          { title: "연간 매출", value: kpis.annual_sales, diff: 0 },
          { title: "일간 매출", value: dailyVals.current, diff: dailyDiffPct },
          { title: "주간 매출", value: weeklyVals.current, diff: weeklyDiffPct },
          { title: "월간 매출", value: monthlyVals.current, diff: monthlyDiffPct }
        ].map(({ title, value, diff }, idx) => (
          <div key={idx} style={{
            backgroundColor: "#f8f9fa",
            borderRadius: "10px",
            boxShadow: "0px 4px 10px rgba(0, 0, 0, 0.1)",
            padding: "15px 20px",
            width: "calc(25% - 15px)",
            minWidth: "200px"
          }}>
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
            <div style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between"
            }}>
              <h2 style={{
                fontSize: "24px",
                fontWeight: "bold",
                color: "#222",
              }}>
                {formatCurrency(value)}
              </h2>
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
          {!isLoading && topSalesItems.map((item, index) => (
            <MemoizedTopSalesItem
              key={item.id || index}
              item={item}
            />
          ))}
        </div>
      </div>

      {/* (일간/주간/월간 KPI 카드와 Trend-list 영역) */}
      <div style={GRAPH_SECTION_STYLE}>
        <div style={{
          ...KPI_CARD_CONTAINER_STYLE,
          width: "70%",  // 왼쪽 카드 너비
          marginRight: "10px",  // 오른쪽 마진 제거
          height: "600px",
          display: "flex",
          flexDirection: "column",
          position: "relative"
        }}>
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
                  minWidth: "110px",
                  border: period === selectedPeriod
                    ? "none"
                    : "1px solid rgba(80, 87, 100, 0.12)"
                }}
              >
                {period}
              </button>
            ))}
          </div>

          <div style={KPI_CARD_TITLE_STYLE}>매출 현황</div>
          <h2 style={KPI_MAIN_VALUE_STYLE}>
            {formatCurrency(
              selectedPeriod === "일간" ? dailyVals.current :
                selectedPeriod === "주간" ? weeklyVals.current :
                  monthlyVals.current
            )}
          </h2>
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

        <div style={{
          ...WATCHLIST_CONTAINER_STYLE,
          width: "30%",  // 오른쪽 카드 너비
          height: "600px"
        }}>
          <div style={WATCHLIST_HEADER_STYLE}>
            <div style={WATCHLIST_TITLE_STYLE}>Trend-list</div>
          </div>
          <div style={WATCHLIST_ITEMS_CONTAINER}>
            {topTrends.map((item, idx) => (
              <WatchListItem key={item.id || idx} item={item} />
            ))}
          </div>
        </div>
      </div>

      {/* 최하단 섹션 */}
      <div style={TRANSACTIONS_CONTAINER_STYLE}>
        <div style={{
          flex: '1 1 70%',
          backgroundColor: 'white',
          borderRadius: '16px',
          padding: '20px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
          minHeight: '520px',
          maxWidth: '70%',
          boxSizing: 'border-box'
        }}>
          <h2 style={{ 
            fontSize: '22px', 
            marginBottom: '30px',
            color: '#2c3e50',
            fontWeight: '600',
            letterSpacing: '0.3px'
          }}>일간 최다 매출 상품</h2>
          
          {/* 테이블 헤더 */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1.2fr 1.5fr 1fr 1fr',
            padding: '16px 25px',
            background: 'linear-gradient(145deg, #f8f9fa, #f1f3f5)',
            borderRadius: '12px',
            marginBottom: '15px',
            fontWeight: '600',
            color: '#505764',
            fontSize: '15px',
            letterSpacing: '0.5px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
          }}>
            <div>대분류</div>
            <div>소분류</div>
            <div>날짜</div>
            <div style={{ textAlign: 'right' }}>매출액</div>
          </div>

          {/* 테이블 내용 */}
          <div style={{ marginTop: '15px' }}>
            {dailyTopSales.map((item, index) => (
              <div key={index} style={{
                display: 'grid',
                gridTemplateColumns: '1.2fr 1.5fr 1fr 1fr',
                padding: '22px 25px',
                alignItems: 'center',
                borderBottom: '1px solid #eef2f6',
                transition: 'all 0.2s ease',
                background: index % 2 === 0 ? 'white' : 'linear-gradient(145deg, #fcfcfc, #fafbfc)',
                borderRadius: '8px',
                margin: '8px 0',
                ':hover': {
                  transform: 'translateX(5px)',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.03)'
                }
              }}>
                <div style={{ 
                  color: '#505764',
                  fontSize: '15px',
                  fontWeight: '500',
                  letterSpacing: '0.3px'
                }}>{item.category}</div>
                <div style={{ 
                  color: '#2c3e50',
                  fontWeight: '600',
                  fontSize: '16px',
                  letterSpacing: '0.3px'
                }}>{item.subcategory}</div>
                <div style={{ 
                  color: '#6c757d',
                  fontSize: '15px',
                  letterSpacing: '0.3px'
                }}>
                  {new Date(item.date).toLocaleDateString('ko-KR', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </div>
                <div style={{ 
                  fontWeight: '600',
                  fontSize: '16px',
                  textAlign: 'right',
                  color: '#2c3e50',
                  letterSpacing: '0.5px'
                }}>
                  {new Intl.NumberFormat('ko-KR', {
                    style: 'currency',
                    currency: 'KRW',
                    maximumFractionDigits: 0
                  }).format(item.sales)}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{
          flex: '1 1 30%',
          backgroundColor: 'white',
          borderRadius: '16px',
          padding: '20px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
          minHeight: showAllItems ? '700px' : '520px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          maxWidth: '30%',
          boxSizing: 'border-box'
        }}>
          <div>
            <h2 style={{ 
              fontSize: '22px', 
              marginBottom: '30px',
              color: '#2c3e50',
              fontWeight: '600',
              letterSpacing: '0.3px'
            }}>판매수량 상위 품목</h2>
            <div>
              {top10.slice(0, showAllItems ? 10 : 5).map((item, index) => (
                <div key={index} style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '20px 25px 20px 60px',  // 패딩 약간 감소
                  marginBottom: '12px',  // 마진 약간 감소
                  borderRadius: '12px',
                  background: index < 3 
                    ? 'linear-gradient(145deg, #ffffff, #fafbfc)'
                    : 'white',
                  boxShadow: index < 3 
                    ? '0 4px 15px rgba(0,0,0,0.06)'
                    : '0 2px 8px rgba(0,0,0,0.03)',
                  transition: 'all 0.2s ease',
                  position: 'relative',
                  ':hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: '0 6px 20px rgba(0,0,0,0.05)'
                  }
                }}>
                  <RankIcon rank={index} />
                  
                  <div style={{ 
                    position: 'absolute',
                    top: '15px',
                    left: index < 3 ? '50px' : '25px',
                    fontSize: '13px',
                    fontWeight: '600',
                    color: index < 3 ? '#2c3e50' : '#6c757d',
                    letterSpacing: '1px',
                    textTransform: 'uppercase'
                  }}>
                    {index === 0 ? '1st' : 
                     index === 1 ? '2nd' : 
                     index === 2 ? '3rd' : 
                     `${index + 1}th`}
                  </div>
                  
                  <div style={{ 
                    flex: 1,
                    marginTop: '20px'
                  }}>
                    <div style={{ 
                      fontWeight: '600',
                      fontSize: index < 3 ? '18px' : '16px',
                      color: '#2c3e50',
                      marginBottom: '8px',
                      letterSpacing: '0.3px'
                    }}>{item.Sub3}</div>
                    <div style={{ 
                      color: '#505764',
                      fontSize: '15px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      <span>총 판매수량:</span>
                      <span style={{
                        fontWeight: '600',
                        color: index < 3 ? '#2196f3' : '#2c3e50'
                      }}>{item.총판매수량.toLocaleString()}개</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* 더보기 버튼 */}
          <div 
            onClick={() => setShowAllItems(!showAllItems)}
            style={{
              textAlign: 'center',
              margin: '15px auto 0',
              padding: '10px 25px',
              cursor: 'pointer',
              borderRadius: '25px',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'all 0.2s ease',
              background: 'linear-gradient(145deg, #f8f9fa, #ffffff)',
              border: '1px solid #e9ecef',
              color: '#2c3e50',
              boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
              width: '90%',  // 버튼 너비 증가
              ':hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'
              }
            }}
          >
            {showAllItems ? '접기' : '더보기'}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DashPage;