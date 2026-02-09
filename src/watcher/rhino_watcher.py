import os
import traceback
import datetime

import Rhino
import scriptcontext as sc
import System


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_SCRIPT = os.path.join(os.path.dirname(BASE_DIR), "sketch", "sketch_minimumSurface.py")

_STICKY_KEY = "vibe_rhino_watcher"
_DEBOUNCE_SECONDS = 0.5
_LOG_PATH = os.path.join(BASE_DIR, "watcher.log")


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


def _clear_log():
    try:
        dir_name = os.path.dirname(_LOG_PATH)
        if dir_name and not os.path.isdir(dir_name):
            os.makedirs(dir_name)
        with open(_LOG_PATH, "w") as fd:
            fd.write("")
    except Exception:
        Rhino.RhinoApp.WriteLine("[watcher] failed to clear watcher.log")


def _write_to_log(msg):
    try:
        dir_name = os.path.dirname(_LOG_PATH)
        if dir_name and not os.path.isdir(dir_name):
            os.makedirs(dir_name)
        with open(_LOG_PATH, "a") as fd:
            timestamp = datetime.datetime.utcnow().isoformat()
            fd.write("{0} {1}\n".format(timestamp, msg))
    except Exception:
        Rhino.RhinoApp.WriteLine("[watcher] failed to write watcher.log")


def log(msg):
    Rhino.RhinoApp.WriteLine(msg)
    _write_to_log(msg)


def _load_build():
    if not os.path.isfile(TARGET_SCRIPT):
        log("[watcher] target script not found.")
        return

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
        log("[watcher] failed to read target script (file busy).")
        return

    exec(compile(code, TARGET_SCRIPT, "exec"), ns)
    build = ns.get("build", None)
    if not callable(build):
        log("[watcher] build(doc) not found in target script.")
        return

    doc = sc.doc or Rhino.RhinoDoc.ActiveDoc
    if doc is None:
        log("[watcher] no active document.")
        return

    # doc.Objects.Clear()
    build(doc)
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
    _clear_log()
    log("[watcher] loading...")

    Rhino.RhinoApp.Idle += _on_idle
    st.idle_hooked = True

    log("[watcher] started.")
    _load_build()


start()
