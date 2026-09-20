bl_info = {
    "name": "SA Empty Anim Export (IFP)",
    "author": "sa_tools",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > SA Anim",
    "description": "Export object-hierarchy animation to GTA SA IFP (ANP3), mirroring anim_export.ms (Max Dummy -> Blender Empty/Mesh). With operation log tracking.",
    "category": "Object",
}

import os

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy_extras.io_utils import ExportHelper
from mathutils import Matrix

from . import ifp
from .log_tracker import TEXT_NAME, default_log_path, log, recent


# ---------------------------------------------------------------- helpers

def iter_descendants(root):
    """Mirror Max getSubs: every descendant, any object type (Empty, Mesh, ...)."""
    out = []

    def walk(o):
        for c in o.children:
            out.append(c)
            walk(c)

    walk(root)
    return out


def get_action_fcurves(obj):
    """Return fcurves affecting obj; works on legacy and layered (Blender 5) actions."""
    ad = getattr(obj, "animation_data", None)
    if not ad or not getattr(ad, "action", None):
        return []
    act = ad.action
    legacy = getattr(act, "fcurves", None)
    if legacy is not None and not callable(legacy):
        try:
            return list(legacy)
        except Exception:
            pass
    # Layered action: match this object's slot handle.
    slot = getattr(ad, "action_slot", None)
    handle = getattr(slot, "handle", None) if slot else None
    try:
        for layer in act.layers:
            for strip in layer.strips:
                bags = getattr(strip, "channelbags", [])
                for cb in bags:
                    if handle is not None and getattr(getattr(cb, "slot", None), "handle", None) != handle:
                        continue
                    try:
                        return list(cb.fcurves)
                    except Exception:
                        continue
    except Exception:
        pass
    return []


ROT_PATHS = {"rotation_euler", "rotation_quaternion", "rotation_axis_angle"}


def collect_frames(obj, have_pos):
    rot, loc = set(), set()
    for fc in get_action_fcurves(obj):
        frames = {round(k.co.x, 3) for k in fc.keyframe_points}
        if fc.data_path in ROT_PATHS:
            rot |= frames
        elif fc.data_path == "location" and have_pos:
            loc |= frames
    frames = rot | loc
    # Mirror .ms: rotation keys always drive the key list; when have_pos is
    # off, location-only frames are ignored. If nothing keyed, bind pose.
    return sorted(frames)


def sample_bone(scene, obj, frames, fps_eff, log_path):
    """Sample parent-space quat+loc at frames. Returns list of (q,loc,t)."""
    cur = scene.frame_current
    cur_sub = scene.frame_subframe if hasattr(scene, "frame_subframe") else 0.0
    keys = []
    try:
        for f in frames:
            fi = int(f)
            sub = float(f - fi)
            try:
                scene.frame_set(fi, subframe=sub)
            except TypeError:
                scene.frame_set(fi)
            bpy.context.view_layer.update()
            pw = obj.parent.matrix_world if obj.parent else Matrix.Identity(4)
            local = pw.inverted() @ obj.matrix_world
            loc, quat, _ = local.decompose()
            quat.normalize()
            t = (f - scene.frame_start) * 60.0 / fps_eff if fps_eff else 0.0
            if t < 0:
                log("bone %s: frame %s -> negative time, clamped to 0" % (obj.name, f),
                    "WARN", log_path)
                t = 0.0
            if t > 65535:
                log("bone %s: frame %s -> time overflow, clamped" % (obj.name, f),
                    "WARN", log_path)
                t = 65535.0
            keys.append((quat.x, quat.y, quat.z, quat.w,
                         (loc.x, loc.y, loc.z), t))
    finally:
        try:
            scene.frame_set(cur, subframe=cur_sub)
        except TypeError:
            scene.frame_set(cur)
        bpy.context.view_layer.update()
    return keys


def validate_names(op, root, items, log_path):
    """Refuse/warn on mesh names that break the IFP name limits.

    The IFP bone field holds 24 bytes; GTA SA itself is only safe up to
    ~12 chars (INU docs: longer names crash the game when the IFP is
    applied). Returns False (and reports an error) when a name cannot
    even fit the field; warns and continues otherwise. Uses live object
    names so renames after Get Hierarchy are honored.
    """
    seen, names = set(), []
    for n in [root.name] + [it.obj.name for it in items
                            if not it.exclude and it.obj is not None]:
        if n not in seen:
            seen.add(n)
            names.append(n)
    bad = ifp.check_names(names)
    for name, ln, level in bad:
        log("name '%s' is %d chars (%s limit %d): shorten it or the "
            "game may fail to open the IFP"
            % (name, ln, "over 24-byte field," if level == "error"
               else "over 12-char safe", ifp.NAME_LEN if level == "error"
               else ifp.SAFE_NAME_LEN),
            "ERROR" if level == "error" else "WARN", log_path)
    errs = ["'%s' (%d)" % (n, ln) for n, ln, lv in bad if lv == "error"]
    warns = ["'%s' (%d)" % (n, ln) for n, ln, lv in bad if lv == "warn"]
    if errs:
        op.report({"ERROR"},
                  "Name(s) exceed 24-char IFP field, export refused: %s. "
                  "Shorten them and retry." % ", ".join(errs))
        return False
    if warns:
        op.report({"WARNING"},
                  "Name(s) exceed 12-char safe limit (game may crash): %s."
                  % ", ".join(warns))
    return True


def build_export_bones(context, items, log_path):
    scene = context.scene
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    bones, skipped = [], 0
    for it in items:
        if it.exclude:
            log("skip excluded: %s" % it.name, "INFO", log_path)
            continue
        obj = it.obj
        if obj is None:
            log("skip missing datablock: %s" % it.name, "WARN", log_path)
            skipped += 1
            continue
        have_pos = not it.skip_pos
        frames = collect_frames(obj, have_pos)
        if not frames:
            frames = [float(scene.frame_current)]
            log("bone %s: no keys -> single bind-pose key at frame %s"
                % (obj.name, scene.frame_current), "WARN", log_path)
        keys = sample_bone(scene, obj, frames, fps, log_path)
        if not have_pos:
            keys = [(qx, qy, qz, qw, None, t) for qx, qy, qz, qw, _, t in keys]
        bones.append((obj.name, keys, have_pos))
        log("bone %s: type=%d keys=%d have_pos=%s frames=%s"
            % (obj.name, 4 if have_pos else 3, len(keys), have_pos, frames),
            "INFO", log_path)
    return bones, fps


# ---------------------------------------------------------------- properties

class SA_BoneItem(bpy.types.PropertyGroup):
    name: StringProperty(default="")
    obj: PointerProperty(type=bpy.types.Object)
    exclude: BoolProperty(name="Exclude", default=False)
    skip_pos: BoolProperty(name="Skip Pos", default=True)


_TYPE_ICONS = {"EMPTY": "EMPTY_ARROWS", "MESH": "MESH_DATA"}


class SA_UL_Bones(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active, sel, idx):
        row = layout.row(align=True)
        otype = item.obj.type if item.obj else ""
        live = item.obj.name if item.obj else item.name
        ln = ifp.sanitized_len(live)
        if ln > ifp.NAME_LEN:
            icon_name, text = "ERROR", "%s  (%d!)" % (live, ln)
        elif ln > ifp.SAFE_NAME_LEN:
            icon_name, text = _TYPE_ICONS.get(otype, "OBJECT_DATA"), "%s  (%d)" % (live, ln)
        else:
            icon_name, text = _TYPE_ICONS.get(otype, "OBJECT_DATA"), live
        row.label(text=text, icon=icon_name)
        row.prop(item, "exclude", text="")
        row.prop(item, "skip_pos", text="P")


# ---------------------------------------------------------------- operators

class SA_OT_get_hierarchy(bpy.types.Operator):
    bl_idname = "sa_anim.get_hierarchy"
    bl_label = "Get Hierarchy (Selected)"
    bl_description = "Collect ALL descendants of the root (Empty, Mesh, ...) like Max getSubs"

    def execute(self, context):
        sc = context.scene
        log_path = sc.sa_log_path or default_log_path()
        root = sc.sa_root or context.active_object
        if root is None:
            self.report({"ERROR"}, "No root: pick a parent object or select one")
            return {"CANCELLED"}
        if sc.sa_root is None:
            sc.sa_root = root
        sc.sa_bones.clear()
        desc = iter_descendants(root)
        n_empty = sum(1 for o in desc if o.type == "EMPTY")
        n_mesh = sum(1 for o in desc if o.type == "MESH")
        for o in desc:
            it = sc.sa_bones.add()
            it.name = o.name
            it.obj = o
            it.exclude = False
            it.skip_pos = True
        sc.sa_bones_index = 0
        log("get_hierarchy root=%s (%s) descendants=%d empty=%d mesh=%d other=%d anim=%s"
            % (root.name, root.type, len(desc), n_empty, n_mesh,
               len(desc) - n_empty - n_mesh, root.name), "INFO", log_path)
        self.report({"INFO"}, "Hierarchy: %d objects (empty %d, mesh %d)"
                    % (len(desc), n_empty, n_mesh))
        return {"FINISHED"}


class SA_OT_export_ifp(bpy.types.Operator, ExportHelper):
    bl_idname = "sa_anim.export_ifp"
    bl_label = "Export IFP"
    filename_ext = ".ifp"
    filter_glob: StringProperty(default="*.ifp", options={"HIDDEN"})

    def execute(self, context):
        sc = context.scene
        log_path = sc.sa_log_path or default_log_path()
        root = sc.sa_root
        if root is None:
            self.report({"ERROR"}, "Pick a root object first")
            return {"CANCELLED"}
        items = list(sc.sa_bones)
        if not items:
            self.report({"ERROR"}, "Hierarchy is empty: press Get Hierarchy first")
            return {"CANCELLED"}
        if not validate_names(self, root, items, log_path):
            return {"CANCELLED"}
        bones, fps = build_export_bones(context, items, log_path)
        if not bones:
            self.report({"ERROR"}, "All bones excluded")
            return {"CANCELLED"}
        ifp_name = os.path.splitext(os.path.basename(self.filepath))[0]
        _, trunc = ifp.encode_name(ifp_name)
        if trunc:
            log("ifp name truncated to 24 chars: %s" % ifp_name, "WARN", log_path)
        try:
            ifp.write_ifp(self.filepath, ifp_name, root.name, bones)
        except Exception as e:
            log("EXPORT FAILED %s: %s" % (self.filepath, e), "ERROR", log_path)
            self.report({"ERROR"}, "Export failed: %s" % e)
            return {"CANCELLED"}
        size = os.path.getsize(self.filepath)
        log("EXPORT OK %s ifp=%s anim=%s bones=%d fps=%.3g size=%d "
            "(rot*4096 pos*1024 t=(frame-frame_start)*60/fps, pad 2048)"
            % (self.filepath, ifp_name, root.name, len(bones), fps, size),
            "INFO", log_path)
        self.report({"INFO"}, "Exported %d bones -> %s" % (len(bones), self.filepath))
        return {"FINISHED"}


class SA_OT_append_ifp(bpy.types.Operator, ExportHelper):
    bl_idname = "sa_anim.append_ifp"
    bl_label = "Append IFP"
    filename_ext = ".ifp"
    filter_glob: StringProperty(default="*.ifp", options={"HIDDEN"})

    def execute(self, context):
        sc = context.scene
        log_path = sc.sa_log_path or default_log_path()
        root = sc.sa_root
        if root is None:
            self.report({"ERROR"}, "Pick a root object first")
            return {"CANCELLED"}
        items = list(sc.sa_bones)
        if not items:
            self.report({"ERROR"}, "Hierarchy is empty: press Get Hierarchy first")
            return {"CANCELLED"}
        if not os.path.exists(self.filepath):
            self.report({"ERROR"}, "File not found, use Export for new files")
            return {"CANCELLED"}
        if not validate_names(self, root, items, log_path):
            return {"CANCELLED"}
        bones, fps = build_export_bones(context, items, log_path)
        try:
            n = ifp.append_ifp(self.filepath, root.name, bones)
        except Exception as e:
            log("APPEND FAILED %s: %s" % (self.filepath, e), "ERROR", log_path)
            self.report({"ERROR"}, "Append failed: %s" % e)
            return {"CANCELLED"}
        size = os.path.getsize(self.filepath)
        log("APPEND OK %s anim=%s bones=%d total_anims=%d size=%d"
            % (self.filepath, root.name, len(bones), n, size), "INFO", log_path)
        self.report({"INFO"}, "Appended %s (%d anims)" % (self.filepath, n))
        return {"FINISHED"}


class SA_OT_show_log(bpy.types.Operator):
    bl_idname = "sa_anim.show_log"
    bl_label = "Show Log"

    def execute(self, context):
        for line in recent(5):
            self.report({"INFO"}, line[-120:])
        area = next((a for a in context.screen.areas if a.type == "TEXT_EDITOR"), None)
        txt = bpy.data.texts.get(TEXT_NAME)
        if txt and area:
            area.spaces.active.text = txt
        return {"FINISHED"}


# ---------------------------------------------------------------- panel

class SA_PT_panel(bpy.types.Panel):
    bl_label = "SA Anim (IFP)"
    bl_idname = "SA_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "SA Anim"

    def draw(self, context):
        sc = context.scene
        L = self.layout
        L.prop(sc, "sa_root", text="Parent Object")
        L.operator("sa_anim.get_hierarchy", icon="OUTLINER")
        L.template_list("SA_UL_Bones", "", sc, "sa_bones", sc, "sa_bones_index")
        it = sc.sa_bones[sc.sa_bones_index] if 0 <= sc.sa_bones_index < len(sc.sa_bones) else None
        if it:
            row = L.row(align=True)
            row.prop(it, "exclude", text="Exclude")
            row.prop(it, "skip_pos", text="Skip Pos")
        row = L.row(align=True)
        row.operator("sa_anim.export_ifp", text="EXPORT", icon="EXPORT")
        row.operator("sa_anim.append_ifp", text="APPEND", icon="APPEND_BLEND")
        L.prop(sc, "sa_log_path", text="Log")
        L.operator("sa_anim.show_log", text="Show Log", icon="TEXT")


classes = (SA_BoneItem, SA_UL_Bones, SA_OT_get_hierarchy, SA_OT_export_ifp,
           SA_OT_append_ifp, SA_OT_show_log, SA_PT_panel)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.sa_root = PointerProperty(type=bpy.types.Object, name="Parent Object")
    bpy.types.Scene.sa_bones = CollectionProperty(type=SA_BoneItem)
    bpy.types.Scene.sa_bones_index = IntProperty(default=0)
    bpy.types.Scene.sa_log_path = StringProperty(
        name="Log path", subtype="FILE_PATH", default="")


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.sa_root
    del bpy.types.Scene.sa_bones
    del bpy.types.Scene.sa_bones_index
    del bpy.types.Scene.sa_log_path


if __name__ == "__main__":
    register()
