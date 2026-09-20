# SA Empty Anim Export (Blender IFP)

Mirror ของ `C:\Program Files\Autodesk\3ds Max 2025\scripts\sa_tools\anim_export.ms`
ย้ายฝั่ง Max (Dummy Object) มาอยู่ฝั่ง Blender (Empty)

- [ภาษาไทย](#ภาษาไทย)
- [English](#english)

---

## ภาษาไทย

### แนวคิด

- ฝั่ง Max ใช้ Dummy ผูก object แล้ว export `.ifp` ฝั่ง Blender ใช้ **Empty/Mesh** แทน (เหมือน `getSubs` ใน `.ms` ทุกประการ)
- Root = object ตัวเดียวชนิดใดก็ได้ (Empty หรือ Mesh ก็ได้) ชื่อของมันกลายเป็น**ชื่อ anim**
- ที่ถูกเขียนลง IFP คือ**ลูกหลานทุกตัว**ใต้ root (Empty, Mesh, ...) — mesh ที่เกาะอยู่ถูก export ด้วย ไม่ใช่แค่ดู
- รายกระดูกตั้งได้ 2 อย่างเหมือน `.ms`: `Exclude` (ไม่ export ตัวนี้) และ `Skip Pos` (default เปิด = เขียนแต่ rotation, ปิด = เขียน rotation+position)

### ติดตั้ง

1. Zip โฟลเดอร์ `sa_empty_anim_export` ทั้งโฟลเดอร์ (ข้างในต้องมี `__init__.py`)
2. Blender > Edit > Preferences > Add-ons > Install from Disk > เลือก zip
3. เปิดสวิตช์ `SA Empty Anim Export (IFP)`
4. เปิดแถบ View3D > Sidebar (กด `N`) > แท็บ `SA Anim`

### วิธีใช้

1. **เตรียม rig:** สร้าง Parent (Empty แนะนำ แต่ใช้ Mesh ก็ได้) แล้วต่อลูกหลานเป็นสาย (เช่น `halo_root` > `halo_pivot1` > `halo_ring`) ทำได้ทั้ง Parent (`Ctrl+P`) หรือ Constraint แบบ Child Of
2. **เลือก root:** ใน panel ช่อง Parent Object จิ้มตัวพ่อ หรือคลิกเลือก object ใน viewport แล้วกด `Get Hierarchy`
3. **ตรวจรายชื่อ:** ลูกหลานทุกตัว (Empty/Mesh/...) จะขึ้นในรายการทั้งหมด ไอคอนบอกชนิด object ละแถว
4. **ตั้งรายกระดูก:** คลิกทีละแถวแล้วติ๊ก `Exclude` / `Skip Pos` ด้านล่างรายการ (`P` ในแถว = Skip Pos)
5. **Keyframe:**  key rotation (Euler/Quaternion ก็ได้ ตัว addon แปลงเป็น quat ให้เอง) และ key location เฉพาะกระดูกที่ปิด Skip Pos ไว้ ถ้ากระดูกไหนไม่มี key เลย จะ export เป็น bind-pose 1 key พร้อม log เตือน
6. **Export:** กด `EXPORT` เลือก path `.ifp` (ไฟล์ใหม่) หรือ `APPEND` เพื่อต่อ anim ใหม่ใส่ไฟล์เดิม (เหมือนปุ่ม GO/APP ใน `.ms`)
7. **ตรวจ log:** กด `Show Log` หรือเปิด Text Editor ดู block `SA_Anim_Log` หรือเปิดไฟล์ log ตาม path ใน panel

### ช่องและปุ่มใน panel

| ส่วน | ใช้ทำอะไร |
|---|---|
| Parent Object | object ตัวพ่อ (ชนิดใดก็ได้) = ชื่อ anim |
| Get Hierarchy | เก็บลูกหลานทุกตัวเข้า List |
| List | แถวละ 1 object (ไอคอนบอกชนิด), ติ๊ก exclude, `P` = Skip Pos |
| EXPORT / APPEND | เขียนไฟล์ใหม่ / ต่อไฟล์เดิม |
| Log | path ไฟล์ log (default อยู่ข้าง `.blend` ชื่อ `sa_anim_export.log` ถ้ายังไม่เซฟไฟล์จะไปอยู่ใน temp) |
| Show Log | โชว์ 5 บรรทัดล่าสุด + เปิด Text `SA_Anim_Log` |

### Log tracking

ทุกครั้งที่กดปุ่มจะ log พร้อมกัน 3 ทาง (ล้มเหลวตรงไหนก็ไม่ crash):

1. Console (System Console ของ Blender)
2. Text block ชื่อ `SA_Anim_Log`
3. ไฟล์ log ตาม path ใน panel

สิ่งที่ log: root (+ชนิด), จำนวนลูกหลานแยกตามชนิด, รายตัว (type/keys/frames), ชื่อไฟล์, fps, ขนาดไฟล์, คำเตือน clamp/truncate, error พร้อมเหตุผล

### สเปก IFP ที่เขียน (ตรง `.ms`)

- Magic `ANP3`, ชื่อ ifp = ชื่อไฟล์, 1 anim ต่อ EXPORT (APPEND บวกเพิ่ม), ชื่อกระดูก/anim เกิน 24 ตัวอักษร ASCII export ไม่ผ่าน (ERROR + log ให้ย่อชื่อก่อน), เกิน 12 ตัวอักษรเตือน (WARNING — เกมอาจแครชตอนโหลด IFP), ในลิสต์ชื่อเกินจะขึ้นจำนวนตัวอักษรเตือน
- Bone: type 4 = rot+pos, type 3 = rot อย่างเดียว, ต่อด้วย `-1`
- Key: quat xyzw × 4096 (int16), เวลา `t = (frame - frame_start) × 60 / fps` (uint16, เทียบเท่า ticks/80 ของ Max), pos xyz × 1024 (int16, เฉพาะ type 4)
- Transform เป็น parent-space (local เทียบพ่อ) ไม่เอา scale ลงไฟล์
- แพดไฟล์ขาออกให้ลงตัว 2048 bytes แล้วแก้ size field ให้ (เหมือน `.ms`)

### ความต่างจาก `.ms` ที่ตั้งใจ

- `data_size` ของ anim เขียนเป็นขนาด bone-block รวม header (ตรงไฟล์จริง เช่น `halo.ifp`: 1 bone × 5 keys = 86) ส่วน `.ms` เขียนแค่ payload (`DataCount*2` = 50)
- เวลาเป็น zero-based จาก `frame_start` ของ scene (Max นับ absolute ticks) ที่ `fps=30` สูตรเดียวกันคือ `t=(frame-frame_start)*2`
- ไฟล์ที่ไม่ได้ pad (เช่น `halo.ifp` 158 bytes) อ่าน/append ได้ แล้วขาออก pad 2048 ตาม `.ms`

### แก้ปัญหาเบื้องต้น

- "No root" — เลือก Parent Object ก่อน หรือ select object แล้วกด Get Hierarchy
- "Hierarchy is empty" — root ไม่มีลูกหลานเลย (root อย่างเดียว export ไม่ได้ ต้องมีลูกอย่างน้อย 1 ตัว)
- "exceed 24-char IFP field, export refused" — ชื่อ mesh/empty ใน empty ยาวเกิน 24 ตัวอักษร ย่อชื่อให้สั้นกว่า 24 (แนะนำ ≤12 ตาม docs INU) แล้ว export ใหม่
- เตือน "exceed 12-char safe limit" — ชื่อยาวเกินขอบเขตปลอดภัย เกมอาจเปิด IFP ไม่ติด/แครช ย่อชื่อแล้ว export ใหม่ชัวร์กว่า
- ค่า pos เพี้ยน/overflow — ฉากใหญ่เกิน int16 ที่สเกล ×1024 จะถูก clamp + log เตือน ให้ย่อ unit หรือแยก anim
- เวลาไม่ตรงเกม — เช็ค `frame_start` กับ fps ของ scene ก่อน export (log บอก fps ที่ใช้ทุกครั้ง)

### โครงไฟล์

- `__init__.py` — UI + operators + sampling (รองรับ action ทั้ง legacy และ layered ของ Blender 5)
- `ifp.py` — writer/reader ล้วน (ไม่มี bpy) + `tests/test_ifp_roundtrip.py`
- `log_tracker.py` — log 3 sink

---

## English

### Concept

- The Max side binds objects to Dummies and exports `.ifp`. The Blender side uses **Empties/Meshes** instead (exactly like `getSubs` in the `.ms`).
- Root = one parent object of any type (Empty or Mesh). Its name becomes the **anim name**.
- **Every descendant** under the root (Empty, Mesh, ...) is written to the IFP — attached meshes are exported too, not view-only.
- Per-bone flags mirror the `.ms`: `Exclude` (skip this item) and `Skip Pos` (on by default = rotation only, off = rotation+position).

### Install

1. Zip the whole `sa_empty_anim_export` folder (it must contain `__init__.py`).
2. Blender > Edit > Preferences > Add-ons > Install from Disk > pick the zip.
3. Enable `SA Empty Anim Export (IFP)`.
4. Open View3D > Sidebar (`N`) > `SA Anim` tab.

### Usage

1. **Build the rig:** create a parent (Empty recommended, Mesh works too) with a chained hierarchy (e.g. `halo_root` > `halo_pivot1` > `halo_ring`). Both object parenting (`Ctrl+P`) and Child Of constraints work.
2. **Pick the root:** set the Parent Object field, or select the object in the viewport and press `Get Hierarchy`.
3. **Check the list:** every descendant (Empty/Mesh/...) appears, with a per-row icon showing the object type.
4. **Per-bone flags:** click a row, then toggle `Exclude` / `Skip Pos` below the list (`P` in a row = Skip Pos).
5. **Keyframe:** key rotation (Euler or Quaternion both fine, converted to quat on export) and key location only for bones with Skip Pos off. A bone with no keys exports one bind-pose key with a logged warning.
6. **Export:** `EXPORT` writes a new `.ifp`, `APPEND` adds a new anim into an existing file (same as GO/APP in the `.ms`).
7. **Check the log:** press `Show Log`, open the `SA_Anim_Log` text block, or open the log file path shown in the panel.

### Panel reference

| Control | What it does |
|---|---|
| Parent Object | Parent object (any type) = anim name |
| Get Hierarchy | Collect every descendant into the list |
| List | One row per object (icon = type); checkbox = exclude, `P` = Skip Pos |
| EXPORT / APPEND | New file / append into existing file |
| Log | Log file path (default `sa_anim_export.log` next to the `.blend`, temp dir if unsaved) |
| Show Log | Show last 5 lines + open the `SA_Anim_Log` text |

### Log tracking

Every operation logs to 3 sinks at once (a sink failure never crashes):

1. Console (Blender's System Console)
2. Text block `SA_Anim_Log`
3. Log file at the panel path

Logged items: root (+type), descendant counts by type, per-item type/keys/frames, filename, fps, file size, clamp/truncate warnings, errors with reasons.

### IFP spec written (mirrors the `.ms`)

- Magic `ANP3`, ifp name = filename, 1 anim per EXPORT (APPEND increments). Bone/anim names over 24 ASCII chars are refused (ERROR + log, shorten and retry); over 12 chars warn (WARNING — the game may crash loading the IFP). Over-long names show their length in the list.
- Bone: type 4 = rot+pos, type 3 = rot only, followed by `-1`.
- Key: quat xyzw × 4096 (int16), time `t = (frame - frame_start) × 60 / fps` (uint16, equiv. of Max ticks/80), pos xyz × 1024 (int16, type 4 only).
- Transforms are parent-space (local vs parent); scale is ignored.
- Output padded to a 2048-byte multiple with the size field patched (like the `.ms`).

### Deliberate deviations from the `.ms`

- Anim `data_size` is the full bone-block size incl. headers (matches real files, e.g. `halo.ifp`: 1 bone × 5 keys = 86); the `.ms` writes payload only (`DataCount*2` = 50).
- Time is zero-based from the scene `frame_start` (Max counts absolute ticks); at `fps=30` both reduce to `t=(frame-frame_start)*2`.
- Unpadded files (e.g. 158-byte `halo.ifp`) can be read/appended; output is still padded to 2048 per the `.ms`.

### Troubleshooting

- "No root" — pick a Parent Object first, or select one and press Get Hierarchy.
- "Hierarchy is empty" — the root has no descendants at all (a lone root exports nothing; it needs at least one child).
- "exceed 24-char IFP field, export refused" — a mesh/empty name under the root is over 24 chars; shorten it (≤12 per INU docs) and export again.
- "exceed 12-char safe limit" warning — the name fits the field but the game may fail to open the IFP; shortening is safer.
- Bad/clamped pos values — scenes larger than int16 at ×1024 get clamped with a logged warning; rescale units or split the anim.
- Wrong timing in game — check scene `frame_start` and fps before export (the fps used is logged every time).

### Layout

- `__init__.py` — UI + operators + sampling (legacy + Blender 5 layered actions)
- `ifp.py` — pure writer/reader (no bpy) + `tests/test_ifp_roundtrip.py`
- `log_tracker.py` — 3-sink logger
