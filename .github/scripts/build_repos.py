#!/usr/bin/env python3
"""生成仓库展示页所需的静态数据与预览图。

产物（repos/repos.json 与 repos/previews/*.png）不进 git，
在 GitHub Actions 部署时生成（见 .github/workflows/static.yml），
也可以在本地手动运行以便本地预览：
    python .github/scripts/build_repos.py
"""
import json
import os
import subprocess
import sys
import urllib.request

USERNAME = "ABitGinger"
API_URL = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "repos")
PREVIEW_DIR = os.path.join(OUT_DIR, "previews")
# 手动图片覆盖配置（进 git）：{ "仓库名": "图片路径或完整 URL" }
OVERRIDES_PATH = os.path.join(OUT_DIR, "overrides.json")

# 与站点一致的金色点缀，纯白底
GOLD = (223, 182, 95)
GOLD_DARK = (170, 128, 40)   # 白底上使用的深金色
BG_TOP = (255, 255, 255)
BG_BOTTOM = (255, 255, 255)
TEXT = (34, 31, 27)
TEXT_DIM = (110, 103, 92)
RED = (202, 62, 62)

LANG_COLORS = {
    "C": "#555555", "C#": "#178600", "C++": "#f34b7d",
    "CSS": "#563d7c", "Dockerfile": "#384d54", "Go": "#00ADD8",
    "HTML": "#e34c26", "Java": "#b07219", "JavaScript": "#f1e05a",
    "Kotlin": "#A97BFF", "PHP": "#4F5D95", "Python": "#3572A5",
    "Ruby": "#701516", "Rust": "#dea584", "Shell": "#89e051",
    "Swift": "#F05138", "TypeScript": "#3178c6", "Vue": "#41b883",
}
DEFAULT_COLOR = "#8b949e"

regular = bold = None


def fetch_repos(token):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-repos-showcase",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API_URL, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def discover_cjk_fonts():
    """fc-list 兜底：列出系统里声明支持中文的字体文件（适用于未预装 Noto CJK 的环境）。"""
    try:
        proc = subprocess.run(
            ["fc-list", ":lang=zh", "file"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return []
    paths = [line.strip().rstrip(":") for line in proc.stdout.splitlines()]
    return [p for p in paths if p.lower().endswith((".ttc", ".ttf", ".otf"))]


def pick_font(paths):
    """在候选字体路径里找到可用的中文字体；TTC 内优先选简体中文变体。

    找不到可用中文字体时直接报错退出——绝不退回 Pillow 内置位图字体
    （它忽略字号，CI 上曾因此生成过文字极小的预览图）。"""
    for path in paths:
        if not os.path.exists(path):
            continue
        index = 0
        for i in range(8):
            try:
                probe = ImageFont.truetype(path, 20, index=i)
            except Exception:
                break
            if "SC" in " ".join(probe.getname()):
                index = i
                break
        return lambda size, path=path, index=index: ImageFont.truetype(path, size, index=index)
    sys.exit("错误：找不到可用的中文字体（Linux 请先安装 fonts-noto-cjk 或等价中文字体包）")


def setup_fonts():
    global regular, bold
    discovered = discover_cjk_fonts()
    regular = pick_font([
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Debian/Ubuntu (fonts-noto-cjk)
        "C:/Windows/Fonts/msyh.ttc",                               # Windows 微软雅黑
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simhei.ttf",                             # Windows 黑体
        "/System/Library/Fonts/PingFang.ttc",                      # macOS
    ] + discovered)
    bold = pick_font([
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
    ] + discovered)


def wrap_text(draw, text, font, max_width):
    lines = []
    for para in text.splitlines() or [""]:
        line = ""
        for ch in para:
            if line and draw.textlength(line + ch, font=font) > max_width:
                # 中文可任意断行；英文单词尽量在空格处断开
                if ch.isascii() and ch.isalnum() and " " in line:
                    cut = line.rfind(" ")
                    lines.append(line[:cut])
                    line = line[cut + 1:] + ch
                else:
                    lines.append(line)
                    line = ch
            else:
                line += ch
        lines.append(line)
    return lines


def fit_lines(draw, text, font, max_width, max_lines):
    lines = wrap_text(draw, text, font, max_width)
    if len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines]
    last = kept[-1]
    while last and draw.textlength(last + "…", font=font) > max_width:
        last = last[:-1]
    kept[-1] = last + "…"
    return kept


def draw_badge(draw, x, y, text, font, outline, text_color):
    text_w = draw.textlength(text, font=font)
    pad_x, pad_y = 22, 10
    box = [x, y, x + text_w + pad_x * 2, y + 30 + pad_y * 2]
    draw.rounded_rectangle(box, radius=26, outline=outline, width=3)
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=text_color)
    return box[2]


def render_preview(repo, out_path):
    from PIL import Image, ImageColor, ImageDraw

    W, H = 1200, 600
    PAD = 72

    img = Image.new("RGB", (W, H), BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        row = tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM))
        draw.line([(0, y), (W, y)], fill=row)

    # 顶部：用户名 + 仓库名（过长时自动缩小）
    draw.text((PAD, 58), f"{USERNAME} /", font=regular(34), fill=TEXT_DIM)
    name_size = 84
    while name_size > 44 and draw.textlength(repo["name"], font=bold(name_size)) > W - PAD * 2:
        name_size -= 4
    draw.text((PAD, 106), repo["name"], font=bold(name_size), fill=TEXT)

    # 描述：最多两行，超长省略
    desc_y = 106 + name_size + 42
    description = repo.get("description") or "暂无简介"
    desc_font = regular(40)
    for i, line in enumerate(fit_lines(draw, description, desc_font, W - PAD * 2, 2)):
        draw.text((PAD, desc_y + i * 58), line, font=desc_font, fill=TEXT_DIM)

    # 底部元信息：语言色点、星标；右侧 Fork / 已归档 徽标
    meta_y = H - 140
    x = PAD
    language = repo.get("language")
    if language:
        color = ImageColor.getrgb(repo.get("lang_color") or DEFAULT_COLOR)
        draw.ellipse([x, meta_y + 14, x + 26, meta_y + 40], fill=color)
        draw.text((x + 40, meta_y + 8), language, font=regular(36), fill=TEXT_DIM)
        x += 40 + draw.textlength(language, font=regular(36)) + 44
    draw.text((x, meta_y + 8), f"★ {repo.get('stargazers_count', 0)}",
              font=regular(36), fill=GOLD)

    right = W - PAD
    if repo.get("archived"):
        badge_font = regular(30)
        box_w = draw.textlength("已归档", font=badge_font) + 44
        right = draw_badge(draw, right - box_w, meta_y, "已归档", badge_font, RED, (255, 201, 201)) - 24
    if repo.get("fork"):
        badge_font = regular(30)
        box_w = draw.textlength("Fork", font=badge_font) + 44
        draw_badge(draw, right - box_w, meta_y, "Fork", badge_font, GOLD, TEXT)

    # 底部金色饰条
    draw.rectangle([0, H - 12, W, H], fill=GOLD)

    img.save(out_path, "PNG", optimize=True)


def load_overrides():
    try:
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {k: v for k, v in data.items() if isinstance(v, str) and v}
    except FileNotFoundError:
        return {}
    except Exception as err:
        print(f"警告：overrides.json 解析失败，忽略覆盖配置（{err}）")
        return {}


def build(token=None, input_file=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    global ImageFont
    from PIL import ImageFont

    if input_file:
        with open(input_file, "r", encoding="utf-8") as fh:
            repos = json.load(fh)
        print(f"从本地文件读取 {len(repos)} 个仓库：{input_file}")
    else:
        repos = fetch_repos(token)
        print(f"从 GitHub API 获取 {len(repos)} 个仓库")

    os.makedirs(PREVIEW_DIR, exist_ok=True)

    overrides = load_overrides()
    manual = [name for name in overrides if name in {r["name"] for r in repos}]
    if manual:
        print(f"应用 {len(manual)} 条手动图片覆盖：{', '.join(manual)}")

    entries = [
        {
            "name": r["name"],
            "description": r.get("description"),
            "html_url": r["html_url"],
            "homepage": r.get("homepage") or None,
            "language": r.get("language"),
            "lang_color": LANG_COLORS.get(r.get("language"), DEFAULT_COLOR),
            "stargazers_count": r.get("stargazers_count", 0),
            "topics": r.get("topics") or [],
            "fork": r.get("fork", False),
            "archived": r.get("archived", False),
            "pushed_at": r.get("pushed_at"),
            # 手动指定的图片（仓库内路径或完整 URL），生成图仅作其加载失败的回退
            "image": overrides.get(r["name"]),
        }
        for r in repos
    ]
    data = {"updated": entries[0]["pushed_at"] if entries else None, "repos": entries}
    json_path = os.path.join(OUT_DIR, "repos.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))

    setup_fonts()
    names = set()
    for r in entries:
        preview_path = os.path.join(PREVIEW_DIR, r["name"] + ".png")
        render_preview(r, preview_path)
        names.add(r["name"] + ".png")

    # 清理已删除/改名仓库的旧预览图
    removed = 0
    for f in os.listdir(PREVIEW_DIR):
        if f not in names:
            os.remove(os.path.join(PREVIEW_DIR, f))
            removed += 1

    print(f"已写入 {json_path}")
    print(f"已生成 {len(names)} 张预览图，清理 {removed} 张过期图片")


if __name__ == "__main__":
    build(
        token=os.environ.get("GITHUB_TOKEN"),
        input_file=sys.argv[1] if len(sys.argv) > 1 else None,
    )
