import os
import traceback

import Rhino
import scriptcontext as sc
import System


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_SCRIPT = os.path.join(BASE_DIR, "vibe_script.py")

_STICKY_KEY = "vibe_rhino_watcher"
_DEBOUNCE_SECONDS = 0.5
_RESTORE_SELECTION = False  # keep doc untouched; no forced reselection


class _State(object):
    def __init__(self):
        self.reload_in_progress = False
        self.last_mtime = None
        self.last_size = None
        self.changed_at = None
        self.idle_hooked = False


def _state():
    st = sc.sticky.get(_STICKY_KEY, None)
    if st is None:
        st = _State()
        sc.sticky[_STICKY_KEY] = st
    return st


def log(msg):
    Rhino.RhinoApp.WriteLine(msg)


def _load_build():
    if not os.path.isfile(TARGET_SCRIPT):
        log("[watcher] vibe_script.py not found.")
        return

    # Capture current selection (it may be lost during reload). Only overwrite the cache when non-empty.
    doc = sc.doc or Rhino.RhinoDoc.ActiveDoc
    if doc:
        selected = list(doc.Objects.GetSelectedObjects(False, False) or [])
        if selected:
            sc.sticky["vibe_selected_ids"] = [o.Id for o in selected if not o.IsDeleted]
            log("[watcher] selection cached: {} objects".format(len(sc.sticky["vibe_selected_ids"])))
        else:
            log("[watcher] no active selection; keeping previous cache ({})".format(len(sc.sticky.get("vibe_selected_ids", []))))
        log("[watcher] selection before build: {}".format(len(selected)))
    else:
        sc.sticky["vibe_selected_ids"] = []

    ns = {}
    code = None
    for _ in range(5):
        try:
            with open(TARGET_SCRIPT, "r") as f:
                code = f.read()
            break
        except Exception:
            System.Threading.Thread.Sleep(50)

    if code is None:
        log("[watcher] failed to read vibe_script.py (file busy).")
        return

    exec(compile(code, TARGET_SCRIPT, "exec"), ns)
    build = ns.get("build", None)
    if not callable(build):
        log("[watcher] build(doc) not found in vibe_script.py.")
        return

    doc = sc.doc or Rhino.RhinoDoc.ActiveDoc
    if doc is None:
        log("[watcher] no active document.")
        return

    # Run build without clearing the document
    build(doc)

    # No reselection; leave doc state untouched
    doc.Views.Redraw()
    log("[watcher] geometry updated.")


def _maybe_reload():
    st = _state()
    if st.reload_in_progress:
        return

    if not os.path.isfile(TARGET_SCRIPT):
        return

    try:
        stat = os.stat(TARGET_SCRIPT)
    except Exception:
        return

    mtime = stat.st_mtime
    size = stat.st_size

    if st.last_mtime is None:
        st.last_mtime = mtime
        st.last_size = size
        st.changed_at = System.DateTime.UtcNow
        return

    if mtime != st.last_mtime or size != st.last_size:
        st.last_mtime = mtime
        st.last_size = size
        st.changed_at = System.DateTime.UtcNow
        return

    if st.changed_at is None:
        return

    delta = System.DateTime.UtcNow - st.changed_at
    if delta.TotalSeconds < _DEBOUNCE_SECONDS:
        return

    st.changed_at = None
    st.reload_in_progress = True
    try:
        _load_build()
    except Exception:
        log("[watcher] error while reloading:")
        log(traceback.format_exc())
    finally:
        st.reload_in_progress = False


def _on_idle(sender, args):
    _maybe_reload()


def start():
    st = _state()

    if st.idle_hooked:
        return

    log("[watcher] loading...")

    Rhino.RhinoApp.Idle += _on_idle
    st.idle_hooked = True

    log("[watcher] started.")
    _load_build()


def stop():
    """Detach the idle handler to stop reloading vibe_script.py."""
    st = _state()
    if not st.idle_hooked:
        return
    try:
        Rhino.RhinoApp.Idle -= _on_idle
    except Exception:
        pass
    st.idle_hooked = False
    log("[watcher] stopped.")


start()
