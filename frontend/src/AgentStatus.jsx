import React, { useState, useEffect, useRef } from 'react';

interface AgentEvent {
  timestamp: string;
  agent: string;
  status: string;
  text?: string;
}

const AgentStatus: React.FC = () => {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/events`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('AgentStatus WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const newEvent: AgentEvent = {
          timestamp: new Date().toLocaleTimeString(),
          agent: message.agent || 'Unknown',
          status: message.status || 'N/A',
          text: message.text || ''
        };
        setEvents((prevEvents) => [...prevEvents, newEvent]);
      } catch (e) {
        console.error("Error parsing agent event message:", e);
      }
    };

    ws.onclose = () => {
      console.log('AgentStatus WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('AgentStatus WebSocket error:', error);
    };

    return () => {
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif', border: '1px solid #eee', borderRadius: '8px', marginTop: '20px', backgroundColor: '#f9f9f9' }}>
      <h2>Agent Activity Log</h2>
      <div ref={scrollRef} style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #ddd', padding: '10px', borderRadius: '4px', backgroundColor: '#fff' }}>
        {events.length === 0 ? (
          <p>No agent activity yet...</p>
        ) : (
          <ul style={{ listStyleType: 'none', padding: 0 }}>
            {events.map((event, index) => (
              <li key={index} style={{ marginBottom: '8px', borderBottom: '1px dotted #eee', paddingBottom: '8px' }}>
                <strong style={{ color: '#555' }}>[{event.timestamp}] {event.agent}:</strong> {event.status}
                {event.text && <span style={{ fontStyle: 'italic', marginLeft: '5px', color: '#777' }}>- "{event.text}"</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default AgentStatus;