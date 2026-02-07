#!/usr/bin/env python3
"""
push_build.py - Push un build PUBLIC vers GitHub (DEV ONLY)

Base sur: docs/SAD.md

Usage:
    python scripts/push_build.py
    python scripts/push_build.py --dry-run
    python scripts/push_build.py --status
"""

import subprocess
import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path

# =============================================================================
# CONFIGURATION (selon SAD.md)
# =============================================================================

LOCALAGENT_DIR = Path.home() / ".localagent"
LOCALAGENT_DEV_DIR = Path.home() / ".localagent-dev"
MODULES_DIR = LOCALAGENT_DIR / "modules"
BUILD_FILE = LOCALAGENT_DIR / "BUILD"
MANIFEST_FILE = LOCALAGENT_DIR / "manifest.json"
GITHUB_TOKEN_FILE = LOCALAGENT_DEV_DIR / "github_token"

# Modules valides (SAD Section 6.3)
VALID_MODULES = ["core", "engine", "connectors", "skills", "roadmap", "service"]

# Exclusions du BUILD PUBLIC (SAD Section 2.2)
EXCLUDED_PATHS = [
    "dashboard/",
    "tests/",
    "scripts/",
    ".github/",
    ".git/",
    ".pytest_cache/",
    "__pycache__/",
    "*.pyc",
    ".DS_Store",
    ".claude/",
]

# Mapping fichiers -> modules (SAD Section 5)
MODULE_MAPPING = {
    "localagent/core/": "core",
    "localagent/engine/": "engine",
    "localagent/connectors/": "connectors",
    "localagent/skills/": "skills",
    "localagent/roadmap/": "roadmap",
    "localagent/service/": "service",
    "localagent/main.py": "core",
    "localagent/__init__.py": "core",
    "default_skills/": "skills",
}


# =============================================================================
# HELPERS
# =============================================================================

def run(cmd, capture=True):
    """Execute une commande shell."""
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def print_header(title):
    """Affiche un header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title):
    """Affiche une section."""
    print()
    print(f"--- {title} ---")


# =============================================================================
# VERIFICATION ENVIRONNEMENT DEV
# =============================================================================

def check_dev_environment():
    """
    Verifie qu'on est en environnement DEV.
    (SAD Section 3.1: Token GitHub requis)
    """
    # Verifier le token GitHub
    if not GITHUB_TOKEN_FILE.exists():
        print("X ERREUR: Token GitHub non trouve")
        print(f"   Attendu: {GITHUB_TOKEN_FILE}")
        print()
        print("   Vous etes en environnement PUBLIC (pas de GitHub)")
        print("   Ce script est reserve a l'environnement DEV")
        return False

    token = GITHUB_TOKEN_FILE.read_text().strip()
    if not token:
        print("X ERREUR: Token GitHub vide")
        return False

    # Verifier qu'on est dans un repo git
    code, _, _ = run("git rev-parse --git-dir")
    if code != 0:
        print("X ERREUR: Pas dans un repository Git")
        return False

    print("[OK] Environnement DEV detecte")
    print(f"    Token: {GITHUB_TOKEN_FILE}")
    return True


# =============================================================================
# GIT STATUS
# =============================================================================

def get_modified_files():
    """
    Recupere les fichiers modifies via git status.
    Retourne: liste de (status, filepath)
    """
    code, output, _ = run("git status --porcelain")
    if code != 0:
        return []

    files = []
    for line in output.split("\n"):
        if line.strip() and len(line) >= 3:
            status = line[:2].strip()
            # git status --porcelain format: "XY path" (2 chars + space + path)
            filepath = line[3:].split(" -> ")[-1].strip()
            # Handle edge case where path might start with space
            if not filepath and len(line) > 3:
                filepath = line.split()[-1] if line.split() else ""
            if filepath:
                files.append((status, filepath))
    return files


def filter_public_files(files):
    """
    Filtre les fichiers pour ne garder que ceux du BUILD PUBLIC.
    Exclut: dashboard/, tests/, scripts/, etc. (SAD Section 2.2)
    """
    public_files = []
    excluded_files = []

    for status, filepath in files:
        is_excluded = False

        for pattern in EXCLUDED_PATHS:
            if pattern.endswith("/"):
                # Directory pattern
                if filepath.startswith(pattern) or f"/{pattern}" in filepath:
                    is_excluded = True
                    break
            elif pattern.startswith("*"):
                # Wildcard pattern
                if filepath.endswith(pattern[1:]):
                    is_excluded = True
                    break
            else:
                # Exact match
                if filepath == pattern or filepath.endswith(f"/{pattern}"):
                    is_excluded = True
                    break

        if is_excluded:
            excluded_files.append((status, filepath))
        else:
            public_files.append((status, filepath))

    return public_files, excluded_files


# =============================================================================
# MODULE MAPPING
# =============================================================================

def map_files_to_modules(files):
    """
    Mappe les fichiers modifies aux modules.
    (SAD Section 5)
    """
    modules = set()
    unmapped = []

    for status, filepath in files:
        mapped = False
        for pattern, module in MODULE_MAPPING.items():
            if filepath.startswith(pattern):
                if module in VALID_MODULES:
                    modules.add(module)
                mapped = True
                break

        if not mapped:
            unmapped.append(filepath)

    return sorted(modules), unmapped


# =============================================================================
# VERSIONING
# =============================================================================

def read_version(filepath):
    """Lit un fichier VERSION."""
    try:
        return Path(filepath).read_text().strip()
    except FileNotFoundError:
        return "1.0.0"


def increment_version(version):
    """Incremente le patch d'une version (1.0.0 -> 1.0.1)."""
    parts = version.split(".")
    if len(parts) >= 3:
        # Detecter si format avec zeros (3.3.035)
        if len(parts[2]) == 3 and parts[2].startswith("0"):
            parts[2] = f"{int(parts[2]) + 1:03d}"
        else:
            parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts[:3])


def write_version(filepath, version):
    """Ecrit un fichier VERSION."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    Path(filepath).write_text(version + "\n")


def load_manifest():
    """Charge le manifest.json."""
    try:
        return json.loads(MANIFEST_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"build": "0.0.0", "modules": {}, "created": "", "updated": ""}


def save_manifest(manifest):
    """Sauvegarde le manifest.json."""
    manifest["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2) + "\n")


def bump_module_version(module):
    """Incremente la version d'un module."""
    version_file = MODULES_DIR / module / "VERSION"
    old_version = read_version(version_file)
    new_version = increment_version(old_version)
    write_version(version_file, new_version)
    return old_version, new_version


def bump_build_version():
    """Incremente le BUILD global."""
    old_version = read_version(BUILD_FILE)
    new_version = increment_version(old_version)
    write_version(BUILD_FILE, new_version)
    return old_version, new_version


# =============================================================================
# GIT OPERATIONS
# =============================================================================

def git_add_public_files(files):
    """
    git add seulement les fichiers PUBLIC.
    """
    if not files:
        return True

    # Ajouter fichier par fichier
    for status, filepath in files:
        if status == "D":
            # Fichier supprime
            run(f'git add "{filepath}"')
        else:
            # Fichier modifie ou ajoute
            run(f'git add "{filepath}"')

    return True


def git_commit(message):
    """git commit avec le message."""
    # Utiliser heredoc pour le message multiligne
    safe_msg = message.replace('"', '\\"').replace('$', '\\$')
    code, out, err = run(f'git commit -m "{safe_msg}"')
    return code == 0, out, err


def git_push():
    """git push origin main."""
    # Essayer main d'abord
    code, out, err = run("git push origin main")
    if code != 0:
        # Essayer master
        code, out, err = run("git push origin master")
    return code == 0, out, err


# =============================================================================
# MAIN
# =============================================================================

def show_status():
    """Affiche le status actuel des versions."""
    print_header("STATUS DES VERSIONS")

    # BUILD
    build = read_version(BUILD_FILE)
    print(f"\nBUILD: {build}")

    # Modules
    print("\nMODULES:")
    for module in VALID_MODULES:
        version_file = MODULES_DIR / module / "VERSION"
        version = read_version(version_file)
        exists = "[OK]" if version_file.exists() else "[--]"
        print(f"  {exists} {module:12} : {version}")

    # Manifest
    print(f"\nMANIFEST: {MANIFEST_FILE}")
    if MANIFEST_FILE.exists():
        manifest = load_manifest()
        print(f"  build: {manifest.get('build', 'N/A')}")
        print(f"  updated: {manifest.get('updated', 'N/A')}")
    else:
        print("  (non trouve)")

    # Environnement
    print(f"\nENVIRONNEMENT:")
    if GITHUB_TOKEN_FILE.exists():
        print(f"  [OK] DEV (token present)")
    else:
        print(f"  [--] PUBLIC (pas de token)")


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args

    # --status
    if "--status" in args:
        show_status()
        return 0

    print_header("PUSH BUILD - DEV ONLY")

    # 1. Verifier environnement DEV
    print_section("1. Verification environnement DEV")
    if not check_dev_environment():
        return 1

    # 2. git status
    print_section("2. Fichiers modifies (git status)")
    all_files = get_modified_files()

    if not all_files:
        print("[OK] Aucun fichier modifie")
        return 0

    # 3. Filtrer fichiers PUBLIC vs EXCLUS
    print_section("3. Filtrage BUILD PUBLIC")
    public_files, excluded_files = filter_public_files(all_files)

    print(f"\nFichiers PUBLIC ({len(public_files)}):")
    for status, filepath in public_files[:20]:
        print(f"  [{status:>2}] {filepath}")
    if len(public_files) > 20:
        print(f"  ... et {len(public_files) - 20} autres")

    if excluded_files:
        print(f"\nFichiers EXCLUS ({len(excluded_files)}) - non commites:")
        for status, filepath in excluded_files[:10]:
            print(f"  [{status:>2}] {filepath}")
        if len(excluded_files) > 10:
            print(f"  ... et {len(excluded_files) - 10} autres")

    if not public_files:
        print("\n[!] Aucun fichier PUBLIC modifie")
        print("    (Seuls les fichiers DEV ont ete modifies)")
        return 0

    # 4. Mapper aux modules
    print_section("4. Modules detectes")
    modules, unmapped = map_files_to_modules(public_files)

    if modules:
        print(f"Modules: {', '.join(modules)}")
    else:
        print("Aucun module identifie (fichiers racine)")

    if unmapped and len(unmapped) <= 5:
        print(f"Non mappes: {', '.join(unmapped)}")

    # 5. Incrementer les versions
    print_section("5. Increment des versions")

    version_changes = []
    manifest = load_manifest()

    # Modules
    for module in modules:
        if dry_run:
            # En dry-run, calculer sans ecrire
            version_file = MODULES_DIR / module / "VERSION"
            old_v = read_version(version_file)
            new_v = increment_version(old_v)
        else:
            old_v, new_v = bump_module_version(module)
        version_changes.append((module, old_v, new_v))
        manifest["modules"][module] = new_v
        print(f"  {module}: {old_v} -> {new_v}")

    # BUILD global
    if dry_run:
        old_build = read_version(BUILD_FILE)
        new_build = increment_version(old_build)
    else:
        old_build, new_build = bump_build_version()
    manifest["build"] = new_build
    print(f"  BUILD: {old_build} -> {new_build}")

    # 6. Sauvegarder manifest
    if not dry_run:
        save_manifest(manifest)
        print(f"\n[OK] Manifest mis a jour: {MANIFEST_FILE}")
    else:
        print(f"\n[DRY-RUN] Manifest non sauvegarde")

    # 7. Demander le nom du build
    print_section("6. Nom du build")

    if dry_run:
        build_name = "DRY_RUN_TEST"
        print(f"[DRY-RUN] Build name: {build_name}")
    else:
        build_name = input("Nom du build (ex: T001_fix_security): ").strip()
        if not build_name:
            print("X Nom de build requis")
            return 1

        # Valider le format
        if not re.match(r'^[A-Z]\d{3}_\w+$', build_name):
            print(f"[!] Format recommande: T001_description")
            confirm = input("    Continuer quand meme? [y/N]: ").strip().lower()
            if confirm != 'y':
                return 1

    # 8. Generer le commit message
    print_section("7. Message de commit")

    commit_lines = [f"[BUILD] {build_name}", ""]

    if version_changes:
        for module, old_v, new_v in version_changes:
            commit_lines.append(f"- {module}: {old_v} -> {new_v}")

    commit_lines.append(f"- BUILD: {old_build} -> {new_build}")
    commit_lines.append("")
    commit_lines.append(f"Files: {len(public_files)} public, {len(excluded_files)} excluded")

    commit_msg = "\n".join(commit_lines)

    print(commit_msg)

    # 9. Confirmation
    print_section("8. Confirmation")

    if dry_run:
        print("[DRY-RUN] Aucune modification effectuee")
        print("\nCommandes qui seraient executees:")
        print(f"  git add <{len(public_files)} fichiers PUBLIC>")
        print(f"  git commit -m '[BUILD] {build_name}...'")
        print(f"  git push origin main")
        return 0

    print(f"  Fichiers a commiter: {len(public_files)}")
    print(f"  Fichiers exclus: {len(excluded_files)}")
    print(f"  Nouvelle version: {new_build}")
    print()

    confirm = input("Confirmer le push? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("X Annule")
        return 1

    # 10. git add (fichiers PUBLIC seulement)
    print_section("9. git add (PUBLIC only)")

    git_add_public_files(public_files)
    print(f"[OK] {len(public_files)} fichiers ajoutes")

    # 11. git commit
    print_section("10. git commit")

    success, out, err = git_commit(commit_msg)
    if not success:
        print(f"X Erreur git commit: {err}")
        return 1
    print(out if out else "[OK] Commit cree")

    # 12. git push
    print_section("11. git push")

    success, out, err = git_push()
    if not success:
        print(f"X Erreur git push: {err}")
        return 1
    print(out if out else "[OK] Push reussi")

    # Resume
    print_header(f"BUILD {build_name} POUSSE")
    print(f"\n  Version: {new_build}")
    print(f"  Modules: {', '.join(modules) if modules else 'aucun'}")
    print(f"  Fichiers: {len(public_files)} PUBLIC")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
