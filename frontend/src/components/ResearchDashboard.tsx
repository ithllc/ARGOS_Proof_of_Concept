import React, { useState, useEffect } from 'react';
import { useCoAgent } from '@copilotkit/react-core';
import { ResearchState, TaskStatus } from '../types';

const INITIAL_STATE: ResearchState = {
  query: "",
  tasks: [],
  papers: [],
  analysis: "",
  status: "idle"
};

export default function ResearchDashboard() {
  // Sync state with the 'coordinator' agent (which we set up as the shared state agent)
  // Note: The agent name in useCoAgent must match the name used in the backend (which is 'coordinator')
  // However, the example used 'shared_state'. In main.py we mapped coordinator to /copilotkit.
  // The agent name in LlmAgent is 'coordinator'.
  const { state: agentState, setState: setAgentState } = useCoAgent<ResearchState>({
    name: "coordinator", 
    initialState: INITIAL_STATE,
  });

  const [localState, setLocalState] = useState(INITIAL_STATE);

  // Sync local state with agent state when it changes
  useEffect(() => {
    if (agentState) {
      setLocalState(agentState);
    }
  }, [agentState]);

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value;
    setLocalState(prev => ({ ...prev, query: newQuery }));
    // We don't necessarily push every keystroke to the agent, but for shared state we might want to.
    // For now, let's update it on blur or enter, or just let the agent handle it via chat.
    // But to follow the "Shared State" pattern where UI controls state:
    setAgentState({ ...agentState, query: newQuery });
  };

  return (
    <div className="research-dashboard" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      
      {/* Header Section */}
      <div className="dashboard-header" style={{ marginBottom: '30px', textAlign: 'center' }}>
        <h1 style={{ fontSize: '2.5rem', color: '#333' }}>ARGOS Research Workspace</h1>
        <p style={{ color: '#666' }}>Collaborative AI Research Assistant</p>
      </div>

      {/* Main Query Input */}
      <div className="query-section" style={{ marginBottom: '40px' }}>
        <input
          type="text"
          value={localState.query}
          onChange={handleQueryChange}
          placeholder="Enter your research topic..."
          style={{
            width: '100%',
            padding: '15px',
            fontSize: '1.2rem',
            borderRadius: '8px',
            border: '1px solid #ddd',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}
        />
      </div>

      <div className="dashboard-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
        
        {/* Left Column: Tasks & Papers */}
        <div className="left-column">
          
          {/* Tasks Section */}
          <div className="section-card" style={cardStyle}>
            <h2 style={sectionTitleStyle}>Research Plan</h2>
            <div className="tasks-list">
              {localState.tasks.length === 0 && <p style={{ color: '#999', fontStyle: 'italic' }}>No tasks generated yet.</p>}
              {localState.tasks.map((task, idx) => (
                <div key={task.id || idx} style={{ 
                  padding: '10px', 
                  borderBottom: '1px solid #eee',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}>
                  <StatusIcon status={task.status} />
                  <span style={{ flex: 1 }}>{task.description}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Papers Section */}
          <div className="section-card" style={{ ...cardStyle, marginTop: '20px' }}>
            <h2 style={sectionTitleStyle}>Found Papers</h2>
            <div className="papers-list">
              {localState.papers.length === 0 && <p style={{ color: '#999', fontStyle: 'italic' }}>No papers found yet.</p>}
              {localState.papers.map((paper, idx) => (
                <div key={idx} style={{ padding: '15px', borderBottom: '1px solid #eee' }}>
                  <a href={paper.url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 'bold', color: '#0066cc', textDecoration: 'none' }}>
                    {paper.title}
                  </a>
                  {paper.summary && <p style={{ fontSize: '0.9rem', color: '#555', marginTop: '5px' }}>{paper.summary}</p>}
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Column: Analysis */}
        <div className="right-column">
          <div className="section-card" style={{ ...cardStyle, height: '100%' }}>
            <h2 style={sectionTitleStyle}>Synthesis & Analysis</h2>
            <div className="analysis-content" style={{ lineHeight: '1.6', color: '#333' }}>
              {localState.analysis ? (
                <div dangerouslySetInnerHTML={{ __html: localState.analysis.replace(/\n/g, '<br/>') }} />
              ) : (
                <p style={{ color: '#999', fontStyle: 'italic' }}>Analysis will appear here as research progresses...</p>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

// --- Helper Components & Styles ---

const cardStyle = {
  backgroundColor: 'white',
  borderRadius: '12px',
  padding: '20px',
  boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
  border: '1px solid #eee'
};

const sectionTitleStyle = {
  fontSize: '1.2rem',
  marginBottom: '15px',
  color: '#444',
  borderBottom: '2px solid #f0f0f0',
  paddingBottom: '10px'
};

function StatusIcon({ status }: { status: TaskStatus }) {
  let color = '#ccc';
  let icon = '○';

  switch (status) {
    case TaskStatus.COMPLETED:
      color = '#4caf50';
      icon = '✓';
      break;
    case TaskStatus.IN_PROGRESS:
      color = '#2196f3';
      icon = '↻';
      break;
    case TaskStatus.FAILED:
      color = '#f44336';
      icon = '✕';
      break;
  }

  return (
    <span style={{ 
      color, 
      fontWeight: 'bold', 
      fontSize: '1.2rem', 
      width: '24px', 
      textAlign: 'center' 
    }}>
      {icon}
    </span>
  );
}
