#!/usr/bin/env python3
import ast, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

#беббеб

ROOT = Path(__file__).resolve().parent
PLUGINS_DIR = ROOT / "plugins"
INDEX = ROOT / "extera-plugins.json"
REPOSITORY = {
    "schema": 1,
    "name": "MTProto Manager",
    "author": "@dimkkq",
    "homepage": "https://github.com/dimkkq/mtproto-manager-plugin",
}
FIELDS = ("id", "name", "description", "author", "version", "icon",
          "app_version", "sdk_version", "requirements", "category")

def read_plugin_file(path):
    meta = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and t.id.startswith("__") and t.id.endswith("__"):
                k = t.id[2:-2]
                if k in FIELDS:
                    meta[k] = ast.literal_eval(node.value)
    return meta

def main():
    prev = {}
    if INDEX.exists():
        prev = {p["id"]: p for p in json.loads(INDEX.read_text(encoding="utf-8")).get("plugins", [])}
    plugins = []
    for path in sorted(PLUGINS_DIR.rglob("*.plugin")):
        meta = read_plugin_file(path)
        missing = [k for k in ("id", "name", "version") if not meta.get(k)]
        if missing:
            raise SystemExit(f"{path}: missing {missing}")
        data = path.read_bytes()
        entry = {
            **meta,
            "file": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
        old = prev.get(meta["id"], {})
        if old.get("sha256") == entry["sha256"] and old.get("updated_at"):
            entry["updated_at"] = old["updated_at"]
        else:
            entry["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        plugins.append(entry)
    INDEX.write_text(
        json.dumps({**REPOSITORY, "plugins": plugins}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{INDEX.name}: {len(plugins)} plugins")

if __name__ == "__main__":
    main()


