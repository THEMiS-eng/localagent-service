class SkillsRegistry {
    constructor() {
        this.skills = new Map();
        this.categories = new Map();
        this.listeners = new Set();
    }

    register(skillId, skillDefinition) {
        if (!skillId || !skillDefinition) {
            throw new Error('Skill ID and definition are required');
        }

        if (this.skills.has(skillId)) {
            console.warn(`Skill ${skillId} already registered, updating...`);
        }

        const skill = {
            id: skillId,
            name: skillDefinition.name || skillId,
            description: skillDefinition.description || '',
            category: skillDefinition.category || 'general',
            version: skillDefinition.version || '1.0.0',
            handler: skillDefinition.handler,
            metadata: skillDefinition.metadata || {},
            registeredAt: new Date().toISOString()
        };

        this.skills.set(skillId, skill);
        this.addToCategory(skill.category, skillId);
        this.notifyListeners('register', skill);

        return skill;
    }

    unregister(skillId) {
        const skill = this.skills.get(skillId);
        if (!skill) return false;

        this.skills.delete(skillId);
        this.removeFromCategory(skill.category, skillId);
        this.notifyListeners('unregister', skill);
        return true;
    }

    get(skillId) {
        return this.skills.get(skillId);
    }

    getAll() {
        return Array.from(this.skills.values());
    }

    getByCategory(category) {
        const skillIds = this.categories.get(category) || new Set();
        return Array.from(skillIds).map(id => this.skills.get(id)).filter(Boolean);
    }

    addToCategory(category, skillId) {
        if (!this.categories.has(category)) {
            this.categories.set(category, new Set());
        }
        this.categories.get(category).add(skillId);
    }

    removeFromCategory(category, skillId) {
        const categorySkills = this.categories.get(category);
        if (categorySkills) {
            categorySkills.delete(skillId);
        }
    }

    addListener(callback) {
        this.listeners.add(callback);
    }

    removeListener(callback) {
        this.listeners.delete(callback);
    }

    notifyListeners(event, skill) {
        this.listeners.forEach(callback => {
            try {
                callback(event, skill);
            } catch (error) {
                console.error('Listener error:', error);
            }
        });
    }
}

module.exports = SkillsRegistry;