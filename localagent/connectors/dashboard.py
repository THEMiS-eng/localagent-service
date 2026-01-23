"""
LocalAgent v2.10.37 - CONNECTOR: Dashboard
HTTP server + HTML generation + API endpoints + File serving
"""

import json
import socket
import platform
import subprocess
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote
from pathlib import Path
from typing import Dict

from ..core import (
    get_all_constraints,
    load_learned_errors
)
from ..engine import (
    get_version, list_snapshots,
    get_backlog, add_backlog_item,
    get_todo, add_todo_item,
    get_changelog, get_conversation, add_message, clear_conversation,
    get_output_files, get_outputs_path, register_output_file, delete_output_file
)
from .llm import call_claude_simple, has_api_key
from .github import get_repos


# ============================================================
# CONFIG
# ============================================================

DASHBOARD_PORT = 8766
JS_ERRORS = []  # Captured JS errors from frontend for agent debugging
CURRENT_PROJECT = None


def set_project(project: str):
    """Set current project."""
    global CURRENT_PROJECT
    CURRENT_PROJECT = project


def get_project() -> str:
    """Get current project."""
    return CURRENT_PROJECT


# ============================================================
# HTTP HANDLER
# ============================================================

class Handler(BaseHTTPRequestHandler):
    """Dashboard HTTP handler."""
    
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == "/" or path == "/dashboard":
            self._html(generate_dashboard())
        elif path == "/api/status":
            self._json(get_status())
        elif path == "/api/conversation":
            self._json(get_conversation(CURRENT_PROJECT) if CURRENT_PROJECT else [])
        elif path == "/api/backlog":
            self._json(get_backlog(CURRENT_PROJECT) if CURRENT_PROJECT else [])
        elif path == "/api/todo":
            self._json(get_todo(CURRENT_PROJECT) if CURRENT_PROJECT else [])
        elif path == "/api/changelog":
            self._json(get_changelog(CURRENT_PROJECT) if CURRENT_PROJECT else [])
        elif path == "/api/constraints":
            self._json(get_all_constraints())
        elif path == "/api/snapshots":
            self._json(list_snapshots(CURRENT_PROJECT) if CURRENT_PROJECT else [])
        elif path == "/api/github":
            self._json(get_repos(CURRENT_PROJECT))
        elif path == "/api/errors":
            self._json(load_learned_errors(CURRENT_PROJECT) if CURRENT_PROJECT else {})
        elif path == "/api/outputs":
            self._json(get_output_files(CURRENT_PROJECT) if CURRENT_PROJECT else [])
        elif path.startswith("/outputs/"):
            self._serve_file(path)
        elif path == "/api/update/status":
            from ..core.updater import get_update_status
            self._json(get_update_status())
        elif path == "/api/update/check":
            from ..core.release_listener import check_for_update
            self._json(check_for_update())
        elif path == "/api/update/backups":
            from ..core.updater import list_backups
            self._json(list_backups())
        elif path == "/api/app":
            from .github import get_app_info
            self._json(get_app_info())
        elif path == "/api/debug/errors":
            # Return captured JS errors for agent analysis
            self._json({"errors": JS_ERRORS, "count": len(JS_ERRORS)})
        elif path == "/api/debug/clear":
            JS_ERRORS.clear()
            self._json({"status": "cleared"})
        else:
            self.send_error(404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        # Handle file upload for updates
        if path == "/api/update/upload":
            self._handle_upload()
            return
        
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == "/api/chat":
            self._json(handle_chat(data.get("message", "")))
        elif path == "/api/clear":
            if CURRENT_PROJECT:
                clear_conversation(CURRENT_PROJECT)
            self._json({"status": "cleared"})
        elif path == "/api/backlog/add" and CURRENT_PROJECT:
            item_id = add_backlog_item(CURRENT_PROJECT, data.get("title", ""), data.get("priority", "medium"))
            self._json({"id": item_id})
        elif path == "/api/todo/add" and CURRENT_PROJECT:
            item_id = add_todo_item(CURRENT_PROJECT, data.get("title", ""), data.get("category", "todo"))
            self._json({"id": item_id})
        elif path == "/api/outputs/delete" and CURRENT_PROJECT:
            filename = data.get("filename", "")
            success = delete_output_file(CURRENT_PROJECT, filename)
            self._json({"status": "deleted" if success else "not_found"})
        elif path == "/api/lint":
            from ..roadmap.prompt_optimizer import lint_prompt
            prompt = data.get("prompt", "")
            result = lint_prompt(prompt)
            self._json(result)
        elif path == "/api/update/install":
            from ..core.updater import install_update
            result = install_update()
            self._json(result)
        elif path == "/api/update/install-from-github":
            from ..core.release_listener import install_from_github
            result = install_from_github()
            self._json(result)
        elif path == "/api/update/rollback":
            from ..core.updater import rollback
            backup_name = data.get("backup")
            result = rollback(backup_name)
            self._json(result)
        elif path == "/api/debug/error":
            # Capture JS error from frontend
            JS_ERRORS.append(data)
            print(f"🐛 JS Error captured: {data.get('message', 'Unknown')[:80]}")
            self._json({"status": "captured", "total": len(JS_ERRORS)})
        else:
            self.send_error(404)
    
    def _handle_upload(self):
        """Handle zip file upload for updates."""
        import tempfile
        import cgi
        
        try:
            content_type = self.headers.get('Content-Type', '')
            
            if 'multipart/form-data' not in content_type:
                self._json({"success": False, "error": "Expected multipart/form-data"})
                return
            
            # Parse multipart form data
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            
            if 'file' not in form:
                self._json({"success": False, "error": "No file uploaded"})
                return
            
            file_item = form['file']
            
            if not file_item.filename:
                self._json({"success": False, "error": "No filename"})
                return
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                tmp.write(file_item.file.read())
                tmp_path = tmp.name
            
            # Process upload
            from ..core.updater import upload_release
            result = upload_release(tmp_path)
            
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
            
            self._json(result)
            
        except Exception as e:
            self._json({"success": False, "error": str(e)})
    
    def _json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode())
    
    def _html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def _serve_file(self, path):
        """Serve file from outputs directory."""
        if not CURRENT_PROJECT:
            self.send_error(404)
            return
        
        # Extract filename from path /outputs/filename
        filename = unquote(path[9:])  # Remove '/outputs/'
        
        # Security: prevent directory traversal
        if '..' in filename or filename.startswith('/'):
            self.send_error(403)
            return
        
        outputs_dir = get_outputs_path(CURRENT_PROJECT)
        filepath = outputs_dir / filename
        
        if not filepath.exists() or not filepath.is_file():
            self.send_error(404)
            return
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(str(filepath))
        if not content_type:
            content_type = 'application/octet-stream'
        
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.send_header('Content-Disposition', f'inline; filename="{filename}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))


# ============================================================
# API
# ============================================================

def get_status() -> Dict:
    """Get agent status."""
    errors = load_learned_errors(CURRENT_PROJECT) if CURRENT_PROJECT else {}
    outputs = get_output_files(CURRENT_PROJECT) if CURRENT_PROJECT else []
    return {
        "version": "2.10.36",
        "project": CURRENT_PROJECT,
        "api_configured": has_api_key(),
        "project_version": get_version(CURRENT_PROJECT) if CURRENT_PROJECT else "N/A",
        "learned_errors": len(errors.get("errors", [])),
        "output_files": len(outputs)
    }


def handle_chat(message: str) -> Dict:
    """
    Handle chat message with FULL PROTOCOL:
    0. LINT prompt (detect issues, optimize)
    1. Négociation avec retry intelligent
    2. Validation ACK
    3. Exécution des tâches
    4. Sauvegarde des fichiers
    """
    if not message.strip():
        return {"error": "Empty message"}
    
    if not CURRENT_PROJECT:
        return {"error": "No project selected"}
    
    add_message(CURRENT_PROJECT, "user", message)
    
    # Commands bypass protocol
    if message.startswith("/"):
        response = _handle_command(message)
        add_message(CURRENT_PROJECT, "agent", response)
        return {"status": "ok", "response": response}
    
    # === FULL PROTOCOL ===
    print(f"\n{'='*50}", flush=True)
    print(f"🤖 PROTOCOL START: {message[:50]}...", flush=True)
    print(f"{'='*50}", flush=True)
    
    # === STEP 0: LINT PROMPT ===
    from ..roadmap.prompt_optimizer import preprocess_for_negotiation, lint_prompt
    optimized_prompt, lint_report = preprocess_for_negotiation(message, CURRENT_PROJECT)
    
    if lint_report["issue_count"] > 0:
        print(f"🔍 LINTER: {lint_report['issue_count']} issues detected (score: {lint_report['score']})", flush=True)
        for issue in lint_report["issues"]:
            print(f"   ⚠️ {issue['message']}: {', '.join(issue['matches'][:2])}", flush=True)
        print(f"📝 Prompt optimized", flush=True)
    else:
        print(f"🔍 LINTER: OK (score: 100)", flush=True)
    
    # Import negotiator
    from ..core.negotiator import negotiate_request, validate_response
    from .llm import call_claude
    
    print(f"🔄 Calling negotiator...", flush=True)
    
    # Negotiate with Claude using OPTIMIZED prompt
    success, result = negotiate_request(
        project=CURRENT_PROJECT,
        instruction=optimized_prompt,  # Use optimized prompt!
        call_claude_fn=call_claude,
        context=f"PROJECT: {CURRENT_PROJECT}",
        max_retries=3
    )
    
    # Log attempts
    attempts = result.get("attempts", [])
    for i, att in enumerate(attempts):
        status = "✅" if att.get("success") else "❌"
        err = att.get("error_type", "")
        print(f"  Attempt {i+1}: {status} {err}", flush=True)
    
    if not success:
        # Handle failure
        error_type = result.get("error", "unknown")
        detail = result.get("detail", "")
        
        if result.get("split_required"):
            parts = result.get("parts", [])
            response = f"⚠️ Instruction trop complexe. Divisée en {len(parts)} parties:\n"
            for i, part in enumerate(parts, 1):
                response += f"\n{i}. {part[:80]}..."
            response += "\n\nExécutez chaque partie séparément."
        else:
            response = f"❌ Échec après {len(attempts)} tentatives\n"
            response += f"Erreur: {error_type}\n"
            if detail:
                response += f"Détail: {detail[:200]}"
        
        print(f"❌ PROTOCOL FAILED: {error_type}", flush=True)
        add_message(CURRENT_PROJECT, "agent", response)
        return {"status": "error", "response": response, "error": error_type}
    
    # === SUCCESS: Execute tasks ===
    tasks = result.get("tasks", [])
    print(f"✅ PROTOCOL SUCCESS: {len(tasks)} tasks", flush=True)
    
    # Build response with linter info
    response_lines = []
    if lint_report["issue_count"] > 0:
        response_lines.append(f"🔍 Linter: {lint_report['issue_count']} issues (score: {lint_report['score']})")
    response_lines.append(f"✅ {len(tasks)} tâches validées (ACK)")
    saved_files = []
    
    for task in tasks:
        task_id = task.get("id", "T???")
        task_type = task.get("type", "unknown")
        task_desc = task.get("description", "")[:50]
        
        print(f"  📋 Executing {task_id}: {task_type}")
        
        # Handle file creation (multiple type variations)
        if task_type in ("create_file", "file", "create", "write_file"):
            # Get filename (handle multiple keys)
            filename = task.get("filename") or task.get("file_path") or task.get("file") or task.get("path") or ""
            content = task.get("content", "") or task.get("code", "") or task.get("data", "")
            
            if filename and content:
                clean_name = Path(filename).name
                register_output_file(CURRENT_PROJECT, clean_name, content)
                saved_files.append(clean_name)
                response_lines.append(f"📄 {task_id}: Créé {clean_name}")
                print(f"    ✅ Created: {clean_name} ({len(content)} chars)")
            else:
                response_lines.append(f"⚠️ {task_id}: Fichier manquant (filename={filename}, content={len(content) if content else 0} chars)")
                print(f"    ❌ Missing filename or content (filename={filename}, content_len={len(content) if content else 0})")
        
        elif task_type == "modify_file":
            filename = task.get("filename") or task.get("file_path") or task.get("file") or ""
            response_lines.append(f"📝 {task_id}: Modifier {filename} (non implémenté)")
        
        elif task_type == "shell" or task_type == "system_command":
            cmd = task.get("command", "")
            response_lines.append(f"🔧 {task_id}: Commande shell ignorée pour sécurité")
            print(f"    ⏭️ Skipped shell: {cmd[:50]}")
        
        else:
            response_lines.append(f"📋 {task_id}: {task_desc}")
    
    # Summary
    if saved_files:
        response_lines.append(f"\n📁 Fichiers créés: {', '.join(saved_files)}")
    
    usage = result.get("usage", {})
    if usage:
        tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        response_lines.append(f"💰 Tokens: {tokens}")
    
    response = "\n".join(response_lines)
    print(f"{'='*50}\n")
    
    add_message(CURRENT_PROJECT, "agent", response)
    return {"status": "ok", "response": response, "files": saved_files}


def _extract_and_save_files(response: str) -> str:
    """
    Extract code blocks or JSON tasks from response and save as files.
    Detects patterns like:
    - JSON tasks: {"tasks": [{"type": "create_file", "filename": "...", "content": "..."}]}
    - ```python filename.py ... ```
    - ```html filename.html ... ```
    - FILE: filename.ext followed by code block
    """
    import re
    
    if not CURRENT_PROJECT:
        return response
    
    saved_files = []
    
    # Pattern 0: JSON task format from Claude
    # Try to parse as JSON first
    try:
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*"tasks"[\s\S]*\}', response)
        if json_match:
            json_str = json_match.group()
            print(f"🔍 Found JSON tasks block ({len(json_str)} chars)")
            data = json.loads(json_str)
            tasks = data.get("tasks", [])
            print(f"🔍 Parsed {len(tasks)} tasks")
            for task in tasks:
                if task.get("type") == "create_file":
                    # Handle both "filename" and "file_path" keys
                    filename = task.get("filename") or task.get("file_path") or ""
                    content = task.get("content", "")
                    print(f"🔍 Task create_file: {filename} ({len(content)} chars)")
                    if filename and content:
                        clean_name = Path(filename).name
                        if clean_name and clean_name not in saved_files:
                            register_output_file(CURRENT_PROJECT, clean_name, content)
                            saved_files.append(clean_name)
                            print(f"📄 Created: {clean_name}")
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"⚠️ JSON parse error: {e}")
        # FALLBACK: Try to extract file content from truncated JSON
        # Pattern: "file_path": "name.html", "content": "..."
        fallback_pattern = r'"(?:file_path|filename)":\s*"([^"]+\.(?:html|py|js|css|json|md))"[^}]*"content":\s*"((?:[^"\\]|\\.)*)'
        fallback_matches = re.findall(fallback_pattern, response, re.DOTALL)
        for filename, content in fallback_matches:
            if filename and content:
                # Unescape JSON string
                try:
                    content = content.encode().decode('unicode_escape')
                except:
                    pass
                clean_name = Path(filename).name
                if clean_name and clean_name not in saved_files:
                    register_output_file(CURRENT_PROJECT, clean_name, content)
                    saved_files.append(clean_name)
                    print(f"📄 Created (fallback): {clean_name}")
    
    # Pattern 1: ```language filename.ext\n...``` or ```filename.ext\n...```
    pattern1 = r'```(\w+)?\s*(\S+\.(?:py|js|html|css|json|md|txt|sh|yaml|yml))\s*\n(.*?)```'
    matches = re.findall(pattern1, response, re.DOTALL | re.IGNORECASE)
    
    for lang, filename, content in matches:
        if filename and content.strip():
            clean_name = Path(filename).name
            if clean_name and clean_name not in saved_files:
                register_output_file(CURRENT_PROJECT, clean_name, content.strip())
                saved_files.append(clean_name)
    
    # Pattern 2: FILE: filename followed by code block
    pattern2 = r'(?:FILE|File|Fichier)[:\s]+(\S+\.(?:py|js|html|css|json|md|txt|sh|yaml|yml))\s*```(?:\w+)?\s*\n(.*?)```'
    matches = re.findall(pattern2, response, re.DOTALL | re.IGNORECASE)
    
    for filename, content in matches:
        if filename and content.strip():
            clean_name = Path(filename).name
            if clean_name and clean_name not in saved_files:
                register_output_file(CURRENT_PROJECT, clean_name, content.strip())
                saved_files.append(clean_name)
    
    # Pattern 3: Create/Creating filename followed by code block
    pattern3 = r'(?:Creat(?:e|ing)|Generating|Writing)[:\s]+[`"]?(\S+\.(?:py|js|html|css|json|md|txt|sh|yaml|yml))[`"]?\s*(?::\s*)?```(?:\w+)?\s*\n(.*?)```'
    matches = re.findall(pattern3, response, re.DOTALL | re.IGNORECASE)
    
    for filename, content in matches:
        if filename and content.strip():
            clean_name = Path(filename).name
            if clean_name and clean_name not in saved_files:
                register_output_file(CURRENT_PROJECT, clean_name, content.strip())
                saved_files.append(clean_name)
    
    # If files were saved, append info to response
    if saved_files:
        files_info = "\n\n📁 Saved to outputs: " + ", ".join(saved_files)
        return response + files_info
    
    return response


def _handle_command(message: str) -> str:
    """Handle slash commands."""
    cmd = message.split()[0].lower()
    
    if cmd == "/status":
        s = get_status()
        return "Project: {}\nVersion: {}\nAPI: {}\nErrors: {}".format(
            s['project'], s['project_version'], 
            'OK' if s['api_configured'] else 'NO', s['learned_errors'])
    elif cmd == "/clear":
        clear_conversation(CURRENT_PROJECT)
        return "Cleared"
    elif cmd == "/errors":
        errors = load_learned_errors(CURRENT_PROJECT)
        if not errors.get("errors"):
            return "No errors learned"
        lines = ["Learned:"]
        for e in errors["errors"][-5:]:
            lines.append("- [{}x] {}: {}...".format(e['count'], e['type'], e['message'][:40]))
        return "\n".join(lines)
    elif cmd == "/help":
        return "/status /clear /errors /help"
    return "Unknown: " + cmd


# ============================================================
# HTML - Dashboard v2 (THEMiS/Google Light Theme)
# ============================================================

def generate_dashboard() -> str:
    """Generate dashboard v2 HTML."""
    from ..connectors.github import get_current_branch_info
    
    # Get app version from GitHub (single source of truth)
    github_info = get_current_branch_info()
    if github_info and github_info.get("version"):
        APP_VERSION = github_info["version"]
    else:
        # Fallback to main.py VERSION
        from ..main import VERSION
        APP_VERSION = VERSION
    
    project_version = get_version(CURRENT_PROJECT) if CURRENT_PROJECT else "N/A"
    conversation = get_conversation(CURRENT_PROJECT) if CURRENT_PROJECT else []
    backlog = get_backlog(CURRENT_PROJECT) if CURRENT_PROJECT else []
    todo = get_todo(CURRENT_PROJECT) if CURRENT_PROJECT else []
    changelog = get_changelog(CURRENT_PROJECT) if CURRENT_PROJECT else []
    constraints = get_all_constraints()
    errors = load_learned_errors(CURRENT_PROJECT) if CURRENT_PROJECT else {}
    output_files = get_output_files(CURRENT_PROJECT) if CURRENT_PROJECT else []
    
    project_name = CURRENT_PROJECT or "No Project"
    error_list = errors.get("errors", [])
    pending_backlog = [b for b in backlog if b["status"] == "pending"]
    pending_todo = [t for t in todo if not t["done"]]
    
    # Build conversation HTML
    conv_html = ""
    for msg in conversation[-30:]:
        role = msg.get("role", "?")
        content = msg.get("content", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        ts = msg.get("timestamp", "")[-8:] if msg.get("timestamp") else ""
        role_class = "user" if role == "user" else "agent"
        icon = "👤 You" if role == "user" else "🤖 Agent"
        conv_html += '<div class="msg {}"><div class="msg-header">{} <span class="ts">{}</span></div><div class="msg-body">{}</div></div>'.format(
            role_class, icon, ts, content)
    
    # Build output files HTML - show ALL files (scrollable panel)
    outputs_html = ""
    ext_icons = {".py": "🐍", ".js": "📜", ".html": "🌐", ".css": "🎨", ".json": "📋", ".md": "📝", ".txt": "📄"}
    for f in output_files:
        ext = f.get("ext", "")
        icon = ext_icons.get(ext, "📄")
        size_kb = f.get("size", 0) / 1024
        size_str = "{:.1f}KB".format(size_kb) if size_kb >= 1 else "{}B".format(f.get("size", 0))
        outputs_html += '<div class="item file"><a href="/outputs/{name}" target="_blank" class="file-link">{icon} {name}</a><span class="file-size">{size}</span></div>'.format(
            name=f["name"], icon=icon, size=size_str)
    if not outputs_html:
        outputs_html = '<div class="item empty">No files</div>'
    
    # Build backlog HTML
    backlog_html = ""
    for b in pending_backlog[:6]:
        prio = b.get("priority", "medium")
        backlog_html += '<div class="item {}"><span class="cid">[{}]</span><span class="text">{}</span><span class="check">✓</span></div>'.format(
            prio, b["id"], b["title"][:30])
    if not backlog_html:
        backlog_html = '<div class="item empty">Empty</div>'
    
    # Build TODO HTML
    todo_html = ""
    for t in pending_todo[:6]:
        cat_icon = {"todo": "📌", "nth": "💡", "idea": "💭"}.get(t.get("category", "todo"), "📝")
        todo_html += '<div class="item"><span class="cid">[{}]</span><span class="text">{} {}</span></div>'.format(
            t["id"], cat_icon, t["title"][:30])
    if not todo_html:
        todo_html = '<div class="item empty">Empty</div>'
    
    # Build constraints HTML
    constraints_html = ""
    sev_icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
    for c in constraints[:8]:
        icon = sev_icons.get(c.get("severity", "MEDIUM"), "⚪")
        constraints_html += '<div class="item"><span class="sev">{}</span><span class="cid">[{}]</span> {}</div>'.format(
            icon, c["id"], c["rule"][:28])
    
    # Build changelog HTML
    changelog_html = ""
    for c in changelog[:3]:
        changes_text = ", ".join(c.get("changes", []))[:35]
        changelog_html += '<div class="changelog-item"><span class="version">v{}</span><div class="changes">{}</div></div>'.format(
            c["version"], changes_text)
    if not changelog_html:
        changelog_html = '<div class="item empty">No entries</div>'
    
    # Build errors HTML
    errors_html = ""
    for e in error_list[:3]:
        errors_html += '<div class="item error"><span class="cid">[{}x]</span> {}</div>'.format(
            e.get("count", 1), e.get("message", "")[:35])
    if not errors_html:
        errors_html = '<div class="item empty">None</div>'
    
    # Health status
    api_status = "online" if has_api_key() else "offline"
    
    html = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>LocalAgent v{app_version} - {project}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root {{
    --blue: #1a73e8;
    --blue-hover: #1557b0;
    --text-primary: #202124;
    --text-secondary: #5f6368;
    --border: #dadce0;
    --bg-light: #f8f9fa;
    --white: #ffffff;
    --success: #34a853;
    --warning: #fbbc04;
    --error: #ea4335;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ height: 100%; overflow: hidden; }}
body {{
    font-family: 'Google Sans', -apple-system, sans-serif;
    background: var(--bg-light);
    color: var(--text-primary);
    display: flex;
    flex-direction: column;
}}

/* FIXED HEADER */
header {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--white);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    height: 56px;
}}
header h1 {{ font-size: 1.1em; font-weight: 500; }}
header h1 .logo {{ color: var(--blue); }}
.header-right {{ display: flex; align-items: center; gap: 12px; }}
.health-monitors {{ display: flex; gap: 8px; }}
.health-item {{
    display: flex; align-items: center; gap: 4px;
    padding: 4px 10px; background: var(--bg-light);
    border-radius: 16px; font-size: 12px;
}}
.health-item .dot {{ width: 6px; height: 6px; border-radius: 50%; }}
.health-item .dot.online {{ background: var(--success); }}
.health-item .dot.offline {{ background: var(--error); }}
.stat-box {{
    background: var(--blue); color: white;
    padding: 4px 12px; border-radius: 6px; font-size: 12px;
}}
.btn {{
    padding: 5px 12px; border-radius: 6px; font-size: 12px;
    cursor: pointer; border: 1px solid var(--border); background: var(--white);
}}
.btn:hover {{ background: var(--bg-light); }}

/* MAIN LAYOUT - below fixed header, above fixed footer */
.main {{
    position: fixed;
    top: 56px;
    bottom: 72px;
    left: 0;
    right: 0;
    display: grid;
    grid-template-columns: 1fr 340px;
}}

/* CHAT AREA - scrollable messages */
.chat {{
    display: flex;
    flex-direction: column;
    background: var(--white);
    border-right: 1px solid var(--border);
    overflow: hidden;
}}
.messages {{
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}}
.msg {{ padding: 10px 12px; border-radius: 10px; margin-bottom: 10px; max-width: 85%; }}
.msg.user {{ background: #e8f0fe; margin-left: auto; border-bottom-right-radius: 4px; }}
.msg.agent {{ background: var(--bg-light); border-bottom-left-radius: 4px; white-space: pre-wrap; }}
.msg-header {{ font-size: 0.75em; margin-bottom: 4px; color: var(--text-secondary); }}
.msg-header .ts {{ float: right; }}
.msg-body {{ line-height: 1.4; font-size: 0.9em; }}

/* SIDEBAR - independent scroll */
.sidebar {{
    overflow-y: auto;
    padding: 12px;
    background: var(--white);
}}
.project-box {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 12px; border-radius: 10px; margin-bottom: 12px;
}}
.project-box .label {{ font-size: 0.7em; opacity: 0.8; text-transform: uppercase; }}
.project-box .name {{ font-size: 1.1em; font-weight: 600; }}
.project-box .version {{ font-size: 0.85em; opacity: 0.9; }}
.panel {{ margin-bottom: 14px; }}
.panel-header {{
    font-size: 0.8em; font-weight: 500; color: var(--text-secondary);
    margin-bottom: 8px; display: flex; justify-content: space-between;
}}
.panel-header .count {{ background: var(--bg-light); padding: 1px 6px; border-radius: 8px; font-size: 0.8em; }}
.panel-scrollable {{ max-height: 180px; overflow-y: auto; }}
.item {{
    padding: 8px 10px; background: var(--bg-light); border-radius: 6px;
    margin-bottom: 4px; font-size: 0.8em; display: flex; align-items: center; gap: 6px;
}}
.item.empty {{ color: var(--text-secondary); justify-content: center; }}
.item .cid {{
    color: var(--blue); font-family: monospace; font-size: 0.75em;
    background: rgba(26,115,232,0.1); padding: 1px 4px; border-radius: 3px;
}}
.item .sev {{ margin-right: 2px; font-size: 0.8em; }}
.item.error {{ background: #fce8e6; }}
.item .text {{ flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.item .check {{
    width: 18px; height: 18px; background: var(--success); border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    color: white; font-size: 10px; cursor: pointer;
}}
.item.critical {{ border-left: 3px solid var(--error); }}
.item.high {{ border-left: 3px solid #ff9800; }}
.item.medium {{ border-left: 3px solid var(--warning); }}
.item.low {{ border-left: 3px solid var(--success); }}
.item.file {{ background: #e6f4ea; }}
.item.file .file-link {{ color: var(--text-primary); text-decoration: none; flex: 1; display: flex; align-items: center; gap: 4px; }}
.item.file .file-link:hover {{ color: var(--blue); }}
.item.file .file-size {{ color: var(--text-secondary); font-size: 0.7em; }}
.add-form {{ display: flex; gap: 6px; margin-top: 6px; }}
.add-form input {{ flex: 1; padding: 6px 10px; border: 1px solid var(--border); border-radius: 5px; font-size: 0.8em; }}
.add-form select {{ padding: 6px; border: 1px solid var(--border); border-radius: 5px; font-size: 0.8em; background: var(--white); }}
.add-form button {{ background: var(--blue); color: white; border: none; width: 28px; height: 28px; border-radius: 5px; cursor: pointer; }}
.changelog-item {{ padding: 6px 10px; background: var(--bg-light); border-radius: 6px; margin-bottom: 4px; font-size: 0.75em; }}
.changelog-item .version {{ color: var(--blue); font-family: monospace; font-weight: 500; }}
.changelog-item .changes {{ color: var(--text-secondary); margin-top: 2px; }}

/* FIXED FOOTER - chat input */
.input-area {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 340px;
    z-index: 100;
    padding: 12px 16px;
    background: var(--white);
    border-top: 1px solid var(--border);
    box-shadow: 0 -2px 4px rgba(0,0,0,0.05);
    height: 72px;
}}
.input-row {{ display: flex; gap: 10px; height: 100%; }}
.input-row textarea {{
    flex: 1; padding: 12px; border: 1px solid var(--border);
    border-radius: 8px; resize: none; font-family: inherit; font-size: 14px;
}}
.input-row textarea:focus {{ outline: none; border-color: var(--blue); }}
.input-row button {{
    background: var(--blue); color: white; border: none;
    padding: 12px 24px; border-radius: 8px; font-weight: 500; cursor: pointer;
    white-space: nowrap;
}}
.input-row button:hover {{ background: var(--blue-hover); }}

/* LINTER BAR */
.linter-bar {{
    position: fixed;
    bottom: 72px;
    left: 0;
    right: 340px;
    z-index: 99;
    padding: 8px 16px;
    background: #fff8e6;
    border-top: 1px solid #ffd54f;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.85em;
}}
.linter-bar.good {{ background: #e8f5e9; border-color: #81c784; }}
.linter-bar.warning {{ background: #fff8e6; border-color: #ffd54f; }}
.linter-bar.bad {{ background: #ffebee; border-color: #e57373; }}
.linter-score {{
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 4px;
    background: rgba(0,0,0,0.1);
}}
.linter-issues {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    flex: 1;
}}
.linter-issue {{
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.85em;
    cursor: help;
}}
.linter-issue.high {{ background: #ffcdd2; color: #c62828; }}
.linter-issue.medium {{ background: #fff9c4; color: #f57f17; }}
.linter-issue.low {{ background: #c8e6c9; color: #2e7d32; }}
.linter-fix-btn {{
    margin-left: auto;
    padding: 6px 14px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    cursor: pointer;
    font-size: 0.85em;
    transition: transform 0.2s, box-shadow 0.2s;
}}
.linter-fix-btn:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102,126,234,0.4);
}}
.linter-meta {{
    background: rgba(0,0,0,0.08);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.8em;
    color: #666;
    font-family: monospace;
}}
/* VERSION BADGE (pill style) */
.version-badge {{
    background: #f1f3f4;
    color: #5f6368;
    font-size: 0.5em;
    padding: 4px 10px;
    border-radius: 12px;
    margin-left: 10px;
    font-weight: 500;
    vertical-align: middle;
}}
/* UPDATE BADGE */
.update-badge {{
    background: #ea4335;
    color: white;
    font-size: 0.6em;
    padding: 2px 6px;
    border-radius: 10px;
    margin-left: 8px;
    cursor: pointer;
    animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.7; }}
}}
.update-badge:hover {{ background: #c5221f; }}
/* UPDATE MODAL */
.modal-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 1000;
    align-items: center;
    justify-content: center;
}}
.modal-overlay.show {{ display: flex; }}
.modal {{
    background: white;
    border-radius: 12px;
    padding: 24px;
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    position: relative;
}}
.modal-close {{
    position: absolute;
    top: 12px;
    right: 16px;
    font-size: 24px;
    cursor: pointer;
    color: #666;
    line-height: 1;
}}
.modal-close:hover {{ color: #333; }}
.modal h2 {{ margin: 0 0 8px 0; font-size: 1.3em; padding-right: 30px; }}
.modal .version-info {{ color: var(--text-secondary); margin-bottom: 16px; font-size: 0.9em; }}
.modal .release-notes {{
    background: var(--bg-light);
    border-radius: 8px;
    padding: 16px;
    max-height: 300px;
    overflow-y: auto;
    font-size: 0.9em;
    white-space: pre-wrap;
    margin-bottom: 16px;
}}
.modal .modal-actions {{ display: flex; gap: 10px; justify-content: flex-end; }}
.modal button {{ padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 1em; }}
.modal button.primary {{ background: var(--blue); color: white; border: none; }}
.modal button.primary:hover {{ background: var(--blue-hover); }}
.modal button.secondary {{ background: transparent; color: var(--text-secondary); border: 1px solid var(--border); }}
.modal .installing {{ text-align: center; padding: 20px; }}
.modal .installing .spinner {{ font-size: 2em; animation: spin 1s linear infinite; display: inline-block; }}
@keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
</style></head>
<body>
<header>
    <h1>
        <span class="logo">🤖</span> LocalAgent 
        <span class="version-badge" onclick="showCurrentVersion()" style="cursor:pointer" title="Click for release info">v{app_version}</span>
        <span class="update-badge" id="updateBadge" style="display:none" onclick="showUpdateModal()">Update Available</span>
    </h1>
    <div class="header-right">
        <div class="health-monitors">
            <div class="health-item"><span class="dot {api_status}"></span><span>Claude</span></div>
            <div class="health-item"><span class="dot online"></span><span>GitHub</span></div>
        </div>
        <div class="stat-box">📁 <span id="fileCount">{outputs_count}</span> files</div>
        <button class="btn" onclick="location.reload()">↻ Refresh</button>
    </div>
</header>
<div class="modal-overlay" id="updateModal" onclick="if(event.target===this)hideUpdateModal()">
    <div class="modal">
        <span class="modal-close" onclick="hideUpdateModal()">&times;</span>
        <h2 id="modalTitle">🆕 Update Available</h2>
        <div class="version-info">
            <span id="currentVersion">v{app_version}</span> <span id="versionArrow">→</span> <strong id="latestVersion">v?.?.?</strong>
        </div>
        <div class="release-notes" id="releaseNotes">Loading release notes...</div>
        <div class="modal-actions" id="updateActions">
            <button class="secondary" onclick="hideUpdateModal()">Later</button>
            <button class="primary" onclick="installUpdate()">Install Update</button>
        </div>
        <div class="modal-actions" id="closeOnly" style="display:none">
            <button class="secondary" onclick="hideUpdateModal()">Close</button>
        </div>
        <div class="installing" id="installingStatus" style="display:none">
            <div class="spinner">⚙️</div>
            <p>Installing update...</p>
        </div>
    </div>
</div>
<div class="main">
    <div class="chat">
        <div class="messages" id="msgs">{conv_html}</div>
    </div>
    <div class="sidebar">
        <div class="project-box">
            <div class="label">Project</div>
            <div class="name">{project}</div>
            <div class="version">v{project_version}</div>
        </div>
        <div class="panel">
            <div class="panel-header">🗂️ Output Files <span class="count" id="outputsCount">{outputs_count}</span></div>
            <div class="panel-scrollable" id="outputFilesPanel">{outputs_html}</div>
        </div>
        <div class="panel">
            <div class="panel-header">📋 Backlog <span class="count">{backlog_count}</span></div>
            <div class="panel-scrollable">{backlog_html}</div>
            <div class="add-form">
                <input type="text" id="newBacklog" placeholder="New task...">
                <select id="backlogPrio"><option value="medium">Med</option><option value="high">High</option><option value="critical">Crit</option><option value="low">Low</option></select>
                <button onclick="addBacklog()">+</button>
            </div>
        </div>
        <div class="panel">
            <div class="panel-header">📝 TODO <span class="count">{todo_count}</span></div>
            <div class="panel-scrollable">{todo_html}</div>
            <div class="add-form">
                <input type="text" id="newTodo" placeholder="New item...">
                <select id="todoCat"><option value="todo">TODO</option><option value="nth">NTH</option><option value="idea">IDEA</option></select>
                <button onclick="addTodo()">+</button>
            </div>
        </div>
        <div class="panel">
            <div class="panel-header">🔒 Constraints <span class="count">{constraints_count}</span></div>
            <div class="panel-scrollable">{constraints_html}</div>
        </div>
        <div class="panel">
            <div class="panel-header">📜 Changelog</div>
            {changelog_html}
        </div>
        <div class="panel">
            <div class="panel-header">⚠️ Errors <span class="count">{errors_count}</span></div>
            {errors_html}
        </div>
    </div>
</div>
<div class="linter-bar" id="linterBar" style="display:none">
    <div class="linter-score"><span id="linterScore">100</span>/100</div>
    <div class="linter-issues" id="linterIssues"></div>
    <button class="linter-fix-btn" id="linterFixBtn" onclick="applyFix()" style="display:none">✨ Auto-fix</button>
</div>
<div class="input-area">
    <div class="input-row">
        <textarea id="inp" placeholder="Enter instruction..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();send();}}" oninput="debounceLint()"></textarea>
        <button onclick="send()">Send</button>
    </div>
</div>
<script>
var msgs=document.getElementById('msgs'),inp=document.getElementById('inp');
function scroll(){{msgs.scrollTop=msgs.scrollHeight}}

// === ERROR CAPTURE FOR AGENT DEBUGGING ===
var capturedErrors = [];
window.onerror = function(msg, url, line, col, error) {{
    var errorInfo = {{
        message: msg,
        url: url,
        line: line,
        column: col,
        stack: error ? error.stack : null,
        timestamp: new Date().toISOString()
    }};
    capturedErrors.push(errorInfo);
    console.error('Captured for agent:', errorInfo);
    // Auto-report to agent endpoint
    fetch('/api/debug/error', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(errorInfo)
    }}).catch(function(){{}});
    return false;
}};

// Capture unhandled promise rejections
window.onunhandledrejection = function(event) {{
    var errorInfo = {{
        message: 'Unhandled Promise: ' + event.reason,
        stack: event.reason && event.reason.stack,
        timestamp: new Date().toISOString()
    }};
    capturedErrors.push(errorInfo);
    fetch('/api/debug/error', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(errorInfo)
    }}).catch(function(){{}});
}};

// Function to get all errors for agent
function getErrorsForAgent() {{
    return JSON.stringify(capturedErrors, null, 2);
}}

// === MARKDOWN RENDERER ===
function renderMarkdown(text){{
    if(!text)return '';
    return text
        .replace(/^### (.+)$/gm,'<h4>$1</h4>')
        .replace(/^## (.+)$/gm,'<h3>$1</h3>')
        .replace(/^# (.+)$/gm,'<h2>$1</h2>')
        .replace(/^- (.+)$/gm,'<li>$1</li>')
        .replace(/[*][*](.+?)[*][*]/g,'<strong>$1</strong>')
        .replace(/[*](.+?)[*]/g,'<em>$1</em>')
        .replace(/\\n\\n/g,'<br><br>')
        .replace(/---/g,'<hr>');
}}

// === UPDATE FUNCTIONS ===
var updateInfo = null;
var currentVersionInfo = {{version:"{app_version}"}};

function checkForUpdates(){{
    fetch('/api/update/check')
    .then(function(r){{return r.json()}})
    .then(function(d){{
        updateInfo = d;
        if(d.update_available){{
            document.getElementById('updateBadge').style.display='inline';
            document.getElementById('updateBadge').textContent='v'+d.latest_version+' available';
        }}
    }})
    .catch(function(e){{console.log('Update check failed:',e)}});
}}

function showCurrentVersion(){{
    document.getElementById('updateModal').classList.add('show');
    document.getElementById('modalTitle').textContent='ℹ️ Version Info';
    document.getElementById('currentVersion').textContent='v'+currentVersionInfo.version;
    document.getElementById('latestVersion').textContent='';
    document.getElementById('versionArrow').style.display='none';
    if(updateInfo && updateInfo.current_version){{
        document.getElementById('releaseNotes').innerHTML='<p>You are running <strong>v'+currentVersionInfo.version+'</strong></p>'+(updateInfo.update_available?'<p style="color:#ea4335">Update available: v'+updateInfo.latest_version+'</p>':'<p style="color:#34a853">You are on the latest version.</p>');
        document.getElementById('updateActions').style.display=updateInfo.update_available?'flex':'none';
        document.getElementById('closeOnly').style.display=updateInfo.update_available?'none':'flex';
    }}else{{
        document.getElementById('releaseNotes').innerHTML='<p>Version <strong>v'+currentVersionInfo.version+'</strong></p>';
        document.getElementById('updateActions').style.display='none';
        document.getElementById('closeOnly').style.display='flex';
    }}
    document.getElementById('installingStatus').style.display='none';
}}

function showUpdateModal(){{
    if(!updateInfo || !updateInfo.update_available)return;
    document.getElementById('updateModal').classList.add('show');
    document.getElementById('modalTitle').textContent='🆕 Update Available';
    document.getElementById('versionArrow').style.display='inline';
    document.getElementById('currentVersion').textContent='v'+updateInfo.current_version;
    document.getElementById('latestVersion').textContent='v'+updateInfo.latest_version;
    document.getElementById('releaseNotes').innerHTML=renderMarkdown(updateInfo.release_notes)||'No release notes available.';
    document.getElementById('updateActions').style.display='flex';
    document.getElementById('closeOnly').style.display='none';
    document.getElementById('updateActions').style.display='flex';
    document.getElementById('installingStatus').style.display='none';
}}

function hideUpdateModal(){{
    document.getElementById('updateModal').classList.remove('show');
}}

function installUpdate(){{
    document.getElementById('updateActions').style.display='none';
    document.getElementById('installingStatus').style.display='block';
    
    fetch('/api/update/install-from-github',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:'{{}}'}})
    .then(function(r){{return r.json()}})
    .then(function(d){{
        if(d.success){{
            document.getElementById('installingStatus').innerHTML='<div style="color:#34a853;font-size:1.2em">✅ Updated to v'+d.new_version+'!</div><p>Reloading in 3 seconds...</p>';
            setTimeout(function(){{location.reload()}},3000);
        }}else{{
            document.getElementById('installingStatus').innerHTML='<div style="color:#ea4335">❌ '+d.error+'</div>';
            document.getElementById('updateActions').style.display='flex';
        }}
    }})
    .catch(function(e){{
        document.getElementById('installingStatus').innerHTML='<div style="color:#ea4335">❌ Install failed: '+e+'</div>';
        document.getElementById('updateActions').style.display='flex';
    }});
}}

// Check for updates on load
checkForUpdates();
// Check every 5 minutes
setInterval(checkForUpdates, 300000);

function send(){{
    var m=inp.value.trim();if(!m)return;inp.value='';
    // Hide linter bar on send
    var linterBar=document.getElementById('linterBar');
    if(linterBar)linterBar.style.display='none';
    
    addMsg('user',m);
    fetch('/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:m}})}})
    .then(function(r){{return r.json()}})
    .then(function(d){{
        if(d.response)addMsg('agent',d.response);
        else if(d.error)addMsg('agent','Error: '+d.error);
        // Refresh all panels after response
        refreshAllPanels();
    }})
    .catch(function(e){{addMsg('agent','Error: '+e)}});
}}
function refreshAllPanels(){{
    refreshOutputFiles();
    refreshBacklog();
    refreshTodo();
    refreshChangelog();
    refreshErrors();
}}
function refreshBacklog(){{
    fetch('/api/backlog')
    .then(function(r){{return r.json()}})
    .then(function(items){{
        var container=document.querySelector('.panel-scrollable');
        // Find backlog panel by header
        document.querySelectorAll('.panel').forEach(function(panel){{
            var header=panel.querySelector('.panel-header');
            if(header&&header.textContent.includes('Backlog')){{
                var scrollable=panel.querySelector('.panel-scrollable');
                if(scrollable){{
                    var html='';
                    var pending=items.filter(function(b){{return b.status==='pending'||b.status==='in_progress'}});
                    pending.forEach(function(b){{
                        var prio=b.priority||'medium';
                        html+='<div class="item '+prio+'"><span class="cid">['+b.id+']</span><span class="text">'+b.title.substring(0,30)+'</span></div>';
                    }});
                    if(!html)html='<div class="item empty">Empty</div>';
                    scrollable.innerHTML=html;
                    var count=panel.querySelector('.count');
                    if(count)count.textContent=pending.length;
                }}
            }}
        }});
    }});
}}
function refreshTodo(){{
    fetch('/api/todo')
    .then(function(r){{return r.json()}})
    .then(function(items){{
        document.querySelectorAll('.panel').forEach(function(panel){{
            var header=panel.querySelector('.panel-header');
            if(header&&header.textContent.includes('TODO')){{
                var scrollable=panel.querySelector('.panel-scrollable');
                if(scrollable){{
                    var html='';
                    var pending=items.filter(function(t){{return !t.done}});
                    pending.forEach(function(t){{
                        var catIcon=t.category==='nth'?'💡':t.category==='idea'?'💭':'📌';
                        html+='<div class="item"><span class="cid">['+t.id+']</span><span class="text">'+catIcon+' '+t.title.substring(0,30)+'</span></div>';
                    }});
                    if(!html)html='<div class="item empty">Empty</div>';
                    scrollable.innerHTML=html;
                    var count=panel.querySelector('.count');
                    if(count)count.textContent=pending.length;
                }}
            }}
        }});
    }});
}}
function refreshChangelog(){{
    fetch('/api/changelog')
    .then(function(r){{return r.json()}})
    .then(function(items){{
        document.querySelectorAll('.panel').forEach(function(panel){{
            var header=panel.querySelector('.panel-header');
            if(header&&header.textContent.includes('Changelog')){{
                var container=panel.querySelector('.panel-scrollable')||panel;
                var html='';
                items.slice(0,3).forEach(function(c){{
                    var changes=(c.changes||[]).join(', ').substring(0,35);
                    html+='<div class="changelog-item"><span class="version">v'+c.version+'</span><div class="changes">'+changes+'</div></div>';
                }});
                if(!html)html='<div class="item empty">No entries</div>';
                // Find the right place to put changelog html
                var existingChangelog=panel.querySelectorAll('.changelog-item');
                if(existingChangelog.length>0){{
                    existingChangelog.forEach(function(el){{el.remove()}});
                }}
                panel.insertAdjacentHTML('beforeend',html);
            }}
        }});
    }});
}}
function refreshErrors(){{
    fetch('/api/errors')
    .then(function(r){{return r.json()}})
    .then(function(data){{
        var errors=data.errors||[];
        document.querySelectorAll('.panel').forEach(function(panel){{
            var header=panel.querySelector('.panel-header');
            if(header&&header.textContent.includes('Errors')){{
                var html='';
                errors.slice(0,3).forEach(function(e){{
                    html+='<div class="item error"><span class="cid">['+(e.count||1)+'x]</span> '+(e.message||'').substring(0,35)+'</div>';
                }});
                if(!html)html='<div class="item empty">None</div>';
                var scrollable=panel.querySelector('.panel-scrollable');
                if(scrollable)scrollable.innerHTML=html;
                var count=panel.querySelector('.count');
                if(count)count.textContent=errors.length;
            }}
        }});
    }});
}}
function updateFileCount(newFiles){{
    var el=document.getElementById('fileCount');
    if(el)el.textContent=parseInt(el.textContent||0)+newFiles;
    var hdr=document.getElementById('headerFileCount');
    if(hdr)hdr.textContent=parseInt(hdr.textContent||0)+newFiles;
}}
function refreshOutputFiles(){{
    fetch('/api/outputs')
    .then(function(r){{return r.json()}})
    .then(function(files){{
        var container=document.getElementById('outputFilesPanel');
        if(!container)return;
        var html='';
        files.forEach(function(f){{
            var icon=f.ext==='.html'?'🌐':f.ext==='.py'?'🐍':f.ext==='.js'?'📜':'📄';
            var size=f.size>1024?(f.size/1024).toFixed(1)+'KB':f.size+'B';
            html+='<div class="item file"><a href="/outputs/'+f.name+'" target="_blank" class="file-link">'+icon+' '+f.name+'</a><span class="file-size">'+size+'</span></div>';
        }});
        if(!html)html='<div class="item empty">No files</div>';
        container.innerHTML=html;
        var countEl=document.getElementById('outputsCount');
        if(countEl)countEl.textContent=files.length;
    }});
}}
function addMsg(role,content){{
    var d=document.createElement('div');
    d.className='msg '+role;
    var icon=role==='user'?'👤 You':'🤖 Agent';
    var now=new Date().toTimeString().slice(0,8);
    d.innerHTML='<div class="msg-header">'+icon+' <span class="ts">'+now+'</span></div><div class="msg-body">'+content.replace(/</g,'&lt;').replace(/\\n/g,'<br>')+'</div>';
    msgs.appendChild(d);scroll();
}}
function addBacklog(){{
    var t=document.getElementById('newBacklog').value.trim();
    var p=document.getElementById('backlogPrio').value;
    if(!t)return;
    fetch('/api/backlog/add',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{title:t,priority:p}})}})
    .then(function(){{location.reload()}});
}}
function addTodo(){{
    var t=document.getElementById('newTodo').value.trim();
    var c=document.getElementById('todoCat').value;
    if(!t)return;
    fetch('/api/todo/add',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{title:t,category:c}})}})
    .then(function(){{location.reload()}});
}}
var lintTimer=null;
function debounceLint(){{
    clearTimeout(lintTimer);
    lintTimer=setTimeout(runLint,500);
}}
var lastOptimized='';
function runLint(){{
    var text=inp.value.trim();
    var bar=document.getElementById('linterBar');
    var fixBtn=document.getElementById('linterFixBtn');
    if(!text||text.length<10){{bar.style.display='none';return;}}
    fetch('/api/lint',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{prompt:text}})}})
    .then(function(r){{return r.json()}})
    .then(function(d){{
        bar.style.display='flex';
        document.getElementById('linterScore').textContent=d.score;
        bar.className='linter-bar '+(d.score>=80?'good':d.score>=50?'warning':'bad');
        var html='';
        // Show task type and tokens
        var taskType=d.task_type?d.task_type.type:'?';
        var estCost=d.tokens?d.tokens.estimated_cost:0;
        html+='<span class="linter-meta">'+d.language.toUpperCase()+' | '+taskType+' | ~$'+estCost.toFixed(3)+'</span>';
        // Show issues
        (d.issues||[]).forEach(function(i){{
            html+='<span class="linter-issue '+i.severity+'" title="'+i.fix+'">'+i.message+'</span>';
        }});
        if(!d.issues||d.issues.length===0){{
            html+='<span style="color:#388e3c">✓ Prompt OK</span>';
        }}
        document.getElementById('linterIssues').innerHTML=html;
        lastOptimized=d.optimized||'';
        if(d.score<80&&lastOptimized&&lastOptimized!==text){{
            fixBtn.style.display='block';
        }}else{{
            fixBtn.style.display='none';
        }}
    }});
}}
function applyFix(){{
    if(lastOptimized){{
        inp.value=lastOptimized;
        runLint();
    }}
}}
scroll();
</script>
</body></html>'''.format(
        project=project_name,
        app_version=APP_VERSION,
        project_version=project_version,
        api_status=api_status,
        conv_html=conv_html if conv_html else '<div style="color:#999;text-align:center;padding:40px">Start a conversation...</div>',
        outputs_html=outputs_html,
        outputs_count=len(output_files),
        backlog_html=backlog_html,
        backlog_count=len(pending_backlog),
        todo_html=todo_html,
        todo_count=len(pending_todo),
        constraints_html=constraints_html,
        constraints_count=len(constraints),
        changelog_html=changelog_html,
        errors_html=errors_html,
        errors_count=len(error_list)
    )
    
    return html


# ============================================================
# SERVER
# ============================================================

def start_server(project: str, port: int = None):
    """Start dashboard server."""
    set_project(project)
    port = port or DASHBOARD_PORT
    
    # Sync app version to GitHub config on startup
    from .github import sync_app_version
    sync_app_version()
    
    # Find available port
    for p in range(port, port + 10):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', p))
                port = p
                break
        except OSError:
            continue
    
    server = HTTPServer(('localhost', port), Handler)
    
    print("Server: http://localhost:{}".format(port))
    print("Project: {}".format(project))
    
    # Open browser
    if platform.system() == "Darwin":
        subprocess.Popen(["open", "http://localhost:{}".format(port)])
    elif platform.system() == "Linux":
        subprocess.Popen(["xdg-open", "http://localhost:{}".format(port)])
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
        server.shutdown()
