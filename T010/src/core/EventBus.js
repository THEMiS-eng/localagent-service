class EventBus {
    constructor() {
        this.events = new Map();
    }

    on(event, listener) {
        if (!this.events.has(event)) {
            this.events.set(event, new Set());
        }
        this.events.get(event).add(listener);
        return () => this.off(event, listener);
    }

    off(event, listener) {
        if (this.events.has(event)) {
            this.events.get(event).delete(listener);
            if (this.events.get(event).size === 0) {
                this.events.delete(event);
            }
        }
    }

    emit(event, data) {
        if (this.events.has(event)) {
            const listeners = this.events.get(event);
            listeners.forEach(listener => {
                try {
                    listener(data);
                } catch (error) {
                    console.error(`Event listener error for ${event}:`, error);
                }
            });
        }
    }

    async emitAsync(event, data) {
        if (this.events.has(event)) {
            const listeners = Array.from(this.events.get(event));
            await Promise.all(listeners.map(async listener => {
                try {
                    await listener(data);
                } catch (error) {
                    console.error(`Async event listener error for ${event}:`, error);
                }
            }));
        }
    }

    clear() {
        this.events.clear();
    }
}

module.exports = EventBus;