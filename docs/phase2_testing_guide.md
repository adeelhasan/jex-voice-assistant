# Phase 2 Testing Guide - Email Integration

## What We Just Built

✅ **n8n Gmail Workflow** - Webhook that fetches emails from Gmail
✅ **Agent Function Tool** - `read_emails()` that calls the n8n workflow
✅ **Artifact Panel** - Visual display for emails on the frontend
✅ **Data Channel** - Real-time communication from agent to browser

---

## Testing Steps

### Step 1: Verify n8n Workflow is Active

1. Go to your n8n workflow in the browser
2. Make sure the workflow is **toggled to "Active"** (top right)
3. Test the webhook directly with curl:

```bash
curl -X POST https://architoon.app.n8n.cloud/webhook/read-emails \
  -H "Content-Type: application/json" \
  -H "X-JEX-API-Key: 805c66a20d5e3684f76c6c963f647a09d08f0d932bf274d1ba3bb17173068446" \
  -d '{"count": 3, "filter": "unread"}'
```

**Expected Response:**
```json
{
  "speech": "You have X emails. The first is from...",
  "artifact": {
    "type": "email_list",
    "data": [
      {
        "id": "...",
        "from": "John Doe <john@example.com>",
        "subject": "Test Email",
        "snippet": "Email content preview...",
        "date": "Mon, 16 Dec 2024 ..."
      }
    ]
  }
}
```

If this fails:
- Check workflow is active
- Verify Gmail OAuth2 is connected
- Check n8n execution logs for errors

---

### Step 2: Start the Agent

In your `agent/` directory:

```bash
# Make sure you're in the agent directory
cd agent

# Activate virtual environment (if using one)
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run the agent
python main.py dev
```

**Expected Output:**
```
INFO:__main__:LLM: openai (gpt-4o-mini)
INFO:__main__:STT: deepgram
INFO:__main__:TTS: openai (alloy)
INFO:livekit.agents.worker:Worker started, waiting for jobs...
```

If you see errors:
- Check `.env` file has correct values
- Verify `N8N_WEBHOOK_BASE_URL` and `N8N_API_KEY` are set
- Check all API keys are valid

---

### Step 3: Start the Frontend

In a **new terminal**, go to `webapp/` directory:

```bash
# Navigate to webapp
cd webapp

# Install dependencies (if you haven't already)
npm install

# Start the dev server
npm run dev
```

**Expected Output:**
```
  ▲ Next.js 15.x.x
  - Local:        http://localhost:3000

✓ Ready in XXXms
```

Open browser to: **http://localhost:3000**

---

### Step 4: Connect and Test Voice Interaction

1. **Click "Connect"** in the browser
   - You should see the agent state change to "listening"
   - JEX should greet you and mention email capabilities

2. **Say:** "Check my emails" or "Show me my unread emails"

3. **What Should Happen:**
   - Agent state changes to "thinking"
   - Agent calls the `read_emails` tool
   - n8n workflow executes
   - Agent responds with voice summary
   - **Emails appear in the right panel** (Artifact Panel)
   - Agent state returns to "listening"

4. **Verify:**
   - ✅ Voice response mentions your emails
   - ✅ Email list appears in the artifact panel on the right
   - ✅ Each email shows: subject, from, snippet, date
   - ✅ Emails are clickable/hoverable

---

### Step 5: Test Different Variations

Try these voice commands:

```
"Check my emails"
"Show me my last 5 emails"
"Do I have any unread emails?"
"Read my emails"
"What emails do I have?"
```

The LLM should recognize these and call the `read_emails` tool.

---

## Debugging

### Agent Not Calling the Tool

**Symptoms:**
- Agent responds conversationally but doesn't fetch emails
- No artifact appears in the panel

**Check:**
1. Agent logs show tool is registered:
   ```
   # Look for something like:
   INFO:livekit.agents.llm:Registered tools: ['read_emails']
   ```

2. LLM model supports function calling:
   - `gpt-4o-mini` supports it ✅
   - If using different model, verify it supports function calling

3. Agent instructions mention the tool capability

**Fix:**
- Restart the agent (`Ctrl+C`, then `python main.py dev`)
- Check `agent/main.py` has `tools=[read_emails]` in JexAgent.__init__

---

### Tool Called but No Artifact Appears

**Symptoms:**
- Agent says it checked emails
- Voice response is correct
- But artifact panel stays empty

**Check:**
1. **Browser Console** (F12 → Console):
   - Look for errors like "Failed to parse artifact"
   - Check for data channel messages

2. **Agent Logs:**
   - Look for "Could not send artifact" error
   - Check if artifact was received from n8n

3. **n8n Workflow:**
   - Verify response includes `artifact` field
   - Check execution logs in n8n

**Fix:**
- Check browser console for detailed error
- Verify `send_artifact_to_frontend()` is called in `tools.py`
- Test n8n webhook directly with curl to verify response format

---

### n8n Workflow Fails

**Symptoms:**
- Agent tries to call tool but gets error
- Agent says "I had trouble connecting to that service"

**Check:**
1. **n8n Execution Logs:**
   - Go to n8n → Executions
   - Check most recent execution
   - Look for errors in Gmail node

2. **Common Issues:**
   - Gmail OAuth2 token expired → Re-authenticate
   - API key mismatch → Verify header auth credential
   - Workflow not active → Toggle to "Active"

3. **Test Directly:**
   ```bash
   # Test with curl to bypass agent
   curl -X POST https://architoon.app.n8n.cloud/webhook/read-emails \
     -H "Content-Type: application/json" \
     -H "X-JEX-API-Key: YOUR_KEY" \
     -d '{"count": 1, "filter": "all"}'
   ```

---

### Frontend Artifact Panel Not Showing

**Symptoms:**
- Artifact panel is missing or blank
- Layout looks wrong

**Check:**
1. **Component Import:**
   - Check `webapp/app/page.tsx` imports `ArtifactPanel`
   - Verify it's rendered in JSX

2. **TypeScript Errors:**
   ```bash
   npm run build
   ```
   - Check for compilation errors

3. **Browser Console:**
   - Look for React errors
   - Check component is rendering

**Fix:**
- Restart Next.js dev server
- Clear browser cache (Cmd+Shift+R / Ctrl+Shift+F5)
- Check for TypeScript errors

---

## Success Criteria

Phase 2 Email Integration is **complete** when:

- ✅ User can say "check my emails"
- ✅ Agent calls the `read_emails` tool
- ✅ n8n workflow executes successfully
- ✅ Agent responds with voice summary
- ✅ Emails appear visually in artifact panel
- ✅ All emails show correct data (subject, from, snippet, date)
- ✅ No errors in agent or browser console

---

## Next Steps (After Email Works)

Once email integration is working:

1. **Test edge cases:**
   - No unread emails
   - Request more than available
   - Network timeout

2. **Add calendar integration** (same pattern):
   - Create n8n calendar workflow
   - Add `check_calendar()` tool
   - Add calendar view to artifact panel

3. **Implement "Important Emails" filter** (your next feature):
   - Modify n8n workflow to filter by importance
   - Update tool to support importance parameter
   - Test with "Show me important emails"

---

## Useful Commands

**Restart Agent:**
```bash
cd agent
# Ctrl+C to stop
python main.py dev
```

**Restart Frontend:**
```bash
cd webapp
# Ctrl+C to stop
npm run dev
```

**Test n8n Directly:**
```bash
curl -X POST https://architoon.app.n8n.cloud/webhook/read-emails \
  -H "Content-Type: application/json" \
  -H "X-JEX-API-Key: 805c66a20d5e3684f76c6c963f647a09d08f0d932bf274d1ba3bb17173068446" \
  -d '{"count": 3, "filter": "unread"}'
```

**Check Agent Logs:**
```bash
# Agent logs print to terminal where you ran it
# Look for:
# - "JEX agent session starting"
# - Tool registration messages
# - Error messages
```

**Check Browser Console:**
```
F12 → Console tab
Look for:
- Data channel messages
- Artifact parsing
- Component errors
```

---

## Questions or Issues?

If you encounter issues not covered here:

1. Check agent terminal logs
2. Check browser console (F12)
3. Check n8n execution logs
4. Test components individually (n8n → agent → frontend)
5. Verify all environment variables are set correctly
