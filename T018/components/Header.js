class Header {
    constructor() {
        this.element = null;
        this.init();
    }

    init() {
        this.element = document.createElement('header');
        this.element.className = 'app-header';
        this.element.innerHTML = `
            <div class="header-content">
                <div class="header-left">
                    <h1 class="app-title">LocalAgent Service</h1>
                    <span class="version-badge">v3.3.011</span>
                </div>
                <div class="header-right">
                    <div class="status-indicator">
                        <span class="status-dot" id="status-dot"></span>
                        <span class="status-text" id="status-text">Disconnected</span>
                    </div>
                    <button class="btn btn-primary" id="connect-btn">Connect</button>
                </div>
            </div>
        `;
        
        this.bindEvents();
    }

    bindEvents() {
        const connectBtn = this.element.querySelector('#connect-btn');
        connectBtn.addEventListener('click', () => {
            this.toggleConnection();
        });
    }

    toggleConnection() {
        const statusDot = this.element.querySelector('#status-dot');
        const statusText = this.element.querySelector('#status-text');
        const connectBtn = this.element.querySelector('#connect-btn');
        
        if (statusDot.classList.contains('connected')) {
            statusDot.classList.remove('connected');
            statusText.textContent = 'Disconnected';
            connectBtn.textContent = 'Connect';
        } else {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
            connectBtn.textContent = 'Disconnect';
        }
    }

    render() {
        return this.element;
    }
}