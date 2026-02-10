Vibe Rhino Live Viewer

Hot-reloads Rhino geometry from a Python script as you edit.

Quick Start
1. Open Rhino.
2. Run the watcher:
   - `_-RunPythonScript "C:\path\to\vibe\rhino_watcher.py"`
3. Edit and save `vibe\vibe_asymptotic_script.py` (both U/V curve families aim for asymptotic directions).

Project Layout
- `vibe/rhino_watcher.py` Rhino idle watcher that reloads geometry.
- `vibe/vibe_asymptotic_script.py` Live-edit script using asymptotic alignment in both parametric directions.
- `vibe/vibe_script.py` Original geodesic/asymptotic hybrid live-edit script.
- `vibe/README.md` Additional notes.
