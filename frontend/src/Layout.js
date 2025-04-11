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
            <Route path="/inventory" element={<InventoryPage/>}/>
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
            width: '290px', // sidebar너비 증가
            backgroundColor: 'white',
            boxShadow: '2px 0 4px rgba(0,0,0,0.1)',
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid #eee'
        },
        logo: {
            padding: '28px 24px',
            borderBottom: '1px solid #eee',
            backgroundColor: '#fafafa'
        },
        title: {
            fontSize: '24px',
            fontWeight: 'bold',
            color: '#333',
            margin: 0,
            letterSpacing: '-0.5px'
        },
        nav: {
            marginTop: '28px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
        },
        menuItem: {
            width: 'calc(100% - 48px)',
            display: 'flex',
            alignItems: 'center',
            padding: '14px 18px',
            margin: '0 24px',
            border: 'none',
            backgroundColor: 'transparent',
            color: '#666',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            textAlign: 'left',
            borderRadius: '12px',
            fontSize: '16px',
            '&:hover': {
                backgroundColor: '#f5f5f5',
                color: '#333'
            }
        },
        activeMenuItem: {
            backgroundColor: '#f0f7ff', // 활성 메뉴 배경색
            color: '#1a73e8', // 활성 메뉴 텍스트 색상
            fontWeight: '600',
            boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
        },
        icon: {
            width: '22px',
            height: '22px',
            marginRight: '14px',
            strokeWidth: 2
        },
        mainContent: {
            flex: 1,
            overflow: 'auto',
            backgroundColor: '#f8f9fa'
        }
    };

export default Layout;
