class BaseModule {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.name = this.constructor.name;
        this.initialized = false;
        this.config = {};
    }

    async initialize() {
        if (this.initialized) {
            return;
        }
        
        await this.onInitialize();
        this.initialized = true;
        this.eventBus?.emit('moduleInitialized', { name: this.name });
    }

    async onInitialize() {
        // Override in subclasses
    }

    async destroy() {
        if (!this.initialized) {
            return;
        }

        await this.onDestroy();
        this.initialized = false;
        this.eventBus?.emit('moduleDestroyed', { name: this.name });
    }

    async onDestroy() {
        // Override in subclasses
    }

    setConfig(config) {
        this.config = { ...this.config, ...config };
    }

    getConfig(key) {
        return key ? this.config[key] : this.config;
    }

    emit(event, data) {
        this.eventBus?.emit(event, data);
    }

    on(event, listener) {
        return this.eventBus?.on(event, listener);
    }

    isInitialized() {
        return this.initialized;
    }
}

module.exports = BaseModule;