# SA Empty Anim Export (IFP)

Blender add-on that exports object-hierarchy animation to GTA San Andreas
`.ifp` (ANP3), mirroring the 3ds Max `anim_export.ms` flow (Empty instead of
Dummy). Every descendant under the root is exported as a bone track.
Requires Blender 4.2+.

Panel: View3D → `N` → `SA Anim`

## 1. Install

1. Zip the whole `sa-anim-export` folder (the zip must contain
   `__init__.py` at its root).
2. Blender → Edit → Preferences → Add-ons → Install from Disk → select
   the zip.
3. Enable `SA Empty Anim Export (IFP)`.

## 2. Build the rig

1. Create an Empty as the root, then parent parts in a chain
   (e.g. `halo_root` → `halo_pivot` → `halo_ring`). Meshes and Empties are
   both accepted — **all** descendants are exported, like Max `getSubs`.
2. Keep names short: **≤ 12 ASCII chars is safe** (`halo`, `gate`, `mill`).
   The IFP bone field holds 24 bytes; the game itself is only reliable up
   to ~12 chars.

## 3. Export

1. Set **Parent Object** to the root (or select the root in the viewport).
2. Press **Get Hierarchy** — the bone list fills with every descendant.
3. Keyframe the animation:
   - Rotation keys (Euler / Quaternion / Axis-Angle) always count.
   - Location keys count only where **Skip Pos (P)** is OFF. P is ON by
     default (rotation-only, bone type 3); turn it off for
     rotation+position (type 4).
   - Use **Exclude** to drop an object from the export without re-picking
     the hierarchy.
4. Press **EXPORT** for a new `.ifp` file, or **APPEND** to add the
   animation into an existing `.ifp`.
5. Over-long names show their length in the list,
   e.g. `Cupcake_Outline_0 (17)` — shorten the object name and press Get
   Hierarchy again.

## 4. Name rules

| Length (ASCII) | Result                                                      |
|----------------|-------------------------------------------------------------|
| ≤ 12 chars     | Safe                                                        |
| 13–24 chars    | Warning — exports, but the game may crash loading the IFP   |
| > 24 chars     | **Export refused** — shorten and retry                      |

Non-ASCII characters are replaced with `_` when measuring/writing. The IFP
internal name comes from the file name and is truncated to 24 chars if
needed.

## 5. Timing

- Effective fps = `scene.render.fps / fps_base`;
  key time = `(frame − frame_start) × 60 / fps`.
- If an object has no keys, one bind-pose key is written at the current
  frame.
- If animation timing looks wrong in-game, check `frame_start` and scene
  fps first.

## 6. Log

- Press **Show Log**, or open the `SA_Anim_Log` text block in the Text
  Editor.
- A copy is also saved to `sa_anim_export.log` next to the blend file (or
  temp dir if unsaved). The **Log** field in the panel overrides the path.

## 7. Troubleshooting

| Symptom                                         | Fix                                                              |
|-------------------------------------------------|------------------------------------------------------------------|
| `exceed 24-char IFP field, export refused`      | Shorten names below 24 chars (≤ 12 recommended), Get Hierarchy, retry |
| `exceed 12-char safe limit` warning             | Exports fine, but shorten for safety                             |
| `Hierarchy is empty`                            | Root has no children (need ≥ 1); press Get Hierarchy first       |
| `Pick a root object first`                      | Set Parent Object / select root                                  |
| `File not found, use Export for new files`      | APPEND needs an existing file; use EXPORT                        |
| `All bones excluded`                            | Uncheck Exclude on at least one bone                             |
