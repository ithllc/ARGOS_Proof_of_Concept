import React from 'react';
import { CopilotKit } from '@copilotkit/react-core';
import { CopilotSidebar } from '@copilotkit/react-ui';
import '@copilotkit/react-ui/styles.css';
import VoiceInterface from './VoiceInterface';
import AgentStatus from './AgentStatus';
import ResearchDashboard from './components/ResearchDashboard';

function App() {
  return (
    <CopilotKit 
      runtimeUrl="/copilotkit"
      agent="coordinator"
    >
      <div className="App" style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
        
        {/* Main Dashboard Content */}
        <main>
          <ResearchDashboard />
        </main>

        {/* Floating/Fixed Utilities */}
        <div style={{ position: 'fixed', bottom: '20px', left: '20px', zIndex: 1000 }}>
          <VoiceInterface />
        </div>
        
        <div style={{ position: 'fixed', top: '20px', right: '20px', zIndex: 1000 }}>
          <AgentStatus />
        </div>

        {/* Copilot Sidebar */}
        <CopilotSidebar
          labels={{
            title: "ARGOS Assistant",
            initial: "Hi! I'm your research coordinator. What topic shall we investigate today?"
          }}
        />
      </div>
    </CopilotKit>
  );
}

export default App;