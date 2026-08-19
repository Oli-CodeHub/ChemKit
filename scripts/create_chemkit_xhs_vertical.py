#!/usr/bin/env python3
"""Create 9:16 Xiaohongshu graphics with a ChemDraw/ChemKit comparison."""

from __future__ import annotations

import base64
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "xhs-chemkit-20260819-vertical"
W, H = 1080, 1920

NAVY = "#102A43"
INK = "#1F2933"
MUTED = "#627D98"
CREAM = "#F7F3EA"
WHITE = "#FFFFFF"
CORAL = "#E76F51"
TEAL = "#2A9D8F"
GOLD = "#F4A261"
PALE_BLUE = "#EAF2F8"
PALE_CORAL = "#FDE9E2"
PALE_TEAL = "#E5F5F2"
FONT = "'PingFang SC','Helvetica Neue',Arial,sans-serif"

FAT_IMAGE = ROOT / "examples" / "20260819-fat-amide-coupling.png"
TAXOL_IMAGE = ROOT / "examples" / "20260819-taxol-10dab-stress-test.png"
DIARYLAMINE_IMAGE = ROOT / "examples" / "20260819-fat-diarylamine.png"
CHEMDRAW_IMAGE = Path("/var/folders/__/t65vg_bx3wg_3x16sx9x4b5w0000gn/T/codex-clipboard-5015e6a5-ccb9-4652-abf5-1911f6c46e9f.png")


def esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def t(x: float, y: float, text: str, size: float, fill=INK, weight=500, anchor="start", cls="body") -> str:
    return f'<text class="{cls}" x="{x}" y="{y}" font-size="{size}px" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{esc(text)}</text>'


def multiline(x: float, y: float, lines: list[str], size: float, line_height: float, fill=INK, weight=500) -> str:
    return "\n".join(t(x, y + i * line_height, line, size, fill, weight) for i, line in enumerate(lines))


def rect(x: float, y: float, w: float, h: float, fill=WHITE, radius=28, stroke="none", sw=0) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def image(path: Path, x: float, y: float, w: float, h: float, radius=24) -> str:
    clip_id = f"clip_{abs(hash((str(path), x, y, w, h))) % 10_000_000}"
    return (
        f'<clipPath id="{clip_id}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}"/></clipPath>'
        f'<image href="{data_uri(path)}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" clip-path="url(#{clip_id})"/>'
    )


def header(slide: int, eyebrow: str, title: str, subtitle: str) -> list[str]:
    return [
        rect(0, 0, W, H, CREAM, 0),
        t(72, 78, f"CHEMKIT  /  0{slide}", 20, CORAL, 800, cls="eyebrow"),
        t(72, 160, title, 60, NAVY, 800, cls="title"),
        t(72, 215, eyebrow, 22, TEAL, 700, cls="eyebrow"),
        t(72, 270, subtitle, 26, MUTED, 500, cls="subtitle"),
    ]


def footer(slide: int) -> list[str]:
    return [
        t(72, 1852, "RDKit  ·  SVG  ·  ChemDraw-like layout", 18, MUTED, 600, cls="footer"),
        t(1008, 1852, f"{slide}/5", 18, MUTED, 700, anchor="end", cls="footer"),
    ]


def svg(parts: list[str]) -> str:
    css = f"""<style>
text {{ font-family: {FONT}; letter-spacing: 0; }}
.title {{ letter-spacing: -1.5px; }}
.eyebrow {{ letter-spacing: 2px; }}
.subtitle {{ letter-spacing: 0.2px; }}
.body {{ letter-spacing: 0.1px; }}
.footer {{ letter-spacing: 1px; }}
</style>"""
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{css}' + "".join(parts) + "</svg>"


def slide_01() -> list[str]:
    parts = header(1, "RDKit路线图工作流升级", "ChemKit 新版来了", "让化学结构，更接近你真正想要的论文风格")
    parts += [
        rect(60, 350, 960, 870, NAVY, 34),
        t(115, 455, "不是把结构“画出来”就结束了", 29, "#D9E2EC", 600),
        t(115, 525, "而是把比例、朝向、间距和层级", 39, WHITE, 800),
        t(115, 585, "一起画对。", 39, GOLD, 800),
        rect(100, 690, 880, 285, WHITE, 22),
        image(FAT_IMAGE, 125, 725, 830, 220, 18),
        rect(60, 1300, 290, 130, PALE_CORAL, 22),
        rect(395, 1300, 290, 130, PALE_TEAL, 22),
        rect(730, 1300, 290, 130, PALE_BLUE, 22),
        t(205, 1376, "统一比例", 25, CORAL, 800, anchor="middle"),
        t(540, 1376, "保留朝向", 25, TEAL, 800, anchor="middle"),
        t(875, 1376, "自动排版", 25, NAVY, 800, anchor="middle"),
        t(540, 1535, "ChemDraw 的观感，ChemKit 的可复用。", 28, NAVY, 700, anchor="middle"),
    ]
    parts += footer(1)
    return parts


def slide_02() -> list[str]:
    parts = header(2, "同一条路线的视觉对比", "ChemDraw vs ChemKit", "结构方向相近，比例、间距和信息层级更统一")
    parts += [
        rect(60, 335, 960, 690, WHITE, 30),
        t(100, 405, "ChemDraw 参考效果", 27, CORAL, 800),
        image(CHEMDRAW_IMAGE, 95, 435, 890, 555, 18),
        rect(60, 1080, 960, 630, WHITE, 30),
        t(100, 1150, "ChemKit 新版效果", 27, TEAL, 800),
        image(TAXOL_IMAGE, 95, 1180, 890, 480, 18),
        rect(60, 1750, 960, 62, NAVY, 18),
        t(540, 1792, "重点不是复制像素，而是复制视觉规则", 23, WHITE, 700, anchor="middle"),
    ]
    parts += footer(2)
    return parts


def slide_03() -> list[str]:
    parts = header(3, "新版规则的核心", "先统一有效键长", "再决定字号、线宽和路线间距")
    parts += [
        rect(60, 340, 960, 480, WHITE, 30),
        image(DIARYLAMINE_IMAGE, 95, 400, 890, 355, 18),
        rect(60, 900, 960, 175, PALE_BLUE, 24),
        t(105, 970, "有效键长", 27, NAVY, 800),
        t(105, 1025, "约 38.2 px，先把环和 bond 的比例稳定下来", 24, NAVY, 600),
        rect(60, 1130, 960, 175, PALE_TEAL, 24),
        t(105, 1200, "文字层级", 27, TEAL, 800),
        t(105, 1255, "原子 / 条件 / 编号统一到同一套尺度", 24, TEAL, 600),
        rect(60, 1360, 960, 175, PALE_CORAL, 24),
        t(105, 1430, "布局锚点", 27, CORAL, 800),
        t(105, 1485, "按可见边界中点放置加号、箭头和编号", 24, CORAL, 600),
        t(540, 1635, "所以“像 ChemDraw”不只是字体问题。", 28, NAVY, 800, anchor="middle"),
    ]
    parts += footer(3)
    return parts


def slide_04() -> list[str]:
    parts = header(4, "复杂路线高强度测试", "多环、保护基、侧链", "也要保持清楚的路线层级")
    parts += [
        rect(60, 335, 960, 900, WHITE, 30),
        image(TAXOL_IMAGE, 88, 370, 904, 760, 20),
        rect(88, 1150, 904, 72, NAVY, 18),
        t(540, 1197, "10-DAB  →  保护基调整  →  侧链安装  →  Taxol", 24, WHITE, 700, anchor="middle"),
        t(72, 1325, "复杂结构不再用“缩小分子”解决拥挤", 29, NAVY, 800),
        multiline(72, 1390, ["让画布增长，让结构保持比例。", "编号、条件和结构之间留出可读空间。"], 26, 48, MUTED, 600),
        rect(60, 1570, 960, 135, PALE_TEAL, 24),
        t(540, 1652, "适合论文路线、组会汇报和文献复刻", 27, TEAL, 800, anchor="middle"),
    ]
    parts += footer(4)
    return parts


def slide_05() -> list[str]:
    parts = header(5, "从结构数据到统一画风", "ChemKit 适合谁？", "文献路线整理、论文配图、汇报图和批量生成")
    cards = [
        (60, 350, PALE_CORAL, CORAL, "文献路线", "把截图里的路线\n整理成统一版式"),
        (60, 650, PALE_TEAL, TEAL, "论文配图", "统一键长、字体\n条件和编号"),
        (60, 950, PALE_BLUE, NAVY, "复杂分子", "多环骨架、保护基\n保持片段朝向"),
        (60, 1250, "#FFF1D6", "#B96B00", "自动化", "SVG / PNG 输出\n规则可以复用"),
    ]
    for x, y, bg, color, title, body in cards:
        parts += [rect(x, y, 960, 220, bg, 28), t(x + 48, y + 72, title, 31, color, 800), multiline(x + 48, y + 132, body.split("\n"), 25, 40, INK, 600)]
    parts += [
        rect(60, 1570, 960, 155, NAVY, 30),
        t(540, 1640, "把“像不像”变成一套可验证的规则", 28, WHITE, 800, anchor="middle"),
        t(540, 1688, "ChemKit  ·  RDKit  ·  SVG", 21, GOLD, 700, anchor="middle"),
    ]
    parts += footer(5)
    return parts


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    builders = (slide_01, slide_02, slide_03, slide_04, slide_05)
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        raise RuntimeError("Google Chrome is required for PNG export")
    if not CHEMDRAW_IMAGE.exists():
        raise RuntimeError(f"ChemDraw reference image not found: {CHEMDRAW_IMAGE}")
    for idx, builder in enumerate(builders, 1):
        svg_path = OUT / f"slide-{idx:02d}.svg"
        png_path = OUT / f"slide-{idx:02d}.png"
        svg_path.write_text(svg(builder()), encoding="utf-8")
        subprocess.run([
            str(chrome), "--headless=new", "--disable-gpu",
            f"--screenshot={png_path}", f"--window-size={W},{H}", svg_path.as_uri(),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(png_path)


if __name__ == "__main__":
    main()
