import React from 'react';
import { CopilotKit } from '@copilotkit/react-core';
import { CopilotSidebar } from '@copilotkit/react-ui';
import '@copilotkit/react-ui/styles.css';
import VoiceInterface from './VoiceInterface';
import AgentStatus from './AgentStatus'; // Import AgentStatus

function App() {
  return (
    <CopilotKit 
      runtimeUrl="/copilotkit"
      agent="coordinator"
    >
      <div className="App">
        <header className="App-header">
          <h1>ARGOS POC - Agent Collaboration Platform</h1>
        </header>
        <main>
          <VoiceInterface />
          <AgentStatus /> {/* Add AgentStatus component */}
          <CopilotSidebar
            labels={{
              title: "ARGOS Assistant",
              initial: "Hi! I can help you analyze research papers and synthesize novel applications. What would you like to explore?"
            }}
          />
        </main>
      </div>
    </CopilotKit>
  );
}

export default App;