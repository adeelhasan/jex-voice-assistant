# JEX Quick-Start Implementation Guide
## For Claude Code Implementation

This is a condensed guide for immediate implementation. See `jex_project_plan.md` for full details.

---

## Step 1: Initialize Project Structure

```bash
mkdir -p jex/{agent,webapp,workflows,docs}
cd jex
```

## Step 2: LiveKit Python Agent

### 2.1 Create agent files

**File: `agent/requirements.txt`**
```
livekit-agents[openai,silero,deepgram]~=1.0
httpx>=0.25.0
python-dotenv>=1.0.0
```

**File: `agent/.env.example`**
```
# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# LLM Config (openai | anthropic | google | ollama)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your-openai-key

# STT Config (deepgram | openai | google)
STT_PROVIDER=deepgram
DEEPGRAM_API_KEY=your-deepgram-key

# TTS Config (openai | elevenlabs | cartesia)
TTS_PROVIDER=openai
TTS_VOICE=alloy
ELEVENLABS_API_KEY=your-key-if-using

# n8n
N8N_WEBHOOK_BASE=https://your-instance.app.n8n.cloud/webhook
```

**File: `agent/main.py`**
```python
import json
import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    RunningJobInfo,
    WorkerOptions,
    cli,
)
from livekit.agents.llm import function_tool
from livekit.plugins import deepgram, openai, silero

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Import tools
from tools import read_emails, check_calendar, get_weather

class JexAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are JEX, a personal voice assistant inspired by Jarvis from Iron Man.
            
            You help the user with:
            - Checking and summarizing emails
            - Managing their calendar
            - Getting weather information
            - Showing photos from their library
            
            Be conversational, helpful, and efficient. When you use a tool:
            1. Acknowledge what you're doing
            2. Use the tool
            3. Summarize the results naturally
            
            Visual information will automatically appear on the user's screen,
            so you don't need to read every detail - just give highlights.
            """,
            tools=[read_emails, check_calendar, get_weather],
        )
    
    async def on_enter(self):
        self.session.generate_reply(
            instructions="Greet the user warmly. Introduce yourself as JEX, their personal assistant. Ask how you can help."
        )


async def entrypoint(ctx: RunningJobInfo):
    await ctx.connect()
    
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-2"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="alloy"),
    )
    
    await session.start(ctx.room, agent=JexAgent())


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

**File: `agent/tools.py`**
```python
import os
import json
import httpx
from livekit.agents.llm import function_tool
from livekit.agents import AgentSession

N8N_BASE = os.getenv("N8N_WEBHOOK_BASE", "")

async def call_n8n_workflow(endpoint: str, payload: dict) -> dict:
    """Call an n8n webhook workflow"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{N8N_BASE}/{endpoint}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e), "speech": "I had trouble connecting to that service."}


async def send_artifact_to_frontend(session: AgentSession, artifact: dict):
    """Send artifact data to the frontend via LiveKit data channel"""
    if session and session.room:
        await session.room.local_participant.publish_data(
            payload=json.dumps({"type": "artifact", "data": artifact}).encode(),
            reliable=True
        )


@function_tool()
async def read_emails(count: int = 5, filter: str = "unread") -> str:
    """
    Read the user's recent emails from Gmail.
    
    Args:
        count: Number of emails to retrieve (1-20)
        filter: Filter type - "unread", "all", or "important"
    
    Returns:
        Summary of emails for voice response
    """
    result = await call_n8n_workflow("read-emails", {
        "count": min(count, 20),
        "filter": filter
    })
    
    # Get current session to send artifact
    from livekit.agents import AgentSession
    session = AgentSession.get_current()
    if result.get("artifact"):
        await send_artifact_to_frontend(session, result["artifact"])
    
    return result.get("speech", "I couldn't retrieve your emails right now.")


@function_tool()
async def check_calendar(date: str = "today") -> str:
    """
    Check the user's calendar for events.
    
    Args:
        date: Date to check - "today", "tomorrow", or specific date like "January 15"
    
    Returns:
        Summary of calendar events
    """
    result = await call_n8n_workflow("check-calendar", {"date": date})
    
    from livekit.agents import AgentSession
    session = AgentSession.get_current()
    if result.get("artifact"):
        await send_artifact_to_frontend(session, result["artifact"])
    
    return result.get("speech", "I couldn't check your calendar right now.")


@function_tool()
async def get_weather(location: str = "current") -> str:
    """
    Get current weather and forecast.
    
    Args:
        location: Location name, or "current" to use user's location
    
    Returns:
        Weather summary
    """
    result = await call_n8n_workflow("weather", {"location": location})
    
    from livekit.agents import AgentSession
    session = AgentSession.get_current()
    if result.get("artifact"):
        await send_artifact_to_frontend(session, result["artifact"])
    
    return result.get("speech", "I couldn't get weather information right now.")


@function_tool()
async def show_photos(query: str = "", date: str = "") -> str:
    """
    Show photos from Google Photos.
    
    Args:
        query: Search query (e.g., "family", "vacation", "dog")
        date: Specific date or date range (e.g., "October 12", "last week")
    
    Returns:
        Description of photos found
    """
    result = await call_n8n_workflow("show-photos", {
        "query": query,
        "date": date
    })
    
    from livekit.agents import AgentSession
    session = AgentSession.get_current()
    if result.get("artifact"):
        await send_artifact_to_frontend(session, result["artifact"])
    
    return result.get("speech", "I couldn't find any matching photos.")
```

---

## Step 3: Next.js Web Frontend

### 3.1 Initialize project

```bash
cd webapp
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir=false
npm install @livekit/components-react livekit-client livekit-server-sdk
```

**File: `webapp/.env.local`**
```
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
```

**File: `webapp/app/page.tsx`**
```tsx
import { VoiceAgent } from '@/components/VoiceAgent';
import { ArtifactPanel } from '@/components/ArtifactPanel';

export default function Home() {
  return (
    <main className="flex h-screen bg-gray-100">
      {/* Voice interaction area */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-800">JEX</h1>
          <p className="text-sm text-gray-500">Your Personal Voice Assistant</p>
        </header>
        <div className="flex-1">
          <VoiceAgent />
        </div>
      </div>
      
      {/* Artifact panel */}
      <aside className="w-[400px] bg-white border-l shadow-lg">
        <ArtifactPanel />
      </aside>
    </main>
  );
}
```

**File: `webapp/app/api/token/route.ts`**
```typescript
import { AccessToken } from 'livekit-server-sdk';
import { NextResponse } from 'next/server';

export async function GET() {
  const roomName = 'jex-room';
  const participantName = `user-${Date.now()}`;
  
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  
  if (!apiKey || !apiSecret) {
    return NextResponse.json({ error: 'Server configuration error' }, { status: 500 });
  }
  
  const at = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
    ttl: '1h',
  });
  
  at.addGrant({
    roomJoin: true,
    room: roomName,
    canPublish: true,
    canSubscribe: true,
    canPublishData: true,
  });
  
  const token = await at.toJwt();
  return NextResponse.json({ token, roomName });
}
```

**File: `webapp/components/VoiceAgent.tsx`**
```tsx
'use client';

import {
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
  BarVisualizer,
  useDataChannel,
  useLocalParticipant,
} from '@livekit/components-react';
import { useCallback, useEffect, useState } from 'react';

export function VoiceAgent() {
  const [connectionState, setConnectionState] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [token, setToken] = useState<string>('');
  const [error, setError] = useState<string>('');

  const connect = useCallback(async () => {
    setConnectionState('connecting');
    try {
      const res = await fetch('/api/token');
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setToken(data.token);
      setConnectionState('connected');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to connect');
      setConnectionState('disconnected');
    }
  }, []);

  if (connectionState === 'disconnected') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center">
        <button
          onClick={connect}
          className="px-8 py-4 bg-blue-600 text-white rounded-full text-lg font-medium hover:bg-blue-700 transition-colors"
        >
          Connect to JEX
        </button>
        {error && <p className="mt-4 text-red-500">{error}</p>}
      </div>
    );
  }

  if (connectionState === 'connecting') {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-gray-500">Connecting...</div>
      </div>
    );
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
      connect={true}
      onDisconnected={() => setConnectionState('disconnected')}
    >
      <AgentInterface />
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
    disconnected: { icon: '⚫', text: 'Disconnected', color: 'text-gray-400' },
    connecting: { icon: '🟡', text: 'Connecting...', color: 'text-yellow-500' },
    initializing: { icon: '🟡', text: 'Initializing...', color: 'text-yellow-500' },
    listening: { icon: '🎤', text: 'Listening...', color: 'text-green-500' },
    thinking: { icon: '🧠', text: 'Thinking...', color: 'text-purple-500' },
    speaking: { icon: '🔊', text: 'Speaking...', color: 'text-blue-500' },
  };

  const current = stateConfig[state] || stateConfig.disconnected;

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <div className={`text-6xl mb-4 ${current.color}`}>
        {isMuted ? '🔇' : current.icon}
      </div>
      <div className={`text-xl font-medium ${current.color}`}>
        {isMuted ? 'Muted' : current.text}
      </div>
      
      {audioTrack && (
        <div className="mt-8">
          <BarVisualizer
            state={state}
            trackRef={audioTrack}
            barCount={7}
            className="w-72 h-20"
          />
        </div>
      )}
      
      {/* Mute Button */}
      <button
        onClick={toggleMute}
        className={`mt-8 px-6 py-3 rounded-full font-medium transition-colors ${
          isMuted 
            ? 'bg-red-100 text-red-600 hover:bg-red-200' 
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
        }`}
      >
        {isMuted ? '🔇 Unmute' : '🎤 Mute'}
      </button>
      
      <p className="mt-8 text-gray-400 text-center max-w-md">
        {isMuted 
          ? 'Microphone is muted. Click Unmute to continue talking.'
          : 'Start speaking to interact with JEX. Try asking about your emails, calendar, or the weather.'
        }
      </p>
    </div>
  );
}
```

**File: `webapp/components/ArtifactPanel.tsx`**
```tsx
'use client';

import { useDataChannel } from '@livekit/components-react';
import { useState } from 'react';

interface Artifact {
  type: string;
  data: any;
}

export function ArtifactPanel() {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [history, setHistory] = useState<Artifact[]>([]);

  useDataChannel((msg) => {
    try {
      const decoded = new TextDecoder().decode(msg.payload);
      const data = JSON.parse(decoded);
      if (data.type === 'artifact' && data.data) {
        setArtifact(data.data);
        setHistory(prev => [data.data, ...prev].slice(0, 10));
      }
    } catch (e) {
      console.error('Failed to parse artifact:', e);
    }
  });

  return (
    <div className="h-full flex flex-col">
      <header className="px-4 py-3 border-b bg-gray-50">
        <h2 className="font-semibold text-gray-700">Display</h2>
      </header>
      
      <div className="flex-1 overflow-y-auto p-4">
        {artifact ? (
          <ArtifactRenderer artifact={artifact} />
        ) : (
          <EmptyState />
        )}
      </div>
      
      {history.length > 1 && (
        <div className="border-t p-3 bg-gray-50">
          <p className="text-xs text-gray-500 mb-2">Recent</p>
          <div className="flex gap-2 overflow-x-auto">
            {history.slice(1, 5).map((item, i) => (
              <button
                key={i}
                onClick={() => setArtifact(item)}
                className="px-3 py-1 text-xs bg-white border rounded-full hover:bg-gray-100"
              >
                {item.type}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-full flex flex-col items-center justify-center text-gray-400">
      <div className="text-4xl mb-3">📱</div>
      <p className="text-center">
        Content will appear here when JEX retrieves information.
      </p>
      <p className="text-sm mt-2">
        Try: "Check my emails" or "What's the weather?"
      </p>
    </div>
  );
}

function ArtifactRenderer({ artifact }: { artifact: Artifact }) {
  switch (artifact.type) {
    case 'email_list':
      return <EmailList emails={artifact.data} />;
    case 'calendar':
      return <CalendarView events={artifact.data} />;
    case 'weather':
      return <WeatherCard weather={artifact.data} />;
    case 'photos':
      return <PhotoGrid photos={artifact.data} />;
    default:
      return <GenericView data={artifact} />;
  }
}

function EmailList({ emails }: { emails: any[] }) {
  if (!Array.isArray(emails)) return null;
  
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        📧 Emails
      </h3>
      {emails.map((email, i) => (
        <div key={i} className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors">
          <div className="font-medium text-gray-900">{email.subject}</div>
          <div className="text-sm text-gray-600 mt-1">{email.from}</div>
          <div className="text-sm text-gray-500 mt-2 line-clamp-2">{email.snippet}</div>
          <div className="text-xs text-gray-400 mt-2">
            {new Date(email.date).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}

function CalendarView({ events }: { events: any[] }) {
  if (!Array.isArray(events)) return null;
  
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        📅 Calendar
      </h3>
      {events.length === 0 ? (
        <p className="text-gray-500">No events scheduled</p>
      ) : (
        events.map((event, i) => (
          <div key={i} className="bg-gray-50 rounded-lg p-4 border-l-4 border-blue-500">
            <div className="font-medium">{event.title}</div>
            <div className="text-sm text-gray-600 mt-1">
              {formatTime(event.start)} - {formatTime(event.end)}
            </div>
            {event.location && (
              <div className="text-sm text-gray-500 mt-1">📍 {event.location}</div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function WeatherCard({ weather }: { weather: any }) {
  return (
    <div className="bg-gradient-to-br from-blue-400 to-blue-600 rounded-xl p-6 text-white">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-5xl font-light">{weather.temperature}°</div>
          <div className="text-xl mt-1">{weather.condition}</div>
          <div className="text-sm opacity-80 mt-1">{weather.location}</div>
        </div>
        <div className="text-6xl">
          {getWeatherEmoji(weather.condition)}
        </div>
      </div>
      
      {weather.forecast && (
        <div className="mt-6 pt-4 border-t border-white/20">
          <div className="grid grid-cols-4 gap-2 text-center">
            {weather.forecast.slice(0, 4).map((day: any, i: number) => (
              <div key={i}>
                <div className="text-xs opacity-70">{day.day}</div>
                <div className="text-lg">{getWeatherEmoji(day.condition)}</div>
                <div className="text-sm font-medium">{day.high}°</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PhotoGrid({ photos }: { photos: any[] }) {
  if (!Array.isArray(photos)) return null;
  
  return (
    <div>
      <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
        📷 Photos
      </h3>
      <div className="grid grid-cols-2 gap-2">
        {photos.map((photo, i) => (
          <div key={i} className="aspect-square rounded-lg overflow-hidden bg-gray-100">
            <img
              src={photo.url}
              alt={photo.description || 'Photo'}
              className="w-full h-full object-cover hover:scale-105 transition-transform"
            />
          </div>
        ))}
      </div>
      {photos[0]?.date && (
        <p className="text-sm text-gray-500 mt-3">
          From {new Date(photos[0].date).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}

function GenericView({ data }: { data: any }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <pre className="text-xs overflow-auto whitespace-pre-wrap">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

// Helpers
function formatTime(dateStr: string) {
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function getWeatherEmoji(condition: string) {
  const lower = condition?.toLowerCase() || '';
  if (lower.includes('sun') || lower.includes('clear')) return '☀️';
  if (lower.includes('cloud')) return '☁️';
  if (lower.includes('rain')) return '🌧️';
  if (lower.includes('snow')) return '❄️';
  if (lower.includes('storm') || lower.includes('thunder')) return '⛈️';
  return '🌤️';
}
```

---

## Step 4: n8n Workflow Templates

### Read Emails Workflow

Import this JSON into n8n Cloud:

```json
{
  "name": "JEX - Read Emails",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "read-emails",
        "responseMode": "lastNode"
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [220, 300]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "getAll",
        "limit": "={{ $json.count || 5 }}",
        "filters": {
          "labelIds": ["INBOX"],
          "q": "={{ $json.filter === 'unread' ? 'is:unread' : '' }}"
        }
      },
      "name": "Gmail",
      "type": "n8n-nodes-base.gmail",
      "position": [440, 300]
    },
    {
      "parameters": {
        "jsCode": "const emails = $input.all().map(item => ({\n  id: item.json.id,\n  from: item.json.from?.emailAddress || 'Unknown',\n  subject: item.json.subject || 'No subject',\n  snippet: item.json.snippet || '',\n  date: item.json.date\n}));\n\nconst count = emails.length;\nlet speech = '';\nif (count === 0) {\n  speech = 'You have no new emails.';\n} else if (count === 1) {\n  speech = `You have 1 email. It's from ${emails[0].from} about \"${emails[0].subject}\".`;\n} else {\n  speech = `You have ${count} emails. The most recent is from ${emails[0].from} about \"${emails[0].subject}\".`;\n}\n\nreturn [{\n  json: {\n    speech,\n    artifact: {\n      type: 'email_list',\n      data: emails\n    }\n  }\n}];"
      },
      "name": "Format Response",
      "type": "n8n-nodes-base.code",
      "position": [660, 300]
    }
  ],
  "connections": {
    "Webhook": { "main": [[{ "node": "Gmail", "type": "main", "index": 0 }]] },
    "Gmail": { "main": [[{ "node": "Format Response", "type": "main", "index": 0 }]] }
  }
}
```

### Weather Workflow

```json
{
  "name": "JEX - Weather",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "weather",
        "responseMode": "lastNode"
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [220, 300]
    },
    {
      "parameters": {
        "operation": "currentWeather",
        "location": "={{ $json.location === 'current' ? 'Metuchen, NJ' : $json.location }}"
      },
      "name": "OpenWeatherMap",
      "type": "n8n-nodes-base.openWeatherMap",
      "position": [440, 300]
    },
    {
      "parameters": {
        "jsCode": "const w = $input.first().json;\nconst temp = Math.round(w.main.temp);\nconst condition = w.weather[0].main;\nconst location = w.name;\n\nconst speech = `It's currently ${temp} degrees and ${condition.toLowerCase()} in ${location}.`;\n\nreturn [{\n  json: {\n    speech,\n    artifact: {\n      type: 'weather',\n      data: {\n        temperature: temp,\n        condition: condition,\n        location: location,\n        humidity: w.main.humidity,\n        wind: w.wind.speed\n      }\n    }\n  }\n}];"
      },
      "name": "Format Response",
      "type": "n8n-nodes-base.code",
      "position": [660, 300]
    }
  ],
  "connections": {
    "Webhook": { "main": [[{ "node": "OpenWeatherMap", "type": "main", "index": 0 }]] },
    "OpenWeatherMap": { "main": [[{ "node": "Format Response", "type": "main", "index": 0 }]] }
  }
}
```

---

## Running the Project

### Terminal 1: Agent
```bash
cd agent
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py dev  # or: lk agent start --console
```

### Terminal 2: Frontend
```bash
cd webapp
npm install
cp .env.example .env.local
# Edit .env.local with your LiveKit keys
npm run dev
```

### n8n Cloud
1. Go to https://app.n8n.cloud
2. Import the workflow JSONs
3. Activate the workflows
4. Copy the webhook URLs to agent/.env

---

## Test Commands

Once running, try these voice commands:

1. **Greeting**: "Hello JEX"
2. **Email**: "Check my emails" / "Do I have any new messages?"
3. **Weather**: "What's the weather like?" / "Will it rain today?"
4. **Calendar**: "What's on my schedule today?" / "Do I have any meetings?"
5. **Photos**: "Show me family photos" / "Pictures from October"

---

## Common Issues

### Agent not responding
- Check LIVEKIT_URL, API_KEY, API_SECRET are correct
- Verify agent is running: `lk agent list`
- Check browser console for connection errors

### n8n workflows not working
- Verify webhook URLs in agent/.env
- Check n8n workflow is activated
- Test webhook directly with curl/Postman

### No audio in browser
- Check microphone permissions
- Verify browser supports WebRTC
- Try Chrome/Firefox (Safari can have issues)

### Artifacts not displaying
- Check browser console for data channel messages
- Verify n8n returns correct artifact structure
- Check useDataChannel hook is working
