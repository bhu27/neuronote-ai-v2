import React, { useState } from 'react';
import { askQuestion } from '../services/api';

const ChatSection = () => {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const userQ = question;
    setQuestion('');
    setIsLoading(true);
    setError('');

    try {
      const response = await askQuestion(userQ);
      if (response.error) {
        setError(response.error);
      } else {
        setHistory((prev) => [
          { type: 'user', text: userQ },
          { type: 'ai', text: response.answer },
          ...prev
        ]);
      }
    } catch (err) {
      setError(err.message || 'Failed to get an answer.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '400px' }}>
      <h2 className="section-header">💬 Chat with PDF</h2>
      
      <div 
        style={{ 
          flex: 1, 
          overflowY: 'auto', 
          marginBottom: '16px',
          paddingRight: '8px',
          display: 'flex',
          flexDirection: 'column-reverse',
          gap: '12px'
        }}
      >
        {history.map((msg, index) => (
          <div 
            key={index} 
            style={{ 
              alignSelf: msg.type === 'user' ? 'flex-end' : 'flex-start',
              background: msg.type === 'user' ? 'var(--primary-color)' : 'rgba(255,255,255,0.1)',
              padding: '12px 16px',
              borderRadius: '16px',
              borderBottomRightRadius: msg.type === 'user' ? '4px' : '16px',
              borderBottomLeftRadius: msg.type === 'ai' ? '4px' : '16px',
              maxWidth: '85%',
              wordWrap: 'break-word',
              lineHeight: '1.5',
              fontSize: '0.95rem'
            }}
          >
            {msg.text}
          </div>
        ))}
        {history.length === 0 && (
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', margin: 'auto' }}>
            Ask anything about your document!
          </p>
        )}
      </div>

      <form onSubmit={handleAsk} style={{ display: 'flex', gap: '8px' }}>
        <input 
          type="text" 
          placeholder="Type your question..." 
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !question.trim()}>
          {isLoading ? '...' : 'Ask'}
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}
    </div>
  );
};

export default ChatSection;
