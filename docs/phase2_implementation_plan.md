# JEX Phase 2 Implementation Plan
## n8n Integration + Function Tools + Artifact Panel

---

## Overview

**Goal**: Transform JEX from a conversational AI into a personal assistant that can access real data and perform actions.

**What We're Adding:**
1. **n8n Workflow Integration** - Connect to external services (Gmail, Calendar, Weather, etc.)
2. **Function Tools** - LLM can call Python functions to trigger workflows
3. **Artifact Panel** - Visual display of data on the frontend
4. **Data Channel** - Real-time communication between agent and browser for visual data

---

## Architecture Changes

### Before (Phase 1):
```
Browser ↔ LiveKit ↔ Agent ↔ [OpenAI LLM]
                            (Voice only)
```

### After (Phase 2):
```
Browser ↔ LiveKit ↔ Agent ↔ [OpenAI LLM] ─┐
   ↑                   ↓                   │ Function calling
   │                   ↓                   ↓
   │              [Function Tools] ─→ [n8n Workflows] ─→ [External APIs]
   │                   ↓                   ↓               (Gmail, etc.)
   │              [Artifact Data]          │
   └──────────────────┘                    │
      Data Channel                         │
      (Visual updates)                     └─→ Returns data
```

---

## Implementation Steps

### Step 1: n8n Workflow Setup (External - You'll Do This)

**Platform**: n8n Cloud (https://app.n8n.cloud)

**Workflows to Create:**

#### 1. Read Emails Workflow
- **Trigger**: Webhook (POST `/webhook/read-emails`)
- **Input**: `{ count: number, filter: "unread" | "all" | "important" }`
- **Steps**:
  1. Gmail node: Fetch messages based on filter
  2. Code node: Format response
- **Output**:
```json
{
  "speech": "You have 3 unread emails. The first is from...",
  "artifact": {
    "type": "email_list",
    "data": [
      {
        "id": "msg123",
        "from": "john@example.com",
        "subject": "Project Update",
        "snippet": "Here's the latest...",
        "date": "2025-12-16T10:30:00Z"
      }
    ]
  }
}
```

#### 2. Check Calendar Workflow
- **Trigger**: Webhook (POST `/webhook/check-calendar`)
- **Input**: `{ date: "today" | "tomorrow" | "2025-12-20" }`
- **Steps**:
  1. Google Calendar node: Get events for date
  2. Code node: Format response
- **Output**:
```json
{
  "speech": "You have 2 events today. First is...",
  "artifact": {
    "type": "calendar",
    "data": [
      {
        "title": "Team Meeting",
        "start": "2025-12-16T14:00:00Z",
        "end": "2025-12-16T15:00:00Z",
        "location": "Zoom"
      }
    ]
  }
}
```

#### 3. Get Weather Workflow
- **Trigger**: Webhook (POST `/webhook/weather`)
- **Input**: `{ location: "current" | "New York, NY" }`
- **Steps**:
  1. OpenWeatherMap node: Get current weather
  2. Code node: Format response
- **Output**:
```json
{
  "speech": "It's currently 72 degrees and sunny in...",
  "artifact": {
    "type": "weather",
    "data": {
      "temperature": 72,
      "condition": "Clear",
      "location": "Metuchen, NJ",
      "humidity": 65,
      "forecast": [...]
    }
  }
}
```

**After creating workflows, you'll get webhook URLs like:**
```
https://your-instance.app.n8n.cloud/webhook/read-emails
https://your-instance.app.n8n.cloud/webhook/check-calendar
https://your-instance.app.n8n.cloud/webhook/weather
```

---

### Step 2: Python Agent - Add Function Tools

**File**: `agent/tools.py` (NEW FILE)

```python
"""
Function tools for JEX agent.
These functions are callable by the LLM to perform actions.
"""

import os
import json
import httpx
from typing import Optional
from livekit.agents.llm import function_tool
from livekit.agents import AgentSession

N8N_BASE_URL = os.getenv("N8N_WEBHOOK_BASE", "")


async def call_n8n_workflow(endpoint: str, payload: dict) -> dict:
    """
    Call an n8n webhook workflow and return the response.

    Args:
        endpoint: Workflow endpoint (e.g., "read-emails")
        payload: Data to send to the workflow

    Returns:
        Response from n8n with 'speech' and 'artifact' fields
    """
    url = f"{N8N_BASE_URL}/{endpoint}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {
                "speech": f"I had trouble connecting to that service: {str(e)}",
                "artifact": None
            }
        except Exception as e:
            return {
                "speech": f"An error occurred: {str(e)}",
                "artifact": None
            }


async def send_artifact_to_frontend(session: AgentSession, artifact: dict):
    """
    Send artifact data to the frontend via LiveKit data channel.

    Args:
        session: Current agent session
        artifact: Artifact data to send (type + data)
    """
    if session and session.room:
        message = json.dumps({
            "type": "artifact",
            "data": artifact
        })
        await session.room.local_participant.publish_data(
            payload=message.encode('utf-8'),
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
    from livekit.agents import AgentSession

    # Call n8n workflow
    result = await call_n8n_workflow("read-emails", {
        "count": min(count, 20),
        "filter": filter
    })

    # Get current session and send artifact if available
    try:
        session = AgentSession.get_current()
        if result.get("artifact"):
            await send_artifact_to_frontend(session, result["artifact"])
    except Exception as e:
        print(f"Could not send artifact: {e}")

    return result.get("speech", "I couldn't retrieve your emails right now.")


@function_tool()
async def check_calendar(date: str = "today") -> str:
    """
    Check the user's calendar for events.

    Args:
        date: Date to check - "today", "tomorrow", or specific date like "December 20"

    Returns:
        Summary of calendar events
    """
    from livekit.agents import AgentSession

    result = await call_n8n_workflow("check-calendar", {
        "date": date
    })

    try:
        session = AgentSession.get_current()
        if result.get("artifact"):
            await send_artifact_to_frontend(session, result["artifact"])
    except Exception as e:
        print(f"Could not send artifact: {e}")

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
    from livekit.agents import AgentSession

    result = await call_n8n_workflow("weather", {
        "location": location
    })

    try:
        session = AgentSession.get_current()
        if result.get("artifact"):
            await send_artifact_to_frontend(session, result["artifact"])
    except Exception as e:
        print(f"Could not send artifact: {e}")

    return result.get("speech", "I couldn't get weather information right now.")
```

---

### Step 3: Update Agent to Use Tools

**File**: `agent/main.py` (MODIFY)

**Changes:**

1. Import the tools:
```python
from tools import read_emails, check_calendar, get_weather
```

2. Update `JexAgent` class to include tools:
```python
class JexAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are JEX, a personal voice assistant inspired by Jarvis from Iron Man.

            You are helpful, conversational, and efficient. You speak naturally and concisely,
            as if you're having a real conversation with someone.

            You can now help the user with:
            - Checking and summarizing emails
            - Viewing their calendar and upcoming events
            - Getting weather information
            - Having natural conversations
            - Answering questions
            - Providing information on various topics

            When you use a tool to get information:
            1. Acknowledge what you're doing ("Let me check your emails...")
            2. Call the appropriate tool
            3. Summarize the results naturally in your response

            The user will see visual information appear on their screen, so you don't
            need to read every single detail - just give them the highlights and let
            them view the details on screen.

            Keep your responses conversational and relatively brief since this is a voice interface.
            """,
            tools=[read_emails, check_calendar, get_weather],  # ← NEW
        )

    async def on_enter(self):
        """Called when the agent session starts."""
        logger.info("JEX agent session starting")
        await self.session.generate_reply(
            instructions="Greet the user warmly. Introduce yourself as JEX, their personal voice assistant. Mention that you can now help them check emails, view their calendar, and get weather updates. Ask how you can help them today. Keep it brief and friendly."
        )
```

3. Update `.env.example` to include n8n webhook URL:
```env
# n8n Configuration
N8N_WEBHOOK_BASE=https://your-instance.app.n8n.cloud/webhook
```

---

### Step 4: Frontend - Add Artifact Panel

**File**: `webapp/app/page.tsx` (MODIFY)

Update layout to include artifact panel:

```tsx
import { VoiceAgent } from '@/components/VoiceAgent';
import { ArtifactPanel } from '@/components/ArtifactPanel';

export default function Home() {
  return (
    <main className="flex h-screen bg-gray-100">
      {/* Voice interaction area */}
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b px-6 py-4 shadow-sm">
          <h1 className="text-2xl font-bold text-gray-800">JEX</h1>
          <p className="text-sm text-gray-500">Your Personal Voice Assistant</p>
        </header>
        <div className="flex-1">
          <VoiceAgent />
        </div>
      </div>

      {/* Artifact panel - NEW */}
      <aside className="w-[400px] bg-white border-l shadow-lg">
        <ArtifactPanel />
      </aside>
    </main>
  );
}
```

**File**: `webapp/components/ArtifactPanel.tsx` (NEW FILE)

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

  // Listen for artifact data from the agent
  useDataChannel((msg) => {
    try {
      const decoded = new TextDecoder().decode(msg.payload);
      const data = JSON.parse(decoded);

      if (data.type === 'artifact' && data.data) {
        setArtifact(data.data);
        setHistory(prev => [data.data, ...prev].slice(0, 10)); // Keep last 10
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

      {/* History navigation */}
      {history.length > 1 && (
        <div className="border-t p-3 bg-gray-50">
          <p className="text-xs text-gray-500 mb-2">Recent</p>
          <div className="flex gap-2 overflow-x-auto">
            {history.slice(1, 5).map((item, i) => (
              <button
                key={i}
                onClick={() => setArtifact(item)}
                className="px-3 py-1 text-xs bg-white border rounded-full hover:bg-gray-100 whitespace-nowrap"
              >
                {item.type.replace('_', ' ')}
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
      <p className="text-sm mt-2 text-center">
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

function GenericView({ data }: { data: any }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <pre className="text-xs overflow-auto whitespace-pre-wrap">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

// Helper functions
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

## Testing Phase 2

### 1. Test n8n Workflows Directly

Before integrating with the agent, test each workflow with curl:

```bash
# Test email workflow
curl -X POST https://your-instance.app.n8n.cloud/webhook/read-emails \
  -H "Content-Type: application/json" \
  -d '{"count": 5, "filter": "unread"}'

# Test calendar workflow
curl -X POST https://your-instance.app.n8n.cloud/webhook/check-calendar \
  -H "Content-Type: application/json" \
  -d '{"date": "today"}'

# Test weather workflow
curl -X POST https://your-instance.app.n8n.cloud/webhook/weather \
  -H "Content-Type: application/json" \
  -d '{"location": "current"}'
```

### 2. Test Agent Function Tools

Once n8n is working:

1. Update `agent/.env` with n8n webhook URL
2. Restart the agent
3. Connect via web interface
4. Try these voice commands:
   - "Check my emails"
   - "What's on my calendar today?"
   - "What's the weather like?"

### 3. Verify Artifact Display

- Artifacts should appear in the right panel
- Visual data should update in real-time
- Recent artifacts should be accessible via history buttons

---

## File Summary

### New Files to Create:
1. `agent/tools.py` - Function tools for n8n integration
2. `webapp/components/ArtifactPanel.tsx` - Visual artifact display

### Files to Modify:
1. `agent/main.py` - Add tools import and update JexAgent
2. `agent/.env.example` - Add N8N_WEBHOOK_BASE
3. `webapp/app/page.tsx` - Add artifact panel to layout

### External Setup (n8n Cloud):
1. Create "Read Emails" workflow
2. Create "Check Calendar" workflow
3. Create "Get Weather" workflow
4. Get webhook URLs for all three

---

## Environment Variables Update

**agent/.env** - Add this line:
```env
N8N_WEBHOOK_BASE=https://your-instance.app.n8n.cloud/webhook
```

---

## Success Criteria

Phase 2 is complete when:
- ✅ User can ask JEX to check emails and see visual list
- ✅ User can ask about calendar and see events displayed
- ✅ User can ask about weather and see weather card
- ✅ Artifact panel shows data in real-time
- ✅ Recent artifacts are accessible via history
- ✅ Voice responses are natural and concise
- ✅ No errors in agent or frontend logs

---

## Next Steps (Future Phases)

### Phase 3 Ideas:
- Add Google Photos integration ("Show me family photos")
- Add more workflows (News, Transit, etc.)
- Implement conversation persistence (SQLite)
- Add proactive notifications
- Background workflows (morning briefing)

### Phase 4 Ideas:
- Multi-user support
- Voice wake word detection
- Mobile app integration
- Smart home control
- Custom workflow creation via voice

---

## Troubleshooting

### Agent can't reach n8n:
- Check `N8N_WEBHOOK_BASE` is set correctly
- Verify n8n workflows are activated
- Test workflows directly with curl

### Artifacts not showing:
- Check browser console for data channel errors
- Verify `useDataChannel` hook is working
- Check agent is calling `send_artifact_to_frontend()`

### Function tools not being called:
- Check tools are imported in main.py
- Verify tools are passed to Agent constructor
- Check LLM model supports function calling (gpt-4o-mini does)

---

## Cost Estimates (Approximate)

**Per 1000 conversations:**
- OpenAI LLM (gpt-4o-mini): ~$5-10
- OpenAI TTS: ~$15
- Deepgram STT: ~$4
- n8n Cloud: Free tier (5,000 workflow executions/month)
- LiveKit Cloud: Free tier (10GB/month)

**Total for development/testing**: <$50/month
