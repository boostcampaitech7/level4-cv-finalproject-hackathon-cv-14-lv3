import React from "react";
import ReactDOM from "react-dom/client"; // React 18 이상에서는 createRoot를 사용
import App from "./App";

const root = ReactDOM.createRoot(document.getElementById("root")); // createRoot 사용
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
