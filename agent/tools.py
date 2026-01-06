"""
Function tools for JEX agent.
These functions are callable by the LLM to perform actions via n8n workflows.
"""

import os
import json
import httpx
import asyncio
import logging
from typing import Optional
from livekit.agents import function_tool, get_job_context
from context_store import get_context_store

# n8n Configuration
N8N_WEBHOOK_BASE_URL = os.getenv("N8N_WEBHOOK_BASE_URL", "")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


async def call_n8n_workflow(endpoint: str, payload: dict, timeout: float = 30.0) -> dict:
    """
    Call an n8n webhook workflow and return the response.

    Args:
        endpoint: Workflow endpoint path (e.g., "read-emails") OR full webhook ID
        payload: Data to send to the workflow
        timeout: HTTP request timeout in seconds (default: 30s)

    Returns:
        Response from n8n with 'speech' and 'artifact' fields
    """
    import logging
    logger = logging.getLogger(__name__)

    # Check if endpoint is a full webhook ID (UUID format: 36 chars with dashes)
    if len(endpoint) == 36 and '-' in endpoint:
        # External webhook - use full architoon URL
        url = f"https://architoon.app.n8n.cloud/webhook/{endpoint}"
    else:
        # Local n8n instance
        url = f"{N8N_WEBHOOK_BASE_URL}/{endpoint}"

    logger.info(f"=== CALLING N8N WORKFLOW ===")
    logger.info(f"URL: {url}")
    logger.info(f"Payload: {payload}")
    logger.info(f"Timeout: {timeout}s")

    headers = {
        "Content-Type": "application/json",
        "X-JEX-API-Key": N8N_API_KEY
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            logger.info(f"Sending POST request to n8n...")
            response = await client.post(
                url,
                json=payload,
                headers=headers
            )
            logger.info(f"Response status: {response.status_code}")
            response.raise_for_status()

            result = response.json()
            logger.info(f"Response data: {result}")
            logger.info(f"=== N8N WORKFLOW COMPLETE ===")
            return result
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error calling n8n: {e}")
            logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            return {
                "speech": f"I had trouble connecting to that service: {str(e)}",
                "artifact": None
            }
        except Exception as e:
            logger.error(f"Exception calling n8n: {e}", exc_info=True)
            return {
                "speech": f"An error occurred: {str(e)}",
                "artifact": None
            }


async def send_artifact_to_frontend(artifact: dict):
    """
    Send artifact data to the frontend via LiveKit data channel.

    Args:
        artifact: Artifact data to send (type + data)
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(">>> SEND_ARTIFACT_TO_FRONTEND CALLED <<<")

    # Get job context (contains room)
    try:
        job_ctx = get_job_context()
        logger.info("✅ Job context obtained")
    except RuntimeError as e:
        logger.error(f"❌ Cannot get job context: {e}")
        return

    room = job_ctx.room
    logger.info(f"Room available: {room is not None}")

    if not room:
        logger.error("❌ No room in job context!")
        return

    logger.info(f"Artifact type: {artifact.get('type')}")
    logger.info(f"Artifact data length: {len(artifact.get('data', []))}")

    message = json.dumps({
        "type": "artifact",
        "data": artifact
    })

    logger.info(f"Message to send: {message[:200]}...")  # First 200 chars
    logger.info(f"Message size: {len(message)} bytes")

    try:
        await room.local_participant.publish_data(
            payload=message.encode('utf-8'),
            reliable=True
        )
        logger.info("✅ Artifact data published successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to publish artifact data: {e}", exc_info=True)


@function_tool()
async def read_emails(count: int = 5, filter: str = "unread") -> str:
    """
    Fetch and read the user's ACTUAL emails from their Gmail inbox.
    This tool MUST be called whenever the user asks about their emails.
    DO NOT make up or hallucinate email content - always call this tool.

    Args:
        count: Number of emails to retrieve (1-20)
        filter: Filter type - "unread", "all", or "important"

    Returns:
        Summary of emails for voice response
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"@@@ READ_EMAILS TOOL CALLED @@@")
    logger.info(f"Parameters: count={count}, filter={filter}")

    # Call n8n workflow
    result = await call_n8n_workflow("read-emails", {
        "count": min(count, 20),
        "filter": filter
    })

    logger.info(f"Tool result speech: {result.get('speech', 'No speech')}")

    # Send artifact to frontend if available
    if result.get("artifact"):
        logger.info(f"Sending artifact to frontend: {result['artifact'].get('type')}")
        await send_artifact_to_frontend(result["artifact"])

        # NEW: Auto-store for follow-up queries
        if result["artifact"].get("data"):
            store = get_context_store()
            store.save(
                context_type='emails',
                data=result["artifact"]["data"],
                metadata={'count': count, 'filter': filter}
            )
            logger.info(f"Stored {len(result['artifact']['data'])} emails in context")
    else:
        logger.warning("No artifact in result")

    logger.info(f"@@@ READ_EMAILS TOOL COMPLETE @@@")
    return result.get("speech", "I couldn't retrieve your emails right now.")


@function_tool()
async def read_calendar(days: int = 7) -> str:
    """
    Fetch and display the user's upcoming calendar events from Google Calendar.
    This tool MUST be called whenever the user asks about their schedule or calendar.
    DO NOT make up or hallucinate calendar events - always call this tool.

    Args:
        days: Number of days ahead to check for events (1-30, default 7)

    Returns:
        Summary of calendar events for voice response
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"@@@ READ_CALENDAR TOOL CALLED @@@")
    logger.info(f"Parameters: days={days}")

    # Call n8n workflow
    # Note: The workflow expects "numberOfDays" parameter
    result = await call_n8n_workflow(
        endpoint="8e8472c0-6c4e-47b9-9602-0a0cc2221453",  # Calendar webhook ID
        payload={"numberOfDays": min(days, 30)}
    )

    logger.info(f"Tool result: {result}")

    # The n8n workflow returns a dict with summary, eventCount, and events
    if isinstance(result, dict):
        summary = result.get("summary", "No events found.")
        events = result.get("events", [])

        # Send artifact to frontend if events exist
        if events:
            artifact = {
                "type": "calendar_events",
                "data": events
            }
            logger.info(f"Sending {len(events)} calendar events to frontend")
            await send_artifact_to_frontend(artifact)

            # NEW: Auto-store for follow-up queries
            store = get_context_store()
            store.save(
                context_type='calendar',
                data=events,
                metadata={'days': days}
            )
            logger.info(f"Stored {len(events)} calendar events in context")
        else:
            logger.info("No events to display in artifact panel")

        logger.info(f"@@@ READ_CALENDAR TOOL COMPLETE @@@")
        return summary
    else:
        logger.warning(f"Unexpected result format: {result}")
        return "I couldn't retrieve your calendar events right now."


@function_tool()
async def recall_context(context_type: str) -> str:
    """
    Retrieve previously fetched data from memory to answer follow-up questions.
    Also re-displays the data in the artifact panel.

    Args:
        context_type: Type of data to recall ('emails', 'calendar', 'flights', etc.)

    Returns:
        JSON string of the stored data, or error message if not found
    """
    import logging
    logger = logging.getLogger(__name__)

    store = get_context_store()
    result = store.get_with_metadata(context_type)

    if not result:
        return f"No {context_type} data in memory. Fetch fresh data first."

    data = result['data']
    metadata = result['metadata']
    age = result['age_seconds']

    logger.info(f"Recalled {context_type}: {len(data) if isinstance(data, list) else 1} items, {age:.0f}s old")

    # Re-send to artifact panel so user sees it again
    artifact_type_map = {
        'emails': 'email_list',
        'calendar': 'calendar_events',
        'weather': 'weather',
        # Future: 'flights': 'flight_options', 'youtube': 'summary_with_links', etc.
    }

    if context_type in artifact_type_map:
        await send_artifact_to_frontend({
            'type': artifact_type_map[context_type],
            'data': data
        })

    # Build response for LLM
    llm_response = {
        'context_type': context_type,
        'data': data,
        'age_seconds': int(age),
        'count': len(data) if isinstance(data, list) else 1
    }

    # For weather, include raw forecast for detailed questions
    # (e.g., "What's the wind speed on Friday?", "How much precipitation on Saturday?")
    if context_type == 'weather' and metadata.get('raw_forecast'):
        llm_response['detailed_forecast'] = metadata['raw_forecast']

    # Return the data as JSON for the LLM to parse
    # The LLM can understand "the 3rd email", "first meeting", "Friday's weather", etc.
    return json.dumps(llm_response)


@function_tool()
async def get_weather() -> str:
    """
    Fetch fresh 7-day weather forecast from API.

    Call this tool when:
    - User asks about weather for the FIRST time in the conversation
    - User explicitly requests "refresh" or "check again"
    - Cached data is stale (>1 hour old)

    DO NOT call for follow-up questions about weather just discussed.
    For follow-ups (e.g., "What about Friday?", "Will it rain tomorrow?"),
    use recall_context('weather') instead to avoid unnecessary API calls.

    Examples of FIRST weather questions (call this tool):
    - "What's the weather?"
    - "How's it looking this week?"
    - "Should I bring an umbrella today?"

    Data is cached for 1 hour for follow-up queries.

    Returns:
        Weather summary for voice response
    """
    import logging
    import os
    logger = logging.getLogger(__name__)

    logger.info(f"@@@ GET_WEATHER TOOL CALLED @@@")

    # Get location from environment variable and parse lat/lon
    location = os.getenv("WEATHER_LOCATION", "40.7128,-74.0060")  # Default to NYC
    logger.info(f"Using location: {location}")

    # Parse lat,lon from environment variable
    try:
        lat, lon = location.split(",")
        lat = lat.strip()
        lon = lon.strip()
    except ValueError:
        logger.error(f"Invalid WEATHER_LOCATION format: {location}. Expected 'lat,lon'")
        return "I couldn't get the weather. Location is not configured properly."

    # Call n8n weather workflow (test endpoint)
    result = await call_n8n_workflow(
        endpoint="weather-forecast",
        payload={"lat": lat, "lon": lon}
    )

    logger.info(f"Weather result: {result}")

    # Extract speech and artifact from n8n response
    speech = result.get("speech", "I couldn't get the weather forecast.")
    artifact = result.get("artifact")

    if artifact and artifact.get("data"):
        daily_data = artifact["data"]

        # Transform to WeatherWidget format
        # Extract current weather from first day
        today = daily_data[0] if daily_data else {}

        transformed_data = {
            "current": {
                "temperature": today.get("high", 0),
                "unit": "C",  # Data is in Celsius
                "condition": today.get("conditions", "Unknown"),
                "location": "Your Location",  # Could be from env var
                "humidity": None,  # Not available in current data
                "feels_like": None
            },
            "daily": [
                {
                    "date": day["date"].split("-")[2] + "/" + day["date"].split("-")[1],  # Format as DD/MM
                    "high": day["high"],
                    "low": day["low"]
                }
                for day in daily_data
            ]
        }

        logger.info(f"Transformed weather data with {len(transformed_data['daily'])} days")

        # Send to frontend
        await send_artifact_to_frontend({
            "type": "weather",
            "data": transformed_data
        })

        # Store TRANSFORMED data for follow-up queries (same format as displayed)
        # Also store original daily_data in metadata for detailed LLM analysis
        store = get_context_store()
        store.save(
            context_type='weather',
            data=transformed_data,  # Store transformed data so recall_context displays correctly
            metadata={
                'location': location,
                'days': len(daily_data),
                'raw_forecast': daily_data  # LLM can analyze detailed conditions, wind, precipitation
            }
        )
        logger.info(f"Stored weather forecast for {location} in context")

    logger.info(f"@@@ GET_WEATHER TOOL COMPLETE @@@")
    return speech


@function_tool()
async def search_youtube(query: str, count: int = 3) -> str:
    """
    Search and summarize YouTube videos.

    Args:
        query: Search query or topic
        count: Number of videos to analyze (1-5)

    Returns:
        Summary of videos for voice response
    """
    result = await call_n8n_workflow("youtube-summarize", {
        "query": query,
        "count": min(count, 5)
    })

    # Adapter: Transform to minimal artifact format
    # Support both 'summary' (custom) and 'speech' (JEX standard)
    speech = result.get("summary", result.get("speech", "I couldn't find YouTube videos."))
    videos = result.get("videos", [])

    if videos:
        # Create minimal artifact: summary + links (max 3 for cognitive load)
        artifact = {
            "type": "summary_with_links",
            "data": {
                "title": f"YouTube: {query}",
                "summary": speech,
                "links": [
                    {
                        "text": v.get("title", "Untitled Video"),
                        "url": v.get("url", ""),
                        "subtitle": v.get("channel", "")
                    }
                    for v in videos[:3]  # Max 3 links for minimal cognitive load
                ]
            }
        }
        await send_artifact_to_frontend(artifact)

        store = get_context_store()
        store.save(
            context_type='youtube',
            data=videos,
            metadata={'query': query, 'count': count}
        )

    return speech


def load_x_profiles() -> dict:
    """Load X search profiles from environment variable."""
    import json
    logger = logging.getLogger(__name__)
    profiles_json = os.getenv("X_SEARCH_PROFILES", "[]")

    try:
        profiles_list = json.loads(profiles_json)
        # Convert list to dict keyed by name
        return {p['name']: p for p in profiles_list}
    except Exception as e:
        logger.error(f"Failed to parse X_SEARCH_PROFILES: {e}")
        return {}


def hash_search_params(keywords: str, interests: str) -> str:
    """Generate stable hash from search params for cache key."""
    import hashlib
    combined = f"{keywords}|{interests}"
    return hashlib.md5(combined.encode()).hexdigest()[:8]


@function_tool()
async def search_x_feed(
    profile_name: Optional[str] = None,
    search_keywords: Optional[str] = None,
    user_interests: Optional[str] = None,
    force_refresh: bool = False
) -> str:
    """
    Search X.com for trending threads matching keywords and interests.

    Supports multiple search profiles (e.g., AI_Tech, Climate_Tech) or custom searches.
    First call fetches fresh data (may take 30-60 seconds due to search + ranking).
    Follow-up queries should use recall_context('x_feed:{profile}') for instant responses.

    Args:
        profile_name: Named profile from config (e.g., "AI_Tech", "Climate_Tech")
        search_keywords: Custom keywords (overrides profile)
        user_interests: Custom interests (overrides profile)
        force_refresh: Bypass cache even if recent data exists

    Returns:
        Summary of trending threads for voice response
    """
    logger = logging.getLogger(__name__)
    logger.info("@@@ SEARCH_X_FEED TOOL CALLED @@@")

    store = get_context_store()

    # 1. Resolve profile or custom params
    profiles = load_x_profiles()

    if profile_name and profile_name in profiles:
        # Use named profile
        profile = profiles[profile_name]
        keywords = profile['keywords']
        interests = profile['interests']
        cache_key = f"x_feed:{profile_name}"
        logger.info(f"Using profile '{profile_name}'")
    elif search_keywords or user_interests:
        # Custom search
        keywords = search_keywords or os.getenv("X_SEARCH_KEYWORDS", "AI, technology, programming")
        interests = user_interests or os.getenv("X_USER_INTERESTS", "tech trends, software development")
        cache_hash = hash_search_params(keywords, interests)
        cache_key = f"x_feed:{cache_hash}"
        logger.info(f"Custom search with hash {cache_hash}")
    else:
        # Use default profile
        default_profile_name = os.getenv("X_DEFAULT_PROFILE", "AI_Tech")
        if default_profile_name in profiles:
            profile = profiles[default_profile_name]
            keywords = profile['keywords']
            interests = profile['interests']
            cache_key = f"x_feed:{default_profile_name}"
            profile_name = default_profile_name
            logger.info(f"Using default profile '{default_profile_name}'")
        else:
            # Fallback to env vars
            keywords = os.getenv("X_SEARCH_KEYWORDS", "AI, technology, programming")
            interests = os.getenv("X_USER_INTERESTS", "tech trends, software development")
            cache_hash = hash_search_params(keywords, interests)
            cache_key = f"x_feed:{cache_hash}"
            logger.info(f"Using fallback env vars with hash {cache_hash}")

    # 2. Check cache first (unless force_refresh)
    if not force_refresh:
        cached = store.get_with_metadata(cache_key)
        if cached:
            age_minutes = cached['age_seconds'] / 60
            logger.info(f"Using cached X feed (age: {age_minutes:.1f} min)")

            # Re-publish artifact to frontend
            await send_artifact_to_frontend({
                "type": "x_feed",
                "data": cached['data']
            })

            profile_label = profile_name or f"search {cache_key.split(':')[1]}"
            return (f"Here are the trending threads for {profile_label} from {age_minutes:.0f} minutes ago. "
                    f"I can search for fresh threads if you'd like.")

    # 3. Fetch fresh data from n8n
    logger.info(f"Fetching fresh X feed from n8n (keywords: {keywords[:50]}..., interests: {interests[:50]}...)")
    logger.info("This may take 30-60 seconds for search + ranking...")

    try:
        # Use 90-second timeout for long-running workflow
        result = await asyncio.wait_for(
            call_n8n_workflow(
                endpoint="9e9e4217-1b52-427c-a3cd-ef14d15bf44f",
                payload={
                    "searchKeywords": keywords,
                    "userInterests": interests
                },
                timeout=90.0  # X feed search + ranking takes 30-60s
            ),
            timeout=90.0
        )

        logger.info(f"n8n response received: {result}")

        # 4. Parse response (n8n returns array with single item)
        if isinstance(result, list) and len(result) > 0:
            response_item = result[0]
            speech = response_item.get("speech", "I found some trending threads.")
            threads = response_item.get("data", [])
        else:
            speech = result.get("speech", "I found some trending threads.")
            threads = result.get("data", [])

        if not threads:
            logger.warning("No threads returned from n8n workflow")
            return "I couldn't find any trending threads matching your interests right now. Try different keywords?"

        logger.info(f"Received {len(threads)} threads from n8n")

        # 5. Store with profile-specific cache key
        store.save(
            context_type=cache_key,
            data=threads,
            metadata={
                'profile_name': profile_name,
                'keywords': keywords,
                'interests': interests,
                'thread_count': len(threads)
            }
        )
        logger.info(f"Stored X feed in context with key '{cache_key}'")

        # 6. Publish artifact to frontend
        await send_artifact_to_frontend({
            "type": "x_feed",
            "data": threads
        })

        # 7. Generate speech response
        if threads and len(threads) > 0:
            top_thread = threads[0]
            return (f"Found {len(threads)} trending threads. "
                    f"The top one is from {top_thread.get('authorName', 'someone')} with "
                    f"{top_thread.get('likes', 'many')} likes: {top_thread.get('postText', '')[:100]}...")
        else:
            return speech

    except asyncio.TimeoutError:
        logger.error("X feed search timed out after 90 seconds")
        return "The X search is taking longer than expected. The n8n workflow might be busy. Please try again in a moment."

    except Exception as e:
        logger.error(f"Error fetching X feed: {e}", exc_info=True)
        return f"I encountered an error searching X: {str(e)}. Please try again later."


@function_tool(
    name="preload_all_x_feeds",
    description="Pre-fetch all configured X.com search profiles for instant trending queries. Fetches in parallel."
)
async def preload_all_x_feeds() -> str:
    """
    Pre-populate ALL configured X.com profiles (AI_Tech, Climate_Tech, Startup_News).
    Fetches in parallel for speed (~30-60 seconds total).

    Returns:
        Status message with profile names and completion time
    """
    import time

    profiles = load_x_profiles()

    if not profiles:
        return "No X search profiles configured. Cannot pre-load."

    profile_names = list(profiles.keys())
    start_time = time.time()

    logger.info(f"Pre-loading {len(profile_names)} X profiles in parallel: {profile_names}")

    # Fetch all profiles in parallel
    tasks = [
        search_x_feed(profile_name=name, force_refresh=True)
        for name in profile_names
    ]

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for errors
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            logger.error(f"Errors during preload: {errors}")

        elapsed = time.time() - start_time

        success_count = len(profile_names) - len(errors)

        speech = (
            f"Pre-loaded {success_count} of {len(profile_names)} X feeds "
            f"in {elapsed:.1f} seconds. You can now ask about trending topics."
        )

        if errors:
            speech += f" ({len(errors)} profiles failed to load)"

        return speech

    except Exception as e:
        logger.error(f"Failed to preload X feeds: {e}")
        return f"Failed to pre-load X feeds: {str(e)}"


@function_tool(
    name="schedule_x_feed_preload",
    description="Start X feed preload in background. JEX will announce when done. Non-blocking."
)
async def schedule_x_feed_preload() -> str:
    """
    Schedule X feed preload as background task.
    Returns immediately, task runs asynchronously.
    """
    from context_store import get_context_store

    store = get_context_store()
    profiles = load_x_profiles()

    if not profiles:
        return "No X search profiles configured. Cannot pre-load."

    profile_names = list(profiles.keys())

    # Create background task
    task_id = store.create_task('x_feed_preload', params={'profile_names': profile_names})

    logger.info(f"Scheduled X feed preload task: {task_id}")

    return f"Starting preload in background for {len(profile_names)} profiles: {', '.join(profile_names)}. I'll let you know when it's done!"


@function_tool(
    name="check_task_status",
    description="Check status of a background task by ID"
)
async def check_task_status(task_id: str) -> str:
    """Check if a background task has completed"""
    from context_store import get_context_store

    store = get_context_store()
    task = store.get_task_status(task_id)

    if not task:
        return f"No task found with ID {task_id}"

    status = task['status']
    task_type = task['task_type']

    if status == 'pending':
        return f"Task {task_type} is queued and waiting to start."
    elif status == 'running':
        return f"Task {task_type} is currently running..."
    elif status == 'completed':
        return f"Task {task_type} completed successfully!"
    elif status == 'failed':
        error = task.get('error', 'Unknown error')
        return f"Task {task_type} failed: {error}"
    else:
        return f"Task {task_type} has status: {status}"
