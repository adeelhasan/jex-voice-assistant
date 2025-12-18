# JEX - Personal Voice Assistant

A Jarvis-inspired personal voice assistant built with LiveKit, Next.js, and n8n workflows.

## Current Status

- ✅ **Phase 1: Voice Foundation** - Real-time voice conversation with configurable pipeline
- ✅ **Phase 2: Email Integration** - Gmail integration via n8n with visual artifact panel
- ✅ **Phase 3: Calendar Integration** - Google Calendar with event display
- ✅ **Phase 4: Context Management** - SQLite-based memory for follow-up queries

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

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Web Frontend (Next.js)                      │
│  ┌─────────────────┐              ┌──────────────────┐     │
│  │  Voice Interface│              │  Artifact Panel  │     │
│  │  - Mic controls │              │  - Emails        │     │
│  │  - State visual │              │  - Calendar      │     │
│  │  - Audio viz    │              │  - History tabs  │     │
│  └─────────────────┘              └──────────────────┘     │
└──────────────────┬──────────────────────────────────────────┘
                   │ LiveKit WebRTC + Data Channel
                   │
┌──────────────────▼──────────────────────────────────────────┐
│             Python Agent (LiveKit Agents)                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Voice Pipeline                                        │ │
│  │  VAD → Deepgram STT → OpenAI LLM → OpenAI TTS        │ │
│  └───────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Function Tools                                        │ │
│  │  - read_emails()    - read_calendar()                 │ │
│  │  - recall_context() [memory retrieval]                │ │
│  └───────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Context Store (SQLite)                                │ │
│  │  - Auto-save fetched data                             │ │
│  │  - 1-hour TTL, thread-safe                            │ │
│  │  - Supports scheduled job updates                     │ │
│  └───────────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP Webhooks
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                   n8n Workflows                             │
│  - Gmail API integration (read/filter)                      │
│  - Google Calendar API (fetch events)                       │
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

Edit `agent/context_store.py`:
```python
ContextStore(ttl_seconds=3600)  # 1 hour (default)
ContextStore(ttl_seconds=7200)  # 2 hours
```

## Project Structure

```
jarivsalexa/
├── agent/                     # Python LiveKit agent
│   ├── main.py               # Agent entrypoint & session management
│   ├── config.py             # Configurable LLM/STT/TTS providers
│   ├── tools.py              # Function tools (emails, calendar, recall)
│   ├── context_store.py      # SQLite-based context memory
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
│   │   └── ArtifactPanel.tsx # Email/calendar visual display
│   └── .env.local            # Frontend config (gitignored)
│
└── docs/                      # Project documentation
    └── CLAUDE.md             # Architecture & development guide
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

## Extending JEX

### Adding New Data Sources

1. **Create n8n workflow** for your data source (e.g., weather, flights)
2. **Add function tool** in `agent/tools.py`:
   ```python
   @function_tool()
   async def read_weather(location: str) -> str:
       result = await call_n8n_workflow("weather", {"location": location})
       # Auto-store for context
       store = get_context_store()
       store.save('weather', result['data'])
       return result['speech']
   ```
3. **Add artifact renderer** in `webapp/components/ArtifactPanel.tsx`
4. **Register tool** in `agent/main.py`

Context memory automatically works for any new data type!

## License

MIT
