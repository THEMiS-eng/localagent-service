#!/usr/bin/env python3
"""
Push v10.5.37 to GitHub repositories.
Run this from your local machine after installing the package.
"""
import sys
import os

# Add localagent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from localagent.connectors.github import github_push, github_create_release

VERSION = "10.5.37"
CHANGELOG = """
## v10.5.37 - Fix Mode Toggle (Stale Closure Bug)

### Fixed
- **Critical**: Fixed stale closure bug in `toggleMode()` that caused A/S swap to fail on first click
  - Changed from using outer `state.mode` to using callback `s.mode` inside `setState()`
  - Mode toggle now works correctly on every click

### Base
- Built from v10.5.31 (last stable version)
- Single targeted fix, no other changes
"""

def main():
    print(f"Pushing LocalAgent v{VERSION} to GitHub...")
    
    # Push service repo
    print("\n1. Pushing to localagent-service...")
    result = github_push(
        source_dir=".",
        repo_type="service",
        message=f"v{VERSION}: Fix stale closure in toggleMode"
    )
    print(f"   Result: {result}")
    
    # Create release
    print(f"\n2. Creating release v{VERSION}...")
    result = github_create_release(
        repo_type="service",
        version=VERSION,
        notes=CHANGELOG,
        draft=False,
        prerelease=False
    )
    print(f"   Result: {result}")
    
    print("\nDone!")

if __name__ == "__main__":
    main()
