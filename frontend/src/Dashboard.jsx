import React, {useEffect, useState} from 'react';

import AgentStatus from './AgentStatus';
import VoiceInterface from './VoiceInterface';
import PaperVisualizer from './PaperVisualizer';

export default function Dashboard() {
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/dashboard');
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages((m) => [data, ...m]);
      } catch (e) {
        setMessages((m) => [event.data, ...m]);
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div style={{display: 'flex', gap: 20}}>
      <div style={{flex: 1}}>
        <h2>Mini-ARGOS POC</h2>
        <VoiceInterface />
        <PaperVisualizer />
      </div>
      <div style={{width: 350}}>
        <AgentStatus />
        <div>
          <h3>Agent Events</h3>
          <div style={{height: 400, overflowY: 'auto'}}>
            {messages.map((m, i) => (
              <div key={i} style={{borderBottom: '1px solid #eee', padding: 8}}>
                <pre style={{whiteSpace: 'pre-wrap'}}>{JSON.stringify(m, null, 2)}</pre>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
