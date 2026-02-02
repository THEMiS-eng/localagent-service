import React, { useState } from 'react';
import './ChatInput.css';

const ChatInput = ({ 
  onSendMessage, 
  placeholder = "Type your message...",
  actionButtons = [],
  disabled = false 
}) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-container">
      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="input-wrapper">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            disabled={disabled}
            className="message-input"
            rows={1}
          />
          <div className="action-buttons">
            {actionButtons.map((btn, index) => (
              <button
                key={btn.id || index}
                type="button"
                onClick={() => btn.onClick(message, setMessage)}
                className={`action-btn ${btn.className || ''}`}
                disabled={disabled || btn.disabled}
                title={btn.tooltip}
              >
                {btn.icon && <span className="btn-icon">{btn.icon}</span>}
                {btn.label}
              </button>
            ))}
            <button
              type="submit"
              disabled={!message.trim() || disabled}
              className="send-btn"
            >
              Send
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default ChatInput;