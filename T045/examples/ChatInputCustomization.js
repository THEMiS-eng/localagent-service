import React from 'react';
import ChatInput from '../src/components/ChatInput';

const ChatInputCustomization = () => {
  const handleSendMessage = (message) => {
    console.log('Message sent:', message);
  };

  const customSendAction = (message) => {
    console.log('Custom send action:', message);
    // Custom logic here
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px' }}>
      <h3>Default Chat Input</h3>
      <ChatInput onSendMessage={handleSendMessage} />
      
      <h3>Custom Action Button</h3>
      <ChatInput 
        onSendMessage={handleSendMessage}
        actionButton={{
          text: "Submit",
          icon: "✓",
          color: "#28a745",
          hoverColor: "#1e7e34"
        }}
      />
      
      <h3>Icon Only Button</h3>
      <ChatInput 
        onSendMessage={handleSendMessage}
        actionButton={{
          icon: "📤",
          color: "#6f42c1",
          hoverColor: "#5a32a3"
        }}
      />
      
      <h3>Custom Click Handler</h3>
      <ChatInput 
        placeholder="Enter command..."
        actionButton={{
          text: "Execute",
          icon: "⚡",
          color: "#fd7e14",
          hoverColor: "#e8590c",
          onClick: customSendAction
        }}
      />
    </div>
  );
};

export default ChatInputCustomization;