import React, { useState } from 'react';
import { getMindmap } from '../services/api';

const TreeNode = ({ node }) => {
  if (!node) return null;
  
  return (
    <div style={{ paddingLeft: '20px', marginTop: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ color: 'var(--primary-color)' }}>❖</span>
        <strong style={{ fontSize: '1.05rem' }}>{node.topic || node.name}</strong>
      </div>
      
      {node.points && node.points.length > 0 && (
        <ul style={{ paddingLeft: '32px', marginTop: '8px', color: 'var(--text-muted)' }}>
          {node.points.map((pt, i) => (
            <li key={i} style={{ marginBottom: '4px' }}>{pt}</li>
          ))}
        </ul>
      )}

      {node.subtopics && node.subtopics.map((sub, i) => (
        <TreeNode key={i} node={sub} />
      ))}
    </div>
  );
};

const MindmapViewer = () => {
  const [mindmapData, setMindmapData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFetch = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await getMindmap();
      if (response.error) {
        setError(response.error);
      } else {
        setMindmapData(response.mindmap);
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch mindmap.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '400px' }}>
      <div className="section-header" style={{ justifyContent: 'space-between' }}>
        <span>🧠 Structured Mindmap</span>
        <button onClick={handleFetch} disabled={isLoading}>
          {isLoading ? (
            <><span className="loader" style={{width: '16px', height: '16px', marginRight:'8px'}}></span> Fetching...</>
          ) : 'Generate Map'}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div 
        style={{ 
          flex: 1, 
          overflowY: 'auto',
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '8px',
          padding: '16px',
        }}
      >
        {mindmapData ? (
          <TreeNode node={mindmapData} />
        ) : (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '30%' }}>
            Click generate to visualize the document structure.
          </div>
        )}
      </div>
    </div>
  );
};

export default MindmapViewer;
