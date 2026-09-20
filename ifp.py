"""IFP (GTA SA, ANP3) reader/writer mirroring anim_export.ms.

Byte layout (little-endian, mirroring the .ms):
  header:  magic[4]="ANP3"  uint32 size=size-8  char[24] ifp_name  uint32 n_anims
  anim:    char[24] anim_name  uint32 n_bones  uint32 data_size  uint32 unk(=1 per .ms)
  bone:    char[24] bone_name  int32 type(4=rot+pos,3=rot)  uint32 n_keys  int32 -1
  key rot-only:  int16 x,y,z,w (quat*4096)  uint16 t
  key rot+pos:   above + int16 px,py,pz (pos*1024)

Notes / deliberate deviations from the .ms (all logged by callers):
  * data_size is the total bone-block byte count (36 + keys) as seen in
    real files (e.g. halo.ifp: 1 bone x 5 keys -> 86). The .ms writes
    DataCount*2 (key payload only, 50 here), which omits bone headers.
  * files are padded to 2048 bytes like the .ms EXPORT/APPEND path.
    Real-world files (halo.ifp, 158 bytes) are sometimes unpadded;
    the reader/append path accepts both.
  * time unit mirrors (ticks/80): t = round((frame-frame_start)*60/fps_eff).
"""

import os
import struct

MAGIC = b"ANP3"
NAME_LEN = 24
PAD_ALIGN = 2048
ROT_SCALE = 4096.0
POS_SCALE = 1024.0

HEADER_FMT = "<4sI24sI"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
ANIM_FMT = "<24sIII"
ANIM_SIZE = struct.calcsize(ANIM_FMT)
BONE_FMT = "<24siIi"
BONE_SIZE = struct.calcsize(BONE_FMT)
KEY_ROT_FMT = "<hhhhH"
KEY_ROT_SIZE = struct.calcsize(KEY_ROT_FMT)
KEY_POS_FMT = "<hhh"
KEY_POS_SIZE = struct.calcsize(KEY_POS_FMT)


def encode_name(name):
    """Encode to fixed 24-byte zero-padded ASCII. Returns (bytes, truncated)."""
    safe = "".join(c if 32 <= ord(c) < 127 else "_" for c in str(name))
    raw = safe.encode("ascii", errors="replace")[:NAME_LEN]
    truncated = len(safe.encode("ascii", errors="replace")) > NAME_LEN
    return raw + b"\x00" * (NAME_LEN - len(raw)), truncated


#: Model/frame names longer than this fit the 24-byte IFP field but are
#: unsafe in-game (INU docs: keep <= 12 chars, >~16 may crash at 0x534134).
SAFE_NAME_LEN = 12


def sanitized_len(name):
    """Length of *name* as it will be written (non-ASCII -> '_')."""
    safe = "".join(c if 32 <= ord(c) < 127 else "_" for c in str(name))
    return len(safe.encode("ascii", errors="replace"))


def check_names(names):
    """Flag names that break the IFP/game limits.

    Returns a list of ``(name, ascii_len, level)`` for offenders only:
      level ``"error"`` -- longer than the 24-byte field, cannot be
        written faithfully; the export must be refused.
      level ``"warn"`` -- fits the field but exceeds the 12-char safe
        limit; the game may crash when the IFP is applied.
    """
    out = []
    for n in names:
        ln = sanitized_len(n)
        if ln > NAME_LEN:
            out.append((str(n), ln, "error"))
        elif ln > SAFE_NAME_LEN:
            out.append((str(n), ln, "warn"))
    return out


def clamp_i16(v):
    return max(-32768, min(32767, int(v)))


def clamp_u16(v):
    return max(0, min(65535, int(v)))


def bone_block_size(n_keys, have_pos):
    per = KEY_ROT_SIZE + (KEY_POS_SIZE if have_pos else 0)
    return BONE_SIZE + n_keys * per


def write_bone(f, bone_name, keys, have_pos):
    """keys: iterable of (qx,qy,qz,qw, loc_or_None, t). loc=(x,y,z) floats."""
    raw, _ = encode_name(bone_name)
    f.write(raw)
    f.write(struct.pack("<i", 4 if have_pos else 3))
    keys = list(keys)
    f.write(struct.pack("<I", len(keys)))
    f.write(struct.pack("<i", -1))
    for qx, qy, qz, qw, loc, t in keys:
        f.write(struct.pack(
            KEY_ROT_FMT,
            clamp_i16(round(qx * ROT_SCALE)),
            clamp_i16(round(qy * ROT_SCALE)),
            clamp_i16(round(qz * ROT_SCALE)),
            clamp_i16(round(qw * ROT_SCALE)),
            clamp_u16(round(t)),
        ))
        if have_pos:
            x, y, z = loc if loc is not None else (0.0, 0.0, 0.0)
            f.write(struct.pack(
                KEY_POS_FMT,
                clamp_i16(round(x * POS_SCALE)),
                clamp_i16(round(y * POS_SCALE)),
                clamp_i16(round(z * POS_SCALE)),
            ))


def write_section(f, anim_name, bones):
    """bones: list of (bone_name, keys, have_pos). Returns bone count."""
    raw, _ = encode_name(anim_name)
    live = [(n, list(k), hp) for n, k, hp in bones]
    data_size = sum(bone_block_size(len(k), hp) for _, k, hp in live)
    f.write(raw)
    f.write(struct.pack("<III", len(live), data_size, 1))
    for name, keys, have_pos in live:
        write_bone(f, name, keys, have_pos)
    return len(live)


def _pad_and_patch(f):
    size = f.tell()
    tail = PAD_ALIGN - (size % PAD_ALIGN)
    # mirror .ms: always pad (even when already aligned it writes a full block)
    f.write(b"\x00" * tail)
    f.seek(4)
    f.write(struct.pack("<I", size - 8))
    f.seek(0, os.SEEK_END)


def write_ifp(path, ifp_name, anim_name, bones):
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<I", 0))  # patched later
        raw, _ = encode_name(ifp_name)
        f.write(raw)
        f.write(struct.pack("<I", 1))
        write_section(f, anim_name, bones)
        _pad_and_patch(f)


def read_header(f):
    f.seek(0)
    magic, size, ifp_raw, n_anims = struct.unpack(HEADER_FMT, f.read(HEADER_SIZE))
    ifp_name = ifp_raw.split(b"\x00")[0].decode("ascii", errors="replace")
    return magic, size, ifp_name, n_anims


def append_ifp(path, anim_name, bones):
    with open(path, "r+b") as f:
        magic, data_size, _, n_anims = read_header(f)
        if magic != MAGIC:
            raise ValueError("not an ANP3 ifp file")
        f.seek(32)
        f.write(struct.pack("<I", n_anims + 1))
        f.seek(data_size + 8)  # start of padding / EOF for unpadded files
        write_section(f, anim_name, bones)
        _pad_and_patch(f)
        return n_anims + 1


def read_ifp(path):
    """Parse back for verification. Returns dict; raises on bad magic."""
    out = {"anims": []}
    with open(path, "rb") as f:
        magic, size, ifp_name, n_anims = read_header(f)
        if magic != MAGIC:
            raise ValueError("bad magic")
        out.update(magic=magic, size=size, ifp_name=ifp_name, n_anims=n_anims)
        for _ in range(n_anims):
            anim_raw, n_bones, data_size, unk = struct.unpack(ANIM_FMT, f.read(ANIM_SIZE))
            anim = {
                "name": anim_raw.split(b"\x00")[0].decode("ascii", errors="replace"),
                "n_bones": n_bones, "data_size": data_size, "unk": unk, "bones": [],
            }
            for _ in range(n_bones):
                bone_raw, btype, n_keys, u = struct.unpack(BONE_FMT, f.read(BONE_SIZE))
                bone = {
                    "name": bone_raw.split(b"\x00")[0].decode("ascii", errors="replace"),
                    "type": btype, "keys": [],
                }
                for _ in range(n_keys):
                    rx, ry, rz, rw, tt = struct.unpack(KEY_ROT_FMT, f.read(KEY_ROT_SIZE))
                    key = {"rot": (rx, ry, rz, rw), "t": tt}
                    if btype == 4:
                        px, py, pz = struct.unpack(KEY_POS_FMT, f.read(KEY_POS_SIZE))
                        key["pos"] = (px, py, pz)
                    bone["keys"].append(key)
                anim["bones"].append(bone)
            out["anims"].append(anim)
    return out
