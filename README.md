Vibe Rhino Live Viewer

Hot-reloads Rhino geometry from a Python script while you edit with LLM agent in IDE.

Requirements
- Rhino 7/8 on Windows (Rhino Python enabled).
- This repo cloned locally (paths below assume `C:\Users\(USERNAME)\source\repos\vibe_rhino`).

Install & Start the Watcher (once per Rhino session)
1) Open Rhino.
2) Point the watcher at your script (optional): edit `src/watcher/rhino_watcher.py` and set `TARGET_SCRIPT` to the full path of the script you want hot-reloaded. It defaults to `src/sketch/sketch_minimumSurface.py`.
3) Run the watcher in Rhino:
   ```
   _RunPythonScript 
   ```
   Rhino’s command line should print `[watcher] started.` and create `src/watcher/watcher.log`.
4) Leave Rhino open; the watcher stays attached to Rhino’s idle event until you close Rhino.

Using Hot Reload in IDE
- Edit the target script (e.g., `src/sketch/sketch_minimumSurface.py`).
- Save the file; within ~0.5s the watcher reloads and redraws the active Rhino document.
- Use `src/sketch/sketch_script.py` as a minimal template if you want to start from a clean example.

Project Layout
- `src/watcher/rhino_watcher.py` Idle watcher that monitors the target script and reloads geometry.
- `src/sketch/sketch_minimumSurface.py` Default hot-reload target (Enneper minimal surface demo).
- `src/sketch/sketch_script.py` Simple starter script showing the expected `build(doc)` entry point.

Troubleshooting
- No reload? Confirm `TARGET_SCRIPT` points to an existing file and Rhino has an active document.
- For LLM agent to check error at sketch level, point `src/watcher/watcher.log` to it for checking errors; it is cleared every time you start the watcher.
