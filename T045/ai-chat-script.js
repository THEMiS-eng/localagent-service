let isVoiceActive = false;

function toggleSettings() {
    const panel = document.getElementById('settingsPanel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

function updateButtons() {
    const buttons = {
        'showSend': '.send-btn',
        'showVoice': '.voice-btn', 
        'showAttach': '.attach-btn',
        'showClear': '.clear-btn'
    };
    
    Object.entries(buttons).forEach(([checkboxId, selector]) => {
        const checkbox = document.getElementById(checkboxId);
        const button = document.querySelector(selector);
        button.style.display = checkbox.checked ? 'block' : 'none';
    });
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (message) {
        addMessageToChat('You', message);
        input.value = '';
        
        setTimeout(() => {
            addMessageToChat('AI', `I received: "${message}". This is a demo response.`);
        }, 1000);
    }
}

function addMessageToChat(sender, message) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.innerHTML = `<strong>${sender}:</strong> ${message}`;
    messageDiv.style.margin = '10px 0';
    messageDiv.style.padding = '10px';
    messageDiv.style.backgroundColor = sender === 'You' ? '#e3f2fd' : '#f3e5f5';
    messageDiv.style.borderRadius = '8px';
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function toggleVoice() {
    isVoiceActive = !isVoiceActive;
    const voiceBtn = document.querySelector('.voice-btn');
    voiceBtn.style.backgroundColor = isVoiceActive ? '#ff4444' : '#667eea';
    voiceBtn.textContent = isVoiceActive ? '🔴' : '🎤';
}

function attachFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = () => {
        if (input.files[0]) {
            addMessageToChat('System', `File attached: ${input.files[0].name}`);
        }
    };
    input.click();
}

function clearChat() {
    if (confirm('Clear all messages?')) {
        document.getElementById('chatMessages').innerHTML = '';
    }
}

document.getElementById('messageInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});