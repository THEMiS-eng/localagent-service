const fs = require('fs').promises;
const path = require('path');

class SkillsLoader {
    constructor(registry) {
        this.registry = registry;
        this.loadedPaths = new Set();
        this.watchedDirs = new Set();
    }

    async loadSkill(skillPath) {
        try {
            const absolutePath = path.resolve(skillPath);
            
            if (this.loadedPaths.has(absolutePath)) {
                console.warn(`Skill already loaded from ${absolutePath}`);
                return null;
            }

            const stats = await fs.stat(absolutePath);
            
            if (stats.isFile()) {
                return await this.loadSkillFile(absolutePath);
            } else if (stats.isDirectory()) {
                return await this.loadSkillDirectory(absolutePath);
            }

            throw new Error(`Invalid skill path: ${skillPath}`);
        } catch (error) {
            console.error(`Failed to load skill from ${skillPath}:`, error);
            throw error;
        }
    }

    async loadSkillFile(filePath) {
        try {
            delete require.cache[require.resolve(filePath)];
            const skillModule = require(filePath);
            
            const skillDefinition = typeof skillModule === 'function' 
                ? { handler: skillModule }
                : skillModule;

            if (!skillDefinition.handler) {
                throw new Error('Skill must export a handler function');
            }

            const skillId = skillDefinition.id || path.basename(filePath, '.js');
            const skill = this.registry.register(skillId, skillDefinition);
            
            this.loadedPaths.add(filePath);
            console.log(`Loaded skill: ${skillId} from ${filePath}`);
            
            return skill;
        } catch (error) {
            console.error(`Error loading skill file ${filePath}:`, error);
            throw error;
        }
    }

    async loadSkillDirectory(dirPath) {
        const packagePath = path.join(dirPath, 'package.json');
        const indexPath = path.join(dirPath, 'index.js');
        
        try {
            const packageData = JSON.parse(await fs.readFile(packagePath, 'utf8'));
            const mainFile = packageData.main || 'index.js';
            const skillPath = path.join(dirPath, mainFile);
            
            const skill = await this.loadSkillFile(skillPath);
            skill.metadata = { ...skill.metadata, ...packageData };
            
            return skill;
        } catch (error) {
            if (await fs.access(indexPath).then(() => true).catch(() => false)) {
                return await this.loadSkillFile(indexPath);
            }
            throw error;
        }
    }

    async loadDirectory(dirPath) {
        const skills = [];
        
        try {
            const entries = await fs.readdir(dirPath);
            
            for (const entry of entries) {
                const entryPath = path.join(dirPath, entry);
                try {
                    const skill = await this.loadSkill(entryPath);
                    if (skill) skills.push(skill);
                } catch (error) {
                    console.error(`Failed to load ${entryPath}:`, error.message);
                }
            }
        } catch (error) {
            console.error(`Failed to read directory ${dirPath}:`, error);
        }
        
        return skills;
    }
}

module.exports = SkillsLoader;