import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import Layout from './Layout';

// App 컴포넌트 - 라우팅
const App = () => (
  <BrowserRouter>
    <Layout />
  </BrowserRouter>
);

export default App;