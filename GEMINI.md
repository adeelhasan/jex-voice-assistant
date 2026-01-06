# GEMINI.md - Developer's Guide to the JEX Project

## 1. Project Synthesis

**JEX** is a real-time, voice-first personal assistant. It combines a web-based frontend with a powerful Python agent backend, enabling natural language conversations to perform tasks like checking emails, managing calendars, getting weather forecasts, and providing trending X.com content. It also features a robust background task management system with proactive user announcements.

**Core Technologies:**
- **Frontend**: Next.js 15, React 19, Tailwind CSS
- **Backend**: Python 3.11+ with `livekit-agents`
- **Real-time Engine**: LiveKit Cloud (handles WebRTC signaling and data)
- **AI Pipeline**:
    - **STT**: Deepgram (configurable)
    - **LLM**: OpenAI GPT-4o-mini (configurable)
    - **TTS**: OpenAI (configurable)
- **Task Execution**: n8n for external API integrations (Gmail, Google Calendar, Weather, X.com)
- **Contextual Memory**: SQLite for short-term conversation memory, background task state, and proactive announcements.

**Current Project Status (Completed):**
- **Phase 1: Voice Foundation**: Core conversational loop is stable.
- **Phase 2: Email Integration**: Can read and display Gmail messages.
- **Phase 3: Calendar Integration**: Can read and display Google Calendar events.
- **Phase 4: Context Management**: Remembers previously fetched data for follow-up questions.
- **Phase 5: Weather Integration**: Provides 7-day weather forecasts with intelligent caching.
- **Phase 6: X.com Integration & Background Task Management**: Trending content search, proactive pre-loading of feeds, and intelligent announcements for background task completion.

## 2. Core Architectural Principles

This project prioritizes clean, extensible architecture. Adherence to these principles is critical for long-term success.

### Principle 1: Trust the LLM, Abstract the Tools

We do not build complex logic for parsing user intent (e.g., "what's the second email?"). Instead, we:
1.  **Fetch structured data** using simple, robust tools.
2.  **Store this data** in a short-term `ContextStore`.
3.  **Provide a `recall_context` tool** that feeds this stored data back to the LLM.
4.  **Instruct the LLM** to use `recall_context` for follow-up questions.

This keeps our tools simple and delegates complex natural language understanding to the component best suited for it.

**Example (`agent/tools.py`):**
- `read_emails()` fetches emails and **auto-saves** them to the `ContextStore`.
- `recall_context('emails')` retrieves the saved emails as a JSON blob.
- The LLM receives the JSON and can answer "what was the subject of the third email?".

### Principle 2: Abstraction for Flexibility

All external services are abstracted to allow for interchangeability.
- **AI Services (`agent/config.py`)**: A factory pattern (`create_llm`, `create_stt`, `create_tts`) allows swapping providers (e.g., OpenAI for Anthropic) via environment variables.
- **Context Storage (`agent/context_store.py`)**: The `ContextStore` uses SQLite but is designed as a class that could be subclassed to support Redis or other backends without changing the core tool logic.
- **Tooling**: Tools call a generic `call_n8n_workflow` function, not `fetch_gmail` directly. This decouples the tool's purpose from its execution mechanism.

### Principle 3: Data Flow is Unidirectional and Explicit

1.  **User Speaks**: Audio is streamed to the Python agent via LiveKit.
2.  **Agent Processes**: The STT->LLM->TTS pipeline runs.
    - If a tool is called (e.g., `read_emails`), the agent calls the n8n webhook.
3.  **Agent Responds**:
    - **Voice**: TTS audio is streamed back to the frontend.
    - **Data**: Any visual data (the "artifact") is sent to the frontend via a separate LiveKit `DataChannel`.
4.  **Frontend Renders**:
    - The `RoomAudioRenderer` plays the agent's voice.
    - The `ArtifactPanel.tsx` component listens for data packets and renders the corresponding UI (e.g., a list of emails).

This separation ensures that voice and visual information are managed independently but are presented in a synchronized manner.

## 3. Filesystem Quick Reference

```
jarivsalexa/
├── agent/                      # PYTHON BACKEND
│   ├── main.py                # Agent entrypoint, personality, and tool registration.
│   ├── tools.py               # All function tools (read_emails, get_weather, X.com search, etc.). PRIMARY BUSINESS LOGIC.
│   ├── context_store.py       # SQLite-based short-term memory, background task storage, and proactive announcements.
│   ├── task_processor.py      # Background task processing loop for asynchronous operations.
│   ├── config.py              # Configuration for LLM, STT, TTS providers.
│   ├── requirements.txt       # Python dependencies.
│   └── .env.example           # Required environment variables.
│
├── webapp/                     # NEXT.JS FRONTEND
│   ├── app/page.tsx           # Main React component.
│   ├── components/
│   │   ├── VoiceAgent.tsx     # Handles LiveKit connection and displays agent state.
│   │   └── ArtifactPanel.tsx  # Renders visual data (emails, calendar, weather, X.com threads).
│   ├── app/api/
│   │   ├── token/route.ts   # Generates LiveKit auth tokens.
│   └── package.json           # Node dependencies.
│
├── docs/                       # Detailed documentation.
├── n8n-workflows/              # Exported JSON for n8n email/calendar workflows.
├── CLAUDE.md                   # Original detailed guide.
├── GEMINI.md                   # This guide.
└── SETUP.md                    # Quick-start commands.
```

## 4. How to Extend JEX with a New Tool (e.g., "Search Hacker News")

This is the primary development loop.

### Step 1: Create the n8n Workflow

- Create a new n8n workflow that accepts a `query: string` via a webhook.
- The workflow should call the Hacker News API, format the results into a clean JSON structure, and generate a human-readable summary sentence.
- **Crucially**, the workflow must return a JSON object with two keys:
    - `speech`: "I found 5 top stories on Hacker News about 'AI'."
    - `artifact`: `{ "type": "hackernews_stories", "data": [...] }`

### Step 2: Implement the Python Tool

In `agent/tools.py`, create a new async function.

```python
# agent/tools.py
from livekit.agents import function_tool
from .context_store import get_context_store
from .utils import call_n8n_workflow, send_artifact_to_frontend

@function_tool(
    name="search_hacker_news",
    description="Searches for top stories on Hacker News matching a query."
)
async def search_hacker_news(query: str) -> str:
    """
    Fetches top stories from Hacker News.
    """
    # Call the n8n workflow you created.
    result = await call_n8n_workflow("hacker-news-search", {"query": query})

    # Auto-save the data for potential follow-up questions.
    store = get_context_store()
    store.save(
        context_type='hackernews',
        data=result["artifact"]["data"],
        metadata={'query': query}
    )

    # Send the artifact to the frontend for display.
    await send_artifact_to_frontend(result["artifact"])

    # Return the speech response for the TTS engine.
    return result["speech"]
```

### Step 3: Register the New Tool

In `agent/main.py`, add your new tool to the `tools` list in the `JexAgent` constructor.

```python
# agent/main.py
from .tools import read_emails, read_calendar, get_weather, recall_context, search_hacker_news # 1. Import

class JexAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="Your instructions...",
            tools=[
                read_emails,
                read_calendar,
                get_weather,
                recall_context,
                search_hacker_news, # 2. Register
            ],
        )
```

### Step 4: Create the Frontend Component

In `webapp/components/ArtifactPanel.tsx`, create a renderer for the new artifact type.

```typescript
// webapp/components/ArtifactPanel.tsx

// 1. Define the data structure
interface HackerNewsStory {
  title: string;
  url: string;
  points: number;
}

// 2. Create the renderer component
const HackerNewsList: React.FC<{ stories: HackerNewsStory[] }> = ({ stories }) => (
  <div>
    <h3 className="text-lg font-semibold mb-2">Hacker News Stories</h3>
    {stories.map((story, index) => (
      <div key={index} className="p-2 border-b">
        <a href={story.url} target="_blank" rel="noopener noreferrer">{story.title}</a>
        <p>{story.points} points</p>
      </div>
    ))}
  </div>
);

// 3. Add it to the main ArtifactRenderer switch statement
const ArtifactRenderer: React.FC<{ artifact: Artifact }> = ({ artifact }) => {
  switch (artifact.type) {
    // ... other cases
    case 'hackernews_stories':
      return <HackerNewsList stories={artifact.data} />;
    default:
      return <pre>{JSON.stringify(artifact.data, null, 2)}</pre>;
  }
};
```

### Step 5: Test

1.  Run the agent and frontend (`python main.py dev` and `npm run dev`).
2.  Say, "Search Hacker News for 'prompt engineering'."
3.  **Verify**:
    - The agent speaks the summary response.
    - The `ArtifactPanel` displays the list of stories.
    - The agent logs show the tool call and context storage.
4.  Ask a follow-up: "What was the score of the first one?"
5.  **Verify**:
    - The agent calls `recall_context('hackernews')`.
    - The agent answers correctly without hitting the n8n workflow again.

## 5. Critical Development Notes

- **Environment Variables are Key**: The entire application is configured via `.env` and `.env.local`. Ensure they are correctly populated. Missing variables are a common source of errors.
- **Test n8n Workflows Independently**: Use `curl` or a tool like Postman to test your n8n webhooks before integrating them with the agent. This isolates issues with the workflow itself from issues with the agent's tool-calling logic.
- **Use the Dev Tools**: The LiveKit dashboard, browser console, and agent terminal logs are your primary debugging tools. Use them to trace the flow of data and identify where a breakdown occurs.
- **Follow the Pattern**: When adding functionality, follow the established architecture. Resist the urge to add one-off solutions. The patterns (Tool -> n8n -> ContextStore -> Artifact) are designed for scalability.
