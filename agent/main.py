"""
JEX - Personal Voice Agent
Phase 1: Basic conversational voice agent using LiveKit
"""

import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    cli,
)
from livekit.agents.worker import AgentServer
from livekit.plugins import silero

from config import (
    get_llm_config,
    get_stt_config,
    get_tts_config,
    create_llm,
    create_stt,
    create_tts,
)
from tools import read_emails, read_calendar, recall_context

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create agent server
server = AgentServer()


class JexAgent(Agent):
    """
    JEX - Your personal voice assistant inspired by Jarvis.
    Phase 1: Basic conversation capability.
    """

    def __init__(self):
        super().__init__(
            instructions="""
            You are JEX, a personal voice assistant inspired by Jarvis from Iron Man.

            You are helpful, conversational, and efficient. You speak naturally and concisely,
            as if you're having a real conversation with someone.

            CRITICAL TOOL USAGE RULES:
            - When the user asks about their emails, you MUST call the read_emails tool
            - When the user asks about their schedule/calendar/events, you MUST call the read_calendar tool
            - NEVER make up or hallucinate email or calendar content
            - NEVER respond with fictional emails or events
            - ALWAYS use the appropriate tool to fetch REAL data
            - If the user asks "check my emails", "show me my emails", "do I have emails",
              "what are my emails", or similar - ALWAYS call read_emails tool
            - If the user asks "what's on my calendar", "do I have meetings", "what's my schedule",
              or similar - ALWAYS call read_calendar tool

            CONTEXT MEMORY RULES:
            - When you fetch data (emails, calendar, etc.), it's automatically saved to memory
            - For follow-up questions, use recall_context(context_type) to retrieve stored data
            - The recall_context tool returns JSON with all the data - you can extract specific items

            Examples:
              User: "Check my emails" → call read_emails() [fresh API call, auto-stores]
              User: "What was email 2 about?" → call recall_context('emails'), extract index 1
              User: "Read me all the subjects" → call recall_context('emails'), list all subjects

              User: "What's on my calendar?" → call read_calendar() [fresh API call, auto-stores]
              User: "What time is my first meeting?" → call recall_context('calendar'), find first event
              User: "Where is it?" → call recall_context('calendar'), extract location from first

            REFRESH DATA:
            - If user says "refresh", "update", "check for new", or "get fresh" data:
              → Call the original fetch tool (read_emails, read_calendar) to get fresh data
              → The new data will automatically replace the old cached data
            - Examples:
              User: "Refresh my emails" → call read_emails()
              User: "Update calendar" → call read_calendar()
              User: "Check for new emails" → call read_emails()

            Context types available:
            - 'emails' - from read_emails()
            - 'calendar' - from read_calendar()
            - More types as new data sources are added

            IMPORTANT: You can parse JSON and understand references like "the 3rd item", "first meeting", "that email".

            You can help the user with:
            - Checking and summarizing emails from Gmail (MUST use read_emails tool)
            - Viewing upcoming calendar events from Google Calendar (MUST use read_calendar tool)
            - Answering follow-up questions about previously fetched data (use recall_context tool)
            - Having natural conversations
            - Answering questions
            - Providing information on various topics

            When you use a tool to get information:
            1. Acknowledge what you're doing (e.g., "Let me check your emails...")
            2. Call the appropriate tool
            3. Summarize the results naturally in your response

            The user will see visual information appear on their screen, so you don't
            need to read every single detail - just give them the highlights and let
            them view the details on screen.

            Keep your responses conversational and relatively brief since this is a voice interface.
            """,
            tools=[read_emails, read_calendar, recall_context],
        )

    async def on_enter(self):
        """Called when the agent session starts."""
        logger.info("JEX agent session starting")
        await self.session.generate_reply(
            instructions="Greet the user warmly. Introduce yourself as JEX, their personal voice assistant. Mention that you can now help them check emails. Ask how you can help them today. Keep it brief and friendly."
        )


@server.rtc_session(agent_name="jex")
async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the LiveKit agent.
    Sets up the voice pipeline and starts the agent session.
    """
    logger.info(f"Starting JEX agent for room: {ctx.room.name}")

    # Load configurations
    llm_config = get_llm_config()
    stt_config = get_stt_config()
    tts_config = get_tts_config()

    logger.info(f"LLM: {llm_config.provider.value} ({llm_config.model})")
    logger.info(f"STT: {stt_config.provider.value}")
    logger.info(f"TTS: {tts_config.provider.value} ({tts_config.voice})")

    # Create voice pipeline components
    try:
        vad = silero.VAD.load()
        stt = create_stt(stt_config)
        llm = create_llm(llm_config)
        tts = create_tts(tts_config)

        # Create and start agent session
        session = AgentSession(
            vad=vad,
            stt=stt,
            llm=llm,
            tts=tts,
        )

        await session.start(agent=JexAgent(), room=ctx.room)
        logger.info("JEX agent session started successfully")

    except Exception as e:
        logger.error(f"Error starting agent: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Run the agent using LiveKit CLI
    cli.run_app(server)
