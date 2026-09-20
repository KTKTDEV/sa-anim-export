"""Name-length validation for SA IFP export (no Blender needed).

Rule (INU docs: Animated Map Objects): model/frame names must fit the
24-byte IFP field, and stay <= 12 chars to be safe in-game (>~16 may crash).
  len > 24 -> 'error'   (cannot fit the field; export must refuse)
  len > 12 -> 'warn'    (fits the field but unsafe for the game)
  else      -> 'ok'

Run:  python tests/test_name_limits.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ifp import check_names


def test_short_names_ok():
    assert check_names(["mill", "mill_blades"]) == []


def test_twelve_chars_ok():
    assert check_names(["123456789012"]) == []


def test_thirteen_chars_warns():
    res = check_names(["1234567890123"])
    assert len(res) == 1 and res[0][2] == "warn", res


def test_sixteen_chars_warns():
    res = check_names(["airprtbits12_lvS"])
    assert len(res) == 1 and res[0][2] == "warn", res


def test_over_24_chars_errors():
    res = check_names(["Cupcake_Outline_0_extra_long"])
    assert len(res) == 1 and res[0][2] == "error", res


def test_mixed_batch():
    res = check_names(["mill", "mill_pivot1_extra_long_name_xx", "gate"])
    assert [r[0] for r in res] == ["mill_pivot1_extra_long_name_xx"], res
    assert res[0][2] == "error", res


def test_non_ascii_counts_as_underscore():
    # encode_name maps non-ASCII to '_', so length is measured post-sanitize
    res = check_names(["\u0e2b\u0e25\u0e2d\u0e14" * 7])  # 28 chars -> 28 underscores
    assert len(res) == 1 and res[0][2] == "error", res


if __name__ == "__main__":
    fns = sorted(k for k in globals() if k.startswith("test_"))
    for fn in fns:
        globals()[fn]()
        print("PASS", fn)
    print("ALL %d TESTS PASSED" % len(fns))
