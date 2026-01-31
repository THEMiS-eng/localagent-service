class ModuleLoader {
    constructor() {
        this.modules = new Map();
        this.eventBus = null;
    }

    setEventBus(eventBus) {
        this.eventBus = eventBus;
    }

    async loadModule(moduleName, moduleClass) {
        try {
            const moduleInstance = new moduleClass(this.eventBus);
            await moduleInstance.initialize();
            this.modules.set(moduleName, moduleInstance);
            this.eventBus?.emit('moduleLoaded', { name: moduleName });
            return moduleInstance;
        } catch (error) {
            console.error(`Failed to load module ${moduleName}:`, error);
            throw error;
        }
    }

    getModule(moduleName) {
        return this.modules.get(moduleName);
    }

    async unloadModule(moduleName) {
        const module = this.modules.get(moduleName);
        if (module) {
            await module.destroy();
            this.modules.delete(moduleName);
            this.eventBus?.emit('moduleUnloaded', { name: moduleName });
        }
    }

    listModules() {
        return Array.from(this.modules.keys());
    }

    async shutdown() {
        for (const [name, module] of this.modules) {
            await module.destroy();
        }
        this.modules.clear();
    }
}

module.exports = ModuleLoader;