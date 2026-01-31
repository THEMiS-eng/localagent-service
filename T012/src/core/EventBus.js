class EventBus {
    constructor() {
        this.events = new Map();
        this.middleware = [];
    }

    on(event, callback, context = null) {
        if (!this.events.has(event)) {
            this.events.set(event, []);
        }
        
        this.events.get(event).push({
            callback,
            context,
            once: false
        });
    }

    once(event, callback, context = null) {
        if (!this.events.has(event)) {
            this.events.set(event, []);
        }
        
        this.events.get(event).push({
            callback,
            context,
            once: true
        });
    }

    emit(event, data = null) {
        // Apply middleware
        let processedData = data;
        for (const middleware of this.middleware) {
            processedData = middleware(event, processedData);
        }

        const listeners = this.events.get(event);
        if (!listeners) return;

        const toRemove = [];
        listeners.forEach((listener, index) => {
            try {
                if (listener.context) {
                    listener.callback.call(listener.context, processedData);
                } else {
                    listener.callback(processedData);
                }
                
                if (listener.once) {
                    toRemove.push(index);
                }
            } catch (error) {
                console.error(`Error in event listener for ${event}:`, error);
            }
        });

        // Remove 'once' listeners
        toRemove.reverse().forEach(index => listeners.splice(index, 1));
    }

    off(event, callback) {
        const listeners = this.events.get(event);
        if (!listeners) return;
        
        const index = listeners.findIndex(l => l.callback === callback);
        if (index !== -1) {
            listeners.splice(index, 1);
        }
    }
}

export default new EventBus();