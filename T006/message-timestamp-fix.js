// Fix for incorrect message timestamps

// Get current timestamp in proper format
function getCurrentTimestamp() {
  const now = new Date();
  return now.toISOString();
}

// Format timestamp for display
function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  
  // Check if timestamp is today
  const isToday = date.toDateString() === now.toDateString();
  
  if (isToday) {
    // Show time only for today's messages
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  } else {
    // Show date and time for older messages
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  }
}

// Fix message object with correct timestamp
function createMessage(content, userId) {
  return {
    id: generateMessageId(),
    content: content,
    userId: userId,
    timestamp: getCurrentTimestamp(),
    createdAt: Date.now()
  };
}

// Update existing messages with correct timestamps
function fixExistingTimestamps(messages) {
  return messages.map(message => {
    if (!message.timestamp || isNaN(new Date(message.timestamp))) {
      message.timestamp = new Date(message.createdAt || Date.now()).toISOString();
    }
    return message;
  });
}

function generateMessageId() {
  return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}