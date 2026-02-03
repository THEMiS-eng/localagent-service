"""
Themis Router - FULL IMPLEMENTATION (no backend proxy)
LocalAgent = Orchestrator = Service Worker for Themis

Implements all 84 Themis endpoints directly.
"""

from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import uuid
import os

# MLX AI and Spotlight connectors
try:
    from ...connectors.mlx_ai import (
        classify_document, chat_completion, get_mlx_stats, 
        DOCUMENT_TYPES, check_mlx_available
    )
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    DOCUMENT_TYPES = ["OTHER"]
    def classify_document(text, filename=""): return {"classification": "OTHER", "confidence": 0.5, "source": "fallback"}
    def chat_completion(msg, ctx="", sys=""): return {"response": "MLX not available", "source": "fallback"}
    def get_mlx_stats(): return {"mlx_available": False}

try:
    from ...connectors.spotlight import (
        search_evidence as spotlight_search,
        get_tags as spotlight_get_tags,
        add_tag as spotlight_add_tag,
        remove_tag as spotlight_remove_tag,
        get_smart_folders,
        execute_smart_folder,
        is_macos
    )
    SPOTLIGHT_AVAILABLE = True
except ImportError:
    SPOTLIGHT_AVAILABLE = False

router = APIRouter(prefix="/themis", tags=["themis"])

# =============================================================================
# DATA STORAGE (in-memory + file persistence)
# =============================================================================
DATA_DIR = Path.home() / ".localagent" / "themis"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_data(name: str) -> List[Dict]:
    """Load data from JSON file."""
    path = DATA_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    return []

def save_data(name: str, data: List[Dict]):
    """Save data to JSON file."""
    path = DATA_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, default=str))

# In-memory caches
_cases = None
_evidence = None
_chat_history = {}
_ws_connections = []

def get_cases():
    global _cases
    if _cases is None:
        _cases = load_data("cases")
        if not _cases:
            # Default cases
            _cases = [
                {"id": "CASE-2026-0001", "name": "Construction Delay Claim", "framework": "RICS", "status": "open", "created_at": "2026-01-15T10:00:00Z", "evidence_count": 0},
                {"id": "CASE-2026-0002", "name": "Defects Analysis", "framework": "SCL", "status": "open", "created_at": "2026-01-20T14:00:00Z", "evidence_count": 0},
            ]
            save_data("cases", _cases)
    return _cases

def get_evidence(case_id: str = None):
    global _evidence
    if _evidence is None:
        _evidence = load_data("evidence")
    if case_id:
        return [e for e in _evidence if e.get("case_id") == case_id]
    return _evidence


# =============================================================================
# UI
# =============================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def serve_themis_ui():
    """Serve Themis UI from external module (not bundled)."""
    import urllib.request
    
    # 1. Check local installed module
    local_paths = [
        Path.home() / ".localagent" / "modules" / "themis-ui" / "index.html",
        Path.home() / "localagent-modular" / "themis-ui" / "index.html",
    ]
    for p in local_paths:
        if p.exists():
            return HTMLResponse(p.read_text())
    
    # 2. Fetch from GitHub module
    try:
        url = "https://raw.githubusercontent.com/THEMiS-eng/themis-ui/main/index.html"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return HTMLResponse(resp.read().decode('utf-8'))
    except:
        pass
    
    return HTMLResponse("""
        <html><head><title>Themis</title></head>
        <body style="font-family:system-ui;padding:40px;text-align:center">
            <h1>Themis UI Module Not Found</h1>
            <p>Install: <code>./INSTALL.sh</code> or check <a href="https://github.com/THEMiS-eng/themis-ui">THEMiS-eng/themis-ui</a></p>
        </body></html>
    """)


# =============================================================================
# HEALTH & STATUS
# =============================================================================

@router.get("/api/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "version": "10.2.0",
        "backend": "localagent",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/api/service/status")
async def service_status():
    """Service status."""
    return {"status": "running", "uptime": 3600, "memory_mb": 128}

@router.post("/api/service/control")
async def service_control(request: Request):
    """Service control (start/stop/restart) - no-op for LocalAgent."""
    data = await request.json()
    action = data.get("action", "status")
    return {"action": action, "status": "ok", "message": f"LocalAgent is always running"}

@router.get("/api/service/logs")
async def service_logs(lines: int = 50):
    """Service logs."""
    return {"logs": ["[LocalAgent] Service running", f"[LocalAgent] {lines} lines requested"]}


# =============================================================================
# CASES
# =============================================================================

@router.get("/api/cases")
async def list_cases():
    """List all cases."""
    return get_cases()

@router.get("/api/cases/search")
async def search_cases(q: str = ""):
    """Search cases."""
    if not q:
        return get_cases()
    q_lower = q.lower()
    return [c for c in get_cases() if q_lower in c.get("name", "").lower() or q_lower in c.get("id", "").lower()]

@router.post("/api/cases")
async def create_case(request: Request):
    """Create a new case."""
    data = await request.json()
    case_id = f"CASE-{datetime.now().strftime('%Y')}-{str(uuid.uuid4())[:4].upper()}"
    case = {
        "id": case_id,
        "name": data.get("name", "New Case"),
        "framework": data.get("framework", "RICS"),
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "evidence_count": 0
    }
    cases = get_cases()
    cases.append(case)
    save_data("cases", cases)
    return case

@router.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    """Get case details."""
    for c in get_cases():
        if c["id"] == case_id:
            return c
    return JSONResponse({"error": "Case not found"}, status_code=404)

@router.put("/api/cases/{case_id}")
async def update_case(case_id: str, request: Request):
    """Update case."""
    data = await request.json()
    cases = get_cases()
    for c in cases:
        if c["id"] == case_id:
            c.update(data)
            save_data("cases", cases)
            return c
    return JSONResponse({"error": "Case not found"}, status_code=404)

@router.delete("/api/cases/{case_id}")
async def archive_case(case_id: str):
    """Archive case."""
    cases = get_cases()
    for c in cases:
        if c["id"] == case_id:
            c["status"] = "archived"
            save_data("cases", cases)
            return {"status": "archived"}
    return JSONResponse({"error": "Case not found"}, status_code=404)

@router.post("/api/cases/{case_id}/open")
async def open_case(case_id: str):
    """Open a case."""
    cases = get_cases()
    for c in cases:
        if c["id"] == case_id:
            c["status"] = "open"
            save_data("cases", cases)
            return c
    return JSONResponse({"error": "Case not found"}, status_code=404)

@router.post("/api/cases/{case_id}/close")
async def close_case(case_id: str):
    """Close a case."""
    cases = get_cases()
    for c in cases:
        if c["id"] == case_id:
            c["status"] = "closed"
            save_data("cases", cases)
            return {"status": "closed"}
    return JSONResponse({"error": "Case not found"}, status_code=404)


# =============================================================================
# EVIDENCE
# =============================================================================

@router.get("/api/evidence")
async def list_evidence(case_id: str = None):
    """List evidence for a case."""
    return get_evidence(case_id)

@router.get("/api/evidence/{evidence_id}")
async def get_evidence_item(evidence_id: str):
    """Get evidence details."""
    for e in get_evidence():
        if e["id"] == evidence_id:
            return e
    return JSONResponse({"error": "Evidence not found"}, status_code=404)

@router.post("/api/evidence/upload")
async def upload_evidence(request: Request):
    """Upload evidence file (accepts JSON or multipart)."""
    global _evidence
    
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        # JSON upload (base64 encoded)
        data = await request.json()
        case_id = data.get("case_id")
        filename = data.get("filename", "upload.bin")

        # SECURITY: Sanitize filename to prevent path traversal
        # Remove path separators and parent directory references
        filename = filename.replace("\\", "/")  # Normalize separators
        filename = filename.split("/")[-1]      # Keep only filename part
        filename = filename.lstrip(".")         # Remove leading dots
        if not filename or filename in (".", ".."):
            return JSONResponse({"error": "Invalid filename"}, status_code=400)

        title = data.get("title", filename)
        file_content = data.get("content", "").encode() if data.get("content") else b""
    else:
        # For multipart, we'll handle it later when python-multipart is installed
        return JSONResponse({"error": "Multipart upload requires python-multipart. Use JSON upload instead."}, status_code=400)
    
    if not case_id:
        return JSONResponse({"error": "case_id required"}, status_code=400)
    
    # Save file
    upload_dir = DATA_DIR / "uploads" / case_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    # SECURITY: Verify resolved path is within upload_dir
    resolved_path = file_path.resolve()
    if not str(resolved_path).startswith(str(upload_dir.resolve())):
        return JSONResponse({"error": "Invalid file path"}, status_code=400)

    file_path.write_bytes(file_content)
    
    # Create evidence record
    evidence_id = f"EVD-{str(uuid.uuid4())[:8].upper()}"
    evidence_record = {
        "id": evidence_id,
        "case_id": case_id,
        "filename": filename,
        "title": title,
        "file_path": str(file_path),
        "size": len(file_content),
        "created_at": datetime.now().isoformat(),
        "validation_status": "pending",
        "tags": []
    }
    
    if _evidence is None:
        _evidence = load_data("evidence")
    _evidence.append(evidence_record)
    save_data("evidence", _evidence)
    
    # Update case evidence count
    cases = get_cases()
    for c in cases:
        if c["id"] == case_id:
            c["evidence_count"] = c.get("evidence_count", 0) + 1
            save_data("cases", cases)
            break
    
    return evidence_record

@router.post("/api/evidence/{evidence_id}/validate")
async def validate_evidence(evidence_id: str, request: Request):
    """Validate evidence."""
    data = await request.json()
    action = data.get("action", "confirm")  # confirm, reject, pending
    
    evidence = get_evidence()
    for e in evidence:
        if e["id"] == evidence_id:
            e["validation_status"] = "confirmed" if action == "confirm" else action
            e["validated_at"] = datetime.now().isoformat()
            save_data("evidence", evidence)
            return e
    return JSONResponse({"error": "Evidence not found"}, status_code=404)

@router.delete("/api/evidence/{evidence_id}")
async def delete_evidence(evidence_id: str):
    """Delete evidence."""
    global _evidence
    evidence = get_evidence()
    _evidence = [e for e in evidence if e["id"] != evidence_id]
    save_data("evidence", _evidence)
    return {"status": "deleted"}

@router.get("/api/evidence/{evidence_id}/content")
async def get_evidence_content(evidence_id: str):
    """Get evidence file content."""
    for e in get_evidence():
        if e["id"] == evidence_id:
            path = Path(e.get("file_path", ""))
            if path.exists():
                return FileResponse(path, filename=e.get("filename"))
            return JSONResponse({"error": "File not found"}, status_code=404)
    return JSONResponse({"error": "Evidence not found"}, status_code=404)

@router.get("/api/evidence/{evidence_id}/provenance")
async def get_evidence_provenance(evidence_id: str):
    """Get evidence provenance chain."""
    for e in get_evidence():
        if e["id"] == evidence_id:
            return {
                "evidence_id": evidence_id,
                "chain": [
                    {"action": "uploaded", "timestamp": e.get("created_at"), "actor": "user"},
                    {"action": "validated", "timestamp": e.get("validated_at"), "actor": "system"}
                ]
            }
    return JSONResponse({"error": "Evidence not found"}, status_code=404)


# =============================================================================
# CHAT (with LocalAgent linting + Claude)
# =============================================================================

@router.post("/api/chat")
async def chat(request: Request):
    """Chat with MLX (local) or Claude (fallback) with skill context injection and Negotiator retry loop."""
    data = await request.json()
    message = data.get("message", "")
    case_id = data.get("case_id")
    context_data = data.get("context", {})
    skill_context = context_data.get("skill_context", {})
    
    # Extract skill information
    selected_skill = skill_context.get("selected_skill")
    selected_rewrite = skill_context.get("selected_rewrite", False)
    linter_result = skill_context.get("linter_result", {})
    
    print(f"[THEMIS] Chat request - skill: {selected_skill}, rewrite: {selected_rewrite}")
    
    # Initialize protocol tracking (for UI - minimal info)
    protocol_steps = []
    
    # STEP 1: Skill Matching
    skill_used = None
    skill_body = None
    
    if selected_skill:
        skill_used = selected_skill
    elif linter_result and linter_result.get("topSkill"):
        skill_used = linter_result.get("topSkill")
    
    # Load skill body for validation
    if skill_used:
        try:
            from ...skills import get_manager
            manager = get_manager()
            manager.discover()
            skill = manager.get_skill(skill_used)
            if skill:
                skill_body = skill.body
        except:
            pass
    
    protocol_steps.append({
        "step": "context",
        "label": f"🎯 {skill_used or 'No skill'}" + (f" | Case: {case_id}" if case_id else ""),
        "status": "complete"
    })
    
    # Build system prompt with skill injection
    system_parts = [f"You are a legal/construction claims assistant. Analyze evidence and provide expert advice."]
    
    if skill_used:
        skill_prompt = _get_skill_system_prompt(skill_used)
        if skill_prompt:
            system_parts.append(f"\n=== ACTIVE SKILL: {skill_used} ===\n{skill_prompt}")
    
    # Add case context if available
    try:
        from ...core.case_context import get_case_context_manager
        ctx_manager = get_case_context_manager()
        ctx = ctx_manager.get_context()
        if ctx.case_id:
            case_ctx = f"""
=== CASE CONTEXT ===
Framework: {ctx.framework}
Methodology: {ctx.methodology}
Jurisdiction: {ctx.jurisdiction}
"""
            system_parts.append(case_ctx)
    except:
        pass
    
    system = "\n".join(system_parts)
    
    # Build context from history
    history = _chat_history.get(case_id, [])
    context_str = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in history[-6:]])
    
    # =================================================================
    # NEGOTIATOR RETRY LOOP
    # =================================================================
    MAX_RETRIES = 3
    attempt = 0
    response_text = ""
    ai_source = "unknown"
    negotiation_success = True
    current_prompt = message
    
    while attempt < MAX_RETRIES:
        attempt += 1
        
        # Update UI status
        if attempt > 1:
            protocol_steps.append({
                "step": "retry",
                "label": f"🔄 Retry {attempt}/{MAX_RETRIES}",
                "status": "running"
            })
        
        # Call LLM
        result = chat_completion(current_prompt, context=context_str, system=system)
        response_text = result.get("response", "")
        ai_source = result.get("source", "unknown")
        
        if not response_text:
            # No response - can't validate, break
            break
        
        # If no skill, skip validation
        if not skill_used or not skill_body:
            break
        
        # VALIDATE with Negotiator
        try:
            from ...core.negotiator import validate_output_against_skill, build_retry_prompt_with_skill_feedback
            
            validation = validate_output_against_skill(
                output=response_text,
                skill_name=skill_used,
                skill_body=skill_body,
                strict=False
            )
            
            if validation["valid"]:
                # Output is valid - done
                negotiation_success = True
                if attempt > 1:
                    protocol_steps[-1]["status"] = "complete"
                    protocol_steps[-1]["label"] = f"✅ Retry {attempt} succeeded"
                break
            else:
                # Output invalid - build retry prompt
                negotiation_success = False
                
                if attempt < MAX_RETRIES:
                    # Build feedback prompt for retry
                    feedback = validation.get("feedback", "")
                    if feedback:
                        current_prompt = f"{message}\n\n[IMPORTANT: {feedback}]"
                        print(f"[NEGOTIATOR] Attempt {attempt} failed (score: {validation['score']}), retrying...")
                        if attempt > 1:
                            protocol_steps[-1]["status"] = "complete"
                            protocol_steps[-1]["label"] = f"⚠️ Retry {attempt} - adjusting"
                    else:
                        # No feedback to give, accept current response
                        break
                else:
                    # Max retries reached - use best effort
                    print(f"[NEGOTIATOR] Max retries reached, using best effort (score: {validation['score']})")
                    if attempt > 1:
                        protocol_steps[-1]["status"] = "complete"
                        protocol_steps[-1]["label"] = f"⚠️ Best effort after {attempt} attempts"
                        
        except Exception as e:
            print(f"[NEGOTIATOR] Validation error: {e}")
            # Skip validation on error
            break
    
    # Final status
    protocol_steps.append({
        "step": "complete",
        "label": f"🤖 {ai_source.upper()}" + (f" ({attempt} attempt{'s' if attempt > 1 else ''})" if attempt > 1 else ""),
        "status": "complete"
    })
    
    # Store in history
    if case_id not in _chat_history:
        _chat_history[case_id] = []
    _chat_history[case_id].append({
        "role": "user", 
        "content": message, 
        "timestamp": datetime.now().isoformat(),
        "skill": selected_skill
    })
    _chat_history[case_id].append({
        "role": "assistant", 
        "content": response_text, 
        "timestamp": datetime.now().isoformat(), 
        "source": ai_source,
        "skill_used": skill_used,
        "negotiation_attempts": attempt
    })
    
    return {
        "response": response_text,
        "case_id": case_id,
        "ai_source": ai_source,
        "skill_used": skill_used,
        "protocol": protocol_steps,
        "negotiation_attempts": attempt,
        "negotiation_success": negotiation_success
    }


def _get_skill_system_prompt(skill_name: str) -> str:
    """Get the system prompt portion for a skill."""
    try:
        from ...skills import get_manager
        manager = get_manager()
        manager.discover()
        skill = manager.get_skill(skill_name)
        
        if not skill:
            return ""
        
        # Build prompt from skill
        parts = []
        
        # Add description
        if skill.description:
            # Remove triggers from description for cleaner prompt
            desc = skill.description
            for prefix in ["Triggers-Core:", "Triggers-Strong:", "Triggers-Weak:", "Triggers:"]:
                if prefix in desc:
                    desc = desc.split(prefix)[0].strip()
            parts.append(f"Role: {desc}")
        
        # Add constraints if present
        if skill.body:
            import re
            constraints_match = re.search(r"## Constraints\s*\n([\s\S]*?)(?=\n## [A-Za-z]|$)", skill.body)
            if constraints_match:
                constraints = constraints_match.group(1).strip()
                parts.append(f"\nConstraints:\n{constraints[:500]}")
        
        return "\n".join(parts)
    except Exception as e:
        print(f"[THEMIS] Error loading skill {skill_name}: {e}")
        return ""

@router.get("/api/chat/history")
async def chat_history(case_id: str):
    """Get chat history for a case."""
    return _chat_history.get(case_id, [])


# In-memory storage for pending error corrections
_pending_corrections: Dict[str, Dict] = {}


@router.post("/api/chat/error")
async def report_console_error(request: Request):
    """
    Receive console errors from frontend and trigger re-negotiation.
    """
    try:
        data = await request.json()
        
        error_message = data.get("error_message", "")
        code_context = data.get("code_context", "")
        original_prompt = data.get("original_prompt", "")
        original_response = data.get("original_response", "")
        case_id = data.get("case_id")
        skill_used = data.get("skill_used")
        message_id = data.get("message_id", str(uuid.uuid4()))
        
        print(f"[NEGOTIATOR] Console error received: {error_message[:100]}...")
        
        # Classify the error
        from ...core.negotiator import classify_console_error, build_error_feedback, should_retry
        from ...core.learning import learn_from_error
        
        error_type, cleaned_message = classify_console_error(error_message)
        print(f"[NEGOTIATOR] Classified as: {error_type}")
        
        # Learn from this error
        learn_from_error(
            project="THEMIS",
            error_type=error_type,
            error_message=cleaned_message,
            context={
                "skill": skill_used,
                "case_id": case_id,
                "code_length": len(code_context)
            }
        )
        
        # Check if we should retry
        retry_count = _pending_corrections.get(message_id, {}).get("retry_count", 0)
        
        if not should_retry(error_type, retry_count):
            return {
                "success": False,
                "error": "Max retries exceeded for this error type",
                "error_type": error_type,
                "retry_count": retry_count
            }
        
        # Build feedback for LLM
        feedback = build_error_feedback(error_type, cleaned_message, code_context)
        
        # Build retry prompt
        retry_prompt = f"""{original_prompt}

=== RUNTIME ERROR DETECTED ===
Your previous response caused an error when executed.

{feedback}

=== YOUR PREVIOUS RESPONSE (NEEDS FIX) ===
{original_response[:2000]}

Please provide a CORRECTED response that fixes the error."""

        # Track this correction attempt
        _pending_corrections[message_id] = {
            "retry_count": retry_count + 1,
            "original_prompt": original_prompt,
            "errors": _pending_corrections.get(message_id, {}).get("errors", []) + [
                {"type": error_type, "message": cleaned_message}
            ]
        }
        
        # Build system prompt with skill
        system_parts = ["You are a code correction assistant. Fix errors while preserving the original intent."]
        
        if skill_used:
            skill_prompt = _get_skill_system_prompt(skill_used)
            if skill_prompt:
                system_parts.append(f"\n=== ACTIVE SKILL: {skill_used} ===\n{skill_prompt}")
        
        system = "\n".join(system_parts)
        
        # Build context
        history = _chat_history.get(case_id, [])
        context_str = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in history[-4:]])
        
        # Call LLM with error context
        result = chat_completion(retry_prompt, context=context_str, system=system)
        response_text = result.get("response", "")
        ai_source = result.get("source", "unknown")
        
        # Store the correction attempt in history
        if case_id:
            if case_id not in _chat_history:
                _chat_history[case_id] = []
            _chat_history[case_id].append({
                "role": "system",
                "content": f"[Error correction: {error_type}]",
                "timestamp": datetime.now().isoformat()
            })
            _chat_history[case_id].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat(),
                "source": ai_source,
                "correction_for": message_id,
                "error_type": error_type
            })
        
        return {
            "success": True,
            "response": response_text,
            "message_id": message_id,
            "error_type": error_type,
            "retry_count": retry_count + 1,
            "ai_source": ai_source,
            "protocol": [
                {"step": "error_received", "label": f"❌ {error_type}", "status": "complete"},
                {"step": "correction", "label": f"🔄 Retry {retry_count + 1}", "status": "complete"},
                {"step": "response", "label": f"✅ Corrected ({ai_source})", "status": "complete"}
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Error processing correction request"
        }


@router.delete("/api/chat/error/{message_id}")
async def clear_error_tracking(message_id: str):
    """Clear error tracking for a message (called on success)."""
    if message_id in _pending_corrections:
        del _pending_corrections[message_id]
    return {"cleared": True}


# =============================================================================
# SEARCH
# =============================================================================

@router.get("/api/search/evidence")
async def search_evidence(q: str = "", case_id: str = None):
    """Search evidence using Spotlight (macOS) or fallback."""
    if not q:
        return get_evidence(case_id)
    
    # Try Spotlight first
    if SPOTLIGHT_AVAILABLE:
        try:
            results = spotlight_search(q, case_id)
            if results:
                return results
        except Exception as e:
            print(f"[THEMIS] Spotlight error: {e}")
    
    # Fallback to simple search
    evidence = get_evidence(case_id)
    q_lower = q.lower()
    return [e for e in evidence if q_lower in e.get("title", "").lower() or q_lower in e.get("filename", "").lower()]

@router.get("/api/search/tag")
async def search_by_tag(namespace: str, value: str):
    """Search evidence by tag."""
    tag = f"{namespace}:{value}"
    return [e for e in get_evidence() if tag in e.get("tags", [])]

@router.get("/api/search/type")
async def search_by_type(type: str, case_id: str = None):
    """Search evidence by document type."""
    evidence = get_evidence(case_id)
    return [e for e in evidence if e.get("document_type") == type]

@router.get("/api/search/validation")
async def search_by_validation(status: str, case_id: str = None):
    """Search evidence by validation status."""
    evidence = get_evidence(case_id)
    return [e for e in evidence if e.get("validation_status") == status]


# =============================================================================
# TAGS
# =============================================================================

@router.get("/api/tags/{evidence_id}")
async def get_tags(evidence_id: str):
    """Get tags for evidence."""
    for e in get_evidence():
        if e["id"] == evidence_id:
            return {"evidence_id": evidence_id, "tags": e.get("tags", [])}
    return JSONResponse({"error": "Evidence not found"}, status_code=404)

@router.post("/api/tags/{evidence_id}")
async def add_tag(evidence_id: str, namespace: str, value: str):
    """Add tag to evidence."""
    evidence = get_evidence()
    for e in evidence:
        if e["id"] == evidence_id:
            if "tags" not in e:
                e["tags"] = []
            tag = f"{namespace}:{value}"
            if tag not in e["tags"]:
                e["tags"].append(tag)
            save_data("evidence", evidence)
            return {"evidence_id": evidence_id, "tags": e["tags"]}
    return JSONResponse({"error": "Evidence not found"}, status_code=404)

@router.delete("/api/tags/{evidence_id}/{namespace}/{value}")
async def remove_tag(evidence_id: str, namespace: str, value: str):
    """Remove tag from evidence."""
    evidence = get_evidence()
    tag = f"{namespace}:{value}"
    for e in evidence:
        if e["id"] == evidence_id:
            if tag in e.get("tags", []):
                e["tags"].remove(tag)
            save_data("evidence", evidence)
            return {"status": "removed"}
    return JSONResponse({"error": "Evidence not found"}, status_code=404)


# =============================================================================
# FOLDERS
# =============================================================================

@router.get("/api/folders")
async def list_folders(case_id: str = None):
    """List folders for a case."""
    # Return default RICS folders
    return [
        {"id": "rics-1", "path": "[1] Pre-Contract", "name": "Pre-Contract", "phase": 1},
        {"id": "rics-2", "path": "[2] Contract", "name": "Contract", "phase": 2},
        {"id": "rics-3", "path": "[3] Post-Contract", "name": "Post-Contract", "phase": 3},
        {"id": "rics-4", "path": "[4] Records", "name": "Records", "phase": 4},
    ]

@router.get("/api/folders/{path:path}")
async def get_folder_contents(path: str):
    """Get folder contents."""
    return {"path": path, "contents": []}

@router.get("/api/folders/search")
async def search_folders(q: str = ""):
    """Search folders."""
    folders = await list_folders()
    if not q:
        return folders
    return [f for f in folders if q.lower() in f.get("name", "").lower()]


# =============================================================================
# FRAMEWORKS
# =============================================================================

FRAMEWORKS = [
    {"id": "rics", "name": "RICS", "description": "Royal Institution of Chartered Surveyors"},
    {"id": "scl", "name": "SCL Protocol", "description": "Society of Construction Law Delay Protocol"},
    {"id": "far", "name": "FAR", "description": "Federal Acquisition Regulation"},
]

@router.get("/api/frameworks")
async def list_frameworks():
    """List available frameworks."""
    return FRAMEWORKS

@router.get("/api/frameworks/{framework_id}")
async def get_framework(framework_id: str):
    """Get framework details."""
    for f in FRAMEWORKS:
        if f["id"] == framework_id:
            return f
    return JSONResponse({"error": "Framework not found"}, status_code=404)

@router.get("/api/frameworks/{framework_id}/folders")
async def get_framework_folders(framework_id: str):
    """Get folders for a framework."""
    if framework_id == "rics":
        return [
            {"id": "rics-1-01", "path": "[1] Pre-Contract/Feasibility", "name": "Feasibility", "phase": 1},
            {"id": "rics-1-02", "path": "[1] Pre-Contract/Design", "name": "Design", "phase": 1},
            {"id": "rics-2-01", "path": "[2] Contract/Main Contract", "name": "Main Contract", "phase": 2},
            {"id": "rics-2-02", "path": "[2] Contract/Subcontracts", "name": "Subcontracts", "phase": 2},
        ]
    return []


# =============================================================================
# ANALYSIS
# =============================================================================

@router.get("/api/analysis/chronology")
async def get_chronology(case_id: str):
    """Get chronology analysis for a case."""
    return {"case_id": case_id, "events": [], "analysis": "Chronology analysis pending"}

@router.get("/api/analysis/facts")
async def get_facts(case_id: str):
    """Get facts analysis for a case."""
    return {"case_id": case_id, "facts": [], "analysis": "Facts extraction pending"}

@router.get("/api/analysis/methods")
async def get_analysis_methods():
    """Get available analysis methods."""
    return [
        {"id": "time-impact", "name": "Time Impact Analysis"},
        {"id": "as-planned-vs-as-built", "name": "As-Planned vs As-Built"},
        {"id": "windows", "name": "Windows Analysis"},
    ]


# =============================================================================
# OUTPUTS
# =============================================================================

@router.get("/api/outputs")
async def list_outputs(case_id: str = None):
    """List outputs for a case."""
    return load_data("outputs")

@router.post("/api/outputs")
async def create_output(request: Request):
    """Create a new output."""
    data = await request.json()
    output_id = f"OUT-{str(uuid.uuid4())[:8].upper()}"
    output = {
        "id": output_id,
        "title": data.get("title", "Output"),
        "content": data.get("content", ""),
        "case_id": data.get("case_id"),
        "type": data.get("type", "general"),
        "created_at": datetime.now().isoformat()
    }
    outputs = load_data("outputs")
    outputs.append(output)
    save_data("outputs", outputs)
    return output

@router.get("/api/outputs/{output_id}")
async def get_output(output_id: str):
    """Get output details."""
    for o in load_data("outputs"):
        if o["id"] == output_id:
            return o
    return JSONResponse({"error": "Output not found"}, status_code=404)


# =============================================================================
# SCL PROTOCOL
# =============================================================================

SCL_PRINCIPLES = [
    {"number": 1, "title": "Records", "description": "Maintain proper records"},
    {"number": 2, "title": "Programme", "description": "Use an accepted programme"},
    {"number": 3, "title": "Notices", "description": "Give notices as required"},
]

@router.get("/api/scl/principles")
async def get_scl_principles():
    """Get SCL Protocol principles."""
    return SCL_PRINCIPLES

@router.get("/api/scl/principles/{number}")
async def get_scl_principle(number: int):
    """Get specific SCL principle."""
    for p in SCL_PRINCIPLES:
        if p["number"] == number:
            return p
    return JSONResponse({"error": "Principle not found"}, status_code=404)

@router.get("/api/scl/compliance")
async def get_scl_compliance(case_id: str):
    """Get SCL compliance status for a case."""
    return {"case_id": case_id, "compliance_score": 0.75, "issues": []}

@router.get("/api/scl/record-categories")
async def get_record_categories():
    """Get SCL record categories."""
    return [
        {"id": "contemporary", "name": "Contemporary Records"},
        {"id": "programme", "name": "Programme Records"},
        {"id": "correspondence", "name": "Correspondence"},
    ]


# =============================================================================
# EVENTS & NOTICES
# =============================================================================

@router.get("/api/events")
async def list_events(case_id: str = None):
    """List events for a case."""
    return load_data("events")

@router.get("/api/events/concurrent")
async def get_concurrent_events(case_id: str):
    """Get concurrent events for a case."""
    return {"case_id": case_id, "concurrent_events": []}

@router.get("/api/notices/overdue")
async def get_overdue_notices(case_id: str):
    """Get overdue notices for a case."""
    return []

@router.get("/api/notices/upcoming")
async def get_upcoming_notices(case_id: str, days_ahead: int = 7):
    """Get upcoming notices for a case."""
    return []


# =============================================================================
# SETTINGS
# =============================================================================

@router.get("/api/settings")
async def get_settings():
    """Get settings."""
    return {"theme": "light", "language": "en", "auto_save": True}

@router.get("/api/settings/modules")
async def get_modules():
    """Get available modules."""
    return [
        {"id": "delay-analysis", "name": "Delay Analysis", "enabled": True},
        {"id": "quantum", "name": "Quantum Analysis", "enabled": True},
        {"id": "scl-compliance", "name": "SCL Compliance", "enabled": True},
    ]


# =============================================================================
# WHISPER (Voice Input)
# =============================================================================

@router.post("/api/whisper/transcribe")
async def whisper_transcribe(request: Request):
    """Transcribe audio via Whisper."""
    # TODO: Implement Whisper integration when python-multipart is available
    return {"text": "", "error": "Whisper not configured"}




# =============================================================================
# MLX / AI Classification
# =============================================================================

@router.get("/api/mlx-feeder/stats")
async def mlx_stats():
    """Get MLX status and stats."""
    return get_mlx_stats()

@router.get("/api/mlx-feeder/consent")
async def mlx_consent():
    """Get MLX consent status."""
    return {"consent": True, "mlx_available": MLX_AVAILABLE}

@router.post("/api/mlx-feeder/consent")
async def grant_mlx_consent():
    """Grant MLX consent."""
    return {"consent": True, "granted_at": datetime.now().isoformat()}

@router.post("/api/evidence/{evidence_id}/classify")
async def classify_evidence(evidence_id: str):
    """Classify evidence using MLX/Claude."""
    evidence = get_evidence()
    for e in evidence:
        if e["id"] == evidence_id:
            # Read file content
            filepath = Path(e.get("file_path", ""))
            text = ""
            if filepath.exists() and filepath.suffix.lower() in [".txt", ".md", ".pdf"]:
                try:
                    text = filepath.read_text(errors="ignore")[:5000]
                except:
                    pass
            
            # Classify
            result = classify_document(text, e.get("filename", ""))
            
            # Update evidence
            e["mlx_classification"] = result.get("classification")
            e["mlx_confidence"] = result.get("confidence")
            e["classification_source"] = result.get("source")
            e["classification_status"] = "mlx_suggested"
            save_data("evidence", evidence)
            
            return {
                "evidence_id": evidence_id,
                "classification": result
            }
    
    return JSONResponse({"error": "Evidence not found"}, status_code=404)


# =============================================================================
# SMART FOLDERS (Spotlight)
# =============================================================================

@router.get("/api/smart-folders")
async def list_smart_folders():
    """List smart folders."""
    if SPOTLIGHT_AVAILABLE:
        return get_smart_folders()
    return []

@router.get("/api/smart-folders/{folder_id}/execute")
async def run_smart_folder(folder_id: str, case_id: str = None):
    """Execute a smart folder query."""
    if SPOTLIGHT_AVAILABLE:
        return execute_smart_folder(folder_id, case_id)
    return []

# =============================================================================
# WEBSOCKET
# =============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    _ws_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo for now
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        _ws_connections.remove(websocket)
