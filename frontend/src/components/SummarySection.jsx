import React, { useState } from 'react';
import { getSummary } from '../services/api';

const SummarySection = () => {
  const [mode, setMode] = useState('quick');
  const [summary, setSummary] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    setIsLoading(true);
    setError('');
    setSummary('');

    try {
      const response = await getSummary(mode);
      if (response.error) {
        setError(response.error);
      } else {
        setSummary(response.summary);
      }
    } catch (err) {
      setError(err.message || 'Failed to generate summary.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '400px' }}>
      <div className="section-header" style={{ justifyContent: 'space-between' }}>
        <span>⚡ Smart Summary</span>
        <select 
          value={mode} 
          onChange={(e) => setMode(e.target.value)}
          disabled={isLoading}
        >
          <option value="quick">Quick (5 points)</option>
          <option value="exam">Exam Prep</option>
          <option value="beginner">Beginner</option>
        </select>
      </div>

      <button 
        onClick={handleGenerate} 
        disabled={isLoading}
        style={{ marginBottom: '16px' }}
      >
        {isLoading ? (
          <><span className="loader" style={{width: '16px', height: '16px', marginRight:'8px'}}></span> Generating...</>
        ) : 'Generate Summary'}
      </button>

      {error && <p className="error-text">{error}</p>}

      <div 
        style={{ 
          flex: 1, 
          overflowY: 'auto',
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '8px',
          padding: '16px',
          whiteSpace: 'pre-wrap',
          lineHeight: '1.6',
          fontSize: '0.95rem'
        }}
      >
        {summary ? summary : (
          <span style={{ color: 'var(--text-muted)' }}>
            Select a mode and click generate to see the summary here.
          </span>
        )}
      </div>
    </div>
  );
};

export default SummarySection;
