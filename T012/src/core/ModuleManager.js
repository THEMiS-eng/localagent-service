class ModuleManager {
    constructor() {
        this.modules = new Map();
        this.dependencies = new Map();
        this.initialized = false;
    }

    register(name, moduleClass, dependencies = []) {
        if (this.modules.has(name)) {
            throw new Error(`Module ${name} already registered`);
        }
        
        this.modules.set(name, {
            class: moduleClass,
            instance: null,
            dependencies,
            initialized: false
        });
        
        this.dependencies.set(name, dependencies);
    }

    async initialize(name) {
        const module = this.modules.get(name);
        if (!module) {
            throw new Error(`Module ${name} not found`);
        }

        if (module.initialized) {
            return module.instance;
        }

        // Initialize dependencies first
        for (const dep of module.dependencies) {
            await this.initialize(dep);
        }

        // Create and initialize module
        module.instance = new module.class();
        if (module.instance.initialize) {
            await module.instance.initialize();
        }
        
        module.initialized = true;
        return module.instance;
    }

    get(name) {
        const module = this.modules.get(name);
        return module?.instance || null;
    }

    async initializeAll() {
        const names = Array.from(this.modules.keys());
        await Promise.all(names.map(name => this.initialize(name)));
        this.initialized = true;
    }
}

export default new ModuleManager();