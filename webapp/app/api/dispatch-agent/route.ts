import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const { roomName } = await req.json();

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const liveKitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;

  if (!apiKey || !apiSecret || !liveKitUrl) {
    return NextResponse.json(
      { error: 'Missing LiveKit configuration' },
      { status: 500 }
    );
  }

  try {
    // Convert WebSocket URL to HTTP API URL
    const apiUrl = liveKitUrl.replace('wss://', 'https://').replace('ws://', 'http://');

    // Generate JWT for API authentication
    const jwt = require('jsonwebtoken');
    const token = jwt.sign(
      {
        video: { roomAdmin: true, room: roomName },
      },
      apiSecret,
      {
        issuer: apiKey,
        expiresIn: '10m',
      }
    );

    console.log('[DispatchAgent] Dispatching agent to room:', roomName);

    // Call LiveKit Agent Dispatch API
    const response = await fetch(`${apiUrl}/twirp/livekit.AgentDispatchService/CreateDispatch`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        room: roomName,
        agent_name: 'jex',
        metadata: '',
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('[DispatchAgent] Dispatch failed:', error);
      return NextResponse.json(
        { error: `Dispatch failed: ${error}` },
        { status: response.status }
      );
    }

    const result = await response.json();
    console.log('[DispatchAgent] Dispatch successful:', result);

    return NextResponse.json({ success: true, dispatch: result });
  } catch (error) {
    console.error('[DispatchAgent] Error:', error);
    return NextResponse.json(
      { error: String(error) },
      { status: 500 }
    );
  }
}
