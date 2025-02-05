import React from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';  
import { MessageSquare, BarChart2, Package } from 'lucide-react';
import ChatPage from './ChatPage';
import DashPage from './DashPage';
import InventoryPage from './InventoryPage';

const Layout = () => {
    // 페이지 네비게이션 hook
    const navigate = useNavigate();
    const location = useLocation();

    // 사이드바 메뉴 아이템
    const menuItems = [
        { id: 'chat', icon: MessageSquare, label: 'Chatbot' },
        { id: 'dashboard', icon: BarChart2, label: 'Dashboard' },
        { id: 'inventory', icon: Package, label: 'Inventory' }
    ];

    // 현재 활성화된 메뉴 확인
    const isActive = (path) => {
        if (path === 'chat' && location.pathname === '/') return true;
        return location.pathname === `/${path}`;
    };

    return (
        <div style={styles.container}>
        {/* 사이드바 */}
        <div style={styles.sidebar}>
            {/* 로고 영역 */}
            <div style={styles.logo}>
            {/* 임시 title */}
            <h1 style={styles.title}>StockSense</h1> 
            </div>
            
            {/* 네비게이션 메뉴 */}
            <nav style={styles.nav}>
            {menuItems.map(({ id, icon: Icon, label }) => (
                <button
                key={id}
                onClick={() => navigate(`/${id}`)}
                style={{
                    ...styles.menuItem,
                    ...(isActive(id) && styles.activeMenuItem) // 활성 메뉴 스타일 적용
                }}
                >
                <Icon style={styles.icon} />
                <span>{label}</span>
                </button>
            ))}
            </nav>
        </div>

        {/* 메인 컨텐츠 */}
        <div style={styles.mainContent}>
            <Routes>
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/dashboard" element={<DashPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/" element={<ChatPage />} />
            </Routes>
        </div>
        </div>
    );
    };

    const styles = {
    container: {
        display: 'flex',
        height: '100vh',
        backgroundColor: '#f8f9fa'
    },
    sidebar: {
        width: '256px',
        backgroundColor: 'white',
        boxShadow: '2px 0 4px rgba(0,0,0,0.1)'
    },
    logo: {
        padding: '24px',
        borderBottom: '1px solid #eee'
    },
    title: {
        fontSize: '20px',
        fontWeight: 'bold',
        color: '#333'
    },
    nav: {
        marginTop: '24px'
    },
    menuItem: {
        width: 'calc(100% - 48px)', 
        display: 'flex',
        alignItems: 'center',
        padding: '12px 16px',  
        margin: '4px 24px',    
        border: 'none',
        backgroundColor: 'transparent',
        color: '#666',
        cursor: 'pointer',
        transition: 'all 0.2s',
        textAlign: 'left',
        borderRadius: '8px',   
    },
    activeMenuItem: { 
        backgroundColor: '#f0f0f0',  
        color: '#333',              
        fontWeight: '500'          
    },
    icon: {
        width: '20px',
        height: '20px',
        marginRight: '12px'
    },
    mainContent: {
        flex: 1,
        overflow: 'auto'
    },
    contentContainer: {
        width: '100%',
        height: '100%',
        overflow: 'auto',
        padding: '20px'
    },
    contentWrapper: {
        padding: '32px'
    },
    contentBox: {
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    },
    content: {
        padding: '24px'
    }
};

export default Layout;