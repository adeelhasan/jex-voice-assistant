# JEX - Personal Voice Agent
## Hackathon Project Plan

> **Vision**: A Jarvis/Alexa-inspired personal voice agent with visual artifacts, powered by LiveKit for real-time voice and n8n for workflow orchestration.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                              │
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │     Voice UX     │    │   HTML Cards     │                       │
│  │  (LiveKit Room)  │    │ (Artifact Panel) │                       │
│  └────────┬─────────┘    └────────┬─────────┘                       │
│           │                       │                                  │
└───────────┼───────────────────────┼──────────────────────────────────┘
            │                       │
            ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MIDDLEWARE                                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              LiveKit Agent (Python)                           │   │
│  │  • Voice Pipeline (VAD + STT + LLM + TTS)                    │   │
│  │  • Intent Classification                                      │   │
│  │  • Tool Calling (→ n8n workflows)                            │   │
│  │  • Artifact Rendering (→ WebSocket to frontend)              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│  ┌──────────────────────────┴───────────────────────────────────┐   │
│  │              Personal Data Store / Cache                      │   │
│  │  • User preferences                                           │   │
│  │  • Conversation context                                       │   │
│  │  • Workflow registry (intent → workflow mapping)              │   │
│  │  • Notification queue                                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL EXECUTION                              │
│  ┌────────────────────┐    ┌────────────────────┐                   │
│  │   n8n Workflows    │◄──►│  Credential Store  │                   │
│  │   (n8n Cloud)      │    │   (n8n Cloud)      │                   │
│  └─────────┬──────────┘    └────────────────────┘                   │
│            │                                                         │
│            ▼                                                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    3rd Party Services                          │ │
│  │  Gmail • Google Photos • Calendar • Weather • Transit • etc.   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Hosting Strategy (Hackathon)

| Component | Hosting | Notes |
|-----------|---------|-------|
| LiveKit Agent | LiveKit Cloud | Free tier, managed infrastructure |
| n8n Workflows | n8n Cloud | Free trial, focus on building not hosting |
| Web Frontend | Local (localhost:3000) | Next.js dev server |
| Python Agent | Local | LiveKit console mode for dev |

**Future optimization**: Co-locate all services on same box for latency reduction.

---

## LLM Configuration Strategy

> **Design Principle**: The LLM powering JEX should be swappable via configuration, not hardcoded.

**Why this matters**:
- Try different models (GPT-4o, Claude, Gemini) to compare quality/latency
- Future: Run a local LLM (Ollama, llama.cpp) for full privacy
- Cost optimization by choosing the right model for the task

**Implementation Approach**:

```python
# agent/config.py
from enum import Enum
from dataclasses import dataclass

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"  # Local LLM

@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: str | None = None  # None for local models
    base_url: str | None = None  # For Ollama or custom endpoints

def get_llm_from_config(config: LLMConfig):
    """Factory function to create LLM instance based on config"""
    match config.provider:
        case LLMProvider.OPENAI:
            from livekit.plugins import openai
            return openai.LLM(model=config.model)
        case LLMProvider.ANTHROPIC:
            from livekit.plugins import anthropic
            return anthropic.LLM(model=config.model)
        case LLMProvider.GOOGLE:
            from livekit.plugins import google
            return google.LLM(model=config.model)
        case LLMProvider.OLLAMA:
            from livekit.plugins import ollama
            return ollama.LLM(model=config.model, base_url=config.base_url)
```

**Environment-based selection**:
```bash
# .env
LLM_PROVIDER=openai          # openai | anthropic | google | ollama
LLM_MODEL=gpt-4o-mini        # Model name for the provider
OLLAMA_BASE_URL=http://localhost:11434  # Only needed for local
```

**LiveKit Agents supports these LLM plugins**:
- `livekit-plugins-openai` - GPT-4o, GPT-4o-mini
- `livekit-plugins-anthropic` - Claude 3.5 Sonnet, Claude 3 Haiku
- `livekit-plugins-google` - Gemini Pro, Gemini Flash
- `livekit-plugins-ollama` - Any Ollama model (Llama, Mistral, etc.)

**For hackathon**: Start with OpenAI (gpt-4o-mini for speed/cost), but structure the code so swapping is a one-line config change.

---

## Voice Pipeline Configuration

> **Same principle applies to STT and TTS** - all components should be swappable via config.

**Environment-based selection**:
```bash
# .env - Full voice pipeline config
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

STT_PROVIDER=deepgram        # deepgram | openai | google | assemblyai
STT_MODEL=nova-2

TTS_PROVIDER=openai          # openai | elevenlabs | cartesia | google
TTS_VOICE=alloy              # Provider-specific voice ID
ELEVENLABS_VOICE_ID=...      # If using ElevenLabs
```

**LiveKit Agents TTS plugins**:
- `livekit-plugins-openai` - alloy, echo, fable, onyx, nova, shimmer
- `livekit-plugins-elevenlabs` - High quality, many voices, slightly higher latency
- `livekit-plugins-cartesia` - Fast, good quality
- `livekit-plugins-google` - Google Cloud TTS

**LiveKit Agents STT plugins**:
- `livekit-plugins-deepgram` - Fast, accurate, good free tier
- `livekit-plugins-openai` - Whisper
- `livekit-plugins-google` - Google Speech-to-Text
- `livekit-plugins-assemblyai` - AssemblyAI

**For hackathon**: Deepgram STT (fast, free tier) + OpenAI TTS (simple). ElevenLabs as upgrade path for better voice quality.

---

## Personal Data Store

> **Purpose**: Cache data, hold notification queues, store user preferences. Lives alongside the middleware.

**Options** (any works, pick based on what's easy to run locally):

| Option | Pros | Best For |
|--------|------|----------|
| SQLite | Zero config, file-based | Simplest start |
| Redis | Fast, pub/sub for notifications | If already using Redis |
| PostgreSQL | Full SQL, scales well | Production path |

**What it stores**:
- **Notification queue**: Pending alerts from scheduled workflows
- **User preferences**: Location, default accounts, voice settings
- **Conversation cache**: Recent context for continuity
- **Workflow registry**: Dynamic intent → webhook mappings

**For hackathon**: SQLite is fine. Single file, no server needed, Python has built-in support.

```python
# Simple schema
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY,
    type TEXT,
    content TEXT,
    artifact_json TEXT,
    created_at TIMESTAMP,
    delivered BOOLEAN DEFAULT FALSE
);

CREATE TABLE preferences (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

---

## Future Workflow Ideas

> **After the base structure is up**, these are natural extensions:

| Workflow | Data Source | Value |
|----------|-------------|-------|
| YouTube Updates | YouTube Data API | "What's new from channels I follow?" |
| Finance Overview | Plaid API | "How's my spending this month?" |
| News Briefing | RSS / News API | "What's happening today?" |
| Smart Home | Home Assistant | "Turn off the lights" |
| Music Control | Spotify API | "Play my focus playlist" |
| Reminders | Local DB | "Remind me to call mom at 5" |

**YouTube specifically**: Could summarize new videos from subscribed channels, or find videos on a topic. Good use of n8n's YouTube node + AI summarization.

**Plaid**: More involved setup (requires Plaid account, Link flow) but very powerful for personal finance awareness.

---

## Phase 1: Foundation
**Goal**: Basic voice agent with echo/conversation capability

### 1.1 LiveKit Agent Setup
**Duration**: ~2 hours

**Deliverables**:
- Working Python voice agent using LiveKit Agents SDK
- Connected to LiveKit Cloud project
- Basic conversation capability with OpenAI

**Technical Specs for Claude Code**:

```python
# File: agent/main.py
# Dependencies: livekit-agents[openai,silero,deepgram]~=1.0

from livekit.agents import (
    Agent,
    AgentSession,
    RoomInputOptions,
    RunningJobInfo,
    WorkerOptions,
    cli,
)
from livekit.agents.llm import function_tool
from livekit.plugins import deepgram, openai, silero

class JexAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are JEX, a personal voice assistant inspired by Jarvis.
            You help the user with personal tasks, information retrieval,
            and home automation. Be conversational, helpful, and proactive.
            When you perform actions, briefly confirm what you did.
            """,
        )
    
    async def on_enter(self):
        # Greet user when session starts
        self.session.generate_reply(
            instructions="Greet the user warmly and ask how you can help today."
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

**Environment Variables**:
```bash
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENAI_API_KEY=your-openai-key
DEEPGRAM_API_KEY=your-deepgram-key
```

**Verification**:
```bash
# Run in console mode for local testing
lk agent start --console
```

---

### 1.2 Web Frontend Setup
**Duration**: ~1.5 hours

**Deliverables**:
- Next.js app with LiveKit React components
- Voice connection to agent
- Basic UI with conversation area + artifact panel
- Mute button (always-listening with user control)

**Technical Specs for Claude Code**:

```
webapp/
├── package.json
├── .env.local
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── api/
│       └── token/route.ts    # Generate LiveKit tokens
├── components/
│   ├── VoiceAgent.tsx        # LiveKit room connection
│   ├── ArtifactPanel.tsx     # Display cards/content
│   └── TranscriptView.tsx    # Show conversation
└── lib/
    └── livekit.ts            # LiveKit client utils
```

```typescript
// File: app/page.tsx
import { VoiceAgent } from '@/components/VoiceAgent';
import { ArtifactPanel } from '@/components/ArtifactPanel';

export default function Home() {
  return (
    <div className="flex h-screen">
      {/* Main voice interaction area */}
      <div className="flex-1 flex flex-col">
        <VoiceAgent />
      </div>
      
      {/* Artifact panel - like Alexa Show screen */}
      <div className="w-96 border-l bg-gray-50">
        <ArtifactPanel />
      </div>
    </div>
  );
}
```

```typescript
// File: components/VoiceAgent.tsx
'use client';
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
  BarVisualizer,
} from '@livekit/components-react';
import { useEffect, useState } from 'react';

export function VoiceAgent() {
  const [token, setToken] = useState<string>('');
  
  useEffect(() => {
    fetch('/api/token')
      .then(res => res.json())
      .then(data => setToken(data.token));
  }, []);
  
  if (!token) return <div>Connecting...</div>;
  
  return (
    <LiveKitRoom
      token={token}
      serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
      connect={true}
    >
      <AgentInterface />
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

function AgentInterface() {
  const { state, audioTrack } = useVoiceAssistant();
  
  return (
    <div className="flex-1 flex flex-col items-center justify-center">
      <div className="text-2xl mb-4">
        {state === 'listening' ? '🎤 Listening...' : 
         state === 'speaking' ? '🔊 Speaking...' : 
         '💤 Idle'}
      </div>
      <BarVisualizer
        state={state}
        trackRef={audioTrack}
        barCount={5}
        className="w-64 h-16"
      />
    </div>
  );
}
```

```typescript
// File: app/api/token/route.ts
import { AccessToken } from 'livekit-server-sdk';
import { NextResponse } from 'next/server';

export async function GET() {
  const roomName = 'jex-room';
  const participantName = `user-${Date.now()}`;
  
  const at = new AccessToken(
    process.env.LIVEKIT_API_KEY!,
    process.env.LIVEKIT_API_SECRET!,
    { identity: participantName }
  );
  
  at.addGrant({
    roomJoin: true,
    room: roomName,
    canPublish: true,
    canSubscribe: true,
  });
  
  return NextResponse.json({ token: await at.toJwt() });
}
```

**Dependencies (package.json)**:
```json
{
  "dependencies": {
    "@livekit/components-react": "^2.0.0",
    "livekit-client": "^2.0.0",
    "livekit-server-sdk": "^2.0.0",
    "next": "^14.0.0",
    "react": "^18.0.0"
  }
}
```

---

## Phase 2: n8n Integration
**Goal**: Connect voice agent to n8n workflows for action execution

### 2.1 n8n Workflow Setup
**Duration**: ~2 hours

**Deliverables**:
- n8n Cloud account configured
- First workflow: "Read Email" (triggered via webhook)
- Workflow returns structured JSON for agent

**n8n Workflow Specs**:

**Workflow: Read Latest Emails**
```
Trigger: Webhook (POST /webhook/read-emails)
  ↓
Gmail Node: Get messages (last 5, unread)
  ↓
Code Node: Format response
  ↓
Respond to Webhook: Return JSON
```

**Expected Input**:
```json
{
  "action": "read_emails",
  "params": {
    "count": 5,
    "filter": "unread"
  }
}
```

**Expected Output**:
```json
{
  "success": true,
  "speech": "You have 3 unread emails. The first is from John about the project update...",
  "artifact": {
    "type": "email_list",
    "data": [
      {
        "id": "msg123",
        "from": "john@example.com",
        "subject": "Project Update",
        "snippet": "Here's the latest on...",
        "date": "2025-01-15T10:30:00Z"
      }
    ]
  }
}
```

---

### 2.2 Agent Tool Integration
**Duration**: ~2 hours

**Deliverables**:
- Function tools in LiveKit agent that call n8n webhooks
- Intent → workflow mapping
- Artifact data sent to frontend

**Technical Specs for Claude Code**:

```python
# File: agent/tools.py
import httpx
from livekit.agents.llm import function_tool

N8N_BASE_URL = "https://your-instance.app.n8n.cloud/webhook"

class N8NWorkflowTool:
    """Base class for n8n workflow tools"""
    
    def __init__(self, session):
        self.session = session
        self.http = httpx.AsyncClient(timeout=30.0)
    
    async def call_workflow(self, endpoint: str, payload: dict) -> dict:
        """Call an n8n webhook and return the response"""
        response = await self.http.post(
            f"{N8N_BASE_URL}/{endpoint}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        return response.json()
    
    async def send_artifact(self, artifact_data: dict):
        """Send artifact to frontend via data channel"""
        await self.session.room.local_participant.publish_data(
            payload=json.dumps({
                "type": "artifact",
                "data": artifact_data
            }).encode(),
            reliable=True
        )

# Define tools for the agent
@function_tool()
async def read_emails(
    count: int = 5,
    filter: str = "unread"
) -> str:
    """
    Read the user's recent emails.
    
    Args:
        count: Number of emails to retrieve (default 5)
        filter: Filter type - "unread", "all", or "important"
    
    Returns:
        Summary of emails for the agent to speak
    """
    tool = N8NWorkflowTool.get_current()
    result = await tool.call_workflow("read-emails", {
        "action": "read_emails",
        "params": {"count": count, "filter": filter}
    })
    
    # Send artifact to frontend
    if result.get("artifact"):
        await tool.send_artifact(result["artifact"])
    
    return result.get("speech", "I couldn't retrieve your emails.")


@function_tool()
async def check_calendar(
    date: str = "today"
) -> str:
    """
    Check the user's calendar for upcoming events.
    
    Args:
        date: The date to check - "today", "tomorrow", or a specific date
    
    Returns:
        Summary of calendar events
    """
    tool = N8NWorkflowTool.get_current()
    result = await tool.call_workflow("check-calendar", {
        "action": "check_calendar",
        "params": {"date": date}
    })
    
    if result.get("artifact"):
        await tool.send_artifact(result["artifact"])
    
    return result.get("speech", "I couldn't check your calendar.")


@function_tool()
async def get_weather(
    location: str = "current"
) -> str:
    """
    Get the current weather and forecast.
    
    Args:
        location: Location for weather - "current" uses user's location
    
    Returns:
        Weather summary
    """
    tool = N8NWorkflowTool.get_current()
    result = await tool.call_workflow("weather", {
        "action": "get_weather",
        "params": {"location": location}
    })
    
    if result.get("artifact"):
        await tool.send_artifact(result["artifact"])
    
    return result.get("speech", "I couldn't get the weather information.")
```

```python
# File: agent/main.py (updated)
from livekit.agents import Agent, AgentSession
from .tools import read_emails, check_calendar, get_weather

class JexAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are JEX, a personal voice assistant. You have access to:
            - Email: read and summarize emails
            - Calendar: check upcoming events
            - Weather: get current weather
            
            When the user asks about these topics, use the appropriate tool.
            After using a tool, summarize the results conversationally.
            Visual information will automatically appear on their screen.
            """,
            tools=[read_emails, check_calendar, get_weather],
        )
```

---

### 2.3 Artifact Panel Implementation
**Duration**: ~1.5 hours

**Deliverables**:
- Frontend receives artifact data via LiveKit data channel
- Renders different card types (email list, calendar, weather, photos)

**Technical Specs for Claude Code**:

```typescript
// File: components/ArtifactPanel.tsx
'use client';
import { useDataChannel } from '@livekit/components-react';
import { useState, useEffect } from 'react';

interface Artifact {
  type: string;
  data: any;
}

export function ArtifactPanel() {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  
  // Listen for data from agent
  useDataChannel((msg) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === 'artifact') {
        setArtifact(data.data);
      }
    } catch (e) {
      console.error('Failed to parse artifact data', e);
    }
  });
  
  if (!artifact) {
    return (
      <div className="p-4 text-gray-500 text-center">
        <p>Artifacts will appear here</p>
        <p className="text-sm mt-2">Try asking about emails, calendar, or weather</p>
      </div>
    );
  }
  
  return (
    <div className="p-4">
      <ArtifactRenderer artifact={artifact} />
    </div>
  );
}

function ArtifactRenderer({ artifact }: { artifact: Artifact }) {
  switch (artifact.type) {
    case 'email_list':
      return <EmailListCard emails={artifact.data} />;
    case 'calendar':
      return <CalendarCard events={artifact.data} />;
    case 'weather':
      return <WeatherCard weather={artifact.data} />;
    case 'photos':
      return <PhotoGrid photos={artifact.data} />;
    default:
      return <GenericCard data={artifact.data} />;
  }
}

function EmailListCard({ emails }: { emails: any[] }) {
  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-lg">📧 Emails</h3>
      {emails.map((email, i) => (
        <div key={i} className="bg-white p-3 rounded-lg shadow-sm">
          <div className="font-medium">{email.subject}</div>
          <div className="text-sm text-gray-600">{email.from}</div>
          <div className="text-sm text-gray-500 mt-1">{email.snippet}</div>
        </div>
      ))}
    </div>
  );
}

function CalendarCard({ events }: { events: any[] }) {
  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-lg">📅 Calendar</h3>
      {events.map((event, i) => (
        <div key={i} className="bg-white p-3 rounded-lg shadow-sm">
          <div className="font-medium">{event.title}</div>
          <div className="text-sm text-gray-600">
            {new Date(event.start).toLocaleTimeString()} - 
            {new Date(event.end).toLocaleTimeString()}
          </div>
          {event.location && (
            <div className="text-sm text-gray-500">📍 {event.location}</div>
          )}
        </div>
      ))}
    </div>
  );
}

function WeatherCard({ weather }: { weather: any }) {
  return (
    <div className="bg-gradient-to-br from-blue-400 to-blue-600 text-white p-6 rounded-lg">
      <div className="text-4xl font-bold">{weather.temperature}°</div>
      <div className="text-xl">{weather.condition}</div>
      <div className="text-sm mt-2">{weather.location}</div>
      {weather.forecast && (
        <div className="mt-4 flex gap-2">
          {weather.forecast.map((day: any, i: number) => (
            <div key={i} className="text-center">
              <div className="text-xs">{day.day}</div>
              <div className="font-medium">{day.high}°</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PhotoGrid({ photos }: { photos: any[] }) {
  return (
    <div>
      <h3 className="font-semibold text-lg mb-3">📷 Photos</h3>
      <div className="grid grid-cols-2 gap-2">
        {photos.map((photo, i) => (
          <img
            key={i}
            src={photo.url}
            alt={photo.description || ''}
            className="rounded-lg object-cover aspect-square"
          />
        ))}
      </div>
    </div>
  );
}

function GenericCard({ data }: { data: any }) {
  return (
    <div className="bg-white p-4 rounded-lg shadow-sm">
      <pre className="text-sm overflow-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
```

---

## Phase 3: Expanded Workflows
**Goal**: Build out key personal assistant capabilities using n8n's text-to-workflow

### 3.1 Core Workflows to Build
**Duration**: ~3 hours

| Workflow | Trigger | Description | Artifact Type |
|----------|---------|-------------|---------------|
| Read Emails | Webhook | Fetch Gmail messages | email_list |
| Check Calendar | Webhook | Get Google Calendar events | calendar |
| Get Weather | Webhook | OpenWeatherMap API | weather |
| Show Photos | Webhook | Google Photos by date/album | photos |
| Next Train | Webhook | Transit API (local) | transit |
| News Brief | Webhook | RSS feeds summary | news_list |

**n8n Text-to-Workflow Prompts** (for hackathon demo):

```
Workflow: Read Emails
"Create a workflow that:
1. Receives a webhook POST with count and filter parameters
2. Uses Gmail node to fetch recent messages based on those parameters
3. Extracts subject, from, snippet, and date from each email
4. Returns JSON with a speech summary and artifact data for display"

Workflow: Check Calendar
"Create a workflow that:
1. Receives a webhook POST with a date parameter
2. Uses Google Calendar node to get events for that date
3. Formats events with title, time, and location
4. Returns speech summary and calendar artifact"

Workflow: Show Photos
"Create a workflow that:
1. Receives a webhook POST with date or album name
2. Uses Google Photos API to search for matching photos
3. Returns URLs and metadata for up to 6 photos
4. Includes speech description of what was found"
```

---

### 3.2 Intent Registry
**Duration**: ~1 hour

**Deliverables**:
- JSON config mapping intents to workflows
- Dynamic tool generation from registry

```python
# File: agent/intent_registry.py

INTENT_REGISTRY = {
    "read_emails": {
        "workflow_endpoint": "read-emails",
        "description": "Read and summarize recent emails",
        "parameters": {
            "count": {"type": "int", "default": 5, "description": "Number of emails"},
            "filter": {"type": "str", "default": "unread", "options": ["unread", "all", "important"]}
        },
        "examples": [
            "check my email",
            "do I have any new messages",
            "read my inbox"
        ]
    },
    "check_calendar": {
        "workflow_endpoint": "check-calendar",
        "description": "Check upcoming calendar events",
        "parameters": {
            "date": {"type": "str", "default": "today", "description": "Date to check"}
        },
        "examples": [
            "what's on my calendar",
            "do I have any meetings today",
            "what's my schedule for tomorrow"
        ]
    },
    "show_photos": {
        "workflow_endpoint": "show-photos",
        "description": "Display photos from Google Photos",
        "parameters": {
            "query": {"type": "str", "default": "", "description": "Search query or date"},
            "album": {"type": "str", "default": "", "description": "Album name"}
        },
        "examples": [
            "show family pics",
            "photos from October 12",
            "pictures from vacation album"
        ]
    },
    "get_weather": {
        "workflow_endpoint": "weather",
        "description": "Get current weather and forecast",
        "parameters": {
            "location": {"type": "str", "default": "current", "description": "Location"}
        },
        "examples": [
            "what's the weather",
            "will it rain today",
            "forecast for tomorrow"
        ]
    },
    "next_train": {
        "workflow_endpoint": "transit",
        "description": "Get next train/transit times",
        "parameters": {
            "destination": {"type": "str", "default": "", "description": "Where to"},
            "line": {"type": "str", "default": "", "description": "Train line"}
        },
        "examples": [
            "when's the next train",
            "how do I get to manhattan",
            "NJ transit schedule"
        ]
    }
}

def generate_tools_from_registry():
    """Dynamically generate function tools from the registry"""
    tools = []
    for intent_name, config in INTENT_REGISTRY.items():
        tool = create_workflow_tool(intent_name, config)
        tools.append(tool)
    return tools
```

---

## Phase 4: Proactive Notifications
**Goal**: Scheduled workflows that surface attention-worthy items

### 4.1 Notification System
**Duration**: ~2 hours

**Deliverables**:
- n8n scheduled workflows (cron triggers)
- Notification queue in agent
- Morning briefing capability

**n8n Scheduled Workflows**:

```
Workflow: Morning Briefing (Schedule: 7:00 AM daily)
Trigger: Schedule
  ↓
Parallel branches:
  - Gmail: Count unread
  - Calendar: Today's events
  - Weather: Current conditions
  ↓
Merge: Combine results
  ↓
HTTP Request: POST to notification endpoint
```

```
Workflow: Calendar Reminder (Schedule: Every 15 minutes)
Trigger: Schedule
  ↓
Calendar: Get events starting in next 15 minutes
  ↓
IF: Has upcoming events
  ↓
HTTP Request: POST to notification endpoint
```

**Agent Notification Handler**:

```python
# File: agent/notifications.py
from datetime import datetime
from typing import Optional
import asyncio

class NotificationManager:
    def __init__(self, session):
        self.session = session
        self.queue: list[dict] = []
        self.last_check = datetime.now()
    
    async def add_notification(self, notification: dict):
        """Add a notification to the queue"""
        self.queue.append({
            **notification,
            "timestamp": datetime.now().isoformat(),
            "delivered": False
        })
    
    async def check_pending(self) -> Optional[dict]:
        """Get the next undelivered notification"""
        for notif in self.queue:
            if not notif["delivered"]:
                notif["delivered"] = True
                return notif
        return None
    
    async def deliver_if_appropriate(self):
        """Deliver notification if agent is idle and user present"""
        notif = await self.check_pending()
        if notif and self.session.state == "idle":
            # Generate proactive message
            self.session.generate_reply(
                instructions=f"""
                You have a notification to share with the user.
                Type: {notif['type']}
                Content: {notif['content']}
                
                Briefly and naturally inform the user about this.
                """
            )
            # Send artifact if present
            if notif.get("artifact"):
                await self.send_artifact(notif["artifact"])
```

---

## Phase 5: Stretch Goals

### 5.1 Dynamic Workflow Creation (Text-to-Workflow)
**Duration**: ~3 hours (if time permits)

**Goal**: User can verbally request a new capability, and JEX creates a workflow

**Flow**:
1. User: "JEX, I want you to be able to check my stock portfolio"
2. JEX: "I can create that capability. What brokerage do you use?"
3. User: "Robinhood"
4. JEX uses n8n's API to create a workflow using text-to-workflow
5. JEX: "I've added that capability. Try asking about your portfolio now."

```python
# File: agent/workflow_builder.py
import httpx

N8N_API_URL = "https://your-instance.app.n8n.cloud/api/v1"
N8N_API_KEY = "your-api-key"

async def create_workflow_from_description(description: str) -> dict:
    """
    Use n8n's AI workflow builder API to create a new workflow
    from a natural language description.
    """
    async with httpx.AsyncClient() as client:
        # Note: This assumes n8n exposes an API for workflow builder
        # The actual implementation may vary based on n8n's API
        response = await client.post(
            f"{N8N_API_URL}/workflows/generate",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            json={"prompt": description}
        )
        return response.json()

@function_tool()
async def create_new_capability(
    description: str,
    name: str
) -> str:
    """
    Create a new capability/workflow for JEX based on user description.
    
    Args:
        description: What the user wants the capability to do
        name: A short name for this capability
    
    Returns:
        Confirmation of capability creation
    """
    prompt = f"""
    Create an n8n workflow that:
    - Is triggered by a webhook POST
    - {description}
    - Returns JSON with 'speech' (text for voice) and 'artifact' (display data)
    """
    
    result = await create_workflow_from_description(prompt)
    
    if result.get("success"):
        # Register the new intent
        INTENT_REGISTRY[name.lower().replace(" ", "_")] = {
            "workflow_endpoint": result["webhook_path"],
            "description": description,
            "parameters": result.get("parameters", {})
        }
        return f"I've created the '{name}' capability. You can now ask me about it."
    else:
        return "I wasn't able to create that capability. Could you try describing it differently?"
```

---

### 5.2 n8n Chat Hub Integration
**Duration**: ~2 hours (if time permits)

**Goal**: Use n8n's Chat Hub for certain complex queries

```python
# For queries that are better handled by n8n's AI agent directly
@function_tool()
async def ask_n8n_agent(query: str) -> str:
    """
    Forward complex queries to n8n's Chat Hub agent for processing.
    Use this for queries that might need multiple workflow steps or
    complex reasoning about available integrations.
    """
    # n8n Chat Hub API call
    response = await call_n8n_chat(query)
    return response["message"]
```

---

## Project Structure (Final)

```
jex/
├── README.md
├── docker-compose.yml          # For future self-hosting
│
├── agent/                       # LiveKit Python Agent
│   ├── requirements.txt
│   ├── main.py                 # Agent entrypoint
│   ├── tools.py                # n8n workflow tools
│   ├── intent_registry.py      # Intent → workflow mapping
│   ├── notifications.py        # Proactive notification system
│   └── workflow_builder.py     # Dynamic workflow creation
│
├── webapp/                      # Next.js Frontend
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx
│   │   └── api/token/route.ts
│   ├── components/
│   │   ├── VoiceAgent.tsx
│   │   ├── ArtifactPanel.tsx
│   │   └── TranscriptView.tsx
│   └── lib/
│       └── livekit.ts
│
├── workflows/                   # n8n workflow exports (JSON)
│   ├── read-emails.json
│   ├── check-calendar.json
│   ├── weather.json
│   ├── show-photos.json
│   └── morning-briefing.json
│
└── docs/
    ├── SETUP.md                # Setup instructions
    └── DEMO_SCRIPT.md          # Hackathon demo script
```

---

## Demo Script (Hackathon)

### Introduction (30 sec)
"JEX is a personal voice agent inspired by Jarvis and Alexa, but built with open tools - LiveKit for voice and n8n for the brain."

### Demo Flow (3-4 min)

1. **Wake and Greet**
   - Open the web app
   - JEX greets the user

2. **Check Emails** 
   - "JEX, do I have any new emails?"
   - Voice response + email cards appear

3. **Calendar Check**
   - "What's on my calendar today?"
   - Voice response + calendar cards

4. **Show Photos**
   - "Show me family photos from October 12"
   - Voice describes, photo grid appears

5. **Weather**
   - "What's the weather like?"
   - Voice + weather card

6. **Stretch: Create New Capability**
   - "JEX, I want you to be able to tell me the next train to Manhattan"
   - Show workflow being created in n8n
   - "When's the next train?"

### Closing (30 sec)
"Built in a hackathon using LiveKit Cloud, n8n Cloud, and text-to-workflow. The future: local hosting for privacy, more integrations, smarter proactive notifications."

---

## Implementation Checklist

### Phase 1: Foundation ✓
- [ ] Create LiveKit Cloud project
- [ ] Set up Python agent with voice pipeline
- [ ] Create Next.js frontend
- [ ] Verify voice connection works

### Phase 2: n8n Integration
- [ ] Set up n8n Cloud account
- [ ] Create "Read Emails" webhook workflow
- [ ] Add function tools to agent
- [ ] Implement artifact data channel
- [ ] Build artifact panel UI

### Phase 3: Expanded Workflows
- [ ] Create Calendar workflow
- [ ] Create Weather workflow
- [ ] Create Photos workflow
- [ ] Create Transit workflow
- [ ] Build intent registry

### Phase 4: Proactive Notifications
- [ ] Create Morning Briefing scheduled workflow
- [ ] Create Calendar Reminder workflow
- [ ] Implement notification manager
- [ ] Add notification delivery logic

### Phase 5: Stretch Goals
- [ ] Dynamic workflow creation
- [ ] n8n Chat Hub integration
- [ ] Local hosting setup

---

## API Keys Required

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| LiveKit Cloud | Voice infrastructure | Yes |
| n8n Cloud | Workflow automation | Trial |
| OpenAI | LLM + TTS | Pay as you go |
| Deepgram | Speech-to-text | Free tier |
| Google Cloud | Gmail, Calendar, Photos APIs | Free tier |
| OpenWeatherMap | Weather data | Free tier |

---

## Time Estimates

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1 | ~3.5 hours | 3.5 hours |
| Phase 2 | ~5.5 hours | 9 hours |
| Phase 3 | ~4 hours | 13 hours |
| Phase 4 | ~2 hours | 15 hours |
| Phase 5 | ~5 hours | 20 hours |

**Minimum Viable Demo**: Phases 1-2 (~9 hours)
**Full Hackathon Demo**: Phases 1-4 (~15 hours)
**With Stretch Goals**: All phases (~20 hours)
