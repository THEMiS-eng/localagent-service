#!/usr/bin/env python3
"""
LocalAgent v3.0.31 - Service Worker + Agent Orchestrator

SERVICE WORKER (localhost:9998):
  localagent start                 Start service daemon
  localagent stop                  Stop service
  localagent status                Show service status
  localagent logs                  Tail service logs

ARCHITECTURE:
├── service/        # SERVICE WORKER
│   ├── daemon.py        # Daemon lifecycle
│   └── server.py        # HTTP API server
├── core/           # CORE BUSINESS
│   ├── constraints.py   # Rules
│   ├── learning.py      # Error learning
│   └── negotiator.py    # Claude negotiation
├── engine/         # SUPPORT
│   ├── project.py       # Projects, snapshots
│   └── tracking.py      # Backlog, TODO
├── connectors/     # INTERFACES
│   ├── llm.py           # Claude API
│   ├── github.py        # Git operations + Push
│   └── dashboard.py     # Dashboard UI
└── roadmap/        # FUTURE
"""

import sys
from pathlib import Path

VERSION = "3.0.62"


def main():
    # Add parent to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from localagent.core import show_constraints, show_learned_errors, load_learned_errors
    from localagent.engine import (
        AGENT_DIR, list_projects, get_version,
        init_project, commit_project,
        create_snapshot, list_snapshots, rollback,
        show_backlog, show_todo,
        add_backlog_item, update_backlog_item,
        add_todo_item, toggle_todo
    )
    from localagent.connectors import (
        has_api_key, set_api_key,
        github_clone, github_sync, github_list, github_remove,
        start_server
    )
    
    if len(sys.argv) < 2:
        print("""
LocalAgent v{} - Service Worker + Agent Orchestrator

SERVICE WORKER:
  localagent start                      Start service (localhost:9998)
  localagent stop                       Stop service
  localagent status                     Show status
  localagent logs                       Tail service logs
  localagent restart                    Restart service

PROJECT MANAGEMENT:
  localagent init <project> <source>    Initialize project
  localagent commit <project> "message" Commit changes
  
  localagent snapshot <project> [label] Create snapshot
  localagent snapshots <project>        List snapshots
  localagent rollback <project> [id]    Rollback
  
  localagent backlog <project>          Show backlog
  localagent backlog-add <project> "title" [priority]
  localagent backlog-done <project> <id>
  
  localagent todo <project>             Show TODO
  localagent todo-add <project> "title" [category]
  localagent todo-done <project> <id>

DASHBOARD:
  localagent server <project>           Start dashboard UI

GITHUB:
  localagent github list                List configured repos
  localagent github push-service <ver>  Push service to GitHub
  localagent github push-dashboard <ver> Push dashboard to GitHub
  localagent github push-all <ver>      Push both repos
  localagent github releases            List releases

CONFIG:
  localagent set-key <api_key>          Set Claude API key
  localagent constraints                Show constraints
  localagent errors <project>           Show learned errors
""".format(VERSION))
        return
    
    cmd = sys.argv[1]
    
    # ========== SERVICE WORKER COMMANDS ==========
    if cmd == "start":
        from localagent.service import daemon
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 9998
        foreground = "--fg" in sys.argv or "--foreground" in sys.argv
        daemon.start(port=port, foreground=foreground)
        return
    
    elif cmd == "stop":
        from localagent.service import daemon
        daemon.stop()
        return
    
    elif cmd == "restart":
        from localagent.service import daemon
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 9998
        daemon.restart(port=port)
        return
    
    elif cmd == "logs":
        from localagent.service import daemon
        follow = "-f" in sys.argv or "--follow" in sys.argv
        daemon.tail_logs(follow=follow)
        return
    
    # ========== STATUS ==========
    elif cmd == "status":
        from localagent.service import daemon
        
        print()
        print("=" * 50)
        print("  LocalAgent v{}".format(VERSION))
        print("=" * 50)
        print()
        
        # Service status
        svc_status = daemon.status()
        if svc_status["running"]:
            print("Service: 🟢 Running (PID: {})".format(svc_status["pid"]))
            if svc_status.get("url"):
                print("         {}".format(svc_status["url"]))
        else:
            print("Service: 🔴 Stopped")
            print("         Run: localagent start")
        print()
        
        print("API: {}".format("✅ Configured" if has_api_key() else "❌ NOT CONFIGURED"))
        print()
        print("Projects:")
        projects = list_projects()
        if projects:
            for p in projects:
                errors = load_learned_errors(p["name"])
                err_count = len(errors.get("errors", []))
                print("  {}: v{} | {} errors learned".format(p["name"], p["version"], err_count))
        else:
            print("  (none)")
        print()
    
    # ========== INIT ==========
    elif cmd == "init":
        if len(sys.argv) < 4:
            print("Usage: localagent init <project> <source>")
            return
        if init_project(sys.argv[2], sys.argv[3]):
            print("OK: {}".format(sys.argv[2]))
    
    # ========== COMMIT ==========
    elif cmd == "commit":
        if len(sys.argv) < 4:
            print("Usage: localagent commit <project> \"message\"")
            return
        commit_project(sys.argv[2], sys.argv[3])
    
    # ========== SNAPSHOT ==========
    elif cmd == "snapshot":
        if len(sys.argv) < 3:
            print("Usage: localagent snapshot <project> [label]")
            return
        label = sys.argv[3] if len(sys.argv) > 3 else ""
        snap_id = create_snapshot(sys.argv[2], label)
        if snap_id:
            print("OK: {}".format(snap_id))
        else:
            print("FAILED")
    
    elif cmd == "snapshots":
        if len(sys.argv) < 3:
            print("Usage: localagent snapshots <project>")
            return
        snaps = list_snapshots(sys.argv[2])
        print("\nSnapshots for {}:".format(sys.argv[2]))
        for s in snaps[:15]:
            print("  {} (v{})".format(s["id"], s.get("version", "?")))
        print()
    
    elif cmd == "rollback":
        if len(sys.argv) < 3:
            print("Usage: localagent rollback <project> [id]")
            return
        snap_id = sys.argv[3] if len(sys.argv) > 3 else None
        if rollback(sys.argv[2], snap_id):
            print("OK")
        else:
            print("FAILED")
    
    # ========== BACKLOG ==========
    elif cmd == "backlog":
        if len(sys.argv) < 3:
            print("Usage: localagent backlog <project>")
            return
        show_backlog(sys.argv[2])
    
    elif cmd == "backlog-add":
        if len(sys.argv) < 4:
            print("Usage: localagent backlog-add <project> \"title\" [priority]")
            return
        prio = sys.argv[4] if len(sys.argv) > 4 else "medium"
        item_id = add_backlog_item(sys.argv[2], sys.argv[3], prio)
        print("OK: {}".format(item_id))
    
    elif cmd == "backlog-done":
        if len(sys.argv) < 4:
            print("Usage: localagent backlog-done <project> <id>")
            return
        if update_backlog_item(sys.argv[2], sys.argv[3], status="done"):
            print("OK")
        else:
            print("NOT FOUND")
    
    # ========== TODO ==========
    elif cmd == "todo":
        if len(sys.argv) < 3:
            print("Usage: localagent todo <project>")
            return
        show_todo(sys.argv[2])
    
    elif cmd == "todo-add":
        if len(sys.argv) < 4:
            print("Usage: localagent todo-add <project> \"title\" [category]")
            return
        cat = sys.argv[4] if len(sys.argv) > 4 else "todo"
        item_id = add_todo_item(sys.argv[2], sys.argv[3], cat)
        print("OK: {}".format(item_id))
    
    elif cmd == "todo-done":
        if len(sys.argv) < 4:
            print("Usage: localagent todo-done <project> <id>")
            return
        if toggle_todo(sys.argv[2], sys.argv[3]):
            print("OK")
        else:
            print("NOT FOUND")
    
    # ========== SERVER ==========
    elif cmd == "server":
        if len(sys.argv) < 3:
            print("Usage: localagent server <project>")
            return
        start_server(sys.argv[2])
    
    # ========== GITHUB ==========
    elif cmd == "github":
        if len(sys.argv) < 3:
            print("""
Usage: localagent github <command> ...

Commands:
  list                              List configured repos
  clone <project> <url> [branch]    Clone repo into project
  sync <project> [repo]             Pull latest changes
  remove <project> <repo>           Remove cloned repo
  
  push-service <version> [--release]   Push service to GitHub
  push-dashboard <version> [--release] Push dashboard to GitHub  
  push-all <version> [--release]       Push both repos
  
  releases [service|dashboard]      List releases
  release-service <version>         Create service release
  release-dashboard <version>       Create dashboard release
  delete-release <service|dashboard> <version>  Delete a release
""")
            return
        
        sub = sys.argv[2]
        
        if sub == "list":
            github_list()
        
        elif sub == "clone":
            if len(sys.argv) < 5:
                print("Usage: localagent github clone <project> <url> [branch]")
                return
            branch = sys.argv[5] if len(sys.argv) > 5 else "main"
            if github_clone(sys.argv[3], sys.argv[4], branch):
                print("OK")
            else:
                print("FAILED")
        
        elif sub == "sync":
            if len(sys.argv) < 4:
                print("Usage: localagent github sync <project> [repo]")
                return
            repo = sys.argv[4] if len(sys.argv) > 4 else None
            if github_sync(sys.argv[3], repo):
                print("OK")
            else:
                print("FAILED")
        
        elif sub == "remove":
            if len(sys.argv) < 5:
                print("Usage: localagent github remove <project> <repo>")
                return
            if github_remove(sys.argv[3], sys.argv[4]):
                print("OK")
            else:
                print("FAILED")
        
        elif sub == "push-service":
            from localagent.connectors.github import github_push
            if len(sys.argv) < 4:
                print("Usage: localagent github push-service <version> [--release]")
                return
            version = sys.argv[3]
            create_release = "--release" in sys.argv
            
            # Use localagent_v3 directory
            source = Path.home() / "localagent_v3"
            
            result = github_push(str(source), "service", version=version, create_release=create_release)
            if result["success"]:
                print("✅ Service pushed to GitHub")
                print("   Repo: {}".format(result.get("repo")))
                print("   Actions: {}".format(", ".join(result.get("actions", []))))
            else:
                print("❌ Failed: {}".format(result.get("error")))
        
        elif sub == "push-dashboard":
            from localagent.connectors.github import github_push
            if len(sys.argv) < 4:
                print("Usage: localagent github push-dashboard <version> [--release]")
                return
            version = sys.argv[3]
            create_release = "--release" in sys.argv
            
            source = Path.home() / "localagent_v3" / "dashboard"
            
            result = github_push(str(source), "dashboard", version=version, create_release=create_release)
            if result["success"]:
                print("✅ Dashboard pushed to GitHub")
                print("   Repo: {}".format(result.get("repo")))
                print("   Actions: {}".format(", ".join(result.get("actions", []))))
            else:
                print("❌ Failed: {}".format(result.get("error")))
        
        elif sub == "push-all":
            from localagent.connectors.github import github_push_all
            if len(sys.argv) < 4:
                print("Usage: localagent github push-all <version> [--release]")
                return
            version = sys.argv[3]
            create_releases = "--release" in sys.argv
            
            service_dir = str(Path.home() / "localagent_v3")
            dashboard_dir = str(Path.home() / "localagent_v3" / "dashboard")
            
            result = github_push_all(service_dir, dashboard_dir, version, create_releases=create_releases)
            if result["success"]:
                print("\n✅ All repos pushed successfully")
            else:
                print("\n⚠️ Some operations failed")
        
        elif sub == "releases":
            from localagent.connectors.github import github_list_releases
            repo_type = sys.argv[3] if len(sys.argv) > 3 else None
            releases = github_list_releases(repo_type)
            
            if releases:
                print("\nGitHub Releases:")
                for r in releases:
                    print("  {} v{} - {} ({})".format(
                        r.get("repo_type", "?"),
                        r.get("version", "?"),
                        r.get("published_at", "")[:10] if r.get("published_at") else "unpublished",
                        r.get("url", "")
                    ))
            else:
                print("No releases found")
        
        elif sub == "release-service":
            from localagent.connectors.github import github_create_release
            if len(sys.argv) < 4:
                print("Usage: localagent github release-service <version>")
                return
            version = sys.argv[3]
            result = github_create_release("service", version)
            if result["success"]:
                print("✅ Service release created: {}".format(result.get("url")))
            else:
                print("❌ Failed: {}".format(result.get("error")))
        
        elif sub == "release-dashboard":
            from localagent.connectors.github import github_create_release
            if len(sys.argv) < 4:
                print("Usage: localagent github release-dashboard <version>")
                return
            version = sys.argv[3]
            result = github_create_release("dashboard", version)
            if result["success"]:
                print("✅ Dashboard release created: {}".format(result.get("url")))
            else:
                print("❌ Failed: {}".format(result.get("error")))
        
        elif sub == "delete-release":
            from localagent.connectors.github import github_delete_release
            if len(sys.argv) < 5:
                print("Usage: localagent github delete-release <service|dashboard> <version>")
                return
            repo_type = sys.argv[3]
            version = sys.argv[4]
            result = github_delete_release(repo_type, version)
            if result["success"]:
                print("✅ Release deleted: {}".format(result.get("deleted")))
            else:
                print("❌ Failed: {}".format(result.get("error")))
        
        else:
            print("Unknown github command: {}".format(sub))
    
    # ========== CONSTRAINTS ==========
    elif cmd == "constraints":
        show_constraints()
    
    # ========== ERRORS ==========
    elif cmd == "errors":
        if len(sys.argv) < 3:
            print("Usage: localagent errors <project>")
            return
        show_learned_errors(sys.argv[2])
    
    # ========== SET-KEY ==========
    elif cmd == "set-key":
        if len(sys.argv) < 3:
            print("Usage: localagent set-key <api_key>")
            return
        set_api_key(sys.argv[2])
        print("OK")
    
    # ========== VERSION ==========
    elif cmd == "version" or cmd == "--version" or cmd == "-v":
        print("LocalAgent v{}".format(VERSION))
    
    else:
        print("Unknown command: {}".format(cmd))


if __name__ == "__main__":
    main()
