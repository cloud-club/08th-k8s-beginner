#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ATTACH_DIRS = ["99. attachments", "99_attachments"]

# ---- 첨부 폴더 탐색 및 표준화 ----
for d in ATTACH_DIRS:
    attach_dir = ROOT / d
    if attach_dir.exists():
        break
else:
    print("첨부 폴더(99. attachments 또는 99_attachments)가 없음", file=sys.stderr)
    sys.exit(1)

if attach_dir.name != "99_attachments":
    new_dir = attach_dir.parent / "99_attachments"
    print(f"[DIR] {attach_dir} -> {new_dir}")
    attach_dir.rename(new_dir)
    attach_dir = new_dir

# ---- 파일명 공백 -> 하이픈 ----
for f in sorted(attach_dir.rglob("*"), key=lambda p: len(str(p)), reverse=True):
    if " " in f.name and f.exists():
        new_name = f.name.replace(" ", "-")
        print(f"[RENAME] {f.name} -> {new_name}")
        f.rename(f.with_name(new_name))

# ---- Obsidian 이미지 링크 변환 ----
pat = re.compile(r"!\[\[([^|\]]+\.(?:png|jpg|jpeg|gif|svg))(?:\|(\d+))?\]\]", re.IGNORECASE)

def convert_obsidian_links(text: str, md_path: Path) -> str:
    rel_attach = os.path.relpath(attach_dir, md_path.parent)

    def repl(m: re.Match) -> str:
        fname, width = m.group(1), m.group(2)
        fname = fname.replace(" ", "-")
        if width:  # ![[file.png|800]] -> <img ... width="800" />
            return f'<img src="{rel_attach}/{fname}" width="{width}" />'
        alt = os.path.splitext(Path(fname).name)[0]
        return f'![{alt}]({rel_attach}/{fname})'

    return pat.sub(repl, text)

# ---- 이미지 앞줄 강제 줄바꿈(공백 2칸) 삽입 ----
def enforce_linebreak_before_images(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out = []
    in_code = False
    fence_pat = re.compile(r"^\s*```")
    img_line_pat = re.compile(r"^\s*(?:!\[|<img\s)", re.IGNORECASE)

    for i, line in enumerate(lines):
        # 코드블록 토글
        if fence_pat.match(line):
            in_code = not in_code
            out.append(line)
            continue

        if not in_code and img_line_pat.match(line):
            # 이전 의미 있는 줄 찾기
            j = len(out) - 1
            while j >= 0 and out[j].strip() == "":
                j -= 1
            if j >= 0:
                prev = out[j]
                # 이미 공백 2칸 줄바꿈 또는 <br>로 끝나면 패스
                if not (prev.rstrip("\n").endswith("  ") or prev.rstrip().endswith("<br>")):
                    # 줄 끝 개행 앞에 공백 2칸 삽입
                    prev_no_nl = prev.rstrip("\n")
                    nl = prev[len(prev_no_nl):]  # 보존
                    out[j] = prev_no_nl + "  " + nl
        out.append(line)
    return "".join(out)

# ---- 모든 .md 처리 ----
changed = False
for md in ROOT.rglob("*.md"):
    old = md.read_text(encoding="utf-8")
    new = convert_obsidian_links(old, md)
    new = enforce_linebreak_before_images(new)
    if old != new:
        md.write_text(new, encoding="utf-8")
        changed = True
        print(f"[UPDATE] {md}")

if not changed:
    print("변경 사항 없음.")
else:
    print("완료. git status로 확인하세요.")
