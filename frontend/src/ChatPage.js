import React, { useState, useEffect, useRef } from 'react';

const ChatPage = () => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]); // 대화 내역 저장
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState(null); // chat mode 저장

  const chatEndRef = useRef(null); // 스크롤을 제어하기 위한 Ref

  // 스크롤을 최신 메시지로 이동
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    setChatHistory([
      {
        sender: 'bot',
        content: '안녕하세요, 매출&재고 관리 AI 어시스턴트입니다. 무엇을 도와드릴까요?',
        showButtons: true // mode 선택 버튼
      }
    ]);
  }, []);

  // mode 선택 핸들러
  const handleModeSelect = async (selectedMode) => {
    setMode(selectedMode);
    const userChoice = selectedMode === 'data' ? '데이터 기반 조회' : '트렌드 분석';

    setChatHistory((prev) => [...prev, 
      { sender: 'user', content: userChoice },
      { sender: 'bot', content: selectedMode === 'data' ? 
        '데이터 기반 조회를 선택하셨습니다. 어떤 정보를 조회하시겠습니까?' :
        '트렌드 분석을 선택하셨습니다. 어떤 트렌드를 분석하시겠습니까?' 
      }
    ]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    // 사용자의 메시지를 대화 내역에 추가
    setChatHistory((prev) => [...prev, { sender: 'user', content: message }]);

    setIsLoading(true);
    setError(null);

    try {
      // mode에 따라 다른 엔드포인트 호출
      const endpoint = mode === 'data' ? 
        'http://localhost:8000/api/chat' : 
        'http://localhost:8000/api/trend-chat';

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: message,
          mode: mode
        }),
      });

      const data = await res.json();

      if (data.status === 'error') {
        setError(data.error || data.response);
      } else {
        // 챗봇의 응답을 대화 내역에 추가
        setChatHistory((prevHistory) => [
          ...prevHistory,
          { sender: 'bot', content: data.response },
        ]);
      }
    } catch (error) {
      console.error('Error:', error);
      setError('서버 연결에 실패했습니다.');
    } finally {
      setIsLoading(false);
      setMessage(''); // 입력 창 초기화
    }
  };

  const renderMessage = (chat, index) => (
    <>
      <div
        key={`message-${index}`}
        style={chat.sender === 'user' ? styles.userMessageContainer : styles.botMessageContainer}
      >
        {chat.sender === 'bot' && (
          <div style={styles.botProfile}>
            <img src="/bot-profile.png" alt="Bot" style={styles.profileImage} />
          </div>
        )}
        <div style={chat.sender === 'user' ? styles.userMessage : styles.botMessage}>
          {/* 메시지 내용 줄바꿈 처리 */}
          {chat.content.split("\n").map((line, i) => (
            <React.Fragment key={i}>
              {line}
              <br />
            </React.Fragment>
          ))}
        </div>
      </div>
      {/* 버튼을 별도 컨테이너로 분리 */}
      {chat.showButtons && (
        <div key={`buttons-${index}`} style={styles.modeButtonContainer}>
          <button 
            onClick={() => handleModeSelect('data')}
            style={styles.modeButton}
          >
            데이터 기반 조회
          </button>
          <button 
            onClick={() => handleModeSelect('trend')}
            style={styles.modeButton}
          >
            트렌드 분석
          </button>
        </div>
      )}
    </>
  );
  

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>AI 챗봇 상담</h1>
      <div style={styles.container}>
        {/* 대화 내역 표시 */}
        <div style={styles.chatHistory}>
        {chatHistory.map((chat, index) => renderMessage(chat, index))}
          <div ref={chatEndRef} />
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="메시지를 입력하세요..."
            style={styles.input}
            disabled={isLoading || !mode} // 모드 선택 전에는 입력 비활성화
          />
          <button 
            type="submit" 
            disabled={isLoading || !message.trim() || !mode}
            style={styles.button}
          >
            {isLoading ? '전송 중...' : '전송'}
          </button>
        </form>

        {error && (
          <div style={styles.error}>
            <p>{error}</p>
          </div>
        )}
      </div>
    </div>
  );
};

const styles = {
  page: {
    backgroundColor: '#f8f9fa',
    backgroundImage: 'linear-gradient(to bottom right, #f8f9fa, #e9ecef)',
    height: '100vh',
    overflowY: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '20px',
  },
  title: {
    textAlign: 'center',
    color: '#2c3e50',
    fontSize: '28px',
    fontWeight: '600',
    marginBottom: '20px',
    letterSpacing: '0.5px',
    textShadow: '1px 1px 2px rgba(0,0,0,0.1)',
  },
  container: {
    width: '100%',
    maxWidth: '800px',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: '20px',
    boxShadow: '0 10px 20px rgba(0, 0, 0, 0.08)',
    display: 'flex',
    flexDirection: 'column',
    height: '80vh',
    overflow: 'hidden',
    border: '1px solid rgba(0,0,0,0.1)',
  },
  chatHistory: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    borderBottom: '1px solid rgba(0,0,0,0.08)',
    backgroundColor: 'rgba(249, 249, 249, 0.8)',
  },
  userMessageContainer: {
    display: 'flex',
    justifyContent: 'flex-end',
    marginBottom: '10px',
  },
  botMessageContainer: {
    display: 'flex',
    justifyContent: 'flex-start',
    marginBottom: '10px',
    alignItems: 'flex-start', // 상단 정렬을 위해 추가
  },
  userMessage: {
    backgroundColor: '#4a90e2',
    color: 'white',
    padding: '12px 18px',
    borderRadius: '18px 18px 0 18px',
    maxWidth: '70%',
    wordWrap: 'break-word',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  botMessage: {
    backgroundColor: 'white',
    color: '#2c3e50',
    padding: '12px 18px',
    borderRadius: '18px 18px 18px 0',
    maxWidth: '70%',
    wordWrap: 'break-word',
    marginLeft: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    border: '1px solid rgba(0,0,0,0.05)',
  },
  form: {
    display: 'flex',
    padding: '15px 20px',
    borderTop: '1px solid rgba(0,0,0,0.08)',
    backgroundColor: 'white',
  },
  input: {
    flex: 1,
    padding: '12px 18px',
    border: '1px solid rgba(0,0,0,0.1)',
    borderRadius: '25px',
    fontSize: '16px',
    marginRight: '15px',
    transition: 'all 0.3s ease',
    '&:focus': {
      outline: 'none',
      borderColor: '#4a90e2',
      boxShadow: '0 0 0 2px rgba(74,144,226,0.2)',
    },
  },
  button: {
    padding: '12px 28px',
    backgroundColor: '#4a90e2',
    color: 'white',
    border: 'none',
    borderRadius: '25px',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: '500',
    transition: 'all 0.3s ease',
    '&:hover': {
      backgroundColor: '#357abd',
      transform: 'translateY(-1px)',
    },
    '&:disabled': {
      backgroundColor: '#ccc',
      cursor: 'not-allowed',
    },
  },
  error: {
    marginTop: '10px',
    padding: '15px',
    backgroundColor: 'rgba(255,235,238,0.9)',
    color: '#c62828',
    borderRadius: '12px',
    fontSize: '16px',
    lineHeight: '1.5',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
  },
  botProfile: {
    marginRight: '8px',
    marginTop: '4px',
  },
  profileImage: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    backgroundColor: '#e9ecef',
    border: '2px solid white',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  modeButtonContainer: {
    display: 'flex',
    justifyContent: 'flex-end', // 오른쪽 정렬
    gap: '10px',
    padding: '10px 20px',
    marginBottom: '15px',
  },
  modeButton: {
    padding: '10px 20px',
    backgroundColor: '#4a90e2',
    color: 'white',
    border: 'none',
    borderRadius: '20px',
    cursor: 'pointer',
    fontSize: '14px',
    transition: 'all 0.3s ease',
    '&:hover': {
      backgroundColor: '#357abd',
    },
  },
};

export default ChatPage;
