import React, { useState, useEffect } from "react";
import { saveAs } from "file-saver";
import Papa from "papaparse";

const InventoryPage = () => {
  const [inventory, setInventory] = useState([]);
  const [filteredInventory, setFilteredInventory] = useState([]);
  const [sortOrder, setSortOrder] = useState("asc");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  //인벤토리 데이터 가져오기 (자동 갱신 우선 제거)
  useEffect(() => {
    fetchInventory();
  }, [sortOrder]);

  //수동 새로고침으로
  const fetchInventory = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/inventory?sort=${sortOrder}`);
      const data = await response.json();
      setInventory(data);
      setFilteredInventory(data);
    } catch (error) {
      console.error("Error fetching inventory:", error);
    }
  };

  //검색 필터링
  const handleSearch = (e) => {
    const query = e.target.value.toLowerCase();
    setSearchQuery(query);
    filterData(query, selectedCategory);
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

  //CSV 다운로드
  const downloadCSV = () => {
    const csvData = filteredInventory.map(item => ({
      "세부 분류": item.sub3,
      "카테고리": item.main,
      "설명": `${item.main} > ${item.sub1} > ${item.sub2}`,
      "재고 수량": parseFloat(item.value),
      "재고 상태": item.value <= 10 ? "⚠️ 재고 부족" : "정상" //우선 10으로 했는데 태한오빠 그 계산법으로 수정할 예정
    }));
  
    const csv = Papa.unparse(csvData);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    saveAs(blob, "inventory_data.csv");
  };

  return (
    <div>
      <h2>📦 재고 관리</h2>
      <div className="controls">
        <input
          type="text"
          placeholder="🔍 상품명 검색"
          value={searchQuery}
          onChange={handleSearch}
        />
        <select onChange={handleCategoryFilter} value={selectedCategory}>
          <option value="All">전체 카테고리</option>
          {[...new Set(inventory.map((item) => item.main))].map((cat) => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
        <button onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}>
          {sortOrder === "asc" ? "📉 재고 내림차순 정렬" : "📈 재고 오름차순 정렬"}
        </button>
        <button onClick={fetchInventory}>🔄 새로고침</button>
        <button onClick={downloadCSV}>📥 CSV 다운로드</button>
      </div>
      
      <table className="inventory-table">
        <thead>
          <tr>
            <th>세부 분류</th>
            <th>설명</th>
            <th>재고량</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          {filteredInventory.map((item, index) => (
            <tr key={index} className={item.value <= 10 ? "low-stock" : ""}>
              <td>{item.sub3}</td>
              <td className="description">{`${item.main} > ${item.sub1} > ${item.sub2}`}</td>
              <td>{item.value}</td>
              <td className={item.value <= 10 ? "low-stock-text" : "normal-stock"}>
                {item.value <= 10 ? "⚠️ 재고 부족" : "✅"}
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
          .normal-stock {
            color: green;
          }
        `}
      </style>
    </div>
  );
};

export default InventoryPage;
