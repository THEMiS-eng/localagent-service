"""
LocalAgent Skills System
Compatible with Anthropic Skill Creator format (SKILL.md)

Skills are modular packages that extend Claude's capabilities with:
- Specialized workflows
- Domain expertise
- Scripts and tools
- Reference documentation
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Skill:
    """
    A loaded skill following Anthropic format.
    
    Structure:
        skill-name/
        ├── SKILL.md (required)
        ├── scripts/
        ├── references/
        └── assets/
    """
    name: str
    description: str
    path: Path
    body: str = ""  # Markdown content after frontmatter
    
    # Resource paths
    scripts_dir: Optional[Path] = None
    references_dir: Optional[Path] = None
    assets_dir: Optional[Path] = None
    
    # Metadata
    loaded_at: datetime = None
    active: bool = False
    
    def __post_init__(self):
        if self.loaded_at is None:
            self.loaded_at = datetime.now()
        
        # Set resource directories if they exist
        if self.path:
            scripts = self.path / "scripts"
            references = self.path / "references"
            assets = self.path / "assets"
            
            self.scripts_dir = scripts if scripts.exists() else None
            self.references_dir = references if references.exists() else None
            self.assets_dir = assets if assets.exists() else None
    
    def get_scripts(self) -> List[Path]:
        """List available scripts."""
        if not self.scripts_dir:
            return []
        return list(self.scripts_dir.glob("*.py")) + list(self.scripts_dir.glob("*.sh"))
    
    def get_references(self) -> List[Path]:
        """List available reference documents."""
        if not self.references_dir:
            return []
        return list(self.references_dir.glob("*.md"))
    
    def get_assets(self) -> List[Path]:
        """List available assets."""
        if not self.assets_dir:
            return []
        return list(self.assets_dir.rglob("*"))
    
    def read_reference(self, name: str) -> Optional[str]:
        """Read a reference document by name."""
        if not self.references_dir:
            return None
        
        ref_path = self.references_dir / name
        if not ref_path.exists():
            ref_path = self.references_dir / f"{name}.md"
        
        if ref_path.exists():
            return ref_path.read_text()
        return None


class SkillLoader:
    """
    Loads skills from SKILL.md files following Anthropic format.
    """
    
    @staticmethod
    def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
        """
        Parse YAML frontmatter from SKILL.md content.
        
        Returns:
            (frontmatter_dict, body_content)
        """
        if not content.startswith('---'):
            return {}, content
        
        match = re.match(r'^---\n(.*?)\n---\n?(.*)', content, re.DOTALL)
        if not match:
            return {}, content
        
        frontmatter_text = match.group(1)
        body = match.group(2)
        
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if not isinstance(frontmatter, dict):
                return {}, content
            return frontmatter, body
        except yaml.YAMLError:
            return {}, content
    
    @staticmethod
    def validate_skill(skill_path: Path) -> tuple[bool, str]:
        """
        Validate a skill directory.
        
        Returns:
            (is_valid, message)
        """
        skill_md = skill_path / "SKILL.md"
        
        if not skill_md.exists():
            return False, "SKILL.md not found"
        
        content = skill_md.read_text()
        frontmatter, _ = SkillLoader.parse_frontmatter(content)
        
        if 'name' not in frontmatter:
            return False, "Missing 'name' in frontmatter"
        
        if 'description' not in frontmatter:
            return False, "Missing 'description' in frontmatter"
        
        name = frontmatter['name']
        if not re.match(r'^[a-z0-9-]+$', name):
            return False, f"Name '{name}' must be kebab-case"
        
        if name != skill_path.name:
            return False, f"Name '{name}' doesn't match directory '{skill_path.name}'"
        
        return True, "Valid"
    
    @staticmethod
    def load_skill(skill_path: Path) -> Optional[Skill]:
        """
        Load a skill from a directory.
        
        Args:
            skill_path: Path to skill directory containing SKILL.md
        
        Returns:
            Skill object or None if invalid
        """
        skill_md = skill_path / "SKILL.md"
        
        if not skill_md.exists():
            return None
        
        content = skill_md.read_text()
        frontmatter, body = SkillLoader.parse_frontmatter(content)
        
        if 'name' not in frontmatter or 'description' not in frontmatter:
            return None
        
        return Skill(
            name=frontmatter['name'],
            description=frontmatter['description'],
            path=skill_path,
            body=body
        )


class SkillManager:
    """
    Manages skill discovery, loading, and activation.
    """
    
    DEFAULT_SKILLS_DIR = Path.home() / ".localagent" / "skills"
    
    def __init__(self, skills_dir: Path = None):
        self.skills_dir = skills_dir or self.DEFAULT_SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy default skills if not already present
        self._install_default_skills()
        
        self._available: Dict[str, Skill] = {}
        self._active: Dict[str, Skill] = {}
    
    def _install_default_skills(self):
        """Copy default skills from package to user skills directory."""
        import shutil
        
        # Find default_skills relative to this package
        package_dir = Path(__file__).parent.parent.parent
        default_skills_dir = package_dir / "default_skills"
        
        if not default_skills_dir.exists():
            return
        
        for skill_dir in default_skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            target_dir = self.skills_dir / skill_dir.name
            if not target_dir.exists():
                shutil.copytree(skill_dir, target_dir)
                print(f"[Skills] Installed: {skill_dir.name}")
    
    def discover(self) -> List[Skill]:
        """
        Discover all skills in the skills directory.
        
        Returns:
            List of discovered skills
        """
        self._available.clear()
        
        if not self.skills_dir.exists():
            return []
        
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill = SkillLoader.load_skill(skill_dir)
            if skill:
                self._available[skill.name] = skill
        
        return list(self._available.values())
    
    def get_available(self) -> List[Skill]:
        """Get list of available skills."""
        return list(self._available.values())
    
    def get_active(self) -> List[Skill]:
        """Get list of active skills."""
        return list(self._active.values())
    
    def activate(self, skill_name: str) -> bool:
        """
        Activate a skill.
        
        Args:
            skill_name: Name of skill to activate
        
        Returns:
            True if activated successfully
        """
        if skill_name not in self._available:
            # Try to load it
            skill_path = self.skills_dir / skill_name
            skill = SkillLoader.load_skill(skill_path)
            if skill:
                self._available[skill_name] = skill
            else:
                return False
        
        skill = self._available[skill_name]
        skill.active = True
        self._active[skill_name] = skill
        return True
    
    def deactivate(self, skill_name: str) -> bool:
        """
        Deactivate a skill.
        
        Args:
            skill_name: Name of skill to deactivate
        
        Returns:
            True if deactivated successfully
        """
        if skill_name not in self._active:
            return False
        
        skill = self._active.pop(skill_name)
        skill.active = False
        return True
    
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._available.get(skill_name) or self._active.get(skill_name)
    
    def build_context(self) -> str:
        """
        Build context string from active skills for LLM.
        
        Returns:
            Formatted context string with active skill instructions
        """
        if not self._active:
            return ""
        
        lines = ["=== ACTIVE SKILLS ===", ""]
        
        for skill in self._active.values():
            lines.append(f"## {skill.name}")
            lines.append(skill.description)
            lines.append("")
            
            # Include skill body (instructions)
            if skill.body:
                lines.append(skill.body)
                lines.append("")
        
        return "\n".join(lines)


# Global manager instance
_manager: Optional[SkillManager] = None


def get_manager() -> SkillManager:
    """Get the global skill manager instance."""
    global _manager
    if _manager is None:
        _manager = SkillManager()
        _manager.discover()
        # Auto-activate all discovered skills
        for skill in _manager.get_available():
            _manager.activate(skill.name)
    return _manager


# Convenience functions
def discover_skills() -> List[Skill]:
    """Discover all available skills."""
    return get_manager().discover()


def get_available_skills() -> List[Skill]:
    """Get list of available skills."""
    return get_manager().get_available()


def get_active_skills() -> List[Skill]:
    """Get list of active skills."""
    return get_manager().get_active()


def activate_skill(name: str) -> bool:
    """Activate a skill by name."""
    return get_manager().activate(name)


def deactivate_skill(name: str) -> bool:
    """Deactivate a skill by name."""
    return get_manager().deactivate(name)


def build_skill_context() -> str:
    """Build LLM context from active skills."""
    return get_manager().build_context()


__all__ = [
    "Skill",
    "SkillLoader",
    "SkillManager",
    "get_manager",
    "discover_skills",
    "get_available_skills",
    "get_active_skills",
    "activate_skill",
    "deactivate_skill",
    "build_skill_context"
]
