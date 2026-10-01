#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  DIAGNOSTIC DUMP — FamilySafety project state
  Shows every file relevant to the "fileTree for AAR missing" issue
═══════════════════════════════════════════════════════════════
"""
import os
import sys
from pathlib import Path

ROOT = Path.cwd()

SEP = "═" * 72
SUB = "─" * 72


def header(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def sub(title):
    print(f"\n{SUB}\n  {title}\n{SUB}")


def dump_file(path: Path, max_lines: int = 200):
    sub(f"FILE: {path.relative_to(ROOT)}")
    if not path.exists():
        print(f"  ❌ DOES NOT EXIST")
        return
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total = len(lines)
        shown = lines[:max_lines]
        for i, line in enumerate(shown, 1):
            print(f"{i:4d} | {line}")
        if total > max_lines:
            print(f"  ... ({total - max_lines} more lines)")
        print(f"\n  [total: {total} lines, {len(content)} chars]")
    except Exception as e:
        print(f"  ❌ read error: {e}")


def list_dir(path: Path):
    sub(f"DIR: {path.relative_to(ROOT)}")
    if not path.exists():
        print(f"  ❌ DOES NOT EXIST")
        return
    for item in sorted(path.iterdir()):
        kind = "📁" if item.is_dir() else "📄"
        size = ""
        if item.is_file():
            sz = item.stat().st_size
            if sz < 1024:
                size = f"{sz} B"
            elif sz < 1024 * 1024:
                size = f"{sz / 1024:.1f} KB"
            else:
                size = f"{sz / 1024 / 1024:.1f} MB"
        print(f"  {kind} {item.name}  {size}")


def main():
    print(f"\n{SEP}")
    print(f"  PROJECT ROOT: {ROOT}")
    print(f"  NAME: {ROOT.name}")
    print(f"{SEP}")

    # ═══════════════════════════════════════════════════════════
    #  1. TOP-LEVEL STRUCTURE
    # ═══════════════════════════════════════════════════════════
    header("1. TOP-LEVEL STRUCTURE")
    for item in sorted(ROOT.iterdir()):
        if item.name in (".git", "__pycache__", ".gradle", "build", ".idea"):
            print(f"  (skipped) {item.name}/")
            continue
        kind = "📁" if item.is_dir() else "📄"
        print(f"  {kind} {item.name}")

    # ═══════════════════════════════════════════════════════════
    #  2. app/build.gradle  ← MAIN ISSUE
    # ═══════════════════════════════════════════════════════════
    header("2. app/build.gradle  (WHERE fileTree IS MISSING)")
    dump_file(ROOT / "app" / "build.gradle", max_lines=300)

    # ═══════════════════════════════════════════════════════════
    #  3. app/libs/
    # ═══════════════════════════════════════════════════════════
    header("3. app/libs/  (WHERE AAR SHOULD LAND)")
    list_dir(ROOT / "app" / "libs")

    # ═══════════════════════════════════════════════════════════
    #  4. WORKFLOWS
    # ═══════════════════════════════════════════════════════════
    header("4. .github/workflows/")
    wf_dir = ROOT / ".github" / "workflows"
    list_dir(wf_dir)
    if wf_dir.exists():
        for wf in sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")):
            dump_file(wf, max_lines=400)

    # ═══════════════════════════════════════════════════════════
    #  5. settings.gradle
    # ═══════════════════════════════════════════════════════════
    header("5. settings.gradle")
    dump_file(ROOT / "settings.gradle", max_lines=80)
    dump_file(ROOT / "settings.gradle.kts", max_lines=80)

    # ═══════════════════════════════════════════════════════════
    #  6. gradle.properties
    # ═══════════════════════════════════════════════════════════
    header("6. gradle.properties")
    dump_file(ROOT / "gradle.properties", max_lines=80)

    # ═══════════════════════════════════════════════════════════
    #  7. root build.gradle
    # ═══════════════════════════════════════════════════════════
    header("7. build.gradle (root)")
    dump_file(ROOT / "build.gradle", max_lines=120)
    dump_file(ROOT / "build.gradle.kts", max_lines=120)

    # ═══════════════════════════════════════════════════════════
    #  8. tsnet-bridge structure
    # ═══════════════════════════════════════════════════════════
    header("8. tsnet-bridge/")
    list_dir(ROOT / "tsnet-bridge")

    # ═══════════════════════════════════════════════════════════
    #  9. Grep for fileTree / libs references
    # ═══════════════════════════════════════════════════════════
    header("9. GREP: 'fileTree' / 'libs' across project")
    for pattern in ("fileTree", "app/libs", "tsnetbridge"):
        sub(f"pattern: {pattern}")
        found = False
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(x in str(path) for x in (".git/", "build/", ".gradle/", "__pycache__")):
                continue
            if path.suffix not in (".gradle", ".kts", ".yml", ".yaml", ".properties", ".md"):
                continue
            try:
                for i, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
                    if pattern in line:
                        print(f"  {path.relative_to(ROOT)}:{i}: {line.strip()}")
                        found = True
            except Exception:
                pass
        if not found:
            print(f"  (no matches)")

    # ═══════════════════════════════════════════════════════════
    #  10. Git status
    # ═══════════════════════════════════════════════════════════
    header("10. GIT STATUS")
    os.system("git status --short 2>/dev/null | head -40")
    print()
    os.system("git log --oneline -5 2>/dev/null")

    print(f"\n{SEP}")
    print("  DIAGNOSTIC COMPLETE")
    print(f"{SEP}\n")


if __name__ == "__main__":
    main()
