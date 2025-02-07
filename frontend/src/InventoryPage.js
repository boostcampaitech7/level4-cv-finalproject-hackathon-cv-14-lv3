import React, { useState, useEffect,useCallback } from "react";
import { saveAs } from "file-saver";
import Papa from "papaparse";

const InventoryPage = () => {
  const [inventory, setInventory] = useState([]);
  const [filteredInventory, setFilteredInventory] = useState([]);
  const [sortField, setSortField] = useState("value");  // ✅ 기본 정렬 필드: 재고량
  const [sortOrder, setSortOrder] = useState("asc");    // ✅ 기본 정렬 방식: 오름차순
  const [sortConfig, setSortConfig] = useState({ field: "value", order: "asc" });  // ✅ 정렬 기본값
  const [searchQuery, setSearchQuery] = useState("");
  const [keepLowStockTop, setKeepLowStockTop] = useState(true);


  // ✅ 카테고리 상태
  const [mainCategories, setMainCategories] = useState(["전체 대분류"]);
  const [sub1Categories, setSub1Categories] = useState(["전체 중분류"]);
  const [sub2Categories, setSub2Categories] = useState(["전체 소분류"]);
  const [selectedMain, setSelectedMain] = useState("전체 대분류");
  const [selectedSub1, setSelectedSub1] = useState("전체 중분류");
  const [selectedSub2, setSelectedSub2] = useState("전체 소분류");
  const [selectedCategory, setSelectedCategory] = useState("All");  // (이전 오류 해결)

  // 날짜 선택을 위한 (월 선택하게끔)
  const [startMonth, setStartMonth] = useState("2022-01");
  const [endMonth, setEndMonth] = useState("2023-04");
  const [errorMessage, setErrorMessage] = useState("");
  const [reorderPoints, setReorderPoints] = useState({});

  //자동 주문
  const [autoOrders, setAutoOrders] = useState({});


  // ✅ WebSocket 연결
  useEffect(() => { 
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/auto_orders");

    ws.onmessage = (event) => {
      const orderData = JSON.parse(event.data);
      console.log("🛒 주문 완료 수신:", orderData);

      // ✅ WebSocket을 통해 받은 주문 정보를 autoOrders에 반영
      setAutoOrders((prev) => ({
        ...prev,
        [orderData.id]: { status: "✅ 주문 완료", value: orderData.value },
      }));
    };

    ws.onclose = () => console.log("❌ WebSocket 연결 종료");

    return () => {
      ws.close();
    };
  }, []);

  // ✅ 주문 완료 상태가 바뀌면 filteredInventory 업데이트
  useEffect(() => {
    if (Object.keys(autoOrders).length > 0) {
      setFilteredInventory((prev) =>
        prev.map((item) => ({
          ...item,
          orderStatus: autoOrders[item.id] ? "✅ 주문 완료" : item.isLowStock ? "❌ 미주문" : "-",
          value: autoOrders[item.id]?.value ?? item.value, // ✅ 주문 완료 시 value 업데이트
        }))
      );
    }
  }, [autoOrders]);

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
    setSelectedSub1("전체 중분류"); // 하위 카테고리 초기화
    setSelectedSub2("전체 소분류"); // 하위 카테고리 초기화
  
    const filters = await fetchCategoryFilters(value === "전체 대분류" ? "All" : value, "All", "All");
    setSub1Categories(["전체 중분류", ...(filters.sub1 || [])]);
    setSub2Categories(["전체 소분류", ...(filters.sub2 || [])]);
  
    // 기존 필터 유지하면서 적용
    applyFilters(inventory, searchQuery, value, "전체 중분류", "전체 소분류");
  };
  
  const handleSub1CategoryChange = async (e) => {
    const value = e.target.value;
    setSelectedSub1(value); 
    setSelectedSub2("전체 소분류"); // 하위 카테고리 초기화
  
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
  
      const reorderData = await fetchReorderPoints();
      if (Object.keys(reorderData).length > 0) {
        await fetchInventory(reorderData);
      }
    };
    initializeData();
  }, []);
  
  useEffect(() => {
    // ✅ `sortConfig`에 맞춰 데이터 정렬
    if (sortConfig.field) {
      setFilteredInventory((prevInventory) => {
        return [...prevInventory].sort((a, b) => {
          const aValue = parseFloat(a[sortConfig.field]) || 0;
          const bValue = parseFloat(b[sortConfig.field]) || 0;
  
          return sortConfig.order === "asc" ? aValue - bValue : bValue - aValue;
        });
      });
    }
  }, [sortConfig, inventory]);  // ✅ inventory가 바뀌면 정렬 다시 적용
  
  


  
  
  // ✅ 날짜 형식 변환 함수 추가
  const convertDateFormat = (dateStr) => {
    // "2022-02" → "22_m02"
    const [year, month] = dateStr.split('-');
    return `${year.slice(2)}_m${month}`;
  };

  // ✅ fetchReorderPoints 함수 수정
  const fetchReorderPoints = async () => {
    try {
      const start = convertDateFormat(startMonth);
      const end = convertDateFormat(endMonth);

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
            monthly_avg_sales: item.monthly_avg_sales || 0,
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


const handleSort = useCallback((field) => {
  setKeepLowStockTop(false);

  setSortConfig((prevConfig) => {
    const isSameField = prevConfig.field === field;
    const newOrder = isSameField && prevConfig.order === "asc" ? "desc" : "asc";

    setSortField(field);
    setSortOrder(newOrder);

    setFilteredInventory((prevInventory) => {
      return [...prevInventory].sort((a, b) => {
        const aValue = parseFloat(a[field]) || 0;
        const bValue = parseFloat(b[field]) || 0;
        return newOrder === "asc" ? aValue - bValue : bValue - aValue;
      });
    });

    return { field, order: newOrder };
  });
}, []);





const handleResetSort = async () => {
  setSortConfig({ field: "value", order: "asc" });
  setSortField("value");
  setSortOrder("asc");

  setSelectedMain("전체 대분류");
  setSelectedSub1("전체 중분류");
  setSelectedSub2("전체 소분류");

  const categoryData = await fetchCategoryFilters("All", "All", "All");
  setMainCategories(["전체 대분류", ...(categoryData.main || [])]);
  setSub1Categories(["전체 중분류", ...(categoryData.sub1 || [])]);
  setSub2Categories(["전체 소분류", ...(categoryData.sub2 || [])]);

  setSearchQuery("");
  const searchInput = document.querySelector('.search-bar input');
  if (searchInput) {
    searchInput.value = '';
  }

  const reorderData = await fetchReorderPoints();
  if (Object.keys(reorderData).length > 0) {
    await fetchInventory(reorderData);
  }
};




  // ✅ 인벤토리 데이터 가져오기
  const fetchInventory = async (reorderData = null, main = "All", sub1 = "All", sub2 = "All") => {
    try {
      let url = `http://127.0.0.1:8000/api/inventory`;
      const params = [];
  
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
  
      const filteredData = inventoryData.map((item) => ({
        ...item,
        sub3: item.sub3 || "제품명 없음",
      }));
  
      const reorderPointsData = reorderData || reorderPoints;
      const mergedData = filteredData.map((item) => {
        const reorderInfo = reorderPointsData[item.id] || {};
        return {
          ...item,
          reorder_point: reorderInfo.reorder_point ?? 10,
          daily_avg_sales: reorderInfo.daily_avg_sales ?? 0,
          monthly_avg_sales: reorderInfo.monthly_avg_sales ?? 0,
          isLowStock: item.value < (reorderInfo.reorder_point ?? 10),
          orderStatus: item.isLowStock ? "❌ 미주문" : "-",
        };
      });
  
      // ✅ 기본 정렬: `value` 오름차순
      const sortedData = [...mergedData].sort((a, b) => parseFloat(a.value) - parseFloat(b.value));
  
      setInventory(sortedData);
      setFilteredInventory(sortedData);
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
  


  // ✅ 월 선택 핸들러 - 상태 업데이트 및 데이터 즉시 갱신
  const handleStartMonthChange = async (e) => {
    setStartMonth(e.target.value);
    const reorderData = await fetchReorderPoints();
    if (Object.keys(reorderData).length > 0) {
      await fetchInventory(reorderData);
    }
  };

  const handleEndMonthChange = async (e) => {
    setEndMonth(e.target.value);
    const reorderData = await fetchReorderPoints();
    if (Object.keys(reorderData).length > 0) {
      await fetchInventory(reorderData);
    }
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

  // ✅ 자동 주문 핸들러 (주문 완료 후 UI 즉시 반영)
  const handleAutoOrder = async (item) => {
    try {
      const orderData = {
        order_date: new Date().toISOString(),
        items: [{ id: item.id, value: item.reorder_point, is_orderable: true }],
      };

      const response = await fetch(`http://127.0.0.1:8000/api/auto_orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(orderData),
      });

      const result = await response.json();
      if (result.status === "success") {
        // ✅ UI 즉시 반영 (서버 응답을 기다리지 않고 화면 업데이트)
        setAutoOrders((prev) => ({
          ...prev,
          [item.id]: { status: "✅ 주문 완료", value: item.reorder_point },
        }));
      }
    } catch (error) {
      console.error("❌ 주문 처리 중 오류 발생:", error);
    }
  };



  return (
    <div className="inventory-container">
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
        <div className="search-bar">
          <input
            type="text"
            placeholder="🔍 상품명 검색"
            value={searchQuery}
            onChange={handleSearch}
          />
        </div>
        
        <div className="category-filters">
          {/* 대분류 드롭다운 */}
          <div className="category-select">
            <select 
              value={selectedMain} 
              onChange={handleMainCategoryChange}
            >
              <option value="전체 대분류">{selectedMain === "전체 대분류" ? "대분류" : selectedMain}</option>
              {mainCategories.filter(cat => cat !== "전체 대분류").map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* 중분류 드롭다운 */}
          <div className="category-select">
            <select 
              value={selectedSub1} 
              onChange={handleSub1CategoryChange}
            >
              <option value="전체 중분류">{selectedSub1 === "전체 중분류" ? "중분류" : selectedSub1}</option>
              {sub1Categories.filter(cat => cat !== "전체 중분류").map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* 소분류 드롭다운 */}
          <div className="category-select">
            <select 
              value={selectedSub2} 
              onChange={handleSub2CategoryChange}
            >
              <option value="전체 소분류">{selectedSub2 === "전체 소분류" ? "소분류" : selectedSub2}</option>
              {sub2Categories.filter(cat => cat !== "전체 소분류").map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="button-group">
        <button className="sort-button" onClick={() => handleSort("value")}>
          {sortField === "value" && sortOrder === "asc" ? "📉 재고 내림차순" : "📈 재고 오름차순"}
        </button>


          <button className="sort-button" onClick={() => handleSort("monthly_avg_sales")}>
            {sortField === "monthly_avg_sales" && sortOrder === "asc" ? "📉 월 평균 판매량 내림차순" : "📈 월 평균 판매량 오름차순"}
          </button>
          <button className="sort-button" onClick={() => handleSort("daily_avg_sales")}>
            {sortField === "daily_avg_sales" && sortOrder === "asc" ? "📉 일 평균 판매량 내림차순" : "📈 일 평균 판매량 오름차순"}
          </button>
          <button className="reset-button" onClick={handleResetSort}>🔄 새로고침</button>
          <button className="download-button" onClick={downloadCSV}>📥 CSV 다운로드</button>
        </div>
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
        {filteredInventory.map((item) => (
          <tr 
            key={item.id} 
            className={item.isLowStock ? "low-stock" : ""}
            style={{ 
              backgroundColor: item.isLowStock ? '#fff3f3' : 'inherit'
            }}
          >
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
            <td className={autoOrders[item.id] ? "order-success" : item.isLowStock ? "low-stock-text" : ""}>
                {autoOrders[item.id] ? "✅ 주문 완료" : item.isLowStock ? "❌ 미주문" : "-"}
              </td>
          </tr>
        ))}
        </tbody>
      </table>

      <style>
        {`
          .inventory-container {
            padding: 0 24px;  /* 좌우 여백 추가 */
          }

          .controls {
            display: flex;
            flex-direction: column;
            gap: 24px;  /* 컨트롤 요소들 사이 간격 증가 */
            margin: 24px 0;
          }

          .search-bar input {
            width: 300px;
            padding: 12px 16px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s ease;
            background-color: white;
          }

          .search-bar input:focus {
            outline: none;
            border-color: #4a90e2;
            box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
          }

          .category-filters {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
          }

          .category-select {
            display: flex;
            align-items: center;
            gap: 8px;
          }

          .category-select label {
            font-weight: 500;
            color: #666;
          }

          .category-select select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            min-width: 160px;
            background-color: white;
            cursor: pointer;
          }

          .category-select select:hover {
            border-color: #999;
          }

          .button-group {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;  /* 버튼 간격 증가 */
          }

          .button-group button {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
          }

          .sort-button {
            background: linear-gradient(to bottom, #ffffff, #f8f9fa);
            color: #495057;
            border: 1px solid #e9ecef;
          }

          .sort-button:hover {
            background: linear-gradient(to bottom, #f8f9fa, #e9ecef);
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
          }

          .reset-button {
            background: linear-gradient(to bottom, #f1f3f5, #e9ecef);
            color: #495057;
            border: 1px solid #dee2e6;
          }

          .reset-button:hover {
            background: linear-gradient(to bottom, #e9ecef, #dee2e6);
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
          }

          .download-button {
            background: linear-gradient(to bottom, #4a90e2, #357abd);
            color: white;
            border: 1px solid #357abd;
          }

          .download-button:hover {
            background: linear-gradient(to bottom, #357abd, #2b6298);
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(74, 144, 226, 0.2);
          }

          .button-group button:active {
            transform: translateY(1px);
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
          }

          .date-selection {
            display: flex;
            align-items: center;
            gap: 16px;
            margin: 24px 0;
          }

          .date-selection input {
            padding: 10px 14px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s ease;
            background-color: white;
          }

          .date-selection input:focus {
            outline: none;
            border-color: #4a90e2;
            box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
          }

          .inventory-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
          }

          .inventory-table th,
          .inventory-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
          }

          .inventory-table th {
            background-color: #f4f4f4;
          }

          .inventory-table tr:nth-child(even) {
            background-color: #f9f9f9;
          }

          .inventory-table tr:hover {
            background-color: #f5f5f5;
          }

          .low-stock {
            background-color: #fff3f3 !important;
          }

          .low-stock-text {
            color: #dc3545;
          }

          .order-success {
            color: #28a745;
          }
        `}
      </style>
    </div>
  );
};

export default InventoryPage;