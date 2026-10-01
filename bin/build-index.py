#!/usr/bin/env python3
"""Generate index.json from the SKILL.md frontmatters in this repo.

This is an OPTIONAL manifest: it lets an agent runtime that loads skills over
HTTP (instead of from disk) discover which skills exist and where to fetch each
file. Every entry lists SKILL.md plus all references/ and scripts/ with an
absolute URL (base is configurable). If your agents only read skills from the
local filesystem (the plugin install or bin/sync.sh), you don't need this file.

Usage:
    bin/build-index.py [--base-url https://raw.githubusercontent.com/<user>/skills/main]
"""
import os
import sys
import json
import glob
import datetime


def parse_frontmatter(path):
    """Extract the lightweight YAML frontmatter between the first two '---'."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data = {}
    for line in parts[1].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ": " in line:
            key, val = line.split(": ", 1)
        elif line.rstrip().endswith(":"):
            key, val = line.rstrip()[:-1], ""
        else:
            continue
        data[key.strip()] = val.strip()
    # metadata is inline JSON inside the YAML
    if data.get("metadata"):
        try:
            data["metadata"] = json.loads(data["metadata"])
        except Exception:
            pass
    return data


def main():
    base = "https://raw.githubusercontent.com/gwendall/skills/main"
    args = sys.argv[1:]
    if "--base-url" in args:
        base = args[args.index("--base-url") + 1]
    base = base.rstrip("/")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skills = []
    for skill_md in sorted(glob.glob(os.path.join(root, "skills", "*", "*", "SKILL.md"))):
        sd = os.path.dirname(skill_md)
        name = os.path.basename(sd)
        category = os.path.basename(os.path.dirname(sd))
        fm = parse_frontmatter(skill_md)
        meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
        openclaw = meta.get("openclaw") or {}

        files = []
        rel = os.path.relpath(skill_md, root)
        files.append({"path": rel, "url": f"{base}/{rel}", "role": "skill"})
        for sub, role in (("references", "reference"), ("scripts", "script")):
            for p in sorted(glob.glob(os.path.join(sd, sub, "**", "*"), recursive=True)):
                parts = p.split(os.sep)
                if (
                    os.path.isfile(p)
                    and "__pycache__" not in parts
                    and not p.endswith((".pyc", ".pyo"))
                ):
                    r = os.path.relpath(p, root)
                    files.append({"path": r, "url": f"{base}/{r}", "role": role})

        skills.append({
            "name": fm.get("name", name),
            "category": category,
            "description": fm.get("description", ""),
            "version": meta.get("version"),
            "updated": meta.get("updated"),
            "compatibility": fm.get("compatibility", ""),
            "requires": openclaw.get("requires"),
            "emoji": openclaw.get("emoji"),
            "files": files,
        })

    index = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "baseUrl": base,
        "count": len(skills),
        "skills": skills,
    }
    out = os.path.join(root, "index.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {out} - {len(skills)} skills: " + ", ".join(s["name"] for s in skills))


if __name__ == "__main__":
    main()
