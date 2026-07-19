#!/usr/bin/env python3
"""Generate Xiaohongshu promo cards for ChemKit."""

from __future__ import annotations

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path("/Users/yl/Desktop/skills/ChemKit")
OUT_DIR = ROOT / "social" / "xiaohongshu"
REACTION = ROOT / "examples" / "20260719-s-citronellal-terminal-methyl-oxidation.png"

W, H = 1242, 1660
FONT_CN = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_CN_LIGHT = "/System/Library/Fonts/STHeiti Light.ttc"
FONT_LATIN_BOLD = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

INK = "#151515"
MUTED = "#6D7280"
LIGHT_BG = "#F7F8F4"
PANEL = "#FFFFFF"
TEAL = "#116B68"
CORAL = "#EC6A5E"
BLUE = "#2F5EAA"
AMBER = "#C78A1D"
LILAC = "#6E5BAA"
LINE = "#D7DBE2"


def font(size: int, bold: bool = False, latin: bool = False) -> ImageFont.FreeTypeFont:
    if latin and bold:
        return ImageFont.truetype(FONT_LATIN_BOLD, size)
    return ImageFont.truetype(FONT_CN if bold else FONT_CN_LIGHT, size)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        tokens = re.findall(r"[A-Za-z0-9/._+-]+|[^\x00-\x7F]|\s+|.", paragraph)
        for token in tokens:
            if token.isspace() and not current:
                continue
            trial = current + token
            if text_size(draw, trial, fnt)[0] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current.rstrip())
                current = token.lstrip()
                if text_size(draw, current, fnt)[0] > max_width:
                    for char in current:
                        trial = (lines[-1] if lines and text_size(draw, lines[-1], fnt)[0] < max_width else "") + char
                        if lines and text_size(draw, trial, fnt)[0] <= max_width:
                            lines[-1] = trial
                        else:
                            lines.append(char)
                    current = ""
        if current:
            lines.append(current.rstrip())
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: str,
    max_width: int,
    line_gap: int = 12,
) -> int:
    x, y = xy
    for line in wrap_text(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += text_size(draw, line or " ", fnt)[1] + line_gap
    return y


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str | None = None, radius: int = 28, width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def add_shadow_card(img: Image.Image, box: tuple[int, int, int, int], radius: int = 26, fill: str = PANEL) -> None:
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(box, radius=radius, fill=(30, 35, 45, 34))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    img.alpha_composite(shadow)
    draw = ImageDraw.Draw(img)
    rounded(draw, box, fill=fill, outline="#E6E9EF", radius=radius, width=2)


def base(card_no: int, title: str, kicker: str = "ChemKit") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (W, H), LIGHT_BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 18), fill=TEAL)
    draw.text((72, 58), kicker, font=font(34, bold=True, latin=True), fill=TEAL)
    draw.text((W - 180, 62), f"{card_no:02d}/05", font=font(30, bold=True, latin=True), fill=MUTED)
    draw_wrapped(draw, (72, 124), title, font(76, bold=True), INK, 1010, line_gap=20)
    return img, draw


def paste_reaction(img: Image.Image, box: tuple[int, int, int, int]) -> None:
    rxn = Image.open(REACTION).convert("RGBA")
    rxn = trim_white(rxn)
    max_w = box[2] - box[0] - 70
    max_h = box[3] - box[1] - 70
    scale = min(max_w / rxn.width, max_h / rxn.height)
    rxn = rxn.resize((int(rxn.width * scale), int(rxn.height * scale)), Image.Resampling.LANCZOS)
    x = box[0] + (box[2] - box[0] - rxn.width) // 2
    y = box[1] + (box[3] - box[1] - rxn.height) // 2
    img.alpha_composite(rxn, (x, y))


def trim_white(img: Image.Image) -> Image.Image:
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    diff = Image.new("L", img.size, 0)
    pix = img.convert("RGB").load()
    mask = diff.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = pix[x, y]
            if min(255 - r, 255 - g, 255 - b) > 10 or max(abs(r - 255), abs(g - 255), abs(b - 255)) > 12:
                mask[x, y] = 255
    bbox = diff.getbbox()
    return img.crop(bbox) if bbox else img


def pill(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, color: str) -> None:
    x, y = xy
    fnt = font(30, bold=True)
    tw, th = text_size(draw, text, fnt)
    rounded(draw, (x, y, x + tw + 34, y + th + 24), fill=color, radius=18)
    draw.text((x + 17, y + 10), text, font=fnt, fill="#FFFFFF")


def footer(draw: ImageDraw.ImageDraw, text: str = "把化学绘图规范变成可复用的自动化规则") -> None:
    draw.line((72, H - 118, W - 72, H - 118), fill=LINE, width=2)
    draw.text((72, H - 84), text, font=font(28), fill=MUTED)


def card_1() -> Image.Image:
    img, draw = base(1, "我做了一个\n会画论文风格反应路线的 Skill")
    pill(draw, (72, 342), "ChemDraw 审美", TEAL)
    pill(draw, (330, 342), "RDKit 自动化", BLUE)
    add_shadow_card(img, (72, 460, W - 72, 870), radius=30)
    paste_reaction(img, (92, 490, W - 92, 840))
    draw_wrapped(
        draw,
        (92, 960),
        "ChemKit 的目标不是只把结构画出来，而是把 ChemDraw 里反复手调的论文排版经验，沉淀成一套可以复用的自动绘图规则。",
        font(42, bold=True),
        INK,
        W - 184,
        line_gap=18,
    )
    footer(draw)
    return img


def card_2() -> Image.Image:
    img, draw = base(2, "为什么要做 ChemKit？")
    y = 360
    items = [
        ("ChemDraw", "结构能画，但每次手动排版都很耗时间。", CORAL),
        ("RDKit", "可以自动出图，但默认图经常不够像论文。", BLUE),
        ("ChemKit", "把审美规则写进管线，尽量自动画得规范。", TEAL),
    ]
    for name, desc, color in items:
        add_shadow_card(img, (72, y, W - 72, y + 245), radius=24)
        draw.ellipse((112, y + 66, 190, y + 144), fill=color)
        draw.text((220, y + 52), name, font=font(46, bold=True, latin=name.isascii()), fill=INK)
        draw_wrapped(draw, (220, y + 120), desc, font(36), MUTED, 820, line_gap=12)
        y += 295
    draw_wrapped(draw, (92, 1265), "真正麻烦的不是画结构，而是把它调到像论文里真的会出现的图。", font(44, bold=True), INK, W - 184, line_gap=16)
    footer(draw, "初衷：少手排一点，多把注意力留给化学本身")
    return img


def card_3() -> Image.Image:
    img, draw = base(3, "我给 ChemKit 定了这些绘图规则")
    rules = [
        ("结构比例统一", "原料和产物不再一大一小"),
        ("骨架方向继承", "产物沿用原料方向，只突出反应位点"),
        ("箭头自动匹配文字", "条件越长，箭头越合理延长"),
        ("条件居中贴近箭头", "不漂、不挤、不压结构"),
        ("原子标签加粗放大", "更接近 ACS / ChemDraw 观感"),
        ("手性虚线键增强", "避免 PNG 里手性键显得太淡"),
    ]
    y = 345
    for idx, (head, desc) in enumerate(rules, start=1):
        x = 72 if idx % 2 else 632
        if idx % 2 == 1 and idx > 1:
            y += 280
        add_shadow_card(img, (x, y, x + 510, y + 230), radius=22)
        draw.text((x + 34, y + 30), f"{idx:02d}", font=font(34, bold=True, latin=True), fill=TEAL)
        draw.text((x + 34, y + 86), head, font=font(38, bold=True), fill=INK)
        draw_wrapped(draw, (x + 34, y + 142), desc, font(30), MUTED, 430, line_gap=10)
    footer(draw, "核心：让机器不只是画对，还要画得像论文图")
    return img


def card_4() -> Image.Image:
    img, draw = base(4, "未来输入可以很轻：一句话或一张图")
    flow = [
        ("自然语言", "描述反应物、条件、产物"),
        ("结构解析", "不确定就追问，不硬猜"),
        ("规则布局", "统一比例、方向、箭头和文字"),
        ("SVG / PNG", "输出可检查、可继续编辑的图"),
    ]
    y = 380
    centers = []
    for idx, (head, desc) in enumerate(flow):
        x = 112 + idx * 275
        centers.append((x + 115, y + 115))
        rounded(draw, (x, y, x + 230, y + 230), fill="#FFFFFF", outline="#E6E9EF", radius=26, width=2)
        draw.text((x + 38, y + 48), head, font=font(34, bold=True), fill=[TEAL, BLUE, AMBER, LILAC][idx])
        draw_wrapped(draw, (x + 30, y + 106), desc, font(25), MUTED, 170, line_gap=8)
    for a, b in zip(centers, centers[1:]):
        draw.line((a[0] + 120, a[1], b[0] - 120, b[1]), fill=INK, width=3)
        draw.polygon([(b[0] - 120, b[1]), (b[0] - 134, b[1] - 8), (b[0] - 134, b[1] + 8)], fill=INK)
    add_shadow_card(img, (92, 780, W - 92, 1160), radius=28)
    draw.text((132, 825), "两种理想入口", font=font(44, bold=True), fill=INK)
    draw_wrapped(draw, (132, 910), "1. 直接说：从 S-香茅醛出发，用 TBHP 和水杨酸氧化末端甲基。\n2. 上传截图或论文图：先识别结构，再用自己的风格重新画。", font(36), MUTED, W - 264, line_gap=18)
    footer(draw, "目标不是复制别人图，而是提取化学信息后重新规范绘制")
    return img


def card_5() -> Image.Image:
    img, draw = base(5, "一个实际测试：香茅醛末端甲基氧化")
    add_shadow_card(img, (72, 345, W - 72, 815), radius=30)
    paste_reaction(img, (92, 380, W - 92, 780))
    checks = [
        ("S 手性保留", TEAL),
        ("产物骨架同向", BLUE),
        ("dashed wedge 加粗", CORAL),
        ("条件文字居中", AMBER),
    ]
    y = 900
    for idx, (text, color) in enumerate(checks):
        x = 92 if idx % 2 == 0 else 630
        if idx == 2:
            y += 128
        rounded(draw, (x, y, x + 500, y + 88), fill="#FFFFFF", outline="#E6E9EF", radius=20)
        draw.rectangle((x, y, x + 14, y + 88), fill=color)
        draw.text((x + 38, y + 24), text, font=font(34, bold=True), fill=INK)
    draw_wrapped(draw, (92, 1240), "这类小细节单独看都不大，但叠在一起，就是“像不像论文图”的差别。", font(42, bold=True), INK, W - 184, line_gap=18)
    footer(draw, "ChemKit：面向化学反应路线的自动绘图规则集")
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cards = [card_1(), card_2(), card_3(), card_4(), card_5()]
    for idx, card in enumerate(cards, start=1):
        path = OUT_DIR / f"chemkit-xhs-{idx:02d}.png"
        card.convert("RGB").save(path, quality=96)
        print(path)


if __name__ == "__main__":
    main()
