import React from 'react';
import ChatInput from '../components/ChatInput';

const ChatInputExample = () => {
  const actionButtons = [
    {
      id: 'emoji',
      icon: '😀',
      tooltip: 'Add emoji',
      onClick: (message, setMessage) => {
        setMessage(message + '😀');
      }
    },
    {
      id: 'attach',
      icon: '📎',
      label: 'File',
      tooltip: 'Attach file',
      onClick: () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.click();
      }
    },
    {
      id: 'voice',
      icon: '🎤',
      tooltip: 'Voice message',
      className: 'voice-btn',
      onClick: () => {
        console.log('Voice recording started');
      }
    },
    {
      id: 'clear',
      label: 'Clear',
      tooltip: 'Clear message',
      onClick: (message, setMessage) => {
        setMessage('');
      }
    }
  ];

  const handleSendMessage = (message) => {
    console.log('Sending message:', message);
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px' }}>
      <h3>Chat Input with Custom Action Buttons</h3>
      <ChatInput
        onSendMessage={handleSendMessage}
        placeholder="Type your message with custom actions..."
        actionButtons={actionButtons}
      />
      
      <div style={{ marginTop: '20px', fontSize: '14px', color: '#666' }}>
        <p>Available actions:</p>
        <ul>
          <li>😀 - Add emoji to message</li>
          <li>📎 File - Open file picker</li>
          <li>🎤 - Start voice recording</li>
          <li>Clear - Clear current message</li>
        </ul>
      </div>
    </div>
  );
};

export default ChatInputExample;