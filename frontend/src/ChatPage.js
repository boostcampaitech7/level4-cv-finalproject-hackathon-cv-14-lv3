import React, { useState } from 'react';

const ChatPage = () => {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
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
        setResponse('');
      } else {
        setResponse(data.response);
        setError(null);
      }
      setMessage('');
    } catch (error) {
      console.error('Error:', error);
      setError('서버 연결에 실패했습니다.');
      setResponse('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>AI 챗봇 상담</h1>
      <div style={styles.container}>
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
        {error && (
          <div style={styles.error}>
            <p>{error}</p>
          </div>
        )}
        {response && (
          <div style={styles.response}>
            <p>{response}</p>
          </div>
        )}
      </div>
    </div>
  );
};

const styles = {
  page: {
    backgroundColor: "#f4f4f9",
    minHeight: '100vh',
    padding: '20px',
  },
  title: {
    textAlign: 'center',
    color: '#333',
    fontSize: '24px',
    fontWeight: 'bold',
    marginBottom: '30px',
  },
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '20px',
    backgroundColor: 'white',
    borderRadius: '15px',
    boxShadow: '0px 4px 6px rgba(0, 0, 0, 0.1)',
  },
  form: {
    display: 'flex',
    gap: '10px',
    marginBottom: '20px',
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
    marginTop: '20px',
    padding: '15px',
    backgroundColor: '#ffebee',
    color: '#c62828',
    borderRadius: '8px',
    fontSize: '16px',
    lineHeight: '1.5',
  },
  response: {
    marginTop: '20px',
    padding: '15px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    fontSize: '16px',
    lineHeight: '1.5',
  },
};

export default ChatPage;