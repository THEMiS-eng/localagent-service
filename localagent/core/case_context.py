"""
LocalAgent - CORE: Case Context Manager
Manages the active case context and injects it into skills.

The Case Context includes:
- framework: RICS, FAR, FIDIC, NEC, CUSTOM
- methodology: AACE, SCL, CUSTOM
- jurisdiction: US_FEDERAL, UK, EU, INTERNATIONAL
- contract_type: FIDIC, NEC, JCT, FAR, CUSTOM
- dispute_type: delay, quantum, both
- forum: arbitration, adjudication, litigation, mediation, expert_determination
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json


@dataclass
class CaseContext:
    """Active case context that influences skill behavior."""
    
    # Core identifiers
    case_id: str = ""
    case_name: str = ""
    
    # Framework & Methodology
    framework: str = "RICS"  # RICS, FAR, FIDIC, NEC, CUSTOM
    methodology: str = "AACE"  # AACE, SCL, CUSTOM
    
    # Jurisdiction
    jurisdiction: str = "INTERNATIONAL"  # US_FEDERAL, UK, EU, INTERNATIONAL
    
    # Contract
    contract_type: str = ""  # FIDIC, NEC, JCT, FAR, etc.
    contract_ref: str = ""  # Contract number/reference
    
    # Dispute specifics
    dispute_type: str = "both"  # delay, quantum, both
    forum: str = ""  # arbitration, adjudication, litigation, mediation, expert_determination
    
    # Parties
    client: str = ""
    opponent: str = ""
    
    # Special skills for this case
    special_skills: list = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaseContext":
        # Filter only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)
    
    def get_skill_context(self) -> Dict[str, Any]:
        """
        Return context dict to be injected into skills.
        This is what skills receive to adapt their behavior.
        """
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "framework": self.framework,
            "methodology": self.methodology,
            "jurisdiction": self.jurisdiction,
            "contract_type": self.contract_type,
            "dispute_type": self.dispute_type,
            "forum": self.forum,
            # Derived helpers
            "is_us_federal": self.jurisdiction == "US_FEDERAL",
            "is_uk": self.jurisdiction == "UK",
            "uses_aace": self.methodology == "AACE",
            "uses_scl": self.methodology == "SCL",
            "is_delay_case": self.dispute_type in ("delay", "both"),
            "is_quantum_case": self.dispute_type in ("quantum", "both"),
        }


class CaseContextManager:
    """Singleton manager for the active case context."""
    
    _instance = None
    _context: Optional[CaseContext] = None
    _storage_path: Path = Path.home() / ".localagent" / "case_context.json"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._context is None:
            self._load()
    
    def _load(self):
        """Load context from storage."""
        if self._storage_path.exists():
            try:
                data = json.loads(self._storage_path.read_text())
                self._context = CaseContext.from_dict(data)
            except Exception:
                self._context = CaseContext()
        else:
            self._context = CaseContext()
    
    def _save(self):
        """Save context to storage."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(json.dumps(self._context.to_dict(), indent=2))
    
    def get_context(self) -> CaseContext:
        """Get the active case context."""
        return self._context
    
    def set_context(self, context: CaseContext):
        """Set the active case context."""
        self._context = context
        self._save()
    
    def update_context(self, **kwargs):
        """Update specific fields of the context."""
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)
        self._save()
    
    def set_from_case(self, case_data: Dict[str, Any]):
        """
        Set context from a THEMIS CASE object.
        Maps THEMIS CASE structure to CaseContext.
        """
        self._context = CaseContext(
            case_id=case_data.get("id", ""),
            case_name=case_data.get("name", ""),
            framework=case_data.get("framework", "RICS"),
            methodology=case_data.get("methodology", "AACE"),
            jurisdiction=case_data.get("jurisdiction", "INTERNATIONAL"),
            contract_type=case_data.get("contract_type", ""),
            contract_ref=case_data.get("contract", ""),
            dispute_type=case_data.get("dispute_type", "both"),
            forum=case_data.get("forum", ""),
            client=case_data.get("client", ""),
            opponent=case_data.get("opponent", ""),
            special_skills=case_data.get("special_skills", [])
        )
        self._save()
    
    def clear(self):
        """Clear the active context."""
        self._context = CaseContext()
        self._save()
    
    def get_skill_context(self) -> Dict[str, Any]:
        """Get context dict for skill injection."""
        return self._context.get_skill_context()


# Singleton accessor
def get_case_context_manager() -> CaseContextManager:
    return CaseContextManager()


def get_active_context() -> CaseContext:
    return get_case_context_manager().get_context()


def get_skill_context() -> Dict[str, Any]:
    return get_case_context_manager().get_skill_context()
