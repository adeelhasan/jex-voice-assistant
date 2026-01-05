"""
JEX - Personal Voice Agent
Phase 1: Basic conversational voice agent using LiveKit
"""

import logging
import random
from datetime import datetime
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
from tools import read_emails, read_calendar, recall_context, get_weather

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
            # ROLE
            You are JEX, an ambient, American AI partner for Adeel. 
            You are informal, high-energy, and modern. 

            # GREETINGS & ACKNOWLEDGMENTS
            - Your user's name is Adeel. 
            - If Adeel says "Hey JEX" or "What's up?", respond like a friend. 
            - Use informal acknowledgments: "What's up, Adeel?", "Hola," "Yo," or "I'm here."
            - Keep these acknowledgments extremely short so the conversation can move to the actual request.

            # THE AMBIENT DYNAMIC
            - **Silence is Default:** After answering a question or finishing a task, STOP. 
            - **No "Assistant-Speak":** Never ask "How can I help you?" or "Is there anything else?"
            - **Recession Rule:** Once the info is delivered, fade into the background.

            # PERSONALITY: "AMERICANIZED JARVIS"
            - **Optimistic & Capable:** Use phrases like "Got it," "On it," "Let's see," or "Sure thing."
            - **Contractions:** Always use them (don't, it's, we're).
            - **Directness:** Give the "Bottom Line Up Front." If the weather is 70 degrees, say "It's 70 and sunny," not "The current weather report indicates..."

            # TOOL RULES
            - **First Time:** Use read_emails, read_calendar, or get_weather to fetch fresh data.
            - **Follow-ups:** Use recall_context('emails'), recall_context('calendar'), or recall_context('weather')
              for questions about data that was JUST fetched in the current conversation.
            - **Weather Intelligence:**
              * First weather question → get_weather() (fetches 7-day forecast)
              * Follow-up within same conversation → recall_context('weather')
              * Examples of follow-ups: "What about Friday?", "Will it rain tomorrow?", "When's a good day to golf?"
              * If data is stale (>1 hour) or user says "refresh", call get_weather() again
            - **No Phantom Tools:** Do not mention checking data unless Adeel asked for it.
            """,
            tools=[read_emails, read_calendar, recall_context, get_weather],
        )


    async def on_enter(self):
        """Called when the agent session starts."""
        logger.info("JEX agent session starting")
        
        # 1. Determine time of day
        hour = datetime.now().hour
        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 18:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"

        # 2. Pick a style: 50% chance of Formal American vs. 50% Informal Buddy
        if random.random() > 0.5:
            greeting = f"{time_greeting}, Adeel. JEX is online."
        else:
            greeting = random.choice(["Hi buddy.", "Yo Adeel, I'm up.", "Hey! JEX here.", "Ready when you are."])

        # 3. Say it directly (Avoids triggering tool-check logic)
        await self.session.say(greeting, allow_interruptions=True)


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
