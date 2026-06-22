#!/bin/bash
# ดับเบิลคลิกไฟล์นี้ใน Finder เพื่อคืนค่าสีกราฟ Obsidian (galaxy + core graph)
cd "$(dirname "$0")"
python3 tools/restore_galaxy_colors.py
echo
echo "กด Enter เพื่อปิดหน้าต่างนี้..."
read
