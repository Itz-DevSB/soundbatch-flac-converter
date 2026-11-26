"""Bulk audio-to-FLAC converter for Windows. Requires FFmpeg on PATH."""
from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

EXTS = {".mp3", ".aac", ".m4a", ".mp4", ".ogg", ".oga", ".opus", ".wma", ".wav", ".aiff", ".aif", ".alac", ".ape", ".wv", ".flac", ".mka", ".m4b", ".caf", ".amr", ".ac3", ".dts", ".tta"}


class Converter:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("SoundBatch — FLAC Converter")
        root.geometry("850x600")
        root.minsize(700, 500)
        self.files: dict[Path, Path] = {}
        self.events: queue.Queue[tuple] = queue.Queue()
        self.cancel_event = threading.Event()
        self.process: subprocess.Popen | None = None
        self.running = False
        self.output = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self._ui()
        root.after(100, self._poll)
        root.protocol("WM_DELETE_WINDOW", self._close)

    def _ui(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame", background="#111821")
        s.configure("Card.TFrame", background="#1b2633")
        s.configure("TLabel", background="#111821", foreground="#edf2f8", font=("Segoe UI", 10))
        s.configure("Muted.TLabel", foreground="#aab7c7")
        s.configure("Title.TLabel", font=("Segoe UI", 23, "bold"), foreground="#f5f8fc")
        s.configure("TButton", padding=8, font=("Segoe UI", 10))
        s.configure("Accent.TButton", background="#6b8cff", foreground="white", font=("Segoe UI", 10, "bold"))
        s.configure("Treeview", background="#141d28", fieldbackground="#141d28", foreground="#edf2f8", rowheight=27)
        s.configure("Treeview.Heading", background="#283646", foreground="#edf2f8")
        s.configure("Horizontal.TProgressbar", background="#6b8cff", troughcolor="#283646")
        main = ttk.Frame(self.root, padding=22); main.pack(fill="both", expand=True)
        ttk.Label(main, text="SoundBatch", style="Title.TLabel").pack(anchor="w")
        ttk.Label(main, text="Bulk convert audio folders to FLAC.", style="Muted.TLabel").pack(anchor="w", pady=(0, 14))
        card = ttk.Frame(main, style="Card.TFrame", padding=15); card.pack(fill="both", expand=True)
        row = ttk.Frame(card, style="Card.TFrame"); row.pack(fill="x")
        ttk.Button(row, text="Add folder", command=self.add_folder).pack(side="left")
        ttk.Button(row, text="Add files", command=self.add_files).pack(side="left", padx=7)
        ttk.Button(row, text="Remove selected", command=self.remove).pack(side="left")
        ttk.Button(row, text="Clear list", command=self.clear).pack(side="right")
        self.tree = ttk.Treeview(card, columns=("name", "format", "folder"), show="headings", selectmode="extended")
        for col, title, width in (("name", "FILE", 260), ("format", "FORMAT", 90), ("folder", "SOURCE FOLDER", 400)):
            self.tree.heading(col, text=title); self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, pady=(12, 6))
        self.count = ttk.Label(card, text="0 files", style="Muted.TLabel"); self.count.pack(anchor="w", pady=(0, 12))
        ttk.Label(card, text="OUTPUT FOLDER", style="Muted.TLabel").pack(anchor="w")
        out = ttk.Frame(card, style="Card.TFrame"); out.pack(fill="x", pady=(5, 14))
        ttk.Entry(out, textvariable=self.output).pack(side="left", fill="x", expand=True, ipady=5)
        ttk.Button(out, text="Choose…", command=self.choose_output).pack(side="left", padx=(7, 0))
        self.progress = ttk.Progressbar(card, mode="determinate"); self.progress.pack(fill="x", pady=(0, 8))
        bottom = ttk.Frame(card, style="Card.TFrame"); bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status, style="Muted.TLabel").pack(side="left")
        self.cancel_btn = ttk.Button(bottom, text="Cancel", command=self.cancel, state="disabled"); self.cancel_btn.pack(side="right", padx=7)
        self.start_btn = ttk.Button(bottom, text="Convert to FLAC", style="Accent.TButton", command=self.start); self.start_btn.pack(side="right")
        ttk.Label(main, text="Original files are kept. Converting lossy audio to FLAC cannot restore lost sound detail.", style="Muted.TLabel").pack(anchor="w", pady=(10, 0))

    def _add(self, src: Path, rel: Path) -> bool:
        try: key = src.resolve()
        except OSError: key = src.absolute()
        if key in self.files: return False
        self.files[key] = rel.with_suffix(".flac")
        return True

    def add_folder(self):
        chosen = filedialog.askdirectory(title="Choose an audio folder")
        if not chosen: return
        folder = Path(chosen)
        out = Path(self.output.get()).resolve() if self.output.get().strip() else None
        added = 0
        for current, dirs, names in os.walk(folder):
            here = Path(current)
            dirs[:] = [d for d in dirs if not (here / d).is_symlink() and not (out and self._inside(here / d, out))]
            for name in names:
                src = here / name
                if src.suffix.lower() not in EXTS or src.suffix.lower() == ".flac" or (out and self._inside(src, out)): continue
                if self._add(src, src.relative_to(folder)): added += 1
        self.refresh(); self.status.set(f"Added {added} files from {folder.name}")

    def add_files(self):
        chosen = filedialog.askopenfilenames(title="Choose audio files", filetypes=[("Audio files", " ".join("*" + e for e in sorted(EXTS))), ("All files", "*.*")])
        n = 0
        for name in chosen:
            src = Path(name)
            if src.suffix.lower() in EXTS and src.suffix.lower() != ".flac" and self._add(src, Path(src.name)): n += 1
        self.refresh(); self.status.set(f"Added {n} files")

    @staticmethod
    def _inside(path: Path, parent: Path) -> bool:
        try: path.resolve().relative_to(parent.resolve()); return True
        except (ValueError, OSError): return False

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for src, rel in self.files.items(): self.tree.insert("", "end", iid=str(src), values=(src.name, src.suffix[1:].upper(), str(rel.parent)))
        n = len(self.files); self.count.config(text=f"{n} audio file{'s' if n != 1 else ''}")

    def choose_output(self):
        p = filedialog.askdirectory(title="Choose output folder", initialdir=self.output.get() or None)
        if p: self.output.set(p)

    def remove(self):
        for item in self.tree.selection(): self.files.pop(Path(item), None)
        self.refresh()

    def clear(self):
        self.files.clear(); self.refresh(); self.status.set("List cleared")

    def start(self):
        if self.running: return
        if not self.files: messagebox.showinfo("SoundBatch", "Add an audio folder or files first."); return
        if not self.output.get().strip(): messagebox.showinfo("SoundBatch", "Choose an output folder first."); return
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg: messagebox.showerror("SoundBatch", "FFmpeg was not found. Install it and restart this app. See README.md."); return
        output = Path(self.output.get()).expanduser()
        try: output.mkdir(parents=True, exist_ok=True)
        except OSError as exc: messagebox.showerror("SoundBatch", f"Could not use output folder:\n{exc}"); return
        self.running = True; self.cancel_event.clear(); self.start_btn.config(state="disabled"); self.cancel_btn.config(state="normal")
        items = list(self.files.items()); self.progress.config(value=0, maximum=len(items))
        threading.Thread(target=self._worker, args=(items, output, ffmpeg), daemon=True).start()

    def _worker(self, items, output, ffmpeg):
        done = skipped = failed = 0; errors = []
        for src, rel in items:
            if self.cancel_event.is_set(): break
            dst = output / rel; tmp = dst.with_name("." + dst.stem + ".partial.flac")
            if dst.exists(): skipped += 1; done += 1; self.events.put((done, len(items), f"Skipped existing: {dst.name}")); continue
            try:
                dst.parent.mkdir(parents=True, exist_ok=True); tmp.unlink(missing_ok=True)
                args = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-map", "0:a:0", "-map_metadata", "0", "-vn", "-c:a", "flac", "-compression_level", "8", str(tmp)]
                self.process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                while self.process.poll() is None:
                    if self.cancel_event.wait(.1):
                        self.process.terminate()
                        try: self.process.wait(timeout=2)
                        except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
                        break
                err = self.process.stderr.read() if self.process.stderr else ""; code = self.process.wait(); self.process = None
                if self.cancel_event.is_set(): tmp.unlink(missing_ok=True); break
                if code: raise RuntimeError(err.strip() or f"FFmpeg exited with code {code}")
                if not tmp.exists() or tmp.stat().st_size == 0: raise RuntimeError("FFmpeg made no output file")
                if dst.exists(): skipped += 1; tmp.unlink(missing_ok=True)
                else: tmp.replace(dst)
            except Exception as exc:
                if self.process:
                    try: self.process.kill()
                    except OSError: pass
                    self.process = None
                tmp.unlink(missing_ok=True); failed += 1; errors.append(f"{src.name}: {exc}")
            done += 1; self.events.put((done, len(items), f"Processed {src.name}"))
        self.events.put(("finished", done, len(items), skipped, failed, self.cancel_event.is_set(), errors))

    def cancel(self):
        if self.running: self.cancel_event.set(); self.cancel_btn.config(state="disabled"); self.status.set("Cancelling current file…")

    def _poll(self):
        try:
            while True:
                ev = self.events.get_nowait()
                if ev[0] == "finished":
                    _, done, total, skipped, failed, cancelled, errors = ev
                    self.running = False; self.process = None; self.start_btn.config(state="normal"); self.cancel_btn.config(state="disabled")
                    self.status.set(f"Cancelled after {done}/{total}" if cancelled else f"Finished · {done-skipped} converted · {skipped} skipped · {failed} failed")
                    if errors: messagebox.showwarning("SoundBatch", "Some files could not be converted:\n\n" + "\n".join(errors[:8]))
                else:
                    done, total, msg = ev; self.progress.config(value=done, maximum=max(total, 1)); self.status.set(f"{msg} · {done}/{total}")
        except queue.Empty: pass
        self.root.after(100, self._poll)

    def _close(self):
        if self.running:
            self.cancel_event.set()
            if self.process and self.process.poll() is None:
                try: self.process.terminate()
                except OSError: pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk(); Converter(root); root.mainloop()

