"""Export openapi.json without starting the HTTP server."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure the project root is on the path when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application import create_app

schema = create_app().openapi()
output = Path("openapi.json")
output.write_text(json.dumps(schema, indent=2))
print(f"Exported {output} ({len(schema['paths'])} paths)")
