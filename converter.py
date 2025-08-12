#!/usr/bin/env python3
# converter.py — Light theme, DnD, visible Convert button, DPI fix
import sys, threading
from pathlib import Path
from typing import List, Optional

# Windows DPI awareness to avoid blurry UI
try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image

# AVIF plugin registers on import
try:
    import pillow_avif  # noqa: F401
except ImportError:
    messagebox.showerror("Missing plugin", "Install Pillow and pillow-avif-plugin:\n\npip install pillow pillow-avif-plugin")
    sys.exit(1)

# Optional drag and drop
_HAS_DND = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # pip install tkinterdnd2
    _HAS_DND = True
except Exception:
    TkinterDnD = object  # fallback

COMMON_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}

def collect_images(src: Path, recursive: bool) -> List[Path]:
    if src.is_file():
        return [src] if src.suffix.lower() in COMMON_EXTS else []
    if not src.is_dir():
        return []
    it = src.rglob("*") if recursive else src.glob("*")
    return sorted([p for p in it if p.is_file() and p.suffix.lower() in COMMON_EXTS])

def prepare_mode(im: Image.Image) -> Image.Image:
    return im.convert("RGBA") if im.mode in ("RGBA", "LA") else im.convert("RGB")

def save_avif(im: Image.Image, out_path: Path, quality: int, speed: int, lossless: bool, keep_exif: bool):
    params = {"format": "AVIF", "quality": quality, "speed": speed, "lossless": lossless}
    if keep_exif and "exif" in im.info:
        params["exif"] = im.info["exif"]
    if "icc_profile" in im.info:
        params["icc_profile"] = im.info["icc_profile"]
    im.save(out_path, **params)

def convert_one(src: Path, dst_dir: Path, overwrite: bool, quality: int, speed: int, lossless: bool, keep_exif: bool, prefix: Optional[str]) -> Optional[str]:
    try:
        with Image.open(src) as im:
            im.load()
            im2 = prepare_mode(im)
    except Exception as e:
        return f"Skip {src.name}: {e}"
    stem = f"{prefix}_{src.stem}" if prefix else src.stem
    out = dst_dir / f"{stem}.avif"
    if out.exists() and not overwrite:
        n = 2
        while True:
            cand = dst_dir / f"{stem}_{n}.avif"
            if not cand.exists():
                out = cand
                break
            n += 1
    try:
        save_avif(im2, out, quality, speed, lossless, keep_exif)
        return None
    except Exception as e:
        return f"Failed {src.name}: {e}"

class App((TkinterDnD if _HAS_DND else tk).Tk):
    def __init__(self):
        super().__init__()
        self.title("AVIF Converter")
        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass
        self.minsize(880, 560)
        self.geometry("940x620")
        self.resizable(True, True)

        # Vars
        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.keep_exif_var = tk.BooleanVar(value=True)
        self.lossless_var = tk.BooleanVar(value=False)
        self.quality_var = tk.IntVar(value=80)
        self.speed_var = tk.IntVar(value=6)
        self.prefix_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Idle")

        self._build_menu()
        self._build_ui()
        self.bind("<Control-Return>", lambda e: self.start_conversion())

    def _build_menu(self):
        m = tk.Menu(self)
        act = tk.Menu(m, tearoff=0)
        act.add_command(label="Convert    Ctrl+Enter", command=self.start_conversion)
        act.add_separator()
        act.add_command(label="Quit", command=self.destroy)
        m.add_cascade(label="Actions", menu=act)
        self.config(menu=m)

    def _build_ui(self):
        pad = {"padx": 12, "pady": 8}

        # Source
        frm_src = ttk.LabelFrame(self, text="Source")
        frm_src.pack(fill="x", **pad)
        row_src = ttk.Frame(frm_src); row_src.pack(fill="x", pady=4)
        ttk.Entry(row_src, textvariable=self.src_var).pack(side="left", fill="x", expand=True)
        ttk.Button(row_src, text="Browse file", command=self.browse_src_file).pack(side="left", padx=6)
        ttk.Button(row_src, text="Pick folder", command=self.pick_src_folder).pack(side="left")
        self.src_drop = tk.Label(frm_src, text="Drop a file or folder here", relief="groove", height=2, anchor="center")
        self.src_drop.pack(fill="x", pady=6)

        # Destination
        frm_dst = ttk.LabelFrame(self, text="Destination")
        frm_dst.pack(fill="x", **pad)
        row_dst = ttk.Frame(frm_dst); row_dst.pack(fill="x", pady=4)
        ttk.Entry(row_dst, textvariable=self.dst_var).pack(side="left", fill="x", expand=True)
        ttk.Button(row_dst, text="Pick folder", command=self.pick_dst_folder).pack(side="left", padx=6)
        self.dst_drop = tk.Label(frm_dst, text="Drop a folder here", relief="groove", height=2, anchor="center")
        self.dst_drop.pack(fill="x", pady=6)

        # Options
        frm_opts = ttk.LabelFrame(self, text="Options")
        frm_opts.pack(fill="x", **pad)
        left = ttk.Frame(frm_opts); left.pack(side="left", fill="x", expand=True)
        ttk.Checkbutton(left, text="Recursive", variable=self.recursive_var).pack(anchor="w")
        ttk.Checkbutton(left, text="Overwrite", variable=self.overwrite_var).pack(anchor="w")
        ttk.Checkbutton(left, text="Keep EXIF and ICC", variable=self.keep_exif_var).pack(anchor="w")
        ttk.Checkbutton(left, text="Lossless", variable=self.lossless_var).pack(anchor="w")
        right = ttk.Frame(frm_opts); right.pack(side="left", fill="x", expand=True)
        r1 = ttk.Frame(right); r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="Quality 0..100").pack(side="left")
        ttk.Spinbox(r1, from_=0, to=100, textvariable=self.quality_var, width=6).pack(side="left", padx=8)
        r2 = ttk.Frame(right); r2.pack(fill="x", pady=2)
        ttk.Label(r2, text="Speed 0..10").pack(side="left")
        ttk.Spinbox(r2, from_=0, to=10, textvariable=self.speed_var, width=6).pack(side="left", padx=16)
        r3 = ttk.Frame(right); r3.pack(fill="x", pady=2)
        ttk.Label(r3, text="Filename prefix").pack(side="left")
        ttk.Entry(r3, textvariable=self.prefix_var, width=24).pack(side="left", padx=8)

        # Progress + status
        frm_prog = ttk.Frame(self); frm_prog.pack(fill="x", **pad)
        self.prog = ttk.Progressbar(frm_prog, mode="determinate"); self.prog.pack(fill="x")
        ttk.Label(frm_prog, textvariable=self.status_var).pack(anchor="w", pady=(6, 0))

        # Bottom buttons, pinned to bottom
        frm_btn = ttk.Frame(self)
        frm_btn.pack(fill="x", side="bottom", padx=12, pady=12)
        self.btn_convert = ttk.Button(frm_btn, text="Convert", command=self.start_conversion)
        self.btn_convert.pack(side="left")
        ttk.Button(frm_btn, text="Quit", command=self.destroy).pack(side="right")

        # DnD
        if _HAS_DND:
            for w in (self.src_drop, self.dst_drop):
                w.drop_target_register(DND_FILES)
            self.src_drop.dnd_bind("<<Drop>>", self._on_drop_src)
            self.dst_drop.dnd_bind("<<Drop>>", self._on_drop_dst)

    # Pickers
    def browse_src_file(self):
        p = filedialog.askopenfilename(title="Select a file")
        if p: self.src_var.set(p)

    def pick_src_folder(self):
        p = filedialog.askdirectory(title="Select source folder")
        if p: self.src_var.set(p)

    def pick_dst_folder(self):
        p = filedialog.askdirectory(title="Select destination folder")
        if p: self.dst_var.set(p)

    # DnD handlers
    def _split_dnd_paths(self, data: str) -> List[str]:
        try:
            return [str(p) for p in self.tk.splitlist(data)]
        except Exception:
            return [data]

    def _on_drop_src(self, event):
        paths = self._split_dnd_paths(event.data)
        if paths: self.src_var.set(paths[0])

    def _on_drop_dst(self, event):
        paths = self._split_dnd_paths(event.data)
        if not paths: return
        p = Path(paths[0])
        self.dst_var.set(str(p if p.is_dir() else p.parent))

    # Convert
    def start_conversion(self):
        src = Path(self.src_var.get().strip()).expanduser()
        dst = Path(self.dst_var.get().strip()).expanduser()
        if not src.exists():
            messagebox.showerror("Error", "Pick a valid source file or folder")
            return
        if not dst:
            messagebox.showerror("Error", "Pick a destination folder")
            return
        dst.mkdir(parents=True, exist_ok=True)

        recursive = self.recursive_var.get()
        overwrite = self.overwrite_var.get()
        keep_exif = self.keep_exif_var.get()
        lossless = self.lossless_var.get()
        quality = int(self.quality_var.get())
        speed = int(self.speed_var.get())
        prefix = self.prefix_var.get().strip() or None

        items = collect_images(src, recursive=recursive)
        if not items:
            messagebox.showinfo("Nothing to do", "No supported images found")
            return

        self.btn_convert.config(state="disabled")
        self.prog.config(value=0, maximum=len(items))
        self.status_var.set(f"Converting {len(items)} file(s)...")

        def worker():
            errors = 0
            for i, item in enumerate(items, start=1):
                msg = convert_one(item, dst, overwrite, quality, speed, lossless, keep_exif, prefix)
                self.prog.after(0, lambda v=i: self.prog.config(value=v))
                if msg: errors += 1
                self.status_var.set(f"{i}/{len(items)}")
            self.status_var.set(f"Done. {len(items)-errors} succeeded, {errors} failed. Output: {dst}")
            self.btn_convert.after(0, lambda: self.btn_convert.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    App().mainloop()
