"""
JEX - Personal Voice Agent
Phase 1: Basic conversational voice agent using LiveKit
"""

import logging
import random
import asyncio
import os
import time
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
from tools import read_emails, read_calendar, recall_context, get_weather, search_x_feed, preload_all_x_feeds, schedule_x_feed_preload, check_task_status, load_x_profiles

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
            - **X.com Integration - Trending & Interesting Content:**
              * X.com is your source for TRENDING and INTERESTING content (what people are discussing)
              * NOT for generic "news" queries (save those for future news APIs)
              * Multiple search profiles available (AI_Tech, Climate_Tech, Startup_News)

              * **Implicit "Trending/Interesting" Queries** (NO explicit mention of "X"):
                - "What's trending?" → FIRST: recall_context('x_feed:AI_Tech'), if exists use it, else search_x_feed()
                - "Anything interesting?" / "What's interesting?" → Same as above
                - "What are people talking about?" → Same as above
                - Strategy: Check cache first, only fetch if stale/missing
                - Response: "Here's what's trending..." or "Here's what people are talking about..."

              * **Do NOT use X.com for generic news**:
                - "What's the news?" → Don't call X.com (respond: "I don't have a news source yet, but I can show you what's trending on X if you'd like")
                - "Latest headlines?" → Don't call X.com
                - "Breaking news about <topic>?" → Don't call X.com

              * **Explicit X Queries** (always work):
                - "What's trending on X?" → search_x_feed(profile_name="AI_Tech") for default
                - "What about climate tech on X?" → search_x_feed(profile_name="Climate_Tech")
                - "Search X for <topic>" → search_x_feed(search_keywords="<topic>")

              * **Technical Notes**:
                - First call fetches fresh (may take 30-60 seconds for search + ranking)
                - Follow-ups: recall_context('x_feed:AI_Tech') for instant responses
                - "Refresh X feed" → search_x_feed(force_refresh=True)
                - Response style: Mention data freshness, highlight engagement metrics

              * **Pre-loading for Speed**:
                - **Background (Recommended)**: "Pre-load all X feeds" → schedule_x_feed_preload()
                  * Returns IMMEDIATELY (non-blocking)
                  * Task runs in background (~30-60s)
                  * JEX will proactively announce when done
                  * User can ask other questions while waiting
                - **Blocking**: "Pre-load all X feeds now" → preload_all_x_feeds()
                  * Waits for completion (~30-60s)
                  * User must wait, but gets immediate confirmation
                  * Use only if user wants to wait
                - **Status Check**: "Check task status" → check_task_status(task_id)
                  * Usually not needed - JEX announces completion automatically

            # BACKGROUND TASK SYSTEM
            - **Proactive Announcements**:
              * JEX will automatically announce when background tasks complete
              * Example: "All X feeds are loaded! You can now ask about trending topics."
              * User doesn't need to ask - JEX speaks up when done
            - **No Phantom Tools:** Do not mention checking data unless Adeel asked for it.
            """,
            tools=[read_emails, read_calendar, recall_context, get_weather, search_x_feed, preload_all_x_feeds, schedule_x_feed_preload, check_task_status],
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

        # 4. Auto-preload X feeds if enabled
        if os.getenv("X_AUTO_PRELOAD_ON_STARTUP", "false").lower() == "true":
            logger.info("Auto-preloading X feeds on startup")
            await self.session.say("Pre-loading X feeds for you...", allow_interruptions=False)

            # Call the preload tool
            result = await preload_all_x_feeds()

            # Announce completion (brief)
            await self.session.say("All feeds ready.", allow_interruptions=True)


async def x_feed_background_refresh(last_fetch_times: dict):
    """
    Periodically refresh X feeds for ALL configured profiles.
    Only runs if X_BACKGROUND_REFRESH_ENABLED=true.

    Args:
        last_fetch_times: Shared dict to track when each profile was last fetched
                          Format: {profile_name: timestamp}
    """
    interval_minutes = int(os.getenv("X_REFRESH_INTERVAL_MINUTES", "180"))
    interval_seconds = interval_minutes * 60
    initial_delay = int(os.getenv("X_INITIAL_DELAY_SECONDS", "60"))

    logger.info(f"X background refresh: first fetch in {initial_delay}s, then every {interval_minutes} min")

    try:
        await asyncio.sleep(initial_delay)

        # Load profiles
        profiles = load_x_profiles()
        if not profiles:
            logger.warning("No X search profiles configured, background refresh disabled")
            return

        logger.info(f"Background refresh will monitor {len(profiles)} profiles: {list(profiles.keys())}")

        while True:
            for profile_name, profile in profiles.items():
                # Check if this profile was recently refreshed by user
                last_fetch = last_fetch_times.get(profile_name, 0)
                elapsed = time.time() - last_fetch

                if elapsed < interval_seconds:
                    remaining = (interval_seconds - elapsed) / 60
                    logger.info(f"Profile '{profile_name}' recently refreshed, skipping ({remaining:.1f} min remaining)")
                    continue

                try:
                    logger.info(f"Background: Fetching X feed for profile '{profile_name}'...")
                    await search_x_feed(profile_name=profile_name, force_refresh=False)
                    last_fetch_times[profile_name] = time.time()
                    logger.info(f"Background: Profile '{profile_name}' refreshed successfully")
                except Exception as e:
                    logger.error(f"Background refresh failed for profile '{profile_name}': {e}")

            # Wait for next interval
            logger.info(f"Background: All profiles refreshed. Next cycle in {interval_minutes} min.")
            await asyncio.sleep(interval_seconds)

    except asyncio.CancelledError:
        logger.info("Background X feed refresh task canceled")
        raise


async def announcement_poller(session: AgentSession):
    """Poll for announcements and deliver via voice"""
    from context_store import get_context_store

    store = get_context_store()
    logger.info("Announcement poller started")

    while True:
        try:
            # Check for pending announcements
            announcements = store.get_pending_announcements()

            for ann in announcements:
                try:
                    logger.info(f"Announcing: {ann['message']}")

                    # Deliver via voice
                    await session.say(ann['message'], allow_interruptions=True)

                    # Mark as delivered
                    store.mark_announced(ann['announcement_id'])

                except Exception as e:
                    logger.error(f"Failed to announce {ann['announcement_id']}: {e}")

            # Poll every 5 seconds
            await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("Announcement poller cancelled")
            raise
        except Exception as e:
            logger.error(f"Announcement poller error: {e}", exc_info=True)
            await asyncio.sleep(10)  # Back off on error


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

        # Shared state for timer reset (per-profile)
        last_fetch_times = {}  # {profile_name: timestamp}

        # Launch background tasks
        background_tasks = []

        # NEW: Task processor (independent of session)
        from task_processor import task_processor_loop
        task_processor = asyncio.create_task(task_processor_loop())
        background_tasks.append(task_processor)
        logger.info("Task processor launched")

        # NEW: Announcement poller (tied to session for voice delivery)
        announce_poller = asyncio.create_task(announcement_poller(session))
        background_tasks.append(announce_poller)
        logger.info("Announcement poller launched")

        # EXISTING: X feed background refresh (if enabled)
        if os.getenv("X_BACKGROUND_REFRESH_ENABLED", "false").lower() == "true":
            x_refresh_task = asyncio.create_task(
                x_feed_background_refresh(last_fetch_times)
            )
            background_tasks.append(x_refresh_task)
            logger.info("X feed background refresh enabled")

        try:
            # Start agent session (blocking)
            await session.start(agent=JexAgent(), room=ctx.room)
            logger.info("JEX agent session started successfully")
        finally:
            # Cleanup: cancel background tasks when session ends
            logger.info("Session ending, canceling background tasks...")
            for task in background_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            logger.info("Background tasks canceled")

    except Exception as e:
        logger.error(f"Error starting agent: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Run the agent using LiveKit CLI
    cli.run_app(server)
