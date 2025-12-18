"""
Function tools for JEX agent.
These functions are callable by the LLM to perform actions via n8n workflows.
"""

import os
import json
import httpx
from typing import Optional
from livekit.agents import function_tool, get_job_context
from context_store import get_context_store

# n8n Configuration
N8N_WEBHOOK_BASE_URL = os.getenv("N8N_WEBHOOK_BASE_URL", "")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


async def call_n8n_workflow(endpoint: str, payload: dict) -> dict:
    """
    Call an n8n webhook workflow and return the response.

    Args:
        endpoint: Workflow endpoint path (e.g., "read-emails") OR full webhook ID
        payload: Data to send to the workflow

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

    headers = {
        "Content-Type": "application/json",
        "X-JEX-API-Key": N8N_API_KEY
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
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
    age = result['age_seconds']

    logger.info(f"Recalled {context_type}: {len(data) if isinstance(data, list) else 1} items, {age:.0f}s old")

    # Re-send to artifact panel so user sees it again
    artifact_type_map = {
        'emails': 'email_list',
        'calendar': 'calendar_events',
        # Future: 'flights': 'flight_options', etc.
    }

    if context_type in artifact_type_map:
        await send_artifact_to_frontend({
            'type': artifact_type_map[context_type],
            'data': data
        })

    # Return the data as JSON for the LLM to parse
    # The LLM can understand "the 3rd email" or "first meeting" from this
    return json.dumps({
        'context_type': context_type,
        'data': data,
        'age_seconds': int(age),
        'count': len(data) if isinstance(data, list) else 1
    })
