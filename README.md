# JEX - Personal Voice Assistant

A Jarvis-inspired personal voice assistant built with LiveKit, Next.js, and n8n workflows.

## Current Status

- ✅ **Phase 1: Voice Foundation** - Real-time voice conversation with configurable pipeline
- ✅ **Phase 2: Email Integration** - Gmail integration via n8n with visual artifact panel
- ✅ **Phase 3: Calendar Integration** - Google Calendar with event display
- ✅ **Phase 4: Context Management** - SQLite-based memory for follow-up queries
- ✅ **Phase 5: Weather Integration** - 7-day forecast with intelligent caching and follow-up queries
- ✅ **Phase 6: X.com Integration & Background Task Management** - Trending content search, proactive pre-loading, and intelligent announcements

## Features

### Voice Conversation
- Natural voice interaction with state indicators (listening/thinking/speaking)
- Configurable voice pipeline (Deepgram STT → OpenAI LLM → OpenAI TTS)
- Multiple LLM providers supported (OpenAI, Anthropic, Google, Ollama)
- Mute/unmute controls with audio visualization

### Smart Integrations
- **Gmail**: Check emails, filter by unread/all/important
- **Google Calendar**: View upcoming events with date/time/location
- **Visual Artifacts**: Emails and calendar events display in sidebar panel

### Context Memory
- Automatic caching of fetched data (emails, calendar)
- Follow-up questions without re-fetching: "What was email 2 about?"
- Force refresh with voice: "Refresh my emails"
- 1-hour TTL with SQLite persistence

### X.com Integration
- Search for trending and interesting content from X.com (Twitter)
- Supports multiple search profiles (e.g., AI_Tech, Climate_Tech, Startup_News) or custom keyword searches
- Intelligent caching of search results for instant follow-up queries
- Background pre-loading of X feeds for proactive content readiness
- JEX proactively announces when background pre-loading tasks are complete


## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Web Frontend (Next.js)                      │
│  ┌─────────────────┐              ┌───────────────────┐    │
│  │  Voice Interface│              │  Artifact Panel   │    │
│  │  - Mic controls │              │  - Emails         │    │
│  │  - State visual │              │  - Calendar       │    │
│  │  - Audio viz    │              │  - Weather        │    │
│  └─────────────────┘              │  - X.com Threads  │    │
└──────────────────┬─────────────────└───────────────────┘    │
                   │ LiveKit WebRTC + Data Channel (Artifacts)
                   │
┌──────────────────▼──────────────────────────────────────────┐
│             Python Agent (LiveKit Agents)                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Voice Pipeline                                        │ │
│  │  VAD → Deepgram STT → OpenAI LLM → OpenAI TTS        │ │
│  └───────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Function Tools                                        │ │
│  │  - read_emails()        - read_calendar()            │ │
│  │  - get_weather()        - search_x_feed()            │ │
│  │  - recall_context()     - preload_x_feeds()          │ │
│  └───────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Context Store (SQLite)                                │ │
│  │  - Auto-save fetched data                             │ │
│  │  - 1-hour TTL, thread-safe                            │ │
│  │  - Supports scheduled job updates                     │ │
│  │  - Stores background tasks & announcements            │ │
│  └───────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Background Task Processor (asyncio)                  │ │
│  │  - Executes tasks (e.g., X feed preload)              │ │
│  │  - Generates proactive announcements                  │ │
│  └───────────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP Webhooks
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                   n8n Workflows                             │
│  - Gmail API integration (read/filter)                      │
│  - Google Calendar API (fetch events)                       │
│  - Weather API (forecasts)                                  │
│  - X.com (trending content search)                          │
└─────────────────────────────────────────────────────────────┘
```

## Setup

### Prerequisites

1. **LiveKit Account**: Get API keys from [livekit.io](https://livekit.io)
2. **OpenAI API Key**: From [platform.openai.com](https://platform.openai.com) (needs funding)
3. **Deepgram API Key**: From [deepgram.com](https://deepgram.com) (free tier available)
4. **n8n Instance**: For email/calendar workflows (optional for basic voice features)

### 1. Agent Setup

```bash
cd agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env with your API keys:
# LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
# OPENAI_API_KEY, DEEPGRAM_API_KEY
# N8N_WEBHOOK_BASE_URL, N8N_API_KEY (if using workflows)
```

### 2. Frontend Setup

```bash
cd webapp

# Install dependencies
npm install

# Create .env.local file
cp .env.example .env.local

# Edit .env.local with your LiveKit credentials:
# LIVEKIT_API_KEY, LIVEKIT_API_SECRET, NEXT_PUBLIC_LIVEKIT_URL
```

## Running the Application

### Terminal 1: Start the Agent

```bash
cd agent
source venv/bin/activate
python main.py dev
```

You should see:
```
INFO: Starting JEX agent...
INFO: LLM: openai (gpt-4o-mini)
INFO: STT: deepgram
INFO: TTS: openai (alloy)
```

### Terminal 2: Start the Frontend

```bash
cd webapp
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

### Getting Started

1. Click **"Connect to JEX"**
2. Allow microphone permissions when prompted
3. Wait for JEX to greet you
4. Start speaking!

### Voice Commands

**Basic Conversation:**
- "Hello JEX"
- "Tell me a joke"
- "What can you help me with?"

**Email Commands (requires n8n setup):**
- "Check my emails"
- "Show me my unread emails"
- "What was email 2 about?" *(uses context memory)*
- "Read me all the subjects" *(uses context memory)*
- "Refresh my emails" *(force refresh)*

**Calendar Commands (requires n8n setup):**
- "What's on my calendar?"
- "Do I have any meetings today?"
- "What time is my first meeting?" *(uses context memory)*
- "Where is it?" *(uses context memory)*
- "Update calendar" *(force refresh)*

### Context Memory

JEX automatically remembers data you've fetched:
- Ask follow-up questions without re-fetching from APIs
- Reference specific items: "email 2", "first meeting", "that event"
- Data cached for 1 hour with automatic expiration
- Force refresh anytime: "refresh emails", "update calendar"

### X.com Commands (requires n8n setup and X.com API access)
- "What's trending?" / "What are people talking about?" *(searches default profile, e.g., AI_Tech)*
- "What's trending in climate tech?" *(searches specific profile)*
- "Search X for 'new programming languages'" *(custom keyword search)*
- "Pre-load all X feeds" *(schedules background task for faster future queries)*
- "Pre-load all X feeds now" *(blocking call for immediate preload)*
- "Refresh X feed" *(force-fetches new data for the default profile)*


## Configuration

### Swapping LLM Providers

Edit `agent/.env`:

```bash
# Use OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# Use Anthropic Claude
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=your-key

# Use local Ollama
LLM_PROVIDER=ollama
LLM_MODEL=llama2
OLLAMA_BASE_URL=http://localhost:11434
```

### Changing Voice (TTS)

```bash
# OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
TTS_VOICE=nova

# Or use ElevenLabs
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=your-key
```

### Adjusting Context TTL

The context time-to-live (TTL) is configurable via environment variables in `agent/.env`.
For example, to set it to 2 hours:
```bash
CONTEXT_TTL_SECONDS=7200
```

### X.com Integration (agent/.env)

```bash
# Enable X.com functionality
X_ENABLED=true

# X.com Search Profiles (JSON string)
# Example for X_SEARCH_PROFILES:
# [
#   {"name": "AI_Tech", "keywords": "AI, machine learning, GPT, LLM", "interests": "AI breakthroughs, tech innovation"},
#   {"name": "Climate_Tech", "keywords": "climate change, green energy, sustainability", "interests": "environmental solutions, clean tech news"},
#   {"name": "Startup_News", "keywords": "startups, venture capital, entrepreneurship", "interests": "new companies, funding rounds"}
# ]
X_SEARCH_PROFILES=[...]
X_DEFAULT_PROFILE=AI_Tech # Default profile if not specified

# Background Refresh
X_BACKGROUND_REFRESH_ENABLED=true
X_REFRESH_INTERVAL_MINUTES=180 # Refresh every 3 hours
X_INITIAL_DELAY_SECONDS=60   # Initial delay for background refresh on startup

# Auto-preload on agent startup
X_AUTO_PRELOAD_ON_STARTUP=false # Set to true to preload all profiles when agent starts
```

## Project Structure

```
jarivsalexa/
├── agent/                     # Python LiveKit agent
│   ├── main.py               # Agent entrypoint & session management
│   ├── config.py             # Configurable LLM/STT/TTS providers
│   ├── tools.py              # Function tools (emails, calendar, weather, X.com, recall)
│   ├── context_store.py      # SQLite-based context memory, background task storage, and announcements
│   ├── task_processor.py     # Background task processing loop
│   ├── requirements.txt      # Python dependencies
│   └── .env                  # API keys (gitignored)
│
├── webapp/                    # Next.js frontend
│   ├── app/
│   │   ├── page.tsx          # Main UI page
│   │   └── api/
│   │       ├── token/        # LiveKit token generation
│   │       └── dispatch-agent/ # Manual agent dispatch
│   ├── components/
│   │   ├── VoiceAgent.tsx    # Voice interface & agent dispatcher
│   │   └── ArtifactPanel.tsx # Email/calendar/weather/X.com visual display
│   └── .env.local            # Frontend config (gitignored)
│
└── docs/                      # Project documentation
    └── CLAUDE.md             # Architecture & development guide
    └── GEMINI.md             # Detailed developer guide (this file)
```

## Troubleshooting

### Agent not responding

- Check `LIVEKIT_URL`, `API_KEY`, `API_SECRET` are correct in both `.env` files
- Verify agent is running: Look for "JEX agent session started successfully" in terminal
- Check browser console for connection errors

### No audio in browser

- Check microphone permissions in browser
- Verify browser supports WebRTC (Chrome/Firefox recommended)
- Check that you're using HTTPS or localhost (WebRTC requirement)

### "Server configuration error"

- Make sure you've created `.env.local` in webapp directory
- Verify all three LiveKit environment variables are set

### Context memory not working

- Check `context.db` file is being created in `agent/` directory
- Verify logs show "Stored X emails/events in context"
- SQLite database persists across agent restarts

### Emails/Calendar not fetching

- Verify n8n workflows are set up and running
- Check `N8N_WEBHOOK_BASE_URL` and `N8N_API_KEY` in `agent/.env`
- Test webhooks directly with curl to isolate issues

### X.com Integration not working

- Verify `X_ENABLED=true` in `agent/.env`
- Ensure `X_SEARCH_PROFILES` is correctly formatted JSON in `agent/.env`
- Check n8n workflows for X.com search are set up and running (endpoint ID should match the one in `agent/tools.py`)
- Check agent logs for "X feed search timed out" - n8n workflow might be too slow or stuck
- If using `preload_all_x_feeds`, check agent logs for background task failures

### Background tasks not running or announcements not delivered

- Check `agent/task_processor.py` is running (look for "Task processor started" in agent logs)
- Check `agent/main.py`'s `entrypoint` for task and announcement poller launch (look for "Task processor launched" and "Announcement poller launched")
- Verify `agent/context_store.py` is creating `tasks` and `announcements` tables
- Check agent logs for errors from `task_processor_loop` or `announcement_poller`


## Extending JEX

### Adding New Data Sources

1. **Create n8n workflow** for your data source (e.g., weather, flights, news). The workflow should return a JSON object with `speech` and `artifact` fields.
   ```json
   {
     "speech": "Here is the weather forecast for London...",
     "artifact": {
       "type": "weather",
       "data": { ... weather data ... }
     }
   }
   ```
2. **Add function tool** in `agent/tools.py`:
   ```python
   from livekit.agents import function_tool
   from .context_store import get_context_store
   from .utils import call_n8n_workflow, send_artifact_to_frontend

   @function_tool()
   async def get_my_weather(location: str) -> str:
       # Call the n8n webhook with its ID or name
       result = await call_n8n_workflow("your-weather-workflow-id-or-name", {"location": location})

       # Auto-store for context management and follow-up queries
       store = get_context_store()
       store.save('weather', result['artifact']['data'], metadata={'location': location})

       # Send the artifact to the frontend for visual display
       await send_artifact_to_frontend(result['artifact'])

       return result['speech']
   ```
3. **Add artifact renderer** in `webapp/components/ArtifactPanel.tsx` (similar to `XFeedList` or `WeatherWidget`).
4. **Register tool** in `agent/main.py`.

Context memory and artifact display automatically work for any new data type!

## License

MIT
