import React, { useState, useRef } from 'react';
import { uploadPdf } from '../services/api';

const UploadSection = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected && selected.type === 'application/pdf') {
      setFile(selected);
      setError('');
      setMessage('');
    } else {
      setFile(null);
      setError('Please select a valid PDF file.');
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setError('');
    setMessage('');
    
    try {
      const response = await uploadPdf(file);
      if (response.error) {
        setError(response.error);
      } else {
        setMessage('Upload successful! Document is ready.');
        if (onUploadSuccess) onUploadSuccess();
      }
    } catch (err) {
      setError(err.message || 'Failed to upload document.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ textAlign: 'center' }}>
      <h2 className="section-header">📄 Upload PDF Document</h2>
      
      <div 
        style={{
          border: '2px dashed var(--panel-border)',
          borderRadius: '12px',
          padding: '40px 20px',
          marginBottom: '20px',
          background: 'rgba(0,0,0,0.2)',
          cursor: 'pointer'
        }}
        onClick={() => fileInputRef.current.click()}
      >
        <input 
          type="file" 
          accept="application/pdf"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        {file ? (
          <p style={{ color: 'var(--primary-color)' }}>{file.name}</p>
        ) : (
          <p style={{ color: 'var(--text-muted)' }}>Click here or browse to select a PDF</p>
        )}
      </div>

      <button 
        onClick={handleUpload} 
        disabled={!file || isUploading}
        style={{ width: '100%' }}
      >
        {isUploading ? (
          <><span className="loader" style={{width: '16px', height: '16px', marginRight:'8px'}}></span> Uploading...</>
        ) : 'Analyze Document'}
      </button>

      {error && <p className="error-text">{error}</p>}
      {message && <p className="success-text">{message}</p>}
    </div>
  );
};

export default UploadSection;
