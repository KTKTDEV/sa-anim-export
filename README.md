# SA Empty Anim Export (IFP)

Export ท่าเคลื่อนไหวจาก Blender เป็นไฟล์ `.ifp` ของเกม GTA San Andreas
พร้อมระบบเช็คชื่ออัตโนมัติ — ชื่อยาวเกินเกมเปิดไม่ติด จะโดนเตือนก่อนพัง

---

## มันคืออะไร

ปกติ export IFP แล้วชื่อ object ยาวเกินไป เกมจะเปิดไฟล์ไม่ติดหรือแครช
addon นี้เช็คชื่อให้ก่อน export:

| ชื่อยาว | ผล |
|---|---|
| ไม่เกิน 12 ตัวอักษร | ผ่าน ชื่อปลอดภัย |
| 13–24 ตัวอักษร | เตือน (export ได้ แต่เกมอาจแครช) |
| เกิน 24 ตัวอักษร | **ไม่ให้ export** ต้องย่อชื่อก่อน |

## ติดตั้ง

1. Zip โฟลเดอร์ `sa_empty_anim_export` ทั้งโฟลเดอร์
2. Blender → Edit → Preferences → Add-ons → Install from Disk → เลือก zip
3. เปิดสวิตช์ `SA Empty Anim Export (IFP)`
4. แถบเครื่องมืออยู่ View3D → กด `N` → แท็บ `SA Anim`

## วิธีใช้

1. สร้าง Empty เป็นตัวพ่อ แล้ว parent ชิ้นส่วนเป็นสาย (เช่น `halo_root` > `halo_pivot1` > `halo_ring`)
2. ตั้งชื่อสั้นๆ (ไม่เกิน 12 ตัวอักษร เช่น `halo`, `gate`, `mill`)
3. ช่อง Parent Object เลือกตัวพ่อ → กด **Get Hierarchy**
4. key ท่า (rotation ได้ทุกแบบ, location key เฉพาะชิ้นที่ปิด Skip Pos)
5. กด **EXPORT** (ไฟล์ใหม่) หรือ **APPEND** (ต่อใส่ไฟล์เดิม)

> ชื่อในลิสต์ถ้ายาวเกินจะมีตัวเลขเตือน เช่น `Cupcake_Outline_0 (17)` — ย่อชื่อแล้วกด Get Hierarchy ใหม่

## ดู log

กด **Show Log** หรือเปิด Text Editor ดู block `SA_Anim_Log`

## ปัญหาที่เจอบ่อย

| อาการ | แก้ |
|---|---|
| `export refused ... exceed 24-char` | ย่อชื่อ object ให้สั้นกว่า 24 (แนะนำ ≤12) แล้ว export ใหม่ |
| เตือน `exceed 12-char safe limit` | export ได้ แต่ย่อชื่อชัวร์กว่า |
| `Hierarchy is empty` | root ไม่มีลูกเลย ต้องมีลูกอย่างน้อย 1 ตัว |
| ท่าในเกมเวลาเพี้ยน | เช็ค `frame_start` กับ fps ของ scene |

## ไฟล์ในโฟลเดอร์

- `__init__.py` — หน้าตา + ปุ่มกด
- `ifp.py` — ตัวเขียน/อ่านไฟล์ IFP
- `log_tracker.py` — ระบบ log
- `tests/` — เทส (`python tests/test_name_limits.py`)

---

## English

Export object animation from Blender to GTA SA `.ifp`, mirroring the Max
`anim_export.ms` flow (Empty instead of Dummy). Every descendant under the
root object is exported as a bone track.

**Name rules:** over 24 ASCII chars → export refused; over 12 chars →
warning (the game may crash loading the IFP). Over-long names show their
length in the list.

**Install:** zip the folder → Preferences → Add-ons → Install from Disk →
enable it. Panel: View3D → `N` → `SA Anim`.

**Use:** parent parts under an Empty → pick it as Parent Object → Get
Hierarchy → keyframe → EXPORT / APPEND.
