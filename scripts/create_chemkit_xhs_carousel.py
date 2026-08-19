#!/usr/bin/env python3
"""Create deterministic Xiaohongshu carousel graphics for ChemKit."""

from __future__ import annotations

import base64
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "xhs-chemkit-20260819"
# Landscape format for Xiaohongshu notes, presentations, and article headers.
W, H = 1920, 1080

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


def esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def t(x: float, y: float, text: str, size: float, fill=INK, weight=500, anchor="start", cls="body") -> str:
    return f'<text class="{cls}" x="{x}" y="{y}" font-size="{size}px" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{esc(text)}</text>'


def multiline(x: float, y: float, lines: list[str], size: float, line_height: float, fill=INK, weight=500, anchor="start", cls="body") -> str:
    return "\n".join(t(x, y + i * line_height, line, size, fill, weight, anchor, cls) for i, line in enumerate(lines))


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
        t(100, 62, f"CHEMKIT  /  0{slide}", 20, CORAL, 800, cls="eyebrow"),
        t(100, 132, title, 62, NAVY, 800, cls="title"),
        t(100, 180, eyebrow, 22, TEAL, 700, cls="eyebrow"),
        t(100, 225, subtitle, 26, MUTED, 500, cls="subtitle"),
    ]


def footer(slide: int) -> list[str]:
    return [
        t(100, 1045, "RDKit  ·  SVG  ·  ChemDraw-like layout", 18, MUTED, 600, cls="footer"),
        t(1820, 1045, f"{slide}/5", 18, MUTED, 700, anchor="end", cls="footer"),
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
        rect(100, 285, 1720, 455, NAVY, 34),
        t(165, 365, "不是把结构“画出来”就结束了", 29, "#D9E2EC", 600),
        t(165, 430, "而是把比例、朝向、间距和层级", 42, WHITE, 800),
        t(165, 490, "一起画对。", 42, GOLD, 800),
        rect(900, 345, 835, 285, WHITE, 22),
        image(FAT_IMAGE, 925, 378, 785, 220, 18),
        rect(100, 800, 500, 110, PALE_CORAL, 22),
        rect(710, 800, 500, 110, PALE_TEAL, 22),
        rect(1320, 800, 500, 110, PALE_BLUE, 22),
        t(350, 867, "统一比例", 26, CORAL, 800, anchor="middle"),
        t(960, 867, "保留朝向", 26, TEAL, 800, anchor="middle"),
        t(1570, 867, "自动排版", 26, NAVY, 800, anchor="middle"),
    ]
    parts += footer(1)
    return parts


def slide_02() -> list[str]:
    parts = header(2, "为什么以前总觉得“不像”", "问题不在结构", "而在结构和文字没有使用同一套视觉尺度")
    parts += [
        rect(100, 300, 820, 640, WHITE, 30),
        rect(1000, 300, 820, 640, NAVY, 30),
        t(150, 370, "以前", 28, CORAL, 800),
        t(1050, 370, "新版 ChemKit", 28, GOLD, 800),
        multiline(150, 455, ["苯环大小对了", "但原子标签偏小", "条件文字漂得太高", "编号贴着结构", "加号不在两个分子中间"], 27, 62, INK, 600),
        multiline(1050, 455, ["以有效键长为基准", "原子 / 条件 / 编号统一比例", "按可见边界放置加号和箭头", "共享编号基线", "保留片段朝向"], 27, 62, WHITE, 600),
        rect(150, 805, 720, 92, PALE_CORAL, 22),
        rect(1050, 805, 720, 92, "#1E405F", 22),
        t(510, 862, "“能画” ≠ “像论文”", 25, CORAL, 800, anchor="middle"),
        t(1410, 862, "视觉规则可复用", 25, GOLD, 800, anchor="middle"),
    ]
    parts += footer(2)
    return parts


def slide_03() -> list[str]:
    parts = header(3, "新版规则的核心", "先统一有效键长", "再决定字号、线宽和路线间距")
    parts += [
        rect(100, 300, 1720, 390, WHITE, 30),
        image(DIARYLAMINE_IMAGE, 170, 355, 1580, 280, 18),
        rect(100, 755, 520, 170, PALE_BLUE, 24),
        rect(700, 755, 520, 170, PALE_TEAL, 24),
        rect(1300, 755, 520, 170, PALE_CORAL, 24),
        t(360, 815, "有效键长", 26, NAVY, 800, anchor="middle"),
        t(360, 870, "38.2 px 左右", 25, NAVY, 700, anchor="middle"),
        t(960, 815, "文字层级", 26, TEAL, 800, anchor="middle"),
        t(960, 870, "26 / 25 / 25 px", 25, TEAL, 700, anchor="middle"),
        t(1560, 815, "布局锚点", 26, CORAL, 800, anchor="middle"),
        t(1560, 870, "可见边界中点", 25, CORAL, 700, anchor="middle"),
    ]
    parts += footer(3)
    return parts


def slide_04() -> list[str]:
    parts = header(4, "复杂路线高强度测试", "多环、保护基、侧链", "也要保持清楚的路线层级")
    parts += [
        rect(100, 280, 1720, 605, WHITE, 30),
        image(TAXOL_IMAGE, 145, 315, 1630, 500, 20),
        rect(145, 830, 1630, 72, NAVY, 18),
        t(960, 877, "10-DAB  →  保护基调整  →  侧链安装  →  Taxol", 25, WHITE, 700, anchor="middle"),
        t(100, 955, "复杂结构不再用“缩小分子”来解决拥挤", 29, NAVY, 800),
        t(100, 1000, "让画布增长，让结构保持比例。", 26, MUTED, 600),
    ]
    parts += footer(4)
    return parts


def slide_05() -> list[str]:
    parts = header(5, "从结构数据到统一画风", "ChemKit 适合谁？", "文献路线整理、论文配图、汇报图和批量生成")
    cards = [
        (100, 300, PALE_CORAL, CORAL, "文献路线", "把截图里的路线\n整理成统一版式"),
        (1000, 300, PALE_TEAL, TEAL, "论文配图", "统一键长、字体\n条件和编号"),
        (100, 600, PALE_BLUE, NAVY, "复杂分子", "多环骨架、保护基\n保持片段朝向"),
        (1000, 600, "#FFF1D6", "#B96B00", "自动化", "SVG / PNG 输出\n规则可以复用"),
    ]
    for x, y, bg, color, title, body in cards:
        parts += [rect(x, y, 820, 220, bg, 28), t(x + 48, y + 66, title, 31, color, 800), multiline(x + 48, y + 125, body.split("\n"), 25, 40, INK, 600)]
    parts += [
        rect(100, 900, 1720, 85, NAVY, 30),
        t(960, 950, "把“像不像”变成一套可验证的规则", 30, WHITE, 800, anchor="middle"),
        t(960, 980, "ChemKit  ·  RDKit  ·  SVG", 18, GOLD, 700, anchor="middle"),
    ]
    parts += footer(5)
    return parts


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for idx, builder in enumerate((slide_01, slide_02, slide_03, slide_04, slide_05), 1):
        svg_path = OUT / f"slide-{idx:02d}.svg"
        png_path = OUT / f"slide-{idx:02d}.png"
        svg_path.write_text(svg(builder()), encoding="utf-8")
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        if not chrome.exists():
            raise RuntimeError("Google Chrome is required for PNG export")
        subprocess.run(
            [
                str(chrome),
                "--headless=new",
                "--disable-gpu",
                f"--screenshot={png_path}",
                f"--window-size={W},{H}",
                svg_path.as_uri(),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(png_path)


if __name__ == "__main__":
    main()
