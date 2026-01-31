import React, { useState, useEffect } from 'react';

const Dashboard = () => {
  const [status, setStatus] = useState('Disconnected');
  const [messages, setMessages] = useState([]);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8080');
    setWs(websocket);

    websocket.onopen = () => setStatus('Connected');
    websocket.onclose = () => setStatus('Disconnected');
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev.slice(-49), data]);
    };

    return () => websocket.close();
  }, []);

  return React.createElement(
    'div',
    { className: 'dashboard' },
    React.createElement(
      'div',
      { className: 'status-bar' },
      React.createElement('span', { className: `status ${status.toLowerCase()}` }, status)
    ),
    React.createElement(
      'div',
      { className: 'messages' },
      React.createElement('h2', null, 'Messages'),
      React.createElement(
        'div',
        { className: 'message-list' },
        messages.map((msg, idx) =>
          React.createElement(
            'div',
            { key: idx, className: 'message' },
            JSON.stringify(msg)
          )
        )
      )
    )
  );
};

export default Dashboard;