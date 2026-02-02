class ChatInputConfig {
    constructor(container) {
        this.container = container;
        this.actions = new Map();
        this.init();
    }

    init() {
        this.setupDefaultActions();
        this.bindEvents();
    }

    setupDefaultActions() {
        this.addAction('send', {
            icon: 'fas fa-paper-plane',
            className: 'success',
            callback: this.handleSend.bind(this),
            tooltip: 'Send message'
        });

        this.addAction('voice', {
            icon: 'fas fa-microphone',
            className: 'secondary',
            callback: this.handleVoice.bind(this),
            tooltip: 'Voice input'
        });

        this.addAction('attach', {
            icon: 'fas fa-paperclip',
            className: 'secondary',
            callback: this.handleAttach.bind(this),
            tooltip: 'Attach file'
        });

        this.addAction('emoji', {
            icon: 'fas fa-smile',
            className: 'warning',
            callback: this.handleEmoji.bind(this),
            tooltip: 'Add emoji'
        });
    }

    addAction(id, config) {
        this.actions.set(id, config);
        this.renderAction(id, config);
    }

    renderAction(id, config) {
        const btn = document.createElement('button');
        btn.className = `action-btn ${config.className}`;
        btn.id = `${id}Btn`;
        btn.title = config.tooltip;
        btn.innerHTML = `<i class="${config.icon}"></i>`;
        btn.onclick = config.callback;
        return btn;
    }

    handleSend() {
        const input = this.container.querySelector('.chat-input');
        console.log('Sending:', input.value);
        input.value = '';
    }

    handleVoice() {
        console.log('Voice input activated');
    }

    handleAttach() {
        console.log('File attachment');
    }

    handleEmoji() {
        console.log('Emoji picker');
    }

    bindEvents() {
        const input = this.container.querySelector('.chat-input');
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });
    }
}