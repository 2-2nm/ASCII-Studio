import os, numpy as np
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ProcessPoolExecutor

MAX_WORKERS = os.cpu_count() or 8
ASCII_CHARS_BLACK_BG = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", ".", " "]
ASCII_CHARS_WHITE_BG = [" ", ".", ",", ":", ";", "+", "*", "?", "%", "S", "#", "@"]
ASCII_CHARS_COLOR_BLACK_BG = [" ", ".", ":", "+", "x", "X", "$", "&", "#", "@"]

def resize_image_aspect_ratio(image, new_width=55, font_aspect_ratio=0.50):
    w, h = image.size; return image.resize((new_width, max(1, int((h / w) * new_width * font_aspect_ratio))), Image.Resampling.LANCZOS)

def _process_color_chunk_process(task_data):
    y_range, width, r_sub, g_sub, b_sub, a_sub, mapped_chars_sub = task_data
    A, G = [], []
    for idx, y in enumerate(y_range):
        al, gl = [], []; ar, rr, gr, br, cr = a_sub[idx], r_sub[idx], g_sub[idx], b_sub[idx], mapped_chars_sub[idx]
        for x in range(width):
            if ar[x] < 128: al.append(" "); gl.append((" ", "#121212"))
            else:
                rv, gv, bv, ch = rr[x], gr[x], br[x], cr[x]
                al.append(f"\033[38;2;{rv};{gv};{bv}m{ch}\033[0m"); gl.append((ch, f"#{rv:02x}{gv:02x}{bv:02x}"))
        A.append((y, "".join(al))); G.append((y, gl))
    return A, G

def convert_image_to_fullcolor(image_path, size_txt=55, num_workers=None):
    if num_workers is None: num_workers = MAX_WORKERS
    try: img = Image.open(image_path)
    except Exception as e: raise Exception(f"Failed: {e}")
    r_img = resize_image_aspect_ratio(img, new_width=size_txt, font_aspect_ratio=0.50)
    arr = np.array(r_img.convert("RGBA"))
    h, w, _ = arr.shape
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    gray = (0.299 * r + 0.587 * g + 0.114 * b).astype(np.uint8)
    ac = ASCII_CHARS_COLOR_BLACK_BG; nc = len(ac); anp = np.array(list(ac))
    ci = np.clip((gray.astype(np.uint16) * nc) // 256, 0, nc - 1)
    mc = anp[ci]
    cs = max(1, h // num_workers); tasks = []
    for i in range(num_workers):
        sy = i * cs; ey = h if i == num_workers - 1 else (i + 1) * cs
        if sy < h: tasks.append((list(range(sy, ey)), w, r[sy:ey], g[sy:ey], b[sy:ey], a[sy:ey], mc[sy:ey]))
    aa, ag = [], []
    with ProcessPoolExecutor(max_workers=num_workers) as ex:
        res = ex.map(_process_color_chunk_process, tasks)
        for anc, gnc in res: aa.extend(anc); ag.extend(gnc)
    aa.sort(key=lambda x: x[0]); ag.sort(key=lambda x: x[0])
    return "\n".join([l for _, l in aa]), [l for _, l in ag]

def render_gui_preview_to_image(gui_preview_data, bg_color="#0F111A"):
    if not gui_preview_data: return None
    f = None
    for fn in ["consola.ttf", "Consolas.ttf", "cour.ttf", "Courier New.ttf"]:
        try: f = ImageFont.truetype(fn, 12); break
        except Exception: continue
    if f is None: f = ImageFont.load_default()
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    try: cw = int(d.textlength("M", font=f))
    except AttributeError: b = d.textbbox((0, 0), "M", font=f); cw = b[2] - b[0]
    try: asc, desc = f.getmetrics(); ch = asc + desc
    except AttributeError: b = d.textbbox((0, 0), "M", font=f); ch = b[3] - b[1] + 2
    cw, ch = max(cw, 7), max(ch, 14)
    mr, mc = len(gui_preview_data), max((len(l) for l in gui_preview_data), default=1)
    p = 10; iw, ih = mc * cw + (p * 2), mr * ch + (p * 2)
    img = Image.new("RGB", (iw, ih), color=bg_color); dr = ImageDraw.Draw(img)
    for y, line in enumerate(gui_preview_data):
        py = p + y * ch; x = 0; n = len(line)
        while x < n:
            char, col = line[x]; sx = x; rc = [char]; x += 1
            while x < n and line[x][1] == col: rc.append(line[x][0]); x += 1
            dr.text((p + sx * cw, py), "".join(rc), font=f, fill=col)
    return img

def convert_image_to_ascii_str(image_path, new_width=80, transparent_target="white"):
    try: img = Image.open(image_path)
    except Exception as e: raise Exception(f"Failed: {e}")
    ri = resize_image_aspect_ratio(img, new_width=new_width, font_aspect_ratio=0.50)
    ra, ga = np.array(ri.convert("RGBA")), np.array(ri.convert("L"))
    ac = ASCII_CHARS_BLACK_BG if transparent_target == "white" else ASCII_CHARS_WHITE_BG
    nc = len(ac); anp = np.array(list(ac))
    idx = np.clip((ga.astype(np.uint16) * nc) // 256, 0, nc - 1)
    cm = anp[idx]; cm[ra[:, :, 3] < 128] = " "
    return "\n".join("".join(row) for row in cm)

def save_ascii_as_image(ascii_content, output_path, bg_color="#090A0F", text_color="#9ECE6A", gui_preview_data=None):
    f = None
    for fn in ["consola.ttf", "Consolas.ttf", "cour.ttf", "Courier New.ttf", "DejaVuSansMono.ttf"]:
        try: f = ImageFont.truetype(fn, 14); break
        except Exception: continue
    if f is None: f = ImageFont.load_default()
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    try: cw = int(d.textlength("M", font=f))
    except AttributeError: b = d.textbbox((0, 0), "M", font=f); cw = b[2] - b[0]
    try: asc, desc = f.getmetrics(); ch = asc + desc
    except AttributeError: b = d.textbbox((0, 0), "M", font=f); ch = b[3] - b[1] + 2
    cw, ch = max(cw, 8), max(ch, 16)
    if gui_preview_data: mr, mc = len(gui_preview_data), max((len(l) for l in gui_preview_data), default=1)
    else:
        lines = ascii_content.splitlines() if isinstance(ascii_content, str) else []
        while lines and not lines[-1]: lines.pop()
        mr = len(lines) if lines else 1; mc = max((len(l) for l in lines), default=1) if lines else 1
    p = 16; iw, ih = mc * cw + (p * 2), mr * ch + (p * 2)
    img = Image.new("RGB", (iw, ih), color=bg_color); dr = ImageDraw.Draw(img)
    if gui_preview_data:
        for y, line in enumerate(gui_preview_data):
            py = p + y * ch; x = 0; n = len(line)
            while x < n:
                char, col = line[x]; sx = x; rc = [char]; x += 1
                while x < n and line[x][1] == col: rc.append(line[x][0]); x += 1
                dr.text((p + sx * cw, py), "".join(rc), font=f, fill=col)
    else:
        lines = ascii_content.splitlines() if isinstance(ascii_content, str) else []
        for y, line in enumerate(lines): dr.text((p, p + y * ch), line, font=f, fill=text_color)
    img.save(output_path)

def get_resource_path(relative_path):
    return os.path.join(getattr(os.sys, "_MEIPASS", os.path.abspath(".")), relative_path)