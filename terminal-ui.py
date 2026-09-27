import os, platform, sys, threading, time, multiprocessing, tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

try: import psutil
except ImportError: psutil = None
try: import pywinstyles
except ImportError: pywinstyles = None

from core import MAX_WORKERS, convert_image_to_ascii_str, convert_image_to_fullcolor, get_resource_path, render_gui_preview_to_image, save_ascii_as_image

ctk.set_appearance_mode("Dark"); ctk.set_default_color_theme("blue")

class AsciiArtAppCTk(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VoxelText")
        self.THEME_COLORS = {
            "Dark": {"bg_dark": "#090A0F", "bg_surface": "#0F111A", "bg_panel": "#1A1D2B", "text_primary": "#A9B1D6", "text_muted": "#565F89", "accent": "#7AA2F7", "cmd_prompt": "#73DACA", "title_tag": "#BB9AF7", "key_tag": "#7DCFFF", "val_tag": "#C0CAF5", "note_tag": "#E0AF68", "log_info": "#7DCFFF", "log_warn": "#E0AF68", "log_err": "#F7768E"},
            "Light": {"bg_dark": "#E2E8F0", "bg_surface": "#FFFFFF", "bg_panel": "#CBD5E1", "text_primary": "#0F172A", "text_muted": "#475569", "accent": "#2563EB", "cmd_prompt": "#059669", "title_tag": "#6D28D9", "key_tag": "#0284C7", "val_tag": "#1E293B", "note_tag": "#D97706", "log_info": "#0284C7", "log_warn": "#D97706", "log_err": "#DC2626"}
        }
        self.CTK_BG_DARK, self.CTK_BG_SURFACE, self.CTK_BG_PANEL = ("#E2E8F0", "#090A0F"), ("#FFFFFF", "#0F111A"), ("#CBD5E1", "#1A1D2B")
        self.CTK_TEXT_PRIMARY, self.CTK_TEXT_MUTED, self.CTK_ACCENT = ("#0F172A", "#A9B1D6"), ("#475569", "#565F89"), ("#2563EB", "#7AA2F7")
        self.current_theme = "Dark"; self.colors = self.THEME_COLORS[self.current_theme]
        self.current_ascii_text, self.current_gui_preview, self.last_converted_basename, self.preview_photo_img = "", None, "", None
        self.overdrive_mode = ctk.BooleanVar(value=False)
        self.configure(fg_color=self.CTK_BG_DARK)
        ww, wh = 1200, 840; sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        cx, cy = int((sw - ww) / 2), int((sh - wh) / 2)
        self.geometry(f"{ww}x{wh}+{cx}+{cy}"); self.minsize(920, 620)
        self.is_fullscreen = False
        ip = get_resource_path("app-icon.ico")
        if os.path.exists(ip):
            try: self.iconbitmap(ip)
            except Exception: pass
        self.bind("<F11>", lambda e: self.toggle_fullscreen()); self.bind("<Escape>", lambda e: self.exit_fullscreen())
        self.bind("<Up>", lambda e: self.scroll_text_v(-3)); self.bind("<Down>", lambda e: self.scroll_text_v(3))
        self.bind("<Left>", lambda e: self.scroll_text_h(-3)); self.bind("<Right>", lambda e: self.scroll_text_h(3))
        self.color_mode = ctk.StringVar(value="Green"); self.transparent_target = ctk.StringVar(value="white")
        self.color_buttons = {}
        self.setup_ui(); self.show_fastfetch_placeholder(); self.apply_title_bar_color()

    def toggle_overdrive(self):
        if self.overdrive_mode.get():
            self.lbl_width.pack_forget(); self.entry_overdrive.pack(side="right", padx=(0, 4))
            self.slider_width.configure(state="disabled")
            self.append_system_log("Overdrive Width Mode ENABLED (Custom Input Active)", "warn")
        else:
            self.entry_overdrive.pack_forget(); self.lbl_width.pack(side="right")
            self.slider_width.configure(state="normal")
            self.append_system_log("Overdrive Width Mode DISABLED (Standard Slider Active)", "info")

    def apply_title_bar_color(self):
        if pywinstyles and platform.system() == "Windows":
            try: pywinstyles.change_header_color(self, color=self.colors["bg_dark"])
            except Exception: pass

    def get_sys_info(self):
        import datetime
        hn, un = platform.node() or "terminal", os.getlogin() if hasattr(os, "getlogin") else "root"
        oi, kr = f"{platform.system()} {platform.release()} ({platform.machine()})", platform.version().split(" ")[0]
        cpu = "Unknown CPU"
        try:
            if platform.system() == "Windows":
                import winreg
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu = winreg.QueryValueEx(k, "ProcessorNameString")[0].strip(); winreg.CloseKey(k)
            else: cpu = platform.processor() or "Unknown CPU"
        except Exception: cpu = platform.processor() or "Unknown CPU"
        gpu = "Unknown GPU"
        try:
            if platform.system() == "Windows":
                import winreg
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000")
                gpu = winreg.QueryValueEx(k, "DriverDesc")[0].strip(); winreg.CloseKey(k)
        except Exception: gpu = "Integrated / System Graphics"
        ram_str, disk_str, uptime_str = "N/A", "N/A", "N/A"
        if psutil:
            try:
                mem = psutil.virtual_memory()
                ram_str = f"{round(mem.used/(1024**3), 1)} GB / {round(mem.total/(1024**3), 1)} GB ({mem.percent}%)"
                dl = []
                for p in psutil.disk_partitions(all=False):
                    if os.name == "nt" and "cdrom" in p.opts.lower(): continue
                    try:
                        u = psutil.disk_usage(p.mountpoint)
                        dl.append(f"{p.mountpoint.replace('\\', '')} {round(u.used/(1024**3),1)}/{round(u.total/(1024**3),1)} GB")
                    except PermissionError: continue
                disk_str = " | ".join(dl)
                hrs, rem = divmod(int(time.time() - psutil.boot_time()), 3600); mins, _ = divmod(rem, 60)
                uptime_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"
            except Exception: pass
        return {"title": f"{un}@{hn}", "OS": oi, "Kernel": kr, "Uptime": uptime_str, "DateTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "CPU": cpu, "GPU": gpu, "Memory": ram_str, "Disk": disk_str, "Terminal": f"ASCII Engine v1.0.0 Global ({MAX_WORKERS} Threads Active)"}

    def load_ascii_art_logo(self):
        sd = os.path.dirname(os.path.abspath(__file__)); tp = os.path.join(sd, "ascii_terminal.txt")
        if not os.path.exists(tp): tp = get_resource_path("ascii_terminal.txt")
        if os.path.exists(tp):
            try:
                with open(tp, "r", encoding="utf-8") as f:
                    lines = [l.rstrip("\r\n") for l in f.readlines()]
                    if lines: return lines
            except Exception: pass
        return []

    def show_fastfetch_placeholder(self):
        self.scroll_preview.pack_forget(); self.txt_ascii.pack(fill="both", expand=True, padx=12, pady=10)
        info, ascii_logo = self.get_sys_info(), self.load_ascii_art_logo()
        self.txt_ascii.configure(state="normal", font=("Consolas", 8)); self.txt_ascii.delete("1.0", tk.END)
        self.txt_ascii.tag_config("cmd_prompt", foreground=self.colors["cmd_prompt"], font=("Consolas", 10, "bold"))
        self.txt_ascii.tag_config("ascii_art", foreground=self.colors["accent"], font=("Consolas", 9))
        self.txt_ascii.tag_config("title", foreground=self.colors["title_tag"], font=("Consolas", 10, "bold"))
        self.txt_ascii.tag_config("sep", foreground="#94A3B8" if self.current_theme == "Light" else "#3B4261")
        self.txt_ascii.tag_config("key", foreground=self.colors["key_tag"], font=("Consolas", 9, "bold"))
        self.txt_ascii.tag_config("val", foreground=self.colors["val_tag"], font=("Consolas", 9))
        self.txt_ascii.tag_config("note", foreground=self.colors["note_tag"], font=("Consolas", 9, "italic"))
        specs = [("OS", info["OS"]), ("Kernel", info["Kernel"]), ("Uptime", info["Uptime"]), ("Date Time", info["DateTime"]), ("CPU", info["CPU"]), ("GPU", info["GPU"]), ("Memory", info["Memory"]), ("Disk", info["Disk"]), ("Terminal", info["Terminal"])]
        self.txt_ascii.insert(tk.END, " ┌──(user@voxel-text)-[~]\n └─$ afetch --system-diagnostics\n\n", "cmd_prompt")
        maw = max(len(l) for l in ascii_logo) if ascii_logo else 0
        il = [("title", info["title"]), ("sep", "━" * (len(info["title"]) + 2))] + [("spec", s) for s in specs]
        tr = max(len(ascii_logo), len(il) + 2)
        for i in range(tr):
            if ascii_logo and maw > 0:
                ap = ascii_logo[i] if i < len(ascii_logo) else ""
                self.txt_ascii.insert(tk.END, ap.ljust(maw) + (" " * 4), "ascii_art")
            if i < len(il):
                tt, ct = il[i]
                if tt == "title": self.txt_ascii.insert(tk.END, ct + "\n", "title")
                elif tt == "sep": self.txt_ascii.insert(tk.END, ct + "\n", "sep")
                elif tt == "spec":
                    k, v = ct
                    self.txt_ascii.insert(tk.END, f"{k:<10}: ", "key"); self.txt_ascii.insert(tk.END, f"{v}\n", "val")
            elif i == len(il):
                self.txt_ascii.insert(tk.END, "Palette   : ", "key")
                cols = ["#0F172A", "#DC2626", "#16A34A", "#D97706", "#2563EB", "#9333EA", "#0284C7", "#475569"] if self.current_theme == "Light" else ["#1A1B26", "#F7768E", "#9ECE6A", "#E0AF68", "#7AA2F7", "#BB9AF7", "#7DCFFF", "#A9B1D6"]
                for idx, c in enumerate(cols):
                    tn = f"pal_{idx}"; self.txt_ascii.tag_config(tn, foreground=c, background=c); self.txt_ascii.insert(tk.END, "  ", (tn,))
                self.txt_ascii.insert(tk.END, "\n")
            else: self.txt_ascii.insert(tk.END, "\n")
        self.txt_ascii.insert(tk.END, "\n" + "─" * 90 + "\n", "sep")
        self.txt_ascii.insert(tk.END, "   > Execute 'Convert Image' command to render local graphics into ASCII.\n", "note")
        self.txt_ascii.insert(tk.END, "─" * 90 + "\n", "sep")
        self.txt_ascii.configure(state="disabled")

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen; self.attributes("-fullscreen", self.is_fullscreen)

    def exit_fullscreen(self):
        if self.is_fullscreen: self.is_fullscreen = False; self.attributes("-fullscreen", False)

    def toggle_theme_mode(self):
        self.current_theme = "Dark" if self.switch_theme.get() == 1 else "Light"
        ctk.set_appearance_mode(self.current_theme); self.colors = self.THEME_COLORS[self.current_theme]
        self.txt_ascii.configure(bg=self.colors["bg_surface"], fg=self.colors["text_primary"], insertbackground=self.colors["text_primary"])
        self.txt_logs.configure(bg=self.colors["bg_dark"], fg=self.colors["text_primary"])
        self.txt_logs.tag_config("info", foreground=self.colors["log_info"])
        self.txt_logs.tag_config("warn", foreground=self.colors["log_warn"])
        self.txt_logs.tag_config("err", foreground=self.colors["log_err"])
        self.select_color_mode(self.color_mode.get()); self.show_fastfetch_placeholder(); self.apply_title_bar_color()
        self.append_system_log(f"Session theme switched to {self.current_theme}.", "info")

    def update_transparency_options(self, *args):
        self.seg_alpha.configure(state="disabled" if self.color_mode.get() == "Color" else "normal")

    def select_color_mode(self, value):
        self.color_mode.set(value)
        for val, (btn, ac) in self.color_buttons.items():
            if val == value: btn.configure(fg_color=ac, text_color="#0F111A" if ac in ["#7DCFFF", "#F8FAFC", "#9ECE6A", "#E0AF68", "#C0CAF5"] else "#FFFFFF")
            else: btn.configure(fg_color=self.CTK_BG_PANEL, text_color=self.CTK_TEXT_PRIMARY)

    def scroll_text_v(self, amount):
        if self.scroll_preview.winfo_ismapped(): self.scroll_preview._parent_canvas.yview_scroll(amount, "units")
        else: self.txt_ascii.yview_scroll(amount, "units")

    def scroll_text_h(self, amount):
        if self.scroll_preview.winfo_ismapped(): self.scroll_preview._parent_canvas.xview_scroll(amount, "units")
        else: self.txt_ascii.xview_scroll(amount, "units")

    def _on_mousewheel(self, event):
        if self.scroll_preview.winfo_ismapped(): self.scroll_preview._parent_canvas.yview_scroll(int(-1 * (event.delta / 120) * 4), "units")
        else:
            if event.state & 0x0001: self.txt_ascii.xview_scroll(int(-1 * (event.delta / 120) * 4), "units")
            else: self.txt_ascii.yview_scroll(int(-1 * (event.delta / 120) * 4), "units")

    def append_system_log(self, text, tag="info"):
        self.txt_logs.configure(state="normal")
        self.txt_logs.insert(tk.END, f"[sys@kernel] {time.strftime('%H:%M:%S')} > {text}\n", (tag,))
        self.txt_logs.see(tk.END); self.txt_logs.configure(state="disabled")

    def setup_ui(self):
        tb = ctk.CTkFrame(self, fg_color=self.CTK_BG_SURFACE, height=42, corner_radius=8, border_width=1, border_color=self.CTK_BG_PANEL)
        tb.pack(side="top", fill="x", padx=12, pady=(12, 6))
        df = ctk.CTkFrame(tb, fg_color="transparent"); df.pack(side="left", padx=(12, 6))
        for dc in ["#F7768E", "#E0AF68", "#9ECE6A"]: ctk.CTkFrame(df, width=10, height=10, corner_radius=5, fg_color=dc).pack(side="left", padx=3)
        ctk.CTkLabel(tb, text="bash - voxel-text@tty1", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=self.CTK_TEXT_PRIMARY).pack(side="left", padx=12, pady=8)
        self.switch_theme = ctk.CTkSwitch(tb, text="DARK MODE", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=self.CTK_TEXT_PRIMARY, command=self.toggle_theme_mode, progress_color="#2563EB")
        self.switch_theme.select(); self.switch_theme.pack(side="right", padx=12, pady=8)
        self.btn_top_load = ctk.CTkButton(tb, text="Convert Image", fg_color=self.CTK_ACCENT, hover_color="#1D4ED8", text_color="#FFFFFF", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), corner_radius=4, command=self.convert_image_process)
        self.btn_top_load.pack(side="right", padx=6, pady=6)

        ml = ctk.CTkFrame(self, fg_color="transparent"); ml.pack(fill="both", expand=True, padx=12, pady=6)
        pf = ctk.CTkFrame(ml, fg_color=self.CTK_BG_SURFACE, corner_radius=8, border_width=1, border_color=self.CTK_BG_PANEL)
        pf.pack(side="top", fill="both", expand=True, pady=(0, 10))
        th = ctk.CTkFrame(pf, fg_color=self.CTK_BG_PANEL, height=28, corner_radius=6); th.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(th, text="TERMINAL OUTPUT PREVIEW", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.CTK_TEXT_MUTED).pack(side="left", padx=12, pady=2)
        nf = ctk.CTkFrame(th, fg_color="transparent"); nf.pack(side="right", padx=6)

        for txt, cmd in [("▲", lambda: self.scroll_text_v(-5)), ("▼", lambda: self.scroll_text_v(5)), ("◄", lambda: self.scroll_text_h(-5)), ("►", lambda: self.scroll_text_h(5))]:
            ctk.CTkButton(nf, text=txt, width=24, height=20, fg_color=self.CTK_BG_SURFACE, hover_color=self.CTK_ACCENT, text_color=self.CTK_TEXT_PRIMARY, font=ctk.CTkFont(family="Consolas", size=10), corner_radius=3, command=cmd).pack(side="left", padx=1, pady=2)

        self.txt_ascii = tk.Text(pf, font=("Consolas", 8), bg=self.colors["bg_surface"], fg=self.colors["text_primary"], relief="flat", bd=0, highlightthickness=0, wrap="none", insertbackground=self.colors["text_primary"])
        self.txt_ascii.pack(fill="both", expand=True, padx=12, pady=10); self.txt_ascii.bind("<MouseWheel>", self._on_mousewheel)
        self.scroll_preview = ctk.CTkScrollableFrame(pf, fg_color="transparent")
        try: self.scroll_preview._scrollbar.grid_forget()
        except Exception: pass
        self.lbl_preview_img = ctk.CTkLabel(self.scroll_preview, text=""); self.lbl_preview_img.pack(expand=True, padx=10, pady=10)

        bd = ctk.CTkFrame(ml, fg_color=self.CTK_BG_SURFACE, corner_radius=8, height=135, border_width=1, border_color=self.CTK_BG_PANEL)
        bd.pack(side="bottom", fill="x"); bd.pack_propagate(False)
        bd.columnconfigure(0, weight=0); bd.columnconfigure(1, weight=1); bd.columnconfigure(2, weight=1)

        c1 = ctk.CTkFrame(bd, fg_color="transparent", width=170); c1.grid(row=0, column=0, sticky="nsew", padx=(12, 16), pady=10)
        ctk.CTkLabel(c1, text="// PALETTE SELECT", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.CTK_TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        sc = ctk.CTkScrollableFrame(c1, fg_color="transparent", height=100, width=155); sc.pack(fill="both", expand=True)

        c_opts = [
            ("Matrix Green", "Green", "#16A34A" if self.current_theme == "Light" else "#9ECE6A"),
            ("Full ANSI Color", "Color", "#A03F54" if self.current_theme == "Light" else "#A03F54"),
            ("Monochrome", "White", "#1E293B" if self.current_theme == "Light" else "#C0CAF5"),
            ("Cyber Cyan", "Cyan", "#0284C7" if self.current_theme == "Light" else "#7DCFFF"),
            ("Neon Pink", "Pink", "#DC2626" if self.current_theme == "Light" else "#F7768E"),
            ("Coral Red", "Red", "#DC2626" if self.current_theme == "Light" else "#F7768E"),
            ("Amber Yellow", "Amber", "#D97706" if self.current_theme == "Light" else "#E0AF68"),
            ("Lime Accent", "Lime", "#059669" if self.current_theme == "Light" else "#73DACA"),
            ("Violet Glow", "Violet", "#7C3AED" if self.current_theme == "Light" else "#BB9AF7"),
            ("Tokyo Blue", "Blue", "#2563EB" if self.current_theme == "Light" else "#7AA2F7"),
            ("Sunset Orange", "Orange", "#EA580C" if self.current_theme == "Light" else "#FF9E64")
        ]
        for t, v, ch in c_opts:
            b = ctk.CTkButton(sc, text=f"> {t}", font=ctk.CTkFont(family="Consolas", size=10, weight="bold" if v == self.color_mode.get() else "normal"), fg_color=ch if v == self.color_mode.get() else self.CTK_BG_PANEL, text_color="#FFFFFF" if v == self.color_mode.get() else self.CTK_TEXT_PRIMARY, hover_color=ch, anchor="w", height=24, corner_radius=4, command=lambda val=v: self.select_color_mode(val))
            b.pack(fill="x", pady=2); self.color_buttons[v] = (b, ch)
        self.color_mode.trace_add("write", self.update_transparency_options)

        c2 = ctk.CTkFrame(bd, fg_color="transparent"); c2.grid(row=0, column=1, sticky="nsew", padx=12, pady=10)
        ctk.CTkLabel(c2, text="// PARAMETERS CONFIG", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.CTK_TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        sf1 = ctk.CTkFrame(c2, fg_color="transparent"); sf1.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(sf1, text="• Width Units:", font=ctk.CTkFont(family="Consolas", size=10), text_color=self.CTK_TEXT_PRIMARY).pack(side="left")

        self.chk_overdrive = ctk.CTkCheckBox(sf1, text="Overdrive", font=ctk.CTkFont(family="Consolas", size=9, weight="bold"), text_color="#F7768E", checkbox_width=14, checkbox_height=14, border_width=2, corner_radius=3, variable=self.overdrive_mode, command=self.toggle_overdrive)
        self.chk_overdrive.pack(side="right", padx=(6, 0))
        self.entry_overdrive = ctk.CTkEntry(sf1, width=55, height=20, font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), fg_color=self.CTK_BG_DARK, text_color="#F7768E", border_color="#F7768E", border_width=1, corner_radius=4, justify="center")
        self.entry_overdrive.insert(0, "2000")
        self.lbl_width = ctk.CTkLabel(sf1, text="85 px", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.CTK_TEXT_PRIMARY, fg_color=self.CTK_BG_PANEL, corner_radius=4, padx=6, pady=1)
        self.lbl_width.pack(side="right")

        self.slider_width = ctk.CTkSlider(c2, from_=30, to=200, number_of_steps=170, fg_color=self.CTK_BG_DARK, progress_color=self.CTK_ACCENT, button_color=self.CTK_ACCENT, button_hover_color="#3B82F6", command=lambda v: self.lbl_width.configure(text=f"{round(v)} px"))
        self.slider_width.set(85); self.slider_width.pack(fill="x", pady=(2, 4))

        sf2 = ctk.CTkFrame(c2, fg_color="transparent"); sf2.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(sf2, text="• Cutoff Threshold:", font=ctk.CTkFont(family="Consolas", size=10), text_color=self.CTK_TEXT_PRIMARY).pack(side="left")
        self.lbl_thresh = ctk.CTkLabel(sf2, text="30%", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.CTK_TEXT_PRIMARY, fg_color=self.CTK_BG_PANEL, corner_radius=4, padx=6, pady=1)
        self.lbl_thresh.pack(side="right")
        self.slider_thresh = ctk.CTkSlider(c2, from_=0, to=100, number_of_steps=100, fg_color=self.CTK_BG_DARK, progress_color=self.CTK_ACCENT, button_color=self.CTK_ACCENT, button_hover_color="#3B82F6", command=lambda v: self.lbl_thresh.configure(text=f"{round(v)}%"))
        self.slider_thresh.set(30); self.slider_thresh.pack(fill="x", pady=(2, 4))

        af = ctk.CTkFrame(c2, fg_color="transparent"); af.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(af, text="• Transparency Target:", font=ctk.CTkFont(family="Consolas", size=10), text_color=self.CTK_TEXT_PRIMARY).pack(side="left")
        self.seg_alpha = ctk.CTkSegmentedButton(af, values=["Black", "White"], selected_color=self.colors["accent"], unselected_color=self.CTK_BG_PANEL, selected_hover_color="#1D4ED8", unselected_hover_color="#3B4261", command=lambda v: self.transparent_target.set(v.lower()), text_color="#FFFFFF", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), corner_radius=16, height=24)
        self.seg_alpha.set("White"); self.seg_alpha.pack(side="right")

        self.btn_save_photo = ctk.CTkButton(c2, text="Save as PNG", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), fg_color=self.CTK_ACCENT, hover_color="#1D4ED8", text_color="#FFFFFF", height=26, corner_radius=4, command=self.save_as_photo_process)
        self.btn_save_photo.pack(fill="x", pady=(6, 0))

        c3 = ctk.CTkFrame(bd, fg_color="transparent"); c3.grid(row=0, column=2, sticky="nsew", padx=(6, 12), pady=10)
        ctk.CTkLabel(c3, text="// CONSOLE LOGS", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=self.CTK_TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.txt_logs = tk.Text(c3, height=5, bg=self.colors["bg_dark"], fg=self.colors["text_primary"], font=("Consolas", 8), relief="flat", bd=0, wrap="word")
        self.txt_logs.pack(fill="both", expand=True)
        self.txt_logs.tag_config("info", foreground=self.colors["log_info"]); self.txt_logs.tag_config("warn", foreground=self.colors["log_warn"]); self.txt_logs.tag_config("err", foreground=self.colors["log_err"])
        self.append_system_log(f"Engine initialized. Multi-Core Active ({MAX_WORKERS} Threads).", "info")

    def save_as_photo_process(self):
        if not self.current_ascii_text and not self.current_gui_preview:
            self.append_system_log("Save PNG cancelled: No ASCII data present.", "warn"); return
        dpn = f"{self.last_converted_basename}_ascii.png" if self.last_converted_basename else "ascii_photo.png"
        sp = filedialog.asksaveasfilename(title="Save ASCII as PNG...", initialfile=dpn, defaultextension=".png", filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg *.jpeg"), ("All Files", "*.*")])
        if not sp:
            self.append_system_log("Save PNG cancelled by user.", "warn"); return
        m = self.color_mode.get()
        cmap = {"Green": "#16A34A", "Cyan": "#0284C7", "Pink": "#DC2626", "Red": "#DC2626", "Amber": "#D97706", "Lime": "#059669", "Violet": "#7C3AED", "Blue": "#2563EB", "Orange": "#EA580C", "White": "#1E293B"} if self.current_theme == "Light" else {"Green": "#9ECE6A", "Cyan": "#7DCFFF", "Pink": "#F7768E", "Red": "#F7768E", "Amber": "#E0AF68", "Lime": "#73DACA", "Violet": "#BB9AF7", "Blue": "#7AA2F7", "Orange": "#FF9E64", "White": "#C0CAF5"}
        try:
            save_ascii_as_image(ascii_content=self.current_ascii_text, output_path=sp, bg_color=self.colors["bg_surface"], text_color=cmap.get(m, "#9ECE6A"), gui_preview_data=self.current_gui_preview if m == "Color" else None)
            self.append_system_log(f"Photo exported to: {os.path.basename(sp)}", "info")
        except Exception as e:
            self.append_system_log(f"Save PNG error: {e}", "err"); messagebox.showerror("Error", f"Failed:\n{e}")

    def convert_image_process(self):
        fp = filedialog.askopenfilename(title="Select Source Image", filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.jfif"), ("All Files", "*.*")])
        if not fp: self.append_system_log("Process aborted by user.", "warn"); return
        self.last_converted_basename = os.path.splitext(os.path.basename(fp))[0]
        self.append_system_log(f"Target file loaded: {os.path.basename(fp)}", "info")
        m, tt = self.color_mode.get(), self.transparent_target.get()
        sp = filedialog.asksaveasfilename(title="Save ASCII Output...", initialfile=f"{self.last_converted_basename}_ascii.txt", defaultextension=".txt", filetypes=[("Text File", "*.txt")])
        if not sp: self.append_system_log("Export directory selection cancelled.", "warn"); return
        if self.overdrive_mode.get():
            try:
                tw = int(self.entry_overdrive.get().strip())
                if tw <= 0: raise ValueError
            except ValueError:
                self.append_system_log("Invalid Overdrive value! Reverting to default slider width.", "err")
                tw = round(float(self.slider_width.get()))
        else: tw = round(float(self.slider_width.get()))
        tth = round(float(self.slider_thresh.get())); self.btn_top_load.configure(state="disabled")
        self.append_system_log(f"Rendering ASCII ({MAX_WORKERS} Threads)... [W: {tw}px, Cutoff: {tth}%]", "info")

        def process_thread():
            try:
                txt_res, gui_data, pimg = "", None, None
                if m == "Color":
                    txt_res, gui_data = convert_image_to_fullcolor(fp, size_txt=tw, num_workers=MAX_WORKERS)
                    pimg = render_gui_preview_to_image(gui_data, bg_color=self.colors["bg_surface"])
                else:
                    txt_res = convert_image_to_ascii_str(fp, new_width=tw, transparent_target=tt)
                with open(sp, "w", encoding="utf-8") as f: f.write(txt_res)

                def on_success():
                    self.current_ascii_text, self.current_gui_preview = txt_res, gui_data
                    self.append_system_log(f"Render output written to: {os.path.basename(sp)}", "info")
                    cmap = {"Green": "#16A34A", "Cyan": "#0284C7", "Pink": "#DC2626", "Red": "#DC2626", "Amber": "#D97706", "Lime": "#059669", "Violet": "#7C3AED", "Blue": "#2563EB", "Orange": "#EA580C", "White": "#1E293B"} if self.current_theme == "Light" else {"Green": "#9ECE6A", "Cyan": "#7DCFFF", "Pink": "#F7768E", "Red": "#F7768E", "Amber": "#E0AF68", "Lime": "#73DACA", "Violet": "#BB9AF7", "Blue": "#7AA2F7", "Orange": "#FF9E64", "White": "#C0CAF5"}
                    self.update_idletasks(); pbw = max(800, self.winfo_width() - 80)
                    if m in cmap:
                        self.scroll_preview.pack_forget(); self.txt_ascii.pack(fill="both", expand=True, padx=12, pady=10)
                        dfs = max(2, min(8, int(pbw / (tw * 0.65))))
                        self.txt_ascii.configure(state="normal", font=("Consolas", dfs))
                        self.txt_ascii.delete("1.0", tk.END); self.txt_ascii.tag_config("center", justify="center")
                        self.txt_ascii.configure(fg=cmap[m]); self.txt_ascii.insert("1.0", txt_res); self.txt_ascii.tag_add("center", "1.0", "end")
                        self.txt_ascii.configure(state="disabled")
                    elif m == "Color" and pimg:
                        self.txt_ascii.pack_forget(); self.scroll_preview.pack(fill="both", expand=True, padx=12, pady=10)
                        iw, ih = pimg.size
                        if iw > pbw:
                            sf = pbw / float(iw)
                            dimg = pimg.resize((max(1, int(iw * sf)), max(1, int(ih * sf))), Image.Resampling.LANCZOS)
                        else: dimg = pimg
                        self.preview_photo_img = ImageTk.PhotoImage(dimg)
                        self.lbl_preview_img.configure(image=self.preview_photo_img, text="")
                    self.btn_top_load.configure(state="normal"); self.append_system_log("GUI Preview rendering completed smoothly.", "info")

                self.after(0, on_success)
            except Exception as e:
                emsg = str(e)
                def on_error():
                    self.append_system_log(f"Render Error: {emsg}", "err")
                    messagebox.showerror("Terminal Error", f"Process failed:\n{emsg}")
                    self.btn_top_load.configure(state="normal")
                self.after(0, on_error)

        threading.Thread(target=process_thread, daemon=True).start()

if __name__ == "__main__":
    multiprocessing.freeze_support(); app = AsciiArtAppCTk()
    try: app.mainloop()
    except KeyboardInterrupt: pass
