Vibe Rhino Live Viewer

Hot-reloads Rhino geometry from a Python script as you edit.

Quick Start
1. Open Rhino.
2. Run the watcher:
   - `_-RunPythonScript "C:\path\to\vibe\rhino_watcher.py"`
3. Edit and save `vibe\vibe_script.py`.

Project Layout
- `vibe/rhino_watcher.py` Rhino idle watcher that reloads geometry.
- `vibe/vibe_script.py` Your live-edit geometry script.
- `vibe/README.md` Additional notes.
