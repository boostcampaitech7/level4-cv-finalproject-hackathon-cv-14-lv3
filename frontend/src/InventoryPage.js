import React, { useState, useEffect } from "react";
import { saveAs } from "file-saver";
import Papa from "papaparse";

const InventoryPage = () => {
  const [inventory, setInventory] = useState([]);
  const [filteredInventory, setFilteredInventory] = useState([]);
  const [sortField, setSortField] = useState(null);
  const [sortOrder, setSortOrder] = useState("asc");
  const [searchQuery, setSearchQuery] = useState("");
  const [keepLowStockTop, setKeepLowStockTop] = useState(true);

  // ✅ 카테고리 상태
  const [mainCategories, setMainCategories] = useState(["전체 대분류"]);
  const [sub1Categories, setSub1Categories] = useState(["전체 중분류"]);
  const [sub2Categories, setSub2Categories] = useState(["전체 소분류"]);
  const [selectedMain, setSelectedMain] = useState("전체 대분류");
  const [selectedSub1, setSelectedSub1] = useState("전체 중분류");
  const [selectedSub2, setSelectedSub2] = useState("전체 소분류");

  // 날짜 선택을 위한 (월 선택하게끔)
  const [startMonth, setStartMonth] = useState("2022-01");
  const [endMonth, setEndMonth] = useState("2023-04");
  const [errorMessage, setErrorMessage] = useState("");
  const [reorderPoints, setReorderPoints] = useState({});

  //자동 주문
  const [autoOrders, setAutoOrders] = useState({});
  const [selectedCategory, setSelectedCategory] = useState("All");  // (이전 오류 해결)


  // ✅ 자동 주문된 리스트 가져오기
  const fetchAutoOrders = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/auto_orders`);
      const data = await response.json();

      if (data.status === "success") {
        setAutoOrders(data.orders);
      }
    } catch (error) {
      console.error("❌ Error fetching auto orders:", error);
    }
  };

  const fetchCategoryFilters = async (main = "All", sub1 = "All", sub2 = "All") => {
    try {
      let url = `http://127.0.0.1:8000/api/category_filters`;
      const params = [];
      if (main !== "All" && main !== "전체 대분류") params.push(`main=${encodeURIComponent(main)}`);
      if (sub1 !== "All" && sub1 !== "전체 중분류") params.push(`sub1=${encodeURIComponent(sub1)}`);
      if (sub2 !== "All" && sub2 !== "전체 소분류") params.push(`sub2=${encodeURIComponent(sub2)}`);
      if (params.length > 0) url += `?${params.join("&")}`;
  
      const response = await fetch(url);
      const data = await response.json();
  
      if (data.status === "success") {
        // ✅ 기존 선택값 유지
        setMainCategories((prev) => ["전체 대분류", ...(data.filters.main || [])]);
        setSub1Categories((prev) => ["전체 중분류", ...(data.filters.sub1 || [])]);
        setSub2Categories((prev) => ["전체 소분류", ...(data.filters.sub2 || [])]);
  
        return data.filters;
      }
    } catch (error) {
      console.error("❌ Error fetching category filters:", error);
    }
    return { main: [], sub1: [], sub2: [] };
  };
  
  
  
  const handleMainCategoryChange = async (e) => {
    const value = e.target.value;
    setSelectedMain(value);  // 선택한 값 유지
    setSelectedSub1("전체 중분류"); 
    setSelectedSub2("전체 소분류"); 
  
    const filters = await fetchCategoryFilters(value === "전체 대분류" ? "All" : value, "All", "All");
    setSub1Categories(["전체 중분류", ...(filters.sub1 || [])]);
    setSub2Categories(["전체 소분류", ...(filters.sub2 || [])]);
  
    // 기존 필터 유지하면서 적용
    applyFilters(inventory, searchQuery, value, "전체 중분류", "전체 소분류");
  };
  
  const handleSub1CategoryChange = async (e) => {
    const value = e.target.value;
    setSelectedSub1(value); 
    setSelectedSub2("전체 소분류");
  
    const filters = await fetchCategoryFilters(
      selectedMain === "전체 대분류" ? "All" : selectedMain,
      value === "전체 중분류" ? "All" : value,
      "All"
    );
    setSub2Categories(["전체 소분류", ...(filters.sub2 || [])]);
  
    applyFilters(inventory, searchQuery, selectedMain, value, "전체 소분류");
  };
  
  const handleSub2CategoryChange = (e) => {
    const value = e.target.value;
    setSelectedSub2(value);
    applyFilters(inventory, searchQuery, selectedMain, selectedSub1, value);
  };
  useEffect(() => {
    const initializeData = async () => {
      const categoryData = await fetchCategoryFilters("All", "All", "All");
      setMainCategories(["전체 대분류", ...(categoryData.main || [])]);
      setSub1Categories(["전체 중분류", ...(categoryData.sub1 || [])]);
      setSub2Categories(["전체 소분류", ...(categoryData.sub2 || [])]);
  
      await fetchAutoOrders();
      const reorderData = await fetchReorderPoints();
      await fetchInventory(reorderData, "All", "All", "All");
    };
    initializeData();
  }, []);
  


  
  
  // ✅ 최소 재고 기준(ROP) 데이터 가져오기
  const fetchReorderPoints = async () => {
    try {

      // ✅ "2022-01" → "22_m01" 변환
      const start = startMonth.slice(2, 4) + "_m" + startMonth.slice(5, 7);
      const end = endMonth.slice(2, 4) + "_m" + endMonth.slice(5, 7);


      const response = await fetch(`http://127.0.0.1:8000/api/reorder_points?start=${start}&end=${end}`);
      const data = await response.json();


      if (data.error) {
        setErrorMessage(data.error);
        return [];
      }

      const reorderMap = {};
      data.forEach((item) => {
        if (item.id) {
          reorderMap[item.id] = {
            reorder_point: item.reorder_point || 10,
            daily_avg_sales: item.daily_avg_sales || 0,
            monthly_avg_sales: item.monthly_avg_sales || 0,  // ✅ 추가된 데이터
          };
        }
      });

      setReorderPoints(reorderMap);
      return reorderMap;
    } catch (error) {
      console.error("❌ Error fetching reorder points:", error);
      return {};
    }
};




useEffect(() => {
  const updateReorderData = async () => {
    const reorderData = await fetchReorderPoints();
    if (Object.keys(reorderData).length > 0) {
      await fetchInventory(reorderData);
    }
  };
  updateReorderData();
}, [startMonth, endMonth]);

const handleSort = (field) => {
  setKeepLowStockTop(false); // ✅ 정렬 시 상단 고정 해제

  // ✅ 새로운 정렬 방향을 미리 결정
  let newSortOrder = "asc";
  if (sortField === field && sortOrder === "asc") {
    newSortOrder = "desc";
  }

  // ✅ 상태 업데이트 (비동기적 문제 해결)
  setSortField(field);
  setSortOrder(newSortOrder);

  // ✅ 정렬된 데이터 즉시 적용
  setFilteredInventory((prevInventory) => {
    const sortedData = [...prevInventory].sort((a, b) => {
      const aValue = field === "value" ? parseFloat(a[field]) : a[field];
      const bValue = field === "value" ? parseFloat(b[field]) : b[field];

      return newSortOrder === "asc" ? aValue - bValue : bValue - aValue;
    });

    return sortedData;
  });
};

// ✅ 상태 변경 시 자동 정렬 반영
useEffect(() => {
  if (!keepLowStockTop && sortField) {
    setFilteredInventory((prev) => {
      const sortedData = [...prev].sort((a, b) => {
        const aValue = sortField === "value" ? parseFloat(a[sortField]) : a[sortField];
        const bValue = sortField === "value" ? parseFloat(b[sortField]) : b[sortField];

        return sortOrder === "asc" ? aValue - bValue : bValue - aValue;
      });
      return sortedData;
    });
  }
}, [sortField, sortOrder, keepLowStockTop]);



const handleResetSort = async () => {
  setKeepLowStockTop(true);
  setSortField(null);
  setSortOrder("asc");

  // ✅ 필터 초기화 (드롭다운에는 '전체' 표시, API에는 빈 값 전달)
  setSelectedMain("All");
  setSelectedSub1("All");
  setSelectedSub2("All");
  setSearchQuery("");

  await fetchCategoryFilters("", "", "");
  await fetchInventory();
};




  // ✅ 인벤토리 데이터 가져오기
  const fetchInventory = async (reorderData = null, main = "All", sub1 = "All", sub2 = "All") => {
    try {
      let url = `http://127.0.0.1:8000/api/inventory`;
      const params = [];
  
      // 전체 X분류 처리
      if (main !== "All" && main !== "전체 대분류") params.push(`main=${encodeURIComponent(main)}`);
      if (sub1 !== "All" && sub1 !== "전체 중분류") params.push(`sub1=${encodeURIComponent(sub1)}`);
      if (sub2 !== "All" && sub2 !== "전체 소분류") params.push(`sub2=${encodeURIComponent(sub2)}`);
      if (params.length > 0) url += `?${params.join("&")}`;
  
      const inventoryResponse = await fetch(url);
      const inventoryData = await inventoryResponse.json();
  
      if (!Array.isArray(inventoryData)) {
        console.error("❌ 서버에서 유효한 인벤토리 데이터를 받지 못했습니다:", inventoryData);
        return;
      }
  
      // 기존 로직 유지
      const filteredData = inventoryData.map((item) => ({
        ...item,
        sub3: item.sub3 || "제품명 없음",
      }));
    
      // ✅ 최소 재고 기준 데이터를 먼저 가져오기
      const reorderPointsData = reorderData || reorderPoints;
      const mergedData = filteredData.map((item) => {
        const reorderInfo = reorderPointsData[item.id] || {};

        // ✅ 자동 주문 완료된 상품인지 확인
        const isOrdered = autoOrders[item.sub3]?.status === "success";

        return {
          ...item,
          reorder_point: reorderInfo.reorder_point ?? 10,
          daily_avg_sales: reorderInfo.daily_avg_sales ?? 0,
          monthly_avg_sales: reorderInfo.monthly_avg_sales ?? 0,
          isLowStock: item.value < (reorderInfo.reorder_point ?? 10),
          orderStatus: isOrdered ? "✅ 주문 완료" : item.isLowStock ? "❌ 미주문" : "-",
          value: isOrdered ? reorderInfo.reorder_point : item.value,
        };
      });

      
      // ✅ `keepLowStockTop`이 `true`면 재고 부족 상품을 상단으로 정렬
      if (keepLowStockTop) {
        mergedData.sort((a, b) => {
          if (a.isLowStock === b.isLowStock) return 0;
          return a.isLowStock ? -1 : 1;
        });
      }

      // ✅ 정렬 초기화 (기본값: 재고량 오름차순)
      setInventory(mergedData);
      setFilteredInventory(mergedData);
      
    } catch (error) {
      console.error("❌ Error fetching inventory:", error);
    }
  };


  const getSortedInventory = () => {
    let sortedData = [...filteredInventory];
  
    if (keepLowStockTop) {
      sortedData.sort((a, b) => {
        if (a.isLowStock === b.isLowStock) return 0;
        return a.isLowStock ? -1 : 1;  // ✅ 재고 부족 상품이 먼저 오도록 정렬
      });
    }
  
    return sortedData;
  };
  const applyFilters = (data, query = searchQuery, main = selectedMain, sub1 = selectedSub1, sub2 = selectedSub2) => {
    let filtered = [...data];

    // 검색어 필터
    if (query) {
      filtered = filtered.filter((item) =>
        item.sub3.toLowerCase().includes(query.toLowerCase())
      );
    }

    // 카테고리 필터
    if (main !== "전체 대분류") {
      filtered = filtered.filter((item) => item.main === main);
    }
    if (sub1 !== "전체 중분류") {
      filtered = filtered.filter((item) => item.sub1 === sub1);
    }
    if (sub2 !== "전체 소분류") {
      filtered = filtered.filter((item) => item.sub2 === sub2);
    }

    // 재고 부족 상품 상단 정렬
    if (keepLowStockTop) {
      filtered.sort((a, b) => {
        if (a.isLowStock === b.isLowStock) return 0;
        return a.isLowStock ? -1 : 1;
      });
    }

    setFilteredInventory(filtered);
  };
  


  // ✅ 월 선택 핸들러
  const handleStartMonthChange = (e) => {
    setStartMonth(e.target.value);
  };

  const handleEndMonthChange = (e) => {
    setEndMonth(e.target.value);
  };
  
  // ✅ 버튼 클릭 시 인벤토리 업데이트
  const handleDateChange = async () => {
    await fetchInventory(reorderPoints);
  };


  //검색 필터링
  const handleSearch = (e) => {
    const query = e.target.value.toLowerCase();
    setSearchQuery(query);
    applyFilters(inventory, query, selectedMain, selectedSub1, selectedSub2);
  };

  //카테고리 필터링
  const handleCategoryFilter = (e) => {
    const category = e.target.value;
    setSelectedCategory(category);
    filterData(searchQuery, category);
  };

  //검색 및 카테고리별 필터링
  const filterData = (query, category) => {
    let filtered = inventory.filter((item) =>
      item.sub3.toLowerCase().includes(query)
    );
    if (category !== "All") {
      filtered = filtered.filter((item) => item.main === category);
    }
    setFilteredInventory(filtered);
  };

  
  useEffect(() => {
    if (keepLowStockTop) {
      setFilteredInventory((prev) => {
        let sortedData = [...prev].sort((a, b) => {
          if (a.isLowStock === b.isLowStock) return 0;
          return a.isLowStock ? -1 : 1;
        });
        return sortedData;
      });
    }
  }, [inventory]);  // ✅ `keepLowStockTop`이 변경될 때마다 자동으로 정렬되지 않도록 수정
 


  //CSV 다운로드
  const downloadCSV = () => {
    const csvData = filteredInventory.map(item => ({
      "세부 분류": item.sub3,
      "설명": `${item.main} > ${item.sub1} > ${item.sub2}`,
      "재고 수량": parseFloat(item.value),
      "최소 재고 기준": item.reorder_point,
      "재고 상태": item.isLowStock ? "⚠️ 재고 부족" : "정상"
    }));

    const csv = Papa.unparse(csvData);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    saveAs(blob, "inventory_data.csv");
  };

  return (
    <div>
      <h2>📦 재고 관리</h2>
      
      {/* ✅ 월 선택 UI 추가 */}
      <div className="date-selection">
        <label>📅 시작 월: </label>
        <input
          type="month"
          value={startMonth}
          min="2022-01"
          max="2023-04"
          onChange={handleStartMonthChange}
        />

        <label>📅 종료 월: </label>
        <input
          type="month"
          value={endMonth}
          min="2022-01"
          max="2023-04"
          onChange={handleEndMonthChange}
        />
      </div>

      {errorMessage && <p className="error-message">{errorMessage}</p>}

      <div className="controls">
        <input
          type="text"
          placeholder="🔍 상품명 검색"
          value={searchQuery}
          onChange={handleSearch}
        />
        
        <div className="category-filters">
        {/* ✅ 대분류 드롭다운 */}
        <select value={selectedMain} onChange={handleMainCategoryChange}>
          {mainCategories.map((cat) => (
            <option key={cat} value={cat}>
              {cat === "전체 대분류" ? "대분류" : cat}
            </option>
          ))}
        </select>

        {/* ✅ 중분류 드롭다운 */}
        <select value={selectedSub1} onChange={handleSub1CategoryChange}>
          {sub1Categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat === "전체 중분류" ? "중분류" : cat}
            </option>
          ))}
        </select>

        {/* ✅ 소분류 드롭다운 */}
        <select value={selectedSub2} onChange={handleSub2CategoryChange}>
          {sub2Categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat === "전체 소분류" ? "소분류" : cat}
            </option>
          ))}
        </select>
      </div>

      {/* ✅ 선택한 값 텍스트로 표시 */}
      <div className="selected-category">
        <p>📌 선택된 카테고리: <strong>{selectedMain} > {selectedSub1} > {selectedSub2}</strong></p>
      </div>




      <button onClick={() => handleSort("value")}>
        {sortField === "value" && sortOrder === "desc" ? "📈 재고 오름차순" : "📉 재고 내림차순"}
      </button>
      <button onClick={() => handleSort("monthly_avg_sales")}>
        {sortField === "monthly_avg_sales" && sortOrder === "asc" ? "📉 월 평균 판매량 내림차순" : "📈 월 평균 판매량 오름차순"}
      </button>
      <button onClick={() => handleSort("daily_avg_sales")}>
        {sortField === "daily_avg_sales" && sortOrder === "asc" ? "📉 일 평균 판매량 내림차순" : "📈 일 평균 판매량 오름차순"}
      </button>

      <button onClick={handleResetSort}>🔄 새로고침 (초기화)</button>

        <button onClick={downloadCSV}>📥 CSV 다운로드</button>
      </div>
      
      <table className="inventory-table">
        <thead>
          <tr>
            <th>제품명</th>
            <th>월 평균 판매량</th>
            <th>일 평균 판매량</th>
            <th>재고량</th>
            <th>최소 재고 기준</th>
            <th>상태</th> 
            <th>주문 현황</th>
          </tr>
        </thead>
        <tbody>
        {filteredInventory.map((item, index) => (
          <tr key={index} className={item.isLowStock ? "low-stock" : ""}>
            <td>{item.sub3}</td>
            <td>{item.monthly_avg_sales.toFixed(1)}</td>
            <td>{item.daily_avg_sales.toFixed(1)}</td>  
            <td className={item.isLowStock ? "low-stock-text" : ""}>
              {item.value}
            </td>
            <td className={item.isLowStock ? "low-stock-text" : ""}>
              {item.reorder_point.toFixed(0)}
            </td>
            <td className={item.isLowStock ? "low-stock-text" : ""}>
              {item.isLowStock ? "⚠️ 재고 부족" : "✅"}
            </td>
            <td className={autoOrders[item.sub3] 
                ? "order-success" 
                : item.isLowStock ? "low-stock-text" : ""}
            >
              {autoOrders[item.sub3] 
                ? "✅ 주문 완료" 
                : item.isLowStock ? "❌ 미주문" : "-"}
            </td>

          </tr>
        ))}
      </tbody>
      </table>

      <style>
        {`
          .description {
            color: gray;
            font-size: 14px;
          }
          .inventory-table {
            width: 100%;
            border-collapse: collapse;
          }
          .inventory-table th, .inventory-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
          }
          .low-stock {
            background-color: #ffebee; /* 연한 빨간색 배경 */
          }
          .low-stock-text {
            color: red;
            font-weight: bold;
          }
          .order-success {
            color: green;
            font-weight: bold;
          }
          .date-selection {
            margin-bottom: 10px;
            display: flex;
            gap: 10px;
            align-items: center;
          }
          .error-message {
            color: red;
            font-weight: bold;
          }
          .category-filters {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
          }
        `}
      </style>
    </div>
  );
};

export default InventoryPage;