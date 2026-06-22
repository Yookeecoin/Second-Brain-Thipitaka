#!/usr/bin/env python3
# คืนค่าพาเลตสีกราฟ — ทั้งปลั๊กอิน Buddhist Knowledge Galaxy และ core graph ของ Obsidian
# ใช้เมื่อ "สีหาย": รัน (หรือดับเบิลคลิก restore-galaxy-colors.command) แล้วเปิดกราฟใหม่
import json, os, shutil, sys

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBS = os.path.join(VAULT, ".obsidian")

# พาเลตหลัก (ตาม type ของโน้ต)
PALETTE = {
    "root":     "#39ff88",
    "sutta":    "#00e5ff",
    "doctrine": "#ff35f2",
    "person":   "#a3ff12",
    "place":    "#ff9f1c",
    "event":    "#ffe45e",
    "concept":  "#9b5cff",
}
# จับคู่ folder ใน wiki/ -> สี (สำหรับ core graph colorGroups)
FOLDER_COLOR = {
    "wiki/suttas":  PALETTE["sutta"],
    "wiki/dhamma":  PALETTE["doctrine"],
    "wiki/persons": PALETTE["person"],
    "wiki/places":  PALETTE["place"],
    "wiki/terms":   PALETTE["concept"],
    "wiki/sources": PALETTE["event"],
}

def backup(path):
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")

def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}

def save(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def hex2int(h):
    return int(h.lstrip("#"), 16)

# 1) ปลั๊กอิน Buddhist Knowledge Galaxy
bkg = os.path.join(OBS, "plugins", "buddhist-knowledge-galaxy", "data.json")
if os.path.exists(bkg):
    backup(bkg)
    d = load(bkg)
    d["colors"] = dict(PALETTE)
    d.setdefault("enabledTypes", {})
    for t in PALETTE:
        d["enabledTypes"][t] = True
    save(bkg, d)
    print("✓ คืนสี galaxy plugin แล้ว ->", os.path.relpath(bkg, VAULT))
else:
    print("- ไม่พบปลั๊กอิน galaxy (ข้าม)")

# 2) core graph.json (colorGroups ตาม folder)
gj = os.path.join(OBS, "graph.json")
backup(gj)
g = load(gj)
g["colorGroups"] = [
    {"query": f'path:"{folder}"', "color": {"a": 1, "rgb": hex2int(color)}}
    for folder, color in FOLDER_COLOR.items()
]
save(gj, g)
print("✓ คืนสี core graph แล้ว ->", os.path.relpath(gj, VAULT), f"({len(g['colorGroups'])} กลุ่ม)")

print("\nเสร็จแล้ว 🎨  ขั้นต่อไปใน Obsidian:")
print("  • Galaxy view: กด Cmd+P -> \"Refresh Buddhist Knowledge Galaxy\"")
print("  • Core graph : ปิด-เปิดแท็บ Graph view (หรือรีสตาร์ท Obsidian ถ้าสียังไม่ขึ้น)")
