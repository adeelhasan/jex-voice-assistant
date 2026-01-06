'use client';

import { useDataChannel } from '@livekit/components-react';
import { useState } from 'react';

interface Artifact {
  type: string;
  data: any;
}

interface Thread {
  authorName: string
  authorUsername: string
  likes: string | number
  matchedKeywords: string[]
  postText: string
  replies: string | number
  reposts: string | number
  views: string | number
  engagementScore: number
  metrics?: {
    likes?: number
    replies?: number
    reposts?: number
    views?: number
  }
}

interface XFeedListProps {
  threads: Thread[]
}

export function ArtifactPanel() {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [history, setHistory] = useState<Artifact[]>([]);

  // Listen for artifact data from the agent
  useDataChannel((msg) => {
    try {
      const decoded = new TextDecoder().decode(msg.payload);
      const data = JSON.parse(decoded);

      if (data.type === 'artifact' && data.data) {
        setArtifact(data.data);
        setHistory(prev => [data.data, ...prev].slice(0, 10)); // Keep last 10
      }
    } catch (e) {
      console.error('Failed to parse artifact:', e);
    }
  });

  return (
    <div className="h-full flex flex-col">
      <header className="px-4 py-3 border-b bg-gray-50">
        <h2 className="font-semibold text-gray-700">Display</h2>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        {artifact ? (
          <ArtifactRenderer artifact={artifact} />
        ) : (
          <EmptyState />
        )}
      </div>

      {/* History navigation */}
      {history.length > 1 && (
        <div className="border-t p-3 bg-gray-50">
          <p className="text-xs text-gray-500 mb-2">Recent</p>
          <div className="flex gap-2 overflow-x-auto">
            {history.slice(1, 5).map((item, i) => (
              <button
                key={i}
                onClick={() => setArtifact(item)}
                className="px-3 py-1 text-xs bg-white border rounded-full hover:bg-gray-100 whitespace-nowrap"
              >
                {item.type.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-full flex flex-col items-center justify-center text-gray-400">
      <div className="text-4xl mb-3">📱</div>
      <p className="text-center">
        Content will appear here when JEX retrieves information.
      </p>
      <p className="text-sm mt-2 text-center">
        Try: "Check my emails" • "What's on my calendar?" • "What's the weather?"
      </p>
    </div>
  );
}

function ArtifactRenderer({ artifact }: { artifact: Artifact }) {
  switch (artifact.type) {
    case 'email_list':
      return <EmailList emails={artifact.data} />;
    case 'calendar_events':
      return <CalendarEventList events={artifact.data} />;
    case 'weather':
      return <WeatherWidget data={artifact.data} />;
    case 'x_feed':
      return <XFeedList threads={artifact.data} />;
    default:
      return <GenericView data={artifact} />;
  }
}

function EmailList({ emails }: { emails: any[] }) {
  if (!Array.isArray(emails)) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        📧 Emails
      </h3>
      {emails.map((email, i) => (
        <div key={i} className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors">
          <div className="font-medium text-gray-900">{email.subject}</div>
          <div className="text-sm text-gray-600 mt-1">{email.from}</div>
          <div className="text-sm text-gray-500 mt-2 line-clamp-2">{email.snippet}</div>
          <div className="text-xs text-gray-400 mt-2">
            {email.date ? new Date(email.date).toLocaleString() : ''}
          </div>
        </div>
      ))}
    </div>
  );
}

function CalendarEventList({ events }: { events: any[] }) {
  if (!Array.isArray(events)) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        📅 Calendar Events
      </h3>
      {events.map((event, i) => {
        const startDate = new Date(event.start);
        const endDate = new Date(event.end);
        const isToday = startDate.toDateString() === new Date().toDateString();

        return (
          <div key={i} className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors">
            <div className="font-medium text-gray-900">{event.title}</div>
            <div className="text-sm text-gray-600 mt-1 flex items-center gap-2">
              <span>🕐</span>
              <span>
                {isToday ? 'Today' : startDate.toLocaleDateString()}
                {' '}
                {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                {' - '}
                {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            {event.location && event.location !== 'No location' && (
              <div className="text-sm text-gray-500 mt-1 flex items-center gap-2">
                <span>📍</span>
                <span>{event.location}</span>
              </div>
            )}
            {event.description && event.description !== 'No description' && (
              <div className="text-sm text-gray-500 mt-2">
                {event.description}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function GenericView({ data }: { data: any }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <pre className="text-xs overflow-auto whitespace-pre-wrap">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

function WeatherWidget({ data }: { data: any }) {
  // Support both old format (flat) and new format (with current/hourly/daily)
  const current = data.current || data;

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        🌤️ Weather
      </h3>
      <div className="bg-gradient-to-br from-blue-400 to-blue-600 text-white rounded-lg p-6">
        {/* Current weather */}
        <div className="text-4xl font-bold">{current.temperature}°{current.unit || 'F'}</div>
        <div className="text-xl mt-2">{current.condition}</div>
        <div className="text-sm opacity-80 mt-1">{current.location}</div>
        {current.feels_like && (
          <div className="text-xs opacity-70 mt-1">
            Feels like {current.feels_like}° • Humidity {current.humidity}%
          </div>
        )}

        {/* 7-day daily forecast */}
        {data.daily && data.daily.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/20">
            <div className="text-xs opacity-70 mb-2">7-Day Forecast</div>
            <div className="grid grid-cols-4 gap-2 text-sm">
              {data.daily.slice(0, 4).map((day: any, i: number) => (
                <div key={i} className="text-center">
                  <div className="opacity-70 text-xs">{day.date}</div>
                  <div className="font-medium">{day.high}°</div>
                  <div className="text-xs opacity-80">{day.low}°</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 36-hour hourly forecast - show next 12 hours */}
        {data.hourly && data.hourly.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/20">
            <div className="text-xs opacity-70 mb-2">Next 12 Hours</div>
            <div className="flex overflow-x-auto gap-2 pb-2 -mx-2 px-2">
              {data.hourly.slice(0, 12).map((hour: any, i: number) => (
                <div key={i} className="text-center flex-shrink-0 w-14">
                  <div className="text-xs opacity-70">{hour.time}</div>
                  <div className="text-sm font-medium">{hour.temp}°</div>
                  {hour.precip > 0 && (
                    <div className="text-xs">💧{hour.precip}%</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function XFeedList({ threads }: XFeedListProps) {
  if (!threads || !Array.isArray(threads) || threads.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        No threads available
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <span>🐦</span>
        <span>Trending on X</span>
        <span className="text-sm text-gray-400">({threads.length})</span>
      </h2>

      {threads.map((thread, index) => (
        <ThreadCard key={index} thread={thread} rank={index + 1} />
      ))}
    </div>
  )
}

function ThreadCard({ thread, rank }: { thread: Thread; rank: number }) {
  const truncatedText = thread.postText.length > 280
    ? thread.postText.slice(0, 280) + '...'
    : thread.postText

  return (
    <div className="bg-gray-50 rounded-lg p-4 border hover:border-blue-300 transition-all">
      {/* Header: Rank + Author */}
      <div className="flex items-center gap-3 mb-3">
        <div className="flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-full text-sm font-bold">
          {rank}
        </div>
        <div>
          <div className="font-semibold text-gray-900">{thread.authorName}</div>
          <div className="text-sm text-gray-500">{thread.authorUsername}</div>
        </div>
      </div>

      {/* Post Text */}
      <p className="text-gray-800 mb-3 whitespace-pre-wrap leading-relaxed">
        {truncatedText}
      </p>

      {/* Matched Keywords */}
      {thread.matchedKeywords && thread.matchedKeywords.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {thread.matchedKeywords.filter(k => k).map((keyword, i) => (
            <span
              key={i}
              className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full"
            >
              {keyword}
            </span>
          ))}
        </div>
      )}

      {/* Engagement Metrics */}
      <div className="flex items-center gap-4 text-sm text-gray-500">
        <div className="flex items-center gap-1">
          <span>❤️</span>
          <span>{formatNumber(thread.likes)}</span>
        </div>
        <div className="flex items-center gap-1">
          <span>💬</span>
          <span>{formatNumber(thread.replies)}</span>
        </div>
        <div className="flex items-center gap-1">
          <span>🔁</span>
          <span>{formatNumber(thread.reposts)}</span>
        </div>
        <div className="flex items-center gap-1">
          <span>👁️</span>
          <span>{formatNumber(thread.views)}</span>
        </div>
        {thread.engagementScore && (
          <div className="ml-auto text-blue-600 font-semibold">
            {(thread.engagementScore * 100).toFixed(0)}%
          </div>
        )}
      </div>
    </div>
  )
}

// Utility function to format large numbers
function formatNumber(num: string | number): string {
  const n = typeof num === 'string' ? parseFloat(num.replace(/[KM]/g, '')) : num
  if (isNaN(n)) return String(num)

  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}
