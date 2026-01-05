# CLAUDE.md - Development Guide for JEX Project

## Project Overview

**JEX** is a personal voice assistant inspired by Jarvis from Iron Man, built with:
- **Frontend**: Next.js 15 with React 19, LiveKit Components
- **Backend**: Python agent using LiveKit Agents SDK
- **Voice Pipeline**: Deepgram STT → OpenAI LLM → OpenAI TTS
- **Real-time Communication**: LiveKit Cloud (WebRTC)
- **Future Integration**: n8n workflows for real-world actions (Gmail, Calendar, etc.)

**Current Status**:
- ✅ **Phase 1**: Voice Foundation - Real-time voice conversation with configurable pipeline
- ✅ **Phase 2**: Email Integration - Gmail integration via n8n with visual artifact panel
- ✅ **Phase 3**: Calendar Integration - Google Calendar with event display
- ✅ **Phase 4**: Context Management - SQLite-based memory for follow-up queries
- ✅ **Phase 5**: Weather Integration - 7-day forecast with intelligent caching and follow-up queries

**Long-term Vision**:
- Full personal assistant with email, calendar, weather, and custom workflow integration ✅ (core integrations complete)
- Extensible tool system for adding new capabilities ✅ (pattern established)
- Visual artifact panel for displaying data alongside voice responses ✅ (complete)
- Multi-modal interaction (voice + visual data) ✅ (complete)
- Conversation persistence and context management ✅ (context management complete)

---

## Critical Development Principles

### 1. **ALWAYS Consult Latest APIs**

⚠️ **CRITICAL**: The LiveKit ecosystem evolves rapidly. Documentation examples may be outdated.

**Before implementing ANY LiveKit feature:**
1. Use `mcp__livekit-docs__docs_search` to find current documentation
2. Use `mcp__livekit-docs__code_search` to find actual implementation patterns in LiveKit repositories
3. Use `mcp__livekit-docs__get_changelog` to check for recent API changes
4. Verify against latest SDK versions in use:
   - Python: `livekit-agents>=0.9.0` (currently using 1.3.7)
   - JavaScript: `livekit-client@^2.8.3`, `@livekit/components-react@^2.6.3`

**Example of API evolution we encountered:**
```python
# OLD API (from docs examples):
from livekit.agents import RunningJobInfo, WorkerOptions
async def entrypoint(ctx: RunningJobInfo):
    await ctx.connect()

# CURRENT API (v1.3.7):
from livekit.agents import JobContext
from livekit.agents.worker import AgentServer
server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # No ctx.connect() needed - handled by decorator
```

### 2. **Architectural Decision Framework**

When facing any implementation decision, follow this hierarchy:

#### **Tier 1: Abstraction & Generalization (Preferred)**
Ask these questions FIRST:
- Could this be abstracted into a reusable pattern?
- Will this decision limit future extensibility?
- Is there a more flexible interface we could design?
- Can we make this configurable rather than hardcoded?

**Example - Current Good Abstraction:**
```python
# agent/config.py - Excellent abstraction for swapping providers
class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"

def create_llm(config: LLMConfig):
    # Factory pattern allows easy provider switching
```

**Future Architectural Improvements to Consider:**
- **Tool Registry Pattern**: Instead of hardcoding tools in main.py, create a registry system
- **Plugin Architecture**: Tools as plugins that can be loaded dynamically
- **Conversation Storage Abstraction**: Interface for different storage backends (memory, SQLite, Redis, cloud)
- **Multi-Agent Orchestration**: Framework for multiple specialized agents working together

#### **Tier 2: Best Practices & Patterns**
- Follow LiveKit's recommended patterns (check official examples)
- Use type hints extensively (Python) and TypeScript (frontend)
- Implement proper error handling and logging
- Design for testability (dependency injection, pure functions where possible)

#### **Tier 3: Quick Fixes (Only When Explicitly Directed)**
- Direct code changes without architectural consideration
- Hardcoded solutions
- "Make it work" without "make it right"

**When to use Tier 3:**
- User explicitly says "quick fix" or "just make it work for now"
- Debugging/troubleshooting immediate issues
- Prototyping to validate a concept before proper implementation

### 3. **Code Quality Standards**

**Python (agent/):**
- Type hints for all function signatures
- Docstrings for public APIs
- Use `logging` module, not print statements
- Environment variables for all configuration (via python-dotenv)
- Async/await best practices (avoid blocking calls in async functions)

**TypeScript (webapp/):**
- Strict TypeScript mode enabled
- React hooks best practices (proper dependencies, no stale closures)
- Component composition over complex components
- Proper cleanup in useEffect hooks

**Testing (future):**
- Unit tests for tool functions
- Integration tests for voice pipeline
- E2E tests for critical user flows

---

## Project Structure

```
jarivsalexa/
├── agent/                      # Python LiveKit agent (middleware)
│   ├── main.py                # Agent entrypoint, session management
│   ├── config.py              # LLM/STT/TTS provider configuration
│   ├── tools.py               # ✅ Function tools (read_emails, read_calendar, get_weather, recall_context)
│   ├── context_store.py       # ✅ SQLite context storage for follow-up queries (1-hour TTL)
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables (gitignored)
│
├── webapp/                     # Next.js frontend
│   ├── app/
│   │   ├── page.tsx           # Main landing page
│   │   ├── layout.tsx         # Root layout
│   │   ├── globals.css        # Global styles
│   │   └── api/
│   │       ├── token/
│   │       │   └── route.ts   # LiveKit token generation
│   │       └── dispatch-agent/
│   │           └── route.ts   # ✅ Manual agent dispatch endpoint
│   ├── components/
│   │   ├── VoiceAgent.tsx     # Main voice interface & agent dispatcher
│   │   └── ArtifactPanel.tsx  # ✅ Visual data display (emails, calendar, weather)
│   ├── package.json           # Node dependencies
│   └── .env.local             # Frontend environment vars (gitignored)
│
├── docs/
│   ├── phase1_architecture_explained.md
│   ├── phase2_implementation_plan.md
│   └── [Future] api_reference.md
│
├── SETUP.md                   # Quick reference guide
├── CLAUDE.md                  # This file - development guide
└── README.md                  # Project overview
```

---

## Phase 1 Architecture (Current Implementation)

### Voice Pipeline Flow

```
Browser (mic)
  → LiveKit Cloud (WebRTC)
  → Python Agent receives audio
  → Silero VAD detects speech end
  → Deepgram STT converts to text
  → OpenAI LLM generates response (with chat context)
  → OpenAI TTS converts to audio
  → LiveKit Cloud streams to browser
  → Browser speakers play audio
```

### Key Components

**1. Agent Session (`agent/main.py:99-104`)**
```python
session = AgentSession(
    vad=vad,      # Silero VAD for speech detection
    stt=stt,      # Deepgram for transcription
    llm=llm,      # OpenAI GPT-4o-mini
    tts=tts,      # OpenAI TTS (alloy voice)
)
```

**State Management:**
- In-memory chat context (conversation history)
- State: listening → thinking → speaking
- No persistence (lost on disconnect)

**2. JexAgent Class (`agent/main.py:46-63`)**
```python
class JexAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""System prompt defining JEX's personality...""",
            # tools=[]  # Phase 2: Function tools will go here
        )

    async def on_enter(self):
        # Initial greeting when user connects
        await self.session.generate_reply(...)
```

**3. Frontend Voice Interface (`webapp/components/VoiceAgent.tsx`)**
- LiveKit room connection
- State visualization (listening/thinking/speaking)
- Mute/unmute controls
- Audio rendering via RoomAudioRenderer

---

## Phase 2 Architecture (Planned - See docs/phase2_implementation_plan.md)

### Key Additions

**1. Function Tools for Real Actions**
```python
# agent/tools.py (to be created)
from livekit.agents import function_tool

@function_tool(
    name="read_emails",
    description="Fetch recent emails from user's Gmail inbox"
)
async def read_emails(count: int = 5) -> dict:
    """Call n8n webhook to get emails"""
    # HTTP call to n8n workflow
    # Returns structured email data
```

**2. n8n Workflow Integration**
- Gmail API workflow (read emails, send emails)
- Google Calendar API workflow (read events, create events)
- Weather API workflow (get current weather, forecast)
- Webhooks exposed for agent to call

**3. Artifact Panel (Visual Data Display)**
```typescript
// webapp/components/ArtifactPanel.tsx (to be created)
// Displays emails, calendar events, weather visually
// Receives data via LiveKit data channel
// Synchronized with voice responses
```

**4. Data Channel Communication**
```python
# Agent sends visual data to frontend
await ctx.room.local_participant.publish_data(
    payload=json.dumps({"type": "emails", "data": email_list}),
    kind=DataPacket.RELIABLE
)
```

---

## Architectural Considerations for Future

### 1. **Tool System Design**

**Current Approach (Phase 2 plan):**
- Individual @function_tool decorated functions
- Direct n8n webhook calls from each tool
- Tools defined in agent/tools.py

**Better Long-term Architecture:**

```python
# agent/tools/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class ToolProvider(ABC):
    """Base class for tool providers"""

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool action"""
        pass

    @abstractmethod
    def get_schema(self) -> dict:
        """Return tool schema for LLM"""
        pass

# agent/tools/email.py
class EmailToolProvider(ToolProvider):
    def __init__(self, backend: EmailBackend):
        self.backend = backend  # Could be n8n, direct Gmail API, etc.

    async def execute(self, action: str, **kwargs):
        if action == "read":
            return await self.backend.read_emails(**kwargs)
        elif action == "send":
            return await self.backend.send_email(**kwargs)

# agent/tools/registry.py
class ToolRegistry:
    """Central registry for all tools"""
    def __init__(self):
        self._tools: Dict[str, ToolProvider] = {}

    def register(self, name: str, provider: ToolProvider):
        self._tools[name] = provider

    def get_livekit_tools(self):
        """Convert registered tools to LiveKit function_tool format"""
        # Dynamically generate @function_tool wrappers
```

**Benefits:**
- Easy to add new tools without modifying main.py
- Swap backends (n8n → direct API → local mock) without changing tool interface
- Tools can be loaded from config file or plugins
- Testable in isolation

**When to implement:**
- Not immediately - Phase 2 can use simple approach
- Consider when we have 5+ tools
- Definitely before adding user-customizable tools

### 2. **Conversation Persistence Architecture**

**Phase 1 Reality:**
- Chat context in AgentSession memory
- Lost on disconnect/restart

**Simple Phase 2 Approach:**
```python
# Save to SQLite after each turn
import sqlite3
db = sqlite3.connect("conversations.db")
db.execute("INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)")
```

**Better Long-term Architecture:**

```python
# agent/storage/base.py
class ConversationStore(ABC):
    @abstractmethod
    async def save_message(self, user_id: str, message: Message):
        pass

    @abstractmethod
    async def get_history(self, user_id: str, limit: int = 50) -> List[Message]:
        pass

# agent/storage/sqlite.py
class SQLiteStore(ConversationStore):
    # Local persistence

# agent/storage/redis.py
class RedisStore(ConversationStore):
    # Fast cache, good for multi-instance deployments

# agent/storage/supabase.py
class SupabaseStore(ConversationStore):
    # Cloud persistence with user auth

# agent/main.py
store = create_store(os.getenv("STORAGE_BACKEND", "sqlite"))
```

**Benefits:**
- Switch storage backends via env var
- Easy to add cloud storage later
- Can implement hybrid (Redis cache + SQLite persistence)
- Testable with mock store

**When to implement:**
- Consider for Phase 2 if persistence is needed
- Full abstraction when deploying to production
- Necessary when adding multi-user support

### 3. **Context Management for Follow-up Queries** ✅ IMPLEMENTED

**The Problem:**
Users want to ask follow-up questions about previously fetched data without re-triggering expensive API calls:
- "What was email 2 about?" (after checking emails)
- "What time is my first meeting?" (after viewing calendar)
- "Will it rain on Friday?" (after checking weather)
- "Tell me more about option 3" (after flight search)

**Design Philosophy:**
Let the LLM do the heavy lifting. Instead of complex reference resolution logic, we:
1. **Store transformed data** as JSON (emails, calendar events, weather forecasts, etc.)
2. **Pass it back to the LLM** when needed via recall_context() tool
3. **Let the LLM extract** what the user is asking about

The LLM already understands "the 3rd email", "first meeting", "Friday's weather" - we just provide the data.

**Critical:** Store data in the SAME format that the artifact panel displays. For weather, we store the transformed data (with `current` and `daily` fields) plus raw forecast in metadata for detailed LLM analysis.

**Implemented Architecture:**

```python
# agent/context_store.py - SQLite-based storage
class ContextStore:
    """Simple, flexible short-term memory with TTL."""

    def __init__(self, db_path: str = "context.db", ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds  # 1 hour default
        self._lock = Lock()  # Thread-safe for scheduled jobs

    def save(self, context_type: str, data: Any, metadata: Optional[Dict] = None):
        """Store or update data (uses INSERT OR REPLACE)"""
        # Stores JSON with timestamp

    def get_with_metadata(self, context_type: str) -> Optional[Dict]:
        """Retrieve data with age check, auto-expires old data"""
        # Returns: {'data': ..., 'metadata': ..., 'age_seconds': ...}
```

**Usage Pattern:**

```python
# 1. Auto-store when fetching data
@function_tool()
async def read_emails(count: int = 5, filter: str = "unread") -> str:
    result = await call_n8n_workflow("read-emails", {...})

    # Auto-store for follow-ups
    store = get_context_store()
    store.save('emails', result["artifact"]["data"],
               metadata={'count': count, 'filter': filter})

    return result["speech"]

# 2. Recall for follow-up queries
@function_tool()
async def recall_context(context_type: str) -> str:
    """LLM calls this to answer follow-up questions"""
    store = get_context_store()
    result = store.get_with_metadata(context_type)

    if not result:
        return f"No {context_type} data in memory. Fetch fresh data first."

    # Return as JSON - LLM can parse and extract what user wants
    return json.dumps({
        'context_type': context_type,
        'data': result['data'],  # Full data list
        'age_seconds': int(result['age_seconds']),
        'count': len(result['data']) if isinstance(result['data'], list) else 1
    })
```

**Conversation Flow Example:**

```
User: "Check my emails"
→ Agent calls read_emails()
→ Fetches from n8n, displays in artifact panel
→ Auto-stores: store.save('emails', [...5 emails...])
→ Voice: "You have 5 unread emails..."

User: "What was email 2 about?"
→ Agent calls recall_context('emails')
→ Gets: {'data': [...5 emails...], 'age_seconds': 45}
→ LLM extracts: data[1] (0-indexed)
→ Voice: "Email 2 is from John about the project deadline..."
→ Artifact panel re-displays (via send_artifact_to_frontend)

User: "Refresh my emails"
→ Agent recognizes "refresh" intent (via instructions)
→ Calls read_emails() again
→ New data auto-replaces old (INSERT OR REPLACE)
```

**Key Design Decisions:**

**Why SQLite (not in-memory)?**
- ✅ **Persistent** across agent restarts
- ✅ **Thread-safe** for scheduled background jobs
- ✅ **JSON columns** - no schema changes for new data types
- ✅ **Simple** - single .db file, built into Python
- ✅ **Concurrent access** - agent + cron jobs can both read/write

**Why INSERT OR REPLACE?**
Enables natural refresh without explicit clear logic:
```python
# User: "Refresh emails"
# → LLM calls read_emails() again
# → store.save('emails', new_data)
# → Automatically replaces old data (same PRIMARY KEY)
```

**Why TTL (Time-To-Live)?**
- Data expires after 1 hour (configurable)
- Auto-cleanup on access prevents stale data
- Prevents memory bloat
- Simple to adjust: `ContextStore(ttl_seconds=7200)` for 2 hours

**Why ONE Universal recall_context() Tool?**
Instead of separate `get_stored_emails()`, `get_stored_calendar()`, etc.:
```python
# Generic, extensible
recall_context('emails')
recall_context('calendar')
recall_context('weather')     # ✅ Implemented
recall_context('flights')     # Future - no code changes needed!
```

**Extensibility Pattern:**

Adding a new data source automatically gets context support. Example: weather (implemented):

```python
# 1. Create new tool
@function_tool()
async def get_weather() -> str:
    result = await call_n8n_workflow("weather-forecast", {"lat": lat, "lon": lon})

    # Transform data to match artifact panel format
    transformed_data = {...}  # With 'current' and 'daily' fields

    # Store transformed data (same format as displayed)
    store = get_context_store()
    store.save(
        context_type='weather',
        data=transformed_data,  # Display format
        metadata={'raw_forecast': daily_data}  # Detailed data for LLM
    )

    await send_artifact_to_frontend({"type": "weather", "data": transformed_data})
    return speech

# 2. Update artifact panel type map (in recall_context)
artifact_type_map = {
    'emails': 'email_list',
    'calendar': 'calendar_events',
    'weather': 'weather',  # ✅ Added
    # Future: 'flights': 'flight_options',
}

# 3. That's it! Now users can:
# "What's the weather?"  → get_weather() [first call, fetches fresh]
# "Will it rain on Friday?"  → recall_context('weather') [follow-up, uses cache]
# "When's a good day to golf?"  → recall_context('weather') [LLM analyzes conditions]
```

**Scheduled Jobs Support:**

The Lock-based design supports background updates:

```python
# Hypothetical: Background cron job
async def update_emails_every_10min():
    store = get_context_store()
    emails = await fetch_from_gmail_api()
    store.save('emails', emails)  # Thread-safe update

# User asks later:
# "Any new emails?"
# → recall_context('emails')  → Gets fresh data from background job
# → No API call needed!
```

**Architecture Benefits:**

1. **Simple**: ~100 lines of code in context_store.py
2. **Flexible**: Works for any JSON-serializable data
3. **Extensible**: New data sources require zero changes to context logic
4. **Testable**: Mock ContextStore for unit tests
5. **Future-proof**: Easy upgrade path to Redis/cloud storage:

```python
# Later: Swap storage backend
class RedisContextStore(ContextStore):
    """Same interface, different backend"""

# In main.py
store_type = os.getenv("CONTEXT_STORE", "sqlite")  # or "redis"
```

**Limitations & Future Enhancements:**

Current limitations (acceptable for MVP):
- No multi-user support (single global store)
- No query-specific caching (e.g., "unread emails" vs "all emails")
- Simple TTL (not per-type expiration rules)

Future enhancements to consider:
- User-specific context: `store.save('emails', data, user_id='user123')`
- Query-aware caching: `store.save('emails:unread', data)` vs `store.save('emails:all', data)`
- Hybrid storage: Redis cache + SQLite persistence
- Context pruning: Keep only recent N items to prevent bloat

**When to Enhance:**

- **Multi-user support needed**: Add user_id parameter
- **Complex queries**: Implement query-specific cache keys
- **Production deployment**: Consider Redis for distributed agents
- **Scale issues**: Add LRU eviction, size limits

**Testing Context Management:**

```python
# Unit test
def test_context_ttl():
    store = ContextStore(ttl_seconds=1)
    store.save('test', {'data': 'value'})

    assert store.get('test') == {'data': 'value'}

    time.sleep(2)
    assert store.get('test') is None  # Expired

# Integration test
async def test_email_followup():
    # Fetch emails
    await read_emails(count=3)

    # Recall for follow-up
    result = await recall_context('emails')
    data = json.loads(result)

    assert data['count'] == 3
    assert len(data['data']) == 3
```

**Key Takeaway:**

Context management demonstrates the power of **simple, flexible abstractions**. By trusting the LLM to understand references and storing raw data, we avoid complex parsing logic while enabling powerful follow-up queries across ANY data type.

### 4. **Multi-Agent Orchestration**

**Future Vision:**
- Specialized agents (email agent, calendar agent, research agent)
- Coordinator agent that delegates to specialists
- Agents can collaborate on complex tasks

**Architectural Pattern:**

```python
# agent/orchestration/coordinator.py
class CoordinatorAgent(Agent):
    def __init__(self, specialist_agents: Dict[str, Agent]):
        self.specialists = specialist_agents

    async def handle_request(self, user_message: str):
        # Analyze intent
        intent = await self.classify_intent(user_message)

        # Delegate to specialist
        if intent == "email":
            return await self.specialists["email"].handle(user_message)
        elif intent == "complex_research":
            # Multi-agent collaboration
            results = await asyncio.gather(
                self.specialists["web"].research(topic),
                self.specialists["email"].find_related(),
            )
            return await self.synthesize_results(results)
```

**When to consider:**
- Phase 3+
- When single-agent context becomes too complex
- When specialized models make sense (e.g., coding agent vs chat agent)

### 4. **Frontend State Management**

**Current (Phase 1):**
- Local useState in components
- LiveKit hooks provide state

**Phase 2 Addition:**
- Artifact panel needs to sync with voice state
- Multiple components need shared state

**Consider for Phase 2:**

```typescript
// webapp/lib/store.ts
import { create } from 'zustand'

interface JexStore {
  agentState: 'listening' | 'thinking' | 'speaking'
  artifacts: Artifact[]
  conversationHistory: Message[]

  setAgentState: (state: string) => void
  addArtifact: (artifact: Artifact) => void
}

export const useJexStore = create<JexStore>((set) => ({
  agentState: 'listening',
  artifacts: [],
  conversationHistory: [],

  setAgentState: (state) => set({ agentState: state }),
  addArtifact: (artifact) => set((s) => ({
    artifacts: [...s.artifacts, artifact]
  })),
}))
```

**Benefits:**
- Centralized state
- Easy to debug (Redux DevTools work with Zustand)
- Persistence to localStorage simple to add

**Alternative: React Context**
- Lighter weight
- Good enough for Phase 2 scale
- Consider Zustand/Redux only if state management becomes painful

---

## Development Workflow

### Before Starting ANY Feature

1. **Check Latest Documentation**
   ```
   Use mcp__livekit-docs__docs_search for conceptual info
   Use mcp__livekit-docs__code_search for implementation examples
   Check changelog for recent API changes
   ```

2. **Ask Architectural Questions**
   - Is this a one-off fix or part of a larger pattern?
   - Will we need similar functionality elsewhere?
   - How does this fit into the long-term vision?
   - Can we design an interface that works for multiple backends?

3. **Propose Before Implementing**
   - For significant changes, outline the approach
   - Present architectural trade-offs
   - Get user buy-in on direction

4. **Implement with Best Practices**
   - Type hints / TypeScript types
   - Error handling
   - Logging
   - Comments for non-obvious logic

5. **Test End-to-End**
   - Run agent: `cd agent && python main.py dev`
   - Run frontend: `cd webapp && npm run dev`
   - Test voice interaction
   - Check logs for errors

### When Issues Arise

**Tier 1: Investigate Root Cause**
- Check agent logs in terminal
- Check browser console
- Review LiveKit dashboard for connection issues

**Tier 2: Consult Documentation**
- Search LiveKit docs for error messages
- Check GitHub issues in LiveKit repos
- Review changelog for breaking changes

**Tier 3: Architectural Review**
- Is this a symptom of a design issue?
- Would a different architecture prevent this?
- Should we refactor now or note as tech debt?

---

## Common Patterns & Best Practices

### 1. **LiveKit Agent Patterns**

**Correct Session Initialization (v1.3.7+):**
```python
from livekit.agents import JobContext
from livekit.agents.worker import AgentServer

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # ctx.room is already available
    # No need to call ctx.connect()

    # Create components
    vad = create_vad(...)
    stt = create_stt(...)
    llm = create_llm(...)
    tts = create_tts(...)

    # Create session
    session = AgentSession(vad=vad, stt=stt, llm=llm, tts=tts)

    # Start session (note parameter order!)
    await session.start(agent=MyAgent(), room=ctx.room)

if __name__ == "__main__":
    cli.run_app(server)  # Pass server, not WorkerOptions
```

**Adding Function Tools:**
```python
from livekit.agents import function_tool

@function_tool(
    name="tool_name",
    description="Clear description for LLM to understand when to use this"
)
async def my_tool(param1: str, param2: int = 5) -> dict:
    """
    Detailed docstring explaining what the tool does.

    Args:
        param1: Description of parameter
        param2: Description with default value

    Returns:
        Dictionary with results
    """
    # Implementation
    return {"result": "data"}

# In Agent class:
class MyAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="...",
            tools=[my_tool],  # Pass the function directly
        )
```

### 2. **LiveKit Frontend Patterns**

**Room Connection:**
```typescript
import { LiveKitRoom, RoomAudioRenderer } from '@livekit/components-react'

function VoiceAgent() {
  const [token, setToken] = useState('')

  useEffect(() => {
    fetch('/api/token')
      .then(r => r.json())
      .then(data => setToken(data.token))
  }, [])

  if (!token) return <div>Loading...</div>

  return (
    <LiveKitRoom
      token={token}
      serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
      connect={true}
    >
      <AgentInterface />
      <RoomAudioRenderer />  {/* Must include for audio playback */}
    </LiveKitRoom>
  )
}
```

**Using Voice Assistant Hook:**
```typescript
import { useVoiceAssistant } from '@livekit/components-react'

function AgentInterface() {
  const { state, audioTrack } = useVoiceAssistant()

  // state: 'listening' | 'thinking' | 'speaking'
  // audioTrack: agent's audio track reference

  return (
    <div>
      <p>Agent is {state}</p>
    </div>
  )
}
```

**Data Channel Communication:**
```typescript
import { useDataChannel } from '@livekit/components-react'

function ArtifactPanel() {
  const [artifacts, setArtifacts] = useState([])

  const handleMessage = useCallback((payload: Uint8Array) => {
    const decoder = new TextDecoder()
    const data = JSON.parse(decoder.decode(payload))

    if (data.type === 'artifact') {
      setArtifacts(prev => [...prev, data.content])
    }
  }, [])

  useDataChannel(handleMessage)

  // Render artifacts...
}
```

### 3. **Environment Variables**

**Agent (.env):**
```bash
# LiveKit Connection
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-key
LIVEKIT_API_SECRET=your-secret

# Provider Configuration
LLM_PROVIDER=openai          # openai|anthropic|google|ollama
LLM_MODEL=gpt-4o-mini
STT_PROVIDER=deepgram        # deepgram|assembly_ai|whisper
TTS_PROVIDER=openai          # openai|elevenlabs|cartesia

# API Keys
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
ANTHROPIC_API_KEY=...        # If using Claude

# n8n Workflow Integration
# For production webhooks (UUIDs): endpoint will be https://architoon.app.n8n.cloud/webhook/{UUID}
# For test webhooks: set base URL to https://architoon.app.n8n.cloud/webhook-test
N8N_WEBHOOK_BASE_URL=https://architoon.app.n8n.cloud/webhook-test
N8N_API_KEY=your-n8n-api-key  # Optional, if webhook requires auth

# Personal Preferences
# Weather location: latitude,longitude (e.g., "43.6532,-79.3832" for Toronto)
WEATHER_LOCATION=40.7128,-74.0060
```

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-key
LIVEKIT_API_SECRET=your-secret
```

---

## Testing Strategy

### Phase 1 Testing (Current)
- Manual voice interaction testing
- Check logs for errors
- Verify state transitions in UI

### Phase 2 Testing (When Adding Tools)

**Unit Tests for Tools:**
```python
# tests/test_tools.py
import pytest
from agent.tools import read_emails

@pytest.mark.asyncio
async def test_read_emails_success(mock_n8n):
    """Test successful email fetch"""
    mock_n8n.return_value = {"emails": [...]}

    result = await read_emails(count=5)

    assert len(result["emails"]) == 5
    assert "subject" in result["emails"][0]
```

**Integration Tests:**
```python
# tests/test_agent_integration.py
import pytest
from agent.main import JexAgent

@pytest.mark.asyncio
async def test_email_query_flow():
    """Test full flow: user query → tool call → response"""
    agent = JexAgent()

    # Simulate user asking about emails
    response = await agent.process_message(
        "What are my recent emails?"
    )

    assert "email" in response.lower()
    # Verify tool was called
```

**E2E Tests (Future):**
- Playwright tests for frontend
- Simulate voice input (audio file → agent → verify response)

---

## Debugging Guide

### Agent Not Starting

**Symptoms:**
- Error on `python main.py dev`
- Import errors

**Check:**
1. Virtual environment activated? `which python` should show venv path
2. Dependencies installed? `pip list | grep livekit`
3. Environment variables set? `python -c "import os; print(os.getenv('LIVEKIT_URL'))"`
4. Check LiveKit API version compatibility

### Agent Not Responding to Voice

**Symptoms:**
- Agent connects but doesn't respond when you speak

**Check:**
1. Agent logs show "received user transcript"?
2. Browser console errors?
3. Microphone permissions granted?
4. Check LiveKit dashboard - is audio track publishing?
5. STT API key valid? (Deepgram)
6. LLM API key valid and funded? (OpenAI)

### Frontend Build Errors

**Symptoms:**
- `npm run dev` fails
- Module not found errors

**Check:**
1. All dependencies installed? `npm install`
2. TypeScript errors? Run `npm run lint`
3. Environment variables set in `.env.local`?

### Tool Calls Not Working (Phase 2)

**Symptoms:**
- Agent doesn't call tools when expected
- Tool calls fail

**Check:**
1. Tool decorator syntax correct?
2. Tool description clear enough for LLM?
3. n8n webhook returning 200?
4. Check agent logs for tool invocation attempts
5. LLM has permission to call tools? (some models need explicit enablement)

---

## Migration Path: Phase 1 → Phase 2

### Step 1: Add First n8n Workflow (Gmail)
1. Create n8n workflow for Gmail read
2. Create `agent/tools.py` with `read_emails` function
3. Update `main.py` to import and register tool
4. Test with voice: "What are my recent emails?"

### Step 2: Add Artifact Panel (Frontend)
1. Create `webapp/components/ArtifactPanel.tsx`
2. Add to `app/page.tsx`
3. Implement useDataChannel hook
4. Test data flow: agent → data channel → panel

### Step 3: Connect Tool to Artifact
1. In `read_emails` tool, publish data to channel after n8n call
2. Verify panel displays emails
3. Synchronize with voice response timing

### Step 4: Repeat for Calendar and Weather
1. Create n8n workflows
2. Add tool functions
3. Update artifact panel to handle new data types

### Step 5: (Optional) Add Persistence
1. Create `agent/storage.py` with SQLite store
2. Save messages after each turn
3. Load history on session start
4. Test conversation continuity across disconnects

---

## Future Enhancements (Phase 3+)

### Advanced Features to Consider

**1. Context-Aware Proactivity**
- Agent checks calendar/email periodically
- Proactively notifies user of important events
- "By the way, you have a meeting in 10 minutes"

**2. Multi-Modal Interaction**
- Screen sharing for visual context
- Image analysis (user shows document via camera)
- Collaborative drawing/diagramming

**3. Custom Workflows**
- User-defined automation ("Every morning, summarize my emails and check my calendar")
- Visual workflow builder in frontend
- Save and replay workflows

**4. Voice Customization**
- Clone user's preferred voice (ElevenLabs)
- Personality customization (formal vs casual)
- Multiple agent personas

**5. Integration Ecosystem**
- Slack, Discord, Notion, Linear, etc.
- Plugin marketplace
- OAuth flows for user auth

**6. Conversation Intelligence**
- Automatic summarization of long conversations
- Extract action items
- Follow-up reminders
- Search conversation history

---

## Key Files Reference

### Agent Files

**`agent/main.py`** (~149 lines) ✅ UPDATED
- Main entrypoint: `@server.rtc_session() async def entrypoint(ctx: JobContext)`
- JexAgent class with "Americanized Jarvis" personality (ambient, informal)
- Comprehensive tool usage instructions (first call vs follow-ups)
- Time-based greetings with random variation
- Registered tools: read_emails, read_calendar, get_weather, recall_context

**`agent/config.py`** (98 lines)
- Provider enums (LLM, STT, TTS)
- Config dataclasses
- Factory functions: `create_llm()`, `create_stt()`, `create_tts()`

**`agent/tools.py`** (~499 lines) ✅ IMPLEMENTED
- `call_n8n_workflow()`: HTTP client for n8n webhooks (supports test and production endpoints)
- `send_artifact_to_frontend()`: LiveKit data channel publisher
- `@function_tool read_emails()`: Gmail integration with auto-context storage
- `@function_tool read_calendar()`: Google Calendar integration with auto-context storage
- `@function_tool get_weather()`: 7-day weather forecast with lat/lon parsing and data transformation
- `@function_tool recall_context()`: Universal context retrieval with metadata support
- `@function_tool search_youtube()`: YouTube video search/summary (placeholder)
- `@function_tool search_x_feed()`: X.com posts search/summary (placeholder)

**`agent/context_store.py`** (~113 lines) ✅ IMPLEMENTED
- `ContextStore` class: SQLite-based storage with 1-hour TTL
- Thread-safe (Lock) for scheduled jobs
- JSON columns for flexible data types
- Auto-expiration on access (configurable TTL)
- `get_context_store()`: Global singleton factory

**`agent/requirements.txt`** (3 lines)
- livekit-agents with extras: [openai, silero, deepgram]
- python-dotenv
- httpx

### Frontend Files

**`webapp/app/page.tsx`** (9 lines)
- Simple page importing VoiceAgent component

**`webapp/components/VoiceAgent.tsx`** (~168 lines) ✅ UPDATED
- Token fetch and LiveKit room connection
- Agent dispatcher (automatic on room join)
- AgentInterface: state display (listening/thinking/speaking), mute controls
- Uses hooks: useVoiceAssistant, useLocalParticipant, useRoomContext

**`webapp/components/ArtifactPanel.tsx`** (~224 lines) ✅ IMPLEMENTED
- `ArtifactRenderer`: Switches between email_list, calendar_events, weather, generic views
- `EmailList`: Displays emails with sender, subject, snippet, timestamp
- `CalendarEventList`: Displays events with date/time, location, description
- `WeatherWidget`: Gradient blue card with current conditions and 7-day forecast
- `useDataChannel`: Receives artifacts from agent via data channel
- History navigation between artifacts (email, calendar, weather)

**`webapp/app/api/token/route.ts`** (28 lines)
- GET handler for LiveKit token generation
- Uses AccessToken from livekit-server-sdk
- Grants: roomJoin, publish, subscribe, publishData

**`webapp/app/api/dispatch-agent/route.ts`** (~35 lines) ✅ IMPLEMENTED
- POST handler for manual agent dispatch (debugging)
- Creates RoomServiceClient and dispatches agent to room

**`webapp/package.json`** (31 lines)
- LiveKit dependencies
- Next.js 15, React 19
- TypeScript, Tailwind

### Documentation Files

**`docs/phase1_architecture_explained.md`** (321 lines)
- Complete architectural explanation
- Voice pipeline flow diagrams
- What's working vs not implemented
- File references with line numbers

**`docs/phase2_implementation_plan.md`** (464 lines)
- n8n workflow specifications
- Tool function implementations
- Artifact panel code
- Testing procedures

**`SETUP.md`** (54 lines)
- Quick reference guide
- Current status summary
- Quick start commands

---

## Important Reminders

### When Implementing Features

1. **API First**: Always check latest LiveKit docs/code before implementing
2. **Abstract**: Ask "will we need variations of this?" before hardcoding
3. **Type Safe**: Use type hints (Python) and TypeScript strictly
4. **Error Handle**: Especially for external APIs (n8n, OpenAI, etc.)
5. **Log**: Use proper logging, not print statements
6. **Test**: Manual voice testing minimum, unit tests for tools

### When Reviewing Code

1. **Is it future-proof?** Will this need refactoring soon?
2. **Is it configurable?** Are there hardcoded values that should be env vars?
3. **Is it clear?** Would another developer understand this?
4. **Is it tested?** Can we verify it works?

### When Things Break

1. **Don't assume docs are current** - verify with code search
2. **Check changelogs** - API may have changed
3. **Look for patterns** - how do official examples do it?
4. **Consider architecture** - is this a symptom of a design issue?

---

## Questions to Ask Before Major Changes

1. **"Is there a LiveKit-recommended pattern for this?"**
   - Check official examples and docs first

2. **"Will we need similar functionality elsewhere?"**
   - If yes, design an abstraction (e.g., tool registry)

3. **"What if we want to swap the backend later?"**
   - Design interfaces, not implementations

4. **"How will this scale?"**
   - Multiple users? Multiple agents? Distributed deployment?

5. **"Can this be tested in isolation?"**
   - If no, consider dependency injection

6. **"What's the simplest thing that could work?"**
   - Don't over-engineer, but don't paint into a corner

7. **"Is this the right layer for this logic?"**
   - Frontend vs backend vs external service (n8n)

---

## Success Criteria

### Phase 1 (✅ Complete)
- ✅ Voice conversation works end-to-end
- ✅ State visualization in browser
- ✅ Configurable LLM/STT/TTS providers

### Phase 2 (✅ Complete)
- ✅ Email integration working (read_emails tool + n8n workflow)
- ✅ Artifact panel displays emails visually
- ✅ Data synchronized with voice responses
- ✅ n8n workflows tested and reliable

### Phase 3 (✅ Complete)
- ✅ Calendar integration working (read_calendar tool + n8n workflow)
- ✅ Calendar events display in artifact panel
- ✅ Multiple artifact types (emails + calendar)
- ✅ History navigation between artifacts

### Phase 4 (✅ Complete)
- ✅ Context management with SQLite storage
- ✅ Follow-up queries work without re-fetching (recall_context tool)
- ✅ TTL-based expiration (1 hour default)
- ✅ Force refresh via voice commands
- ✅ Extensible pattern for new data sources

### Phase 5 (✅ Complete)
- ✅ Weather integration with 7-day forecast (get_weather tool + n8n workflow)
- ✅ WeatherWidget displays current conditions and daily forecast
- ✅ Lat/lon configuration via WEATHER_LOCATION environment variable
- ✅ Intelligent caching (1-hour TTL, first call vs follow-ups)
- ✅ Natural language weather queries ("When will it get warm?", "Is it going to rain?")
- ✅ Context-aware follow-ups ("What about Friday?", "When's a good day to golf?")
- ✅ Data transformation pattern (store display format + raw data in metadata)

### Phase 6+ (Future)
- Conversation persistence (full chat history across sessions)
- Multi-agent orchestration (if needed)
- Plugin system for custom tools
- Production deployment with auth
- Additional integrations (flights, news, task management, etc.)

---

## Contact & Resources

**LiveKit Documentation:**
- Main docs: https://docs.livekit.io/
- Agents guide: https://docs.livekit.io/agents/
- Python SDK: https://docs.livekit.io/agents/python/

**Project-Specific Docs:**
- See `docs/phase1_architecture_explained.md` for current architecture
- See `docs/phase2_implementation_plan.md` for next steps
- See `SETUP.md` for quick reference

**When Stuck:**
- Use MCP tools to search LiveKit docs and code
- Check LiveKit GitHub issues
- Review changelog for breaking changes
- Ask architectural questions before implementing

---

## Final Note

This project prioritizes **thoughtful architecture** over **quick fixes**.

When faced with a choice:
- ✅ Take time to design a flexible solution
- ✅ Consult latest APIs and best practices
- ✅ Consider long-term maintainability
- ❌ Don't rush to "make it work" without considering "make it right"

The goal is building a **robust, extensible personal assistant platform**, not just a demo.

Every architectural decision today affects what's possible tomorrow.
