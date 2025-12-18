# JEX Architecture Explanation - Phase 1 Implementation

## Your Question: What is it doing at the moment?

**Short Answer:**
- Yes, it's using the LLM (OpenAI GPT-4o-mini) to figure out what to say
- Yes, the conversation is kept in the middleware (Python agent)
- **Nothing is persistent** - when you disconnect, the conversation history is lost

---

## Detailed Flow: What Happens When You Speak

### 1. **Voice Input (Browser → LiveKit Cloud)**
```
You speak → Browser captures audio → Sent to LiveKit Cloud via WebRTC
```
- Your microphone in the browser captures your voice
- Audio is sent in real-time to LiveKit's cloud servers
- **No processing happens in the browser** - it's just audio capture

### 2. **Speech-to-Text (LiveKit Cloud → Deepgram)**
```
LiveKit Cloud → Python Agent receives audio → Deepgram STT converts to text
```
- The Python agent (middleware) receives your audio stream
- **Silero VAD** (Voice Activity Detection) detects when you stop speaking
- Audio is sent to **Deepgram** API which converts it to text
- Text transcript: "Hello JEX, how are you?"

### 3. **LLM Processing (Python Agent)**
```
Text → OpenAI GPT-4o-mini → Response text
```

**This is where the "thinking" happens:**

The agent maintains a **chat context** (conversation history) that includes:
- **System instructions** (from `JexAgent.__init__()` in main.py:46-63)
- **All previous messages** in the current session
- **Your new message**

The chat context looks like this:
```python
[
  {"role": "system", "content": "You are JEX, a personal voice assistant..."},
  {"role": "assistant", "content": "Hello! I'm JEX..."},  # Initial greeting
  {"role": "user", "content": "Hello JEX, how are you?"},  # Your message
]
```

This is sent to OpenAI's API which returns:
```python
{"role": "assistant", "content": "I'm doing great, thank you for asking! How can I help you today?"}
```

### 4. **Text-to-Speech (Python Agent → OpenAI)**
```
Response text → OpenAI TTS (voice: alloy) → Audio
```
- The LLM's text response is sent to **OpenAI TTS**
- TTS converts it to audio using the "alloy" voice
- Audio is streamed back to the agent

### 5. **Voice Output (Python Agent → Browser)**
```
Audio → LiveKit Cloud → Browser speakers
```
- Audio is sent through LiveKit Cloud to your browser
- You hear JEX speaking!

---

## Where is the Conversation Stored?

### Current Implementation (Phase 1):

**Location:** `AgentSession` object in Python agent (middleware)
**File:** `agent/main.py:99-104`

```python
session = AgentSession(
    vad=vad,
    stt=stt,
    llm=llm,
    tts=tts,
)
```

The `AgentSession` maintains:
- ✅ **Chat context** (conversation history) - in memory
- ✅ **Agent state** (listening, thinking, speaking)
- ✅ **Audio buffers** for streaming

**Storage Type:** **In-Memory Only**
- Conversation lives in the Python process's RAM
- When you disconnect, it's **gone forever**
- When the agent restarts, it's **gone forever**
- No database, no file storage, nothing persistent

---

## What's NOT Happening (Yet):

### ❌ No Local Storage
- No SQLite database
- No Redis cache
- No file storage

### ❌ No n8n Integration
- Agent can't check emails
- Agent can't access calendar
- Agent can't call external APIs

### ❌ No Artifact Panel
- No visual display of data
- Just voice conversation

### ❌ No Context Persistence
- Every new connection = fresh start
- No memory of previous conversations

---

## Architecture Diagram: Current Phase 1

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Frontend)                    │
│  ┌────────────────────────────────────────────────────┐ │
│  │  VoiceAgent.tsx                                    │ │
│  │  - Captures microphone audio                       │ │
│  │  - Shows state (listening/thinking/speaking)       │ │
│  │  - Plays audio from agent                          │ │
│  └────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────┘
                        │ WebRTC (Audio streaming)
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  LiveKit Cloud                           │
│  - Routes audio between browser and agent                │
│  - Manages real-time connection                          │
└───────────────────────┬─────────────────────────────────┘
                        │ WebSocket
                        ▼
┌─────────────────────────────────────────────────────────┐
│           Python Agent (Middleware) - LOCAL              │
│  ┌────────────────────────────────────────────────────┐ │
│  │  AgentSession (IN-MEMORY)                          │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │ Chat Context (Conversation History)          │ │ │
│  │  │ [                                             │ │ │
│  │  │   {role: "system", content: "You are JEX..."} │ │ │
│  │  │   {role: "assistant", content: "Hello!"}     │ │ │
│  │  │   {role: "user", content: "How are you?"}    │ │ │
│  │  │   {role: "assistant", content: "Great!"}     │ │ │
│  │  │ ]                                             │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────┘ │
│                                                           │
│  Voice Pipeline:                                         │
│  Audio → VAD (Silero) → STT → LLM → TTS → Audio        │
└───────────────────────┬─────────┬───────┬────────────────┘
                        │         │       │
                        ▼         ▼       ▼
                    ┌────────┐ ┌──────┐ ┌──────┐
                    │Deepgram│ │OpenAI│ │OpenAI│
                    │  STT   │ │ LLM  │ │ TTS  │
                    └────────┘ └──────┘ └──────┘
                    (Cloud)   (Cloud)  (Cloud)
```

---

## Key Implementation Details

### 1. Chat Context Management

**File:** LiveKit Agents SDK (internal)
**Managed by:** `AgentSession` class

When you speak, the SDK:
1. Appends your message to the chat context
2. Sends entire context to OpenAI
3. Gets response
4. Appends response to chat context
5. Converts to speech

**Context Window:**
- OpenAI GPT-4o-mini supports **128k tokens** (~96k words)
- In practice, conversations are much shorter
- No automatic truncation in Phase 1

### 2. State Synchronization

**Browser ↔ Agent:**
- Browser shows state based on `useVoiceAssistant()` hook
- Hook listens to LiveKit events from the agent
- Agent broadcasts state changes through LiveKit

States:
- `listening` - VAD detected you might speak
- `thinking` - STT sent text, waiting for LLM
- `speaking` - TTS playing audio

### 3. No Tools/Functions Yet

In Phase 1, the agent **only has instructions**, no function tools:

```python
class JexAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""...""",  # ✅ Only this
            # tools=[]  # ❌ Not yet - Phase 2
        )
```

The agent can only:
- Answer questions using LLM knowledge
- Have conversations
- Tell jokes
- Explain concepts

**Cannot:**
- Check your real emails
- Access your real calendar
- Control anything external

---

## What Changes in Phase 2?

### Adding n8n + Function Tools:

```python
class JexAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""...""",
            tools=[read_emails, check_calendar, get_weather],  # ← NEW
        )
```

**New flow:**
1. You: "Check my emails"
2. LLM recognizes intent → calls `read_emails()` function
3. Function makes HTTP call to n8n webhook
4. n8n workflow connects to Gmail API
5. n8n returns email data
6. Agent receives data, adds to chat context
7. LLM generates natural response about emails
8. Agent sends visual data to browser via LiveKit data channel
9. Artifact panel shows emails visually

### Adding Persistence (Optional):

**Option 1: Session-based (temporary)**
```python
# Store in agent's userdata
ctx.userdata["conversation_history"] = messages
```
- Survives disconnects within same session
- Lost when agent restarts

**Option 2: SQLite (persistent)**
```python
# Save to database
db.save_conversation(user_id, messages)
```
- Survives everything
- Can resume conversations across sessions

---

## Summary: Current State

| Component | Current Status | Storage |
|-----------|---------------|---------|
| Voice I/O | ✅ Working | Streamed (not stored) |
| Speech-to-Text | ✅ Deepgram | Not stored |
| LLM Processing | ✅ OpenAI GPT-4o-mini | Not stored |
| Text-to-Speech | ✅ OpenAI TTS | Not stored |
| Chat Context | ✅ In AgentSession | RAM only (lost on disconnect) |
| Function Tools | ❌ Not yet | N/A |
| n8n Integration | ❌ Not yet | N/A |
| Artifact Panel | ❌ Not yet | N/A |
| Persistent Storage | ❌ Not yet | N/A |

**Current Capabilities:**
- General conversation
- Question answering
- Explanations
- Jokes and casual chat

**Cannot Do (Yet):**
- Access real data (emails, calendar, etc.)
- Execute actions
- Remember across sessions
- Show visual information

---

## Next: Phase 2 Planning

When ready for Phase 2, we'll implement:
1. n8n workflow integration
2. Function tools for real actions
3. Artifact panel for visual data
4. Optional: conversation persistence

---

## File References

Key files in current implementation:
- `agent/main.py` - Agent entrypoint and JexAgent class
- `agent/config.py` - Configurable LLM/STT/TTS factory
- `webapp/components/VoiceAgent.tsx` - Frontend voice interface
- `webapp/app/api/token/route.ts` - LiveKit token generation
