class Sidebar {
    constructor() {
        this.element = null;
        this.activeTab = 'dashboard';
        this.init();
    }

    init() {
        this.element = document.createElement('nav');
        this.element.className = 'sidebar';
        this.element.innerHTML = `
            <div class="sidebar-content">
                <ul class="nav-menu">
                    <li class="nav-item">
                        <a href="#" class="nav-link active" data-tab="dashboard">
                            <i class="icon-dashboard"></i>
                            Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a href="#" class="nav-link" data-tab="services">
                            <i class="icon-services"></i>
                            Services
                        </a>
                    </li>
                    <li class="nav-item">
                        <a href="#" class="nav-link" data-tab="logs">
                            <i class="icon-logs"></i>
                            Logs
                        </a>
                    </li>
                    <li class="nav-item">
                        <a href="#" class="nav-link" data-tab="settings">
                            <i class="icon-settings"></i>
                            Settings
                        </a>
                    </li>
                </ul>
            </div>
        `;
        
        this.bindEvents();
    }

    bindEvents() {
        const navLinks = this.element.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tab = e.target.closest('.nav-link').dataset.tab;
                this.setActiveTab(tab);
            });
        });
    }

    setActiveTab(tab) {
        const navLinks = this.element.querySelectorAll('.nav-link');
        navLinks.forEach(link => link.classList.remove('active'));
        
        const activeLink = this.element.querySelector(`[data-tab="${tab}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
            this.activeTab = tab;
            this.onTabChange(tab);
        }
    }

    onTabChange(tab) {
        const event = new CustomEvent('tabchange', { detail: { tab } });
        document.dispatchEvent(event);
    }

    render() {
        return this.element;
    }
}