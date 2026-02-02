function addMessage(message, isUser = false) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    messageDiv.textContent = message;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    if (!message) return;
    
    addMessage(message, true);
    input.value = '';
    
    setTimeout(() => {
        addMessage('This is a simulated AI response to: ' + message);
    }, 1000);
}

function clearChat() {
    document.getElementById('messages').innerHTML = '';
}

function saveChat() {
    const messages = document.getElementById('messages').innerText;
    const blob = new Blob([messages], {type: 'text/plain'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'chat-history.txt';
    a.click();
}

document.getElementById('userInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') sendMessage();
});