"""Log tracking for SA Empty Anim Export.

Sinks (all best-effort, never raise):
  1. Blender console / stdout via print()
  2. Blender Text block "SA_Anim_Log" (when running inside Blender)
  3. Rotating-ish plain text file (default next to the blend file, else temp)

Each line: [YYYY-MM-DD HH:MM:SS] [LEVEL] message
"""

import datetime
import os
import tempfile

TEXT_NAME = "SA_Anim_Log"
_lines = []


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _to_text_block(line):
    try:
        import bpy
        txt = bpy.data.texts.get(TEXT_NAME)
        if txt is None:
            txt = bpy.data.texts.new(TEXT_NAME)
        txt.write(line + "\n")
    except Exception:
        pass


def default_log_path():
    try:
        import bpy
        base = os.path.dirname(bpy.data.filepath)
        if base:
            return os.path.join(base, "sa_anim_export.log")
    except Exception:
        pass
    return os.path.join(tempfile.gettempdir(), "sa_anim_export.log")


def log(msg, level="INFO", log_path=None):
    line = "[%s] [%s] %s" % (_now(), level, msg)
    _lines.append(line)
    if len(_lines) > 2000:
        del _lines[:500]
    print(line)
    _to_text_block(line)
    path = log_path or default_log_path()
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print("[%s] [WARN] log file write failed (%s): %s" % (_now(), path, e))
    return line


def recent(n=30):
    return list(_lines[-n:])
