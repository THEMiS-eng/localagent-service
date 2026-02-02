import React, { useState, useRef } from 'react';
import './ChatInput.css';

const ChatInput = ({ 
  onSendMessage, 
  placeholder = "Type your message...",
  actionButton = {
    text: "Send",
    icon: "→",
    color: "#007bff",
    hoverColor: "#0056b3",
    onClick: null
  },
  disabled = false 
}) => {
  const [message, setMessage] = useState('');
  const inputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      if (actionButton.onClick) {
        actionButton.onClick(message.trim());
      } else {
        onSendMessage(message.trim());
      }
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
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <div className="chat-input-container">
        <input
          ref={inputRef}
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          disabled={disabled}
          className="chat-input-field"
        />
        <button
          type="submit"
          disabled={!message.trim() || disabled}
          className="chat-action-button"
          style={{
            backgroundColor: actionButton.color,
            '--hover-color': actionButton.hoverColor
          }}
        >
          {actionButton.icon && <span className="button-icon">{actionButton.icon}</span>}
          {actionButton.text && <span className="button-text">{actionButton.text}</span>}
        </button>
      </div>
    </form>
  );
};

export default ChatInput;