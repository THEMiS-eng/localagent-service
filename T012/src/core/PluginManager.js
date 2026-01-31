class PluginManager {
    constructor() {
        this.plugins = new Map();
        this.hooks = new Map();
        this.enabled = new Set();
    }

    register(name, plugin) {
        if (this.plugins.has(name)) {
            throw new Error(`Plugin ${name} already registered`);
        }

        // Validate plugin structure
        if (!plugin.initialize || typeof plugin.initialize !== 'function') {
            throw new Error(`Plugin ${name} must have initialize method`);
        }

        this.plugins.set(name, {
            plugin,
            initialized: false,
            metadata: plugin.metadata || {}
        });
    }

    async enable(name) {
        const pluginData = this.plugins.get(name);
        if (!pluginData) {
            throw new Error(`Plugin ${name} not found`);
        }

        if (!pluginData.initialized) {
            await pluginData.plugin.initialize();
            pluginData.initialized = true;
        }

        this.enabled.add(name);
        
        // Register plugin hooks
        if (pluginData.plugin.hooks) {
            for (const [hookName, handler] of Object.entries(pluginData.plugin.hooks)) {
                this.addHook(hookName, handler);
            }
        }
    }

    disable(name) {
        const pluginData = this.plugins.get(name);
        if (!pluginData) return;

        this.enabled.delete(name);
        
        // Cleanup plugin
        if (pluginData.plugin.cleanup) {
            pluginData.plugin.cleanup();
        }
    }

    addHook(name, handler) {
        if (!this.hooks.has(name)) {
            this.hooks.set(name, []);
        }
        this.hooks.get(name).push(handler);
    }

    async executeHook(name, data) {
        const handlers = this.hooks.get(name) || [];
        let result = data;
        
        for (const handler of handlers) {
            result = await handler(result);
        }
        
        return result;
    }

    getEnabled() {
        return Array.from(this.enabled);
    }
}

export default new PluginManager();