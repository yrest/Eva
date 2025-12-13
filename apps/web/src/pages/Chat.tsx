import { useState } from 'react';

export function Chat() {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState('');

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    // TODO: Integrate with chat service
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '1rem' }}>
      <header style={{ padding: '1rem 0', borderBottom: '1px solid #333' }}>
        <h1>Eva</h1>
      </header>

      <main style={{ flex: 1, overflow: 'auto', padding: '1rem 0' }}>
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              padding: '0.75rem',
              margin: '0.5rem 0',
              borderRadius: '8px',
              background: msg.role === 'user' ? '#1a1a2e' : '#16213e',
            }}
          >
            <strong>{msg.role === 'user' ? 'You' : 'Eva'}:</strong> {msg.content}
          </div>
        ))}
      </main>

      <footer style={{ padding: '1rem 0', borderTop: '1px solid #333' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Message Eva..."
            style={{
              flex: 1,
              padding: '0.75rem',
              borderRadius: '8px',
              border: '1px solid #333',
              background: '#1a1a1a',
              color: '#fff',
            }}
          />
          <button
            onClick={handleSend}
            style={{
              padding: '0.75rem 1.5rem',
              borderRadius: '8px',
              border: 'none',
              background: '#4f46e5',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            Send
          </button>
        </div>
      </footer>
    </div>
  );
}
