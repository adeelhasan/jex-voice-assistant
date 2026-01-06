"""
Background task processor - executes queued tasks independently.
Uses handler registry pattern for extensibility.
"""
import asyncio
import logging
from typing import Callable, Dict

from context_store import get_context_store

logger = logging.getLogger(__name__)

# Registry of task handlers
TASK_HANDLERS: Dict[str, Callable] = {}


def register_task_handler(task_type: str):
    """Decorator to register task handlers"""
    def decorator(func):
        TASK_HANDLERS[task_type] = func
        return func
    return decorator


async def process_task(task: dict):
    """Execute a single task"""
    task_id = task['task_id']
    task_type = task['task_type']
    params = task.get('params', {}) or {}

    logger.info(f"========================================")
    logger.info(f"PROCESSING TASK: {task_id}")
    logger.info(f"Task type: {task_type}")
    logger.info(f"Parameters: {params}")
    logger.info(f"========================================")

    store = get_context_store()

    # Find handler
    handler = TASK_HANDLERS.get(task_type)
    if not handler:
        logger.error(f"❌ No handler for task type: {task_type}")
        logger.error(f"Available handlers: {list(TASK_HANDLERS.keys())}")
        store.update_task_status(task_id, 'failed', error=f"Unknown task type: {task_type}")
        return

    logger.info(f"✅ Found handler: {handler.__name__}")

    # Update status to running
    store.update_task_status(task_id, 'running')
    logger.info(f"⏳ Task status updated to 'running'")

    try:
        # Execute handler with timeout (4 minutes max for X feed searches)
        logger.info(f"🚀 Calling handler with params: {params}")
        try:
            result = await asyncio.wait_for(handler(**params), timeout=240.0)
            logger.info(f"✅ Handler completed successfully")
            logger.info(f"Result: {result}")
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Handler timed out after 240 seconds")
            raise Exception("Task execution timed out after 240 seconds")

        # Mark as completed
        store.update_task_status(task_id, 'completed', result=result)
        logger.info(f"✅ Task {task_id} marked as completed")

        # Generate announcement
        announcement_message = generate_announcement(task_type, result, params)
        logger.info(f"📢 Generated announcement: {announcement_message[:100]}...")
        announcement_id = store.create_announcement(task_id, announcement_message, title=f"{task_type} complete")
        logger.info(f"✅ Created announcement {announcement_id}")

    except Exception as e:
        logger.error(f"❌ Task {task_id} failed with exception: {e}", exc_info=True)
        error_msg = f"{type(e).__name__}: {str(e)}"
        store.update_task_status(task_id, 'failed', error=error_msg)
        logger.info(f"❌ Task status updated to 'failed'")

        # Create failure announcement (brief)
        failure_msg = f"Task failed: {str(e)[:100]}"
        store.create_announcement(task_id, failure_msg, title="Task failed")
        logger.info(f"📢 Created failure announcement")


def generate_announcement(task_type: str, result: dict, params: dict) -> str:
    """Generate natural announcement text for completed task"""
    # Template-based approach (can be enhanced with LLM later)

    if task_type == 'x_feed_preload':
        success_count = result.get('success_count', 0)
        total_count = result.get('total_count', 0)
        elapsed = result.get('elapsed', 0)

        return f"All X feeds are loaded! Pre-loaded {success_count} of {total_count} profiles in {elapsed:.1f} seconds. You can now ask about trending topics."

    elif task_type == 'email_check':
        count = result.get('count', 0)
        if count > 0:
            return f"You have {count} new emails. Say 'check my emails' to see them."
        else:
            return "No new emails."

    elif task_type == 'calendar_reminder':
        event_title = result.get('title', 'event')
        minutes_until = result.get('minutes_until', 10)
        return f"Reminder: {event_title} starts in {minutes_until} minutes."

    else:
        return f"Task {task_type} completed successfully."


async def task_processor_loop():
    """Main loop - continuously process pending tasks"""
    store = get_context_store()
    logger.info("Task processor started")

    while True:
        try:
            # Fetch pending tasks
            pending_tasks = store.get_pending_tasks()

            if pending_tasks:
                logger.info(f"Processing {len(pending_tasks)} pending tasks")

                # Process all pending tasks in parallel
                await asyncio.gather(*[process_task(task) for task in pending_tasks], return_exceptions=True)

            # Sleep before next poll
            await asyncio.sleep(2)  # Poll every 2 seconds

        except asyncio.CancelledError:
            logger.info("Task processor cancelled")
            raise
        except Exception as e:
            logger.error(f"Task processor error: {e}", exc_info=True)
            await asyncio.sleep(5)  # Back off on error


# ===== Task Handler Implementations =====

@register_task_handler('x_feed_preload')
async def handle_x_feed_preload(profile_names: list = None) -> dict:
    """Handler for X feed preload task"""
    import time

    logger.info(f"=== X_FEED_PRELOAD HANDLER STARTED ===")
    logger.info(f"Profile names parameter: {profile_names}")

    try:
        from tools import preload_all_x_feeds
        logger.info("Successfully imported preload_all_x_feeds")
    except Exception as e:
        logger.error(f"Failed to import preload_all_x_feeds: {e}", exc_info=True)
        raise

    start_time = time.time()

    logger.info("Calling preload_all_x_feeds()...")
    try:
        speech = await preload_all_x_feeds()
        logger.info(f"preload_all_x_feeds returned: {speech[:200]}")
    except Exception as e:
        logger.error(f"preload_all_x_feeds raised exception: {e}", exc_info=True)
        raise

    elapsed = time.time() - start_time

    # Parse success from speech (basic approach)
    # Better: Refactor preload_all_x_feeds to return structured data
    total_count = len(profile_names) if profile_names else 2  # Updated to 2 profiles
    success_count = total_count  # Assume success unless error in speech

    if "failed" in speech.lower():
        # Try to parse number from speech
        import re
        match = re.search(r'(\d+) of (\d+)', speech)
        if match:
            success_count = int(match.group(1))
            total_count = int(match.group(2))
        else:
            success_count = total_count - 1  # Conservative estimate

    logger.info(f"Task completed: {success_count}/{total_count} successful, {elapsed:.1f}s elapsed")

    return {
        'success_count': success_count,
        'total_count': total_count,
        'elapsed': elapsed,
        'speech': speech
    }


@register_task_handler('email_check')
async def handle_email_check(filter: str = 'unread', count: int = 5) -> dict:
    """Handler for email checking task"""
    from tools import read_emails

    # Call existing email tool
    result = await read_emails(count=count, filter=filter)

    # Return structured data
    return {
        'count': count,  # TODO: Parse actual count from result
        'filter': filter
    }
