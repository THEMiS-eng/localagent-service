const SkillsRegistry = require('./skills-registry');
const SkillsLoader = require('./skills-loader');
const path = require('path');

class SkillsEngine {
    constructor(options = {}) {
        this.registry = new SkillsRegistry();
        this.loader = new SkillsLoader(this.registry);
        this.defaultSkillsPath = options.skillsPath || './skills';
        this.autoLoad = options.autoLoad !== false;
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) {
            console.warn('Skills engine already initialized');
            return;
        }

        console.log('Initializing skills engine...');
        
        if (this.autoLoad) {
            try {
                await this.loadDefaultSkills();
            } catch (error) {
                console.warn('Failed to load default skills:', error.message);
            }
        }

        this.initialized = true;
        console.log('Skills engine initialized');
    }

    async loadDefaultSkills() {
        const skillsPath = path.resolve(this.defaultSkillsPath);
        console.log(`Loading skills from: ${skillsPath}`);
        
        try {
            const skills = await this.loader.loadDirectory(skillsPath);
            console.log(`Loaded ${skills.length} skills`);
            return skills;
        } catch (error) {
            console.error('Error loading default skills:', error);
            throw error;
        }
    }

    async executeSkill(skillId, ...args) {
        const skill = this.registry.get(skillId);
        
        if (!skill) {
            throw new Error(`Skill not found: ${skillId}`);
        }

        if (typeof skill.handler !== 'function') {
            throw new Error(`Invalid skill handler for: ${skillId}`);
        }

        try {
            console.log(`Executing skill: ${skillId}`);
            const result = await skill.handler(...args);
            return result;
        } catch (error) {
            console.error(`Skill execution error (${skillId}):`, error);
            throw error;
        }
    }

    getSkills() {
        return this.registry.getAll();
    }

    getSkill(skillId) {
        return this.registry.get(skillId);
    }

    getSkillsByCategory(category) {
        return this.registry.getByCategory(category);
    }

    async loadSkill(skillPath) {
        return await this.loader.loadSkill(skillPath);
    }

    unloadSkill(skillId) {
        return this.registry.unregister(skillId);
    }

    onSkillEvent(callback) {
        this.registry.addListener(callback);
    }

    removeSkillListener(callback) {
        this.registry.removeListener(callback);
    }
}

module.exports = SkillsEngine;