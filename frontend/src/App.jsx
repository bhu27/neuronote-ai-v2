import React from 'react';
import UploadSection from './components/UploadSection';
import ChatSection from './components/ChatSection';
import SummarySection from './components/SummarySection';
import MindmapViewer from './components/MindmapViewer';

function App() {
  return (
    <>
      <h1 className="title">NeuroNote AI</h1>
      <p className="subtitle">Your intelligent PDF study companion</p>
      
      <div className="dashboard-container">
        {/* Left Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <UploadSection />
          <ChatSection />
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <SummarySection />
          <MindmapViewer />
        </div>
      </div>
    </>
  );
}

export default App;
