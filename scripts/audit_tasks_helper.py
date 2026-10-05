import json
import glob
from pathlib import Path

def inspect_v2():
    for path in sorted(glob.glob("tasks/v2/*/task.json")):
        with open(path, "r", encoding="utf-8") as f:
            t = json.load(f)
        print("=" * 60)
        print(f"Task: {t['task_id']}")
        print(f"Difficulty: {t.get('difficulty')} | Categories: {t.get('categories')} | Domain: {t.get('metadata', {}).get('domain')}")
        print(f"Files ({len(t.get('repo_files', {}))}): {list(t.get('repo_files', {}).keys())}")
        print(f"Description: {t.get('description')}")
        print(f"Spec Notes: {t.get('spec_notes')}")

        print("\n[REPO FILES]")
        for fname, code in t.get("repo_files", {}).items():
            lines = len(code.splitlines())
            print(f"  - {fname} ({lines} lines)")

        print("\n[TESTS]")
        for fname, code in t.get("tests", {}).items():
            lines = len(code.splitlines())
            print(f"  - {fname} ({lines} lines):")
            for l in code.splitlines():
                if l.strip().startswith("def test_"):
                    print(f"      {l.strip()}")

        print("\n[REFERENCE FIX]")
        for fname, code in t.get("reference_fix", {}).items():
            print(f"  - Modifies: {fname}")

if __name__ == "__main__":
    inspect_v2()
