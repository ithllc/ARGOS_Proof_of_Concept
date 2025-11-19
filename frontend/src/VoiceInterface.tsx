import React, { useRef, useState, useEffect, useCallback } from 'react';

const VoiceInterface: React.FC = () => {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null); // Use useRef for WebSocket instance
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<Array<ArrayBuffer>>([]);
  const audioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const [currentMedia, setCurrentMedia] = useState<{ url: string; type: 'image' | 'video' } | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const processAudioQueue = useCallback(async () => {
    if (audioQueueRef.current.length > 0 && audioContextRef.current && !audioSourceRef.current) {
      const audioData = audioQueueRef.current.shift();
      if (audioData) {
        try {
          const audioBuffer = await audioContextRef.current.decodeAudioData(audioData);
          const source = audioContextRef.current.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(audioContextRef.current.destination);
          source.onended = () => {
            audioSourceRef.current = null;
            if (currentMedia?.type === 'video' && videoRef.current) {
              videoRef.current.play().catch(e => console.error("Error playing video:", e));
            }
            processAudioQueue();
          };
          source.start(0);
          audioSourceRef.current = source;
        } catch (e) {
          console.error("Error decoding audio data:", e);
          audioSourceRef.current = null;
          processAudioQueue();
        }
      }
    }
  }, [currentMedia]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setMediaStream(stream);
      setIsRecording(true);

      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/live`;
      const newWs = new WebSocket(wsUrl);
      wsRef.current = newWs; // Assign to ref

      newWs.onopen = () => {
        console.log('WebSocket connected');
      };

      newWs.onmessage = async (event) => {
        if (typeof event.data === 'string') {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'media_url') {
              setCurrentMedia({ url: message.url, type: message.media_type });
            } else if (message.type === 'text_response') {
              // Handle text responses if needed, e.g., display them
              console.log("Agent text response:", message.text);
            }
          } catch (e) {
            console.error("Error parsing WebSocket message:", e);
          }
        } else if (event.data instanceof Blob) {
          const arrayBuffer = await event.data.arrayBuffer();
          audioQueueRef.current.push(arrayBuffer);
          processAudioQueue();
        }
      };

      newWs.onclose = () => {
        console.log('WebSocket disconnected');
        setIsRecording(false);
        if (mediaStream) {
          mediaStream.getTracks().forEach(track => track.stop());
        }
      };

      newWs.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsRecording(false);
        if (mediaStream) {
          mediaStream.getTracks().forEach(track => track.stop());
        }
      };
      
      processor.onaudioprocess = (event) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) { // Use wsRef.current
          const input = event.inputBuffer.getChannelData(0);
          const pcm16 = new Int16Array(input.length);
          for (let i = 0; i < input.length; i++) {
            pcm16[i] = Math.max(-1, Math..min(1, input[i])) * 0x7FFF;
          }
          wsRef.current.send(pcm16.buffer); // Use wsRef.current
        }
      };

      source.connect(processor);
      processor.connect(audioContextRef.current.destination);

    } catch (error) {
      console.error('Error accessing microphone:', error);
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (wsRef.current) { // Use wsRef.current
      wsRef.current.close(); // Use wsRef.current
      wsRef.current = null; // Clean up ref
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      setMediaStream(null);
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setIsRecording(false);
    audioQueueRef.current = [];
    if (audioSourceRef.current) {
      audioSourceRef.current.stop();
      audioSourceRef.current = null;
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Voice Interface</h1>
      <button onClick={isRecording ? stopRecording : startRecording} style={{
        padding: '10px 20px',
        fontSize: '16px',
        backgroundColor: isRecording ? '#ff4d4d' : '#4CAF50',
        color: 'white',
        border: 'none',
        borderRadius: '5px',
        cursor: 'pointer'
      }}>
        {isRecording ? 'Stop Recording' : 'Start Recording'}
      </button>

      {currentMedia && (
        <div style={{ marginTop: '20px', border: '1px solid #ccc', padding: '10px', borderRadius: '5px' }}>
          <h2>Generated Media</h2>
          {currentMedia.type === 'image' && (
            <img src={currentMedia.url} alt="Generated" style={{ maxWidth: '100%', height: 'auto' }} />
          )}
          {currentMedia.type === 'video' && (
            <video ref={videoRef} src={currentMedia.url} controls muted playsInline style={{ maxWidth: '100%', height: 'auto' }} />
          )}
        </div>
      )}
    </div>
  );
};

export default VoiceInterface;