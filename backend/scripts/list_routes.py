"""Print every registered route (used by `python -m backend.manage routes`)."""

import sys

from backend.app.main import app

paths = app.openapi()["paths"]
print("OpenAPI paths:", len(paths))
for path in sorted(paths):
    methods = ",".join(sorted(m.upper() for m in paths[path]))
    print(f"  {methods:<28} {path}")

ws = [
    getattr(r, "path", "<no-path>")
    for r in app.routes
    if type(r).__name__ == "WebSocketRoute"
]
print("\nWebSocket routes:", len(ws))
for path in ws:
    print("  WS", path)

print("\nTotal routes:", len(app.routes))
sys.exit(0 if len(paths) > 40 else 1)
