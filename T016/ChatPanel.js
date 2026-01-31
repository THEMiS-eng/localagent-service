class ChatPanel {
    constructor(container) {
        this.container = container;
        this.messages = [];
        this.init();
    }

    init() {
        this.render();
        this.attachEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="chat-panel">
                <div class="chat-header">
                    <h3>Chat</h3>
                </div>
                <div class="chat-messages" id="chatMessages"></div>
                <div class="chat-input">
                    <input type="text" id="messageInput" placeholder="Type a message..." />
                    <button id="sendButton">Send</button>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');

        sendButton.addEventListener('click', () => this.sendMessage());
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
    }

    sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (message) {
            this.addMessage('user', message);
            input.value = '';
            this.onMessageSent?.(message);
        }
    }

    addMessage(sender, content, timestamp = new Date()) {
        const message = { sender, content, timestamp };
        this.messages.push(message);
        this.updateMessagesDisplay();
    }

    updateMessagesDisplay() {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.innerHTML = this.messages.map(msg => `
            <div class="message ${msg.sender}">
                <span class="content">${msg.content}</span>
                <span class="timestamp">${msg.timestamp.toLocaleTimeString()}</span>
            </div>
        `).join('');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}