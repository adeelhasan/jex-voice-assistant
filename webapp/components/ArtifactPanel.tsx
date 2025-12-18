'use client';

import { useDataChannel } from '@livekit/components-react';
import { useState } from 'react';

interface Artifact {
  type: string;
  data: any;
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
        Try: "Check my emails" • "What's on my calendar?"
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
