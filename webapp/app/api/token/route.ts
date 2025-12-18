import { AccessToken } from 'livekit-server-sdk';
import { NextResponse } from 'next/server';

export async function GET() {
  const roomName = 'jex-room';
  const participantName = `user-${Date.now()}`;

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (!apiKey || !apiSecret) {
    return NextResponse.json(
      { error: 'Server configuration error: Missing LiveKit credentials' },
      { status: 500 }
    );
  }

  const at = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
    ttl: '1h',
  });

  at.addGrant({
    roomJoin: true,
    room: roomName,
    canPublish: true,
    canSubscribe: true,
    canPublishData: true,
  });

  // Request agent dispatch when participant joins
  at.metadata = JSON.stringify({
    agent_dispatch: {
      agent_name: 'jex', // Matches worker agent_name="jex"
      metadata: {}
    }
  });

  const token = await at.toJwt();
  return NextResponse.json({ token, roomName });
}
