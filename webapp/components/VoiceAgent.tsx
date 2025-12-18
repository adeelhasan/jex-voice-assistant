'use client';

import {
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
  BarVisualizer,
  useLocalParticipant,
  useRoomContext,
} from '@livekit/components-react';
import { useCallback, useEffect, useState } from 'react';
import { ArtifactPanel } from './ArtifactPanel';
import { ConnectionState } from 'livekit-client';

export function VoiceAgent() {
  const [connectionState, setConnectionState] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [token, setToken] = useState<string>('');
  const [error, setError] = useState<string>('');

  // Debug: log current state on every render
  console.log('[VoiceAgent] Render - connectionState:', connectionState, 'hasToken:', !!token);

  const connect = useCallback(async () => {
    console.log('[VoiceAgent] Starting connection...');
    setConnectionState('connecting');
    setError('');

    try {
      console.log('[VoiceAgent] Fetching token from /api/token...');
      const res = await fetch('/api/token');
      console.log('[VoiceAgent] Token response status:', res.status);

      if (!res.ok) {
        throw new Error(`Token fetch failed: ${res.status} ${res.statusText}`);
      }

      const data = await res.json();
      console.log('[VoiceAgent] Token data received:', data);

      if (data.error) throw new Error(data.error);
      if (!data.token) throw new Error('No token in response');

      setToken(data.token);
      setConnectionState('connected');
      console.log('[VoiceAgent] Connection state set to connected');
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : 'Failed to connect';
      console.error('[VoiceAgent] Connection error:', errorMsg, e);
      setError(errorMsg);
      setConnectionState('disconnected');
    }
  }, []);

  if (connectionState === 'disconnected') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-6">🎤</div>
          <h2 className="text-2xl font-semibold mb-4 text-gray-800">Ready to Connect</h2>
          <p className="text-gray-600 mb-8">
            Click the button below to start talking with JEX, your personal voice assistant.
          </p>
          <button
            onClick={connect}
            className="px-8 py-4 bg-blue-600 text-white rounded-full text-lg font-medium hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
          >
            Connect to JEX
          </button>
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (connectionState === 'connecting') {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse text-gray-500 text-xl">Connecting to JEX...</div>
          <div className="mt-4 text-gray-400 text-sm">Please wait</div>
          <div className="mt-4 text-xs text-gray-300">State: {connectionState}, Token: {token ? 'yes' : 'no'}</div>
        </div>
      </div>
    );
  }

  // Safety check - if we somehow have token but wrong state, force render
  if (token && connectionState !== 'connected') {
    console.error('[VoiceAgent] STATE MISMATCH! Have token but state is:', connectionState);
    console.log('[VoiceAgent] Forcing state to connected...');
    setTimeout(() => setConnectionState('connected'), 0);
  }

  // Debug LiveKit connection
  console.log('[VoiceAgent] About to render LiveKitRoom:', {
    hasToken: !!token,
    tokenPreview: token?.substring(0, 20) + '...',
    serverUrl: process.env.NEXT_PUBLIC_LIVEKIT_URL,
    connect: true,
    audio: true
  });

  return (
    <LiveKitRoom
      token={token}
      serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={() => setConnectionState('disconnected')}
      onConnected={() => console.log('[VoiceAgent] ✅ LiveKitRoom CONNECTED!')}
      className="flex-1 flex"
    >
      <AgentDispatcher />
      {/* Voice interaction area */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b px-6 py-4 shadow-sm">
          <h1 className="text-2xl font-bold text-gray-800">JEX</h1>
          <p className="text-sm text-gray-500">Your Personal Voice Assistant</p>
        </header>
        <div className="flex-1">
          <AgentInterface />
        </div>
      </div>

      {/* Artifact panel - Phase 2 */}
      <aside className="w-[400px] bg-white border-l shadow-lg">
        <ArtifactPanel />
      </aside>

      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

function AgentInterface() {
  const { state, audioTrack } = useVoiceAssistant();
  const [isMuted, setIsMuted] = useState(false);
  const { localParticipant } = useLocalParticipant();

  const toggleMute = () => {
    if (localParticipant) {
      localParticipant.setMicrophoneEnabled(isMuted);
      setIsMuted(!isMuted);
    }
  };

  const stateConfig = {
    disconnected: { icon: '⚫', text: 'Disconnected', color: 'text-gray-400', bg: 'bg-gray-100' },
    connecting: { icon: '🟡', text: 'Connecting...', color: 'text-yellow-500', bg: 'bg-yellow-50' },
    initializing: { icon: '🟡', text: 'Initializing...', color: 'text-yellow-500', bg: 'bg-yellow-50' },
    listening: { icon: '🎤', text: 'Listening...', color: 'text-green-500', bg: 'bg-green-50' },
    thinking: { icon: '🧠', text: 'Thinking...', color: 'text-purple-500', bg: 'bg-purple-50' },
    speaking: { icon: '🔊', text: 'Speaking...', color: 'text-blue-500', bg: 'bg-blue-50' },
  };

  const current = stateConfig[state] || stateConfig.disconnected;

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      {/* Agent State Display */}
      <div className={`rounded-full p-8 mb-6 ${current.bg} transition-colors duration-300`}>
        <div className={`text-8xl ${current.color} transition-colors duration-300`}>
          {isMuted ? '🔇' : current.icon}
        </div>
      </div>

      <div className={`text-2xl font-medium mb-2 ${current.color} transition-colors duration-300`}>
        {isMuted ? 'Muted' : current.text}
      </div>

      {/* Audio Visualizer */}
      {audioTrack && !isMuted && (
        <div className="mt-6 mb-8">
          <BarVisualizer
            state={state}
            trackRef={audioTrack}
            barCount={7}
            options={{ barWidth: 8, barSpacing: 6, barHeight: 60 }}
          />
        </div>
      )}

      {/* Mute Button */}
      <button
        onClick={toggleMute}
        className={`mt-8 px-8 py-3 rounded-full font-medium transition-all shadow-md hover:shadow-lg ${
          isMuted
            ? 'bg-red-100 text-red-600 hover:bg-red-200 border-2 border-red-300'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border-2 border-gray-300'
        }`}
      >
        {isMuted ? '🔇 Unmute Microphone' : '🎤 Mute Microphone'}
      </button>

      {/* Instructions */}
      <div className="mt-12 text-center max-w-lg">
        {isMuted ? (
          <p className="text-gray-500">
            Your microphone is muted. Click <strong>Unmute</strong> to continue talking with JEX.
          </p>
        ) : (
          <div className="text-gray-500 space-y-2">
            <p className="font-medium text-gray-700">
              {state === 'listening' ? 'I\'m listening...' : 'Start speaking to interact with JEX'}
            </p>
            <p className="text-sm">
              Try saying: "Hello JEX" • "Tell me a joke" • "What can you do?"
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function AgentDispatcher() {
  const room = useRoomContext();
  const [dispatched, setDispatched] = useState(false);

  useEffect(() => {
    if (!room || dispatched) return;

    console.log('[AgentDispatcher] Room state:', room.state, 'Room name:', room.name);

    const dispatchAgent = () => {
      if (dispatched) return;

      console.log('[AgentDispatcher] Room connected, dispatching agent...');

      // Dispatch agent to this room
      fetch('/api/dispatch-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ roomName: room.name }),
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            console.log('[AgentDispatcher] ✅ Agent dispatched successfully!', data);
            setDispatched(true);
          } else {
            console.error('[AgentDispatcher] ❌ Agent dispatch failed:', data.error);
          }
        })
        .catch(err => {
          console.error('[AgentDispatcher] ❌ Error dispatching agent:', err);
        });
    };

    // If already connected, dispatch immediately
    if (room.state === ConnectionState.Connected) {
      dispatchAgent();
    } else {
      // Otherwise, listen for connection event
      console.log('[AgentDispatcher] Waiting for room to connect, current state:', room.state);

      const handleConnected = () => {
        console.log('[AgentDispatcher] Connection event received!');
        dispatchAgent();
      };

      room.on('connected', handleConnected);

      return () => {
        room.off('connected', handleConnected);
      };
    }
  }, [room, dispatched]);

  return null; // This component doesn't render anything
}
