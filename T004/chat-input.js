class DynamicChatInput {
    constructor() {
        this.textarea = document.getElementById('chatInput');
        this.sendBtn = document.querySelector('.send-btn');
        this.chatMessages = document.querySelector('.chat-messages');
        this.init();
    }

    init() {
        this.textarea.addEventListener('input', () => this.handleInput());
        this.textarea.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.updateSendButton();
    }

    handleInput() {
        this.autoResize();
        this.updateSendButton();
    }

    autoResize() {
        this.textarea.style.height = 'auto';
        const scrollHeight = this.textarea.scrollHeight;
        const maxHeight = 120;
        
        if (scrollHeight <= maxHeight) {
            this.textarea.style.height = scrollHeight + 'px';
            this.textarea.style.overflowY = 'hidden';
        } else {
            this.textarea.style.height = maxHeight + 'px';
            this.textarea.style.overflowY = 'auto';
        }
    }

    handleKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    updateSendButton() {
        const hasText = this.textarea.value.trim().length > 0;
        this.sendBtn.disabled = !hasText;
    }

    sendMessage() {
        const message = this.textarea.value.trim();
        if (!message) return;

        this.addMessage(message);
        this.textarea.value = '';
        this.textarea.style.height = 'auto';
        this.updateSendButton();
    }

    addMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        messageDiv.textContent = text;
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

function sendMessage() {
    chatInput.sendMessage();
}

const chatInput = new DynamicChatInput();