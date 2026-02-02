"""
Chat Handler - Core logic for chat processing
Extracted from server.py to keep it thin
"""
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DEFAULT_PROJECT = "LOCALAGENT"


def detect_tracking_type(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect if message is a bug fix or todo request.
    Returns (type, title) or (None, None)
    """
    bug_keywords = ["fix", "bug", "error", "broken", "crash", "issue", "problem", 
                    "wrong", "fail", "dupliqué", "duplicate", "missing", "manque", "incorrect"]
    todo_keywords = ["add", "create", "implement", "build", "make", "ajoute", 
                     "créer", "nouveau", "new", "feature", "améliore", "improve", "optimize"]
    
    message_lower = message.lower()
    title = message[:80] if len(message) > 80 else message
    
    if any(kw in message_lower for kw in bug_keywords):
        return "BF", title
    elif any(kw in message_lower for kw in todo_keywords):
        return "TD", title
    return None, None


def create_tracking_entry(tracking_type: str, title: str, message: str) -> Dict[str, Any]:
    """Create a tracking entry (TODO or BUGFIX)."""
    if tracking_type == "BF":
        from ..engine.tracking import add_bugfix
        entry_id = add_bugfix(DEFAULT_PROJECT, title, message, "chat")
    else:
        from ..engine.tracking import add_todo_item
        entry_id = add_todo_item(DEFAULT_PROJECT, title, "todo")
    
    return {"id": entry_id, "title": title, "type": "bugfix" if tracking_type == "BF" else "todo"}


def mark_tracking_done(tracking_entry: Dict, tracking_type: str):
    """Mark tracking entry as completed."""
    from ..engine.tracking import get_todo, save_todo, get_bugfixes, save_bugfixes
    
    if tracking_type == "TD":
        todo = get_todo(DEFAULT_PROJECT)
        for item in todo:
            if item.get("id") == tracking_entry["id"]:
                item["done"] = True
                item["status"] = "completed"
                item["completed"] = datetime.now().isoformat()
                break
        save_todo(DEFAULT_PROJECT, todo)
        
    elif tracking_type == "BF":
        bugfixes = get_bugfixes(DEFAULT_PROJECT)
        for bf in bugfixes:
            if bf.get("id") == tracking_entry["id"]:
                bf["status"] = "applied"
                bf["applied_at"] = datetime.now().isoformat()
                break
        save_bugfixes(DEFAULT_PROJECT, bugfixes)


def lint_message(message: str, project: str) -> Tuple[str, Dict, bool]:
    """Lint and preprocess message. Returns (optimized, report, is_conversation)."""
    from ..roadmap.prompt_optimizer import lint_prompt, preprocess_for_negotiation, is_conversational
    
    lint_prompt(message)
    optimized, report = preprocess_for_negotiation(message, project)
    is_conv = is_conversational(message) or report.get("task_type", {}).get("type") == "conversation"
    
    return optimized, report, is_conv


def build_conversation_context(history: List[Dict]) -> str:
    """Build context string from conversation history."""
    if not history:
        return ""
    
    context = "Previous conversation:\n"
    for msg in history[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")[:500]
        context += f"{role.upper()}: {content}\n"
    context += "\n---\nCurrent message:\n"
    return context


def handle_conversation(message: str, context: str, project: str) -> str:
    """Handle simple conversation (no task execution)."""
    from ..connectors.llm import call_claude
    from ..engine.tracking import add_message
    
    add_message(project, "user", message)
    
    try:
        full_prompt = context + message if context else message
        result = call_claude(
            full_prompt, 
            f"Casual conversation. Respond naturally in user's language. No JSON. Project: {project}"
        )
        response = result.get("response", "I'm here to help!") if result.get("success") else "Hello! How can I help?"
    except:
        response = "Hello! How can I help you today?"
    
    add_message(project, "assistant", response)
    return response


def execute_negotiation(message: str, project: str, context: str) -> Tuple[bool, Dict]:
    """Execute negotiation with Claude."""
    from ..connectors.llm import call_claude
    from ..core.negotiator import negotiate_request
    from ..core.constraints import get_constraints_for_context
    
    constraints = get_constraints_for_context()
    full_context = f"PROJECT: {project}\n{constraints}"
    if context:
        full_context = context + full_context
    
    return negotiate_request(
        project=project,
        instruction=message,
        call_claude_fn=call_claude,
        context=full_context,
        max_retries=3
    )


def process_tasks(tasks: List[Dict], project: str) -> Tuple[List[str], List[Dict]]:
    """Process tasks from negotiation result. Returns (saved_files, attachments)."""
    from ..engine.tracking import register_output_file
    from pathlib import Path
    
    saved_files = []
    attachments = []
    
    for task in tasks:
        task_type = task.get("type", "").lower()
        is_file_task = task_type in ("create_file", "file", "create", "write_file", "write", "code", "html")
        has_file_content = (task.get("filename") or task.get("file_path")) and (task.get("content") or task.get("code"))
        
        if is_file_task or has_file_content:
            filename = task.get("filename") or task.get("file_path") or task.get("file") or "output.txt"
            content = task.get("content") or task.get("code") or task.get("html") or ""
            
            if filename and content:
                clean_name = Path(filename).name
                register_output_file(project, clean_name, content)
                saved_files.append(clean_name)
                attachments.append({
                    "name": clean_name,
                    "url": f"/outputs/{clean_name}",
                    "size": len(content),
                    "type": Path(clean_name).suffix.lower()
                })
    
    return saved_files, attachments
