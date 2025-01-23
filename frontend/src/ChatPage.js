import React, { useState, useEffect, useRef } from 'react';

const ChatPage = () => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]); // 대화 내역 저장
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const chatEndRef = useRef(null); // 스크롤을 제어하기 위한 Ref

  // 스크롤을 최신 메시지로 이동
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom(); // chatHistory가 업데이트될 때마다 스크롤 이동
  }, [chatHistory]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    // 사용자의 메시지를 대화 내역에 추가
    setChatHistory((prevHistory) => [...prevHistory, { sender: 'user', content: message }]);

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: message }),
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

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>AI 챗봇 상담</h1>
      <div style={styles.container}>
        {/* 대화 내역 표시 */}
        <div style={styles.chatHistory}>
          {chatHistory.map((chat, index) => (
            <div
              key={index}
              style={chat.sender === 'user' ? styles.userMessageContainer : styles.botMessageContainer}
            >
              <div style={chat.sender === 'user' ? styles.userMessage : styles.botMessage}>
                {chat.content}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} /> {/* 스크롤을 끝으로 이동시키기 위한 참조 */}
        </div>

        {/* 입력 폼 */}
        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="메시지를 입력하세요..."
            style={styles.input}
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !message.trim()} style={styles.button}>
            {isLoading ? '전송 중...' : '전송'}
          </button>
        </form>

        {/* 에러 표시 */}
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
    backgroundColor: '#f4f4f9',
    height: '100vh', // 전체 화면을 고정
    overflowY: 'hidden', // 전체 페이지에서 스크롤 비활성화
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '20px',
  },
  title: {
    textAlign: 'center',
    color: '#333',
    fontSize: '24px',
    fontWeight: 'bold',
    marginBottom: '10px',
  },
  container: {
    width: '100%',
    maxWidth: '800px',
    backgroundColor: 'white',
    borderRadius: '15px',
    boxShadow: '0px 4px 6px rgba(0, 0, 0, 0.1)',
    display: 'flex',
    flexDirection: 'column',
    height: '80vh', // 전체 페이지 중 80%를 채우도록 설정
    overflow: 'hidden',
  },
  chatHistory: {
    flex: 1, // 상단 영역을 최대한 차지
    overflowY: 'auto', // 스크롤 활성화
    padding: '10px',
    borderBottom: '1px solid #ddd',
    backgroundColor: '#f9f9f9',
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
  },
  userMessage: {
    backgroundColor: '#007bff',
    color: 'white',
    padding: '10px 15px',
    borderRadius: '15px 15px 0 15px',
    maxWidth: '70%',
    wordWrap: 'break-word',
  },
  botMessage: {
    backgroundColor: '#e9ecef',
    color: '#333',
    padding: '10px 15px',
    borderRadius: '15px 15px 15px 0',
    maxWidth: '70%',
    wordWrap: 'break-word',
  },
  form: {
    display: 'flex',
    padding: '10px',
    borderTop: '1px solid #ddd',
    backgroundColor: 'white',
  },
  input: {
    flex: 1,
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '8px',
    fontSize: '16px',
  },
  button: {
    padding: '12px 24px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '16px',
  },
  error: {
    marginTop: '10px',
    padding: '15px',
    backgroundColor: '#ffebee',
    color: '#c62828',
    borderRadius: '8px',
    fontSize: '16px',
    lineHeight: '1.5',
  },
};

export default ChatPage;
