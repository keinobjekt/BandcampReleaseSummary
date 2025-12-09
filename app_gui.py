"""
Simple GUI wrapper to run the Bandcamp release dashboard generator with
date pickers and a built-in embed proxy.
"""

from __future__ import annotations

import argparse
import datetime
import threading
import webbrowser
import sys
import json
from pathlib import Path
from tkinter import Tk, StringVar, IntVar, Toplevel, Button, Label, Entry, Frame, messagebox
from tkinter.scrolledtext import ScrolledText

from tkcalendar import Calendar

from embed_proxy import app as proxy_app
from BandcampReleaseSummary import gather_releases_with_cache, write_release_dashboard

MULTITHREADING = True
PROXY_PORT = 5050
SETTINGS_PATH = Path("data") / "gui_settings.json"

def find_free_port(preferred: int = 5050) -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", preferred))
            return preferred
        except OSError:
            s.bind(("", 0))
            return s.getsockname()[1]
MAX_RESULTS_HARD = 2000
OUTPUT_DIR = Path("output")


def load_settings():
    try:
        if SETTINGS_PATH.exists():
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_settings(settings: dict):
    SETTINGS_PATH.parent.mkdir(exist_ok=True)
    tmp = SETTINGS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_PATH)


def start_proxy_thread():
    def _run(port):
        proxy_app.run(host="0.0.0.0", port=port)

    port = find_free_port(PROXY_PORT)
    t = threading.Thread(target=_run, args=(port,), daemon=True)
    t.start()
    return t, port


def pick_date(title: str, initial: datetime.date) -> str:
    top = Toplevel()
    top.title(title)
    selected = StringVar(value=initial.strftime("%Y/%m/%d"))

    cal = Calendar(top, selectmode="day", year=initial.year, month=initial.month, day=initial.day, date_pattern="yyyy/mm/dd")
    cal.pack(padx=10, pady=10)

    def on_ok():
        selected.set(cal.get_date())
        top.destroy()

    Button(top, text="OK", command=on_ok).pack(pady=5)
    top.transient()
    top.grab_set()
    top.wait_window()
    return selected.get()


def run_pipeline(after_date: str, before_date: str, max_results: int, proxy_port: int, preload_embeds: bool, *, log=print):
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_dir_name = OUTPUT_DIR / f'bandcamp_listings_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}'
    output_dir_name.mkdir(exist_ok=True)

    releases = gather_releases_with_cache(after_date, before_date, max_results, batch_size=20, log=log)
    output_file = write_release_dashboard(
        releases=releases,
        output_path=output_dir_name / "output.html",
        title="Bandcamp Release Dashboard",
        fetch_missing_ids=preload_embeds,
        embed_proxy_url=f"http://localhost:{proxy_port}/embed-meta",
        log=log,
    )
    webbrowser.open_new_tab(output_file.resolve().as_uri())


def main():
    root = Tk()
    root.title("Bandcamp Release Dashboard")
    root.resizable(False, False)

    today = datetime.date.today()
    two_months_ago = today - datetime.timedelta(days=60)
    settings = load_settings()

    def _coerce_max(val, default):
        try:
            return int(val)
        except Exception:
            return default

    start_date_var = StringVar(value=settings.get("start_date") or two_months_ago.strftime("%Y/%m/%d"))
    end_date_var = StringVar(value=settings.get("end_date") or today.strftime("%Y/%m/%d"))
    max_results_var = StringVar(value=str(_coerce_max(settings.get("max_results"), 500)))
    preload_embeds_var = IntVar(value=1 if settings.get("preload_embeds") else 0)

    # Custom layout for date rows to fit compact buttons around the entry
    date_button_sets = []
    date_frame = Frame(root)
    date_frame.grid(row=0, column=0, columnspan=3, padx=6, pady=4, sticky="w")
    for col in range(1, 8):
        date_frame.grid_columnconfigure(col, minsize=34)

    def layout_date_row(label_text: str, var: StringVar, row: int, is_start: bool):
        left_configs = [("<1m", -30), ("<1w", -7), ("<1d", -1)]
        right_configs = [(">1d", 1), (">1w", 7), (">1m", 30)]

        Label(date_frame, text=label_text).grid(row=row, column=0, padx=4, sticky="w")

        def make_btn(col: int, label: str, days: int):
            delta = datetime.timedelta(days=days)
            btn = Button(
                date_frame,
                text=label,
                width=0,  # let the text size drive width
                padx=1,
                pady=0,
                font=("TkDefaultFont", 8),
                command=lambda v=var, d=delta: adjust_date(v, is_start, d) if days !=0 else v.set(today.strftime("%Y/%m/%d")),
            )
            btn.grid(row=row, column=col, padx=1, pady=1, sticky="w")
            date_button_sets.append((btn, delta, is_start))

        col = 1
        for label, days in left_configs:
            make_btn(col, label, days)
            col += 1

        Entry(date_frame, textvariable=var, width=12).grid(row=row, column=4, padx=4, pady=2, sticky="w")
        col = 5
        for label, days in right_configs:
            make_btn(col, label, days)
            col += 1
        if is_start:
            btn = Button(
                date_frame,
                text="Same as end",
                width=12,
                padx=1,
                pady=0,
                font=("TkDefaultFont", 8),
                command=lambda: var.set(end_date_var.get()),
            )
            btn.grid(row=row, column=col, padx=1, pady=1, sticky="w")
            date_button_sets.append((btn, datetime.timedelta(days=0), is_start))
        else:
            btn = Button(
                date_frame,
                text="Same as start",
                width=12,
                padx=1,
                pady=0,
                font=("TkDefaultFont", 8),
                command=lambda: var.set(start_date_var.get()),
            )
            btn.grid(row=row, column=col, padx=1, pady=1, sticky="w")
            date_button_sets.append((btn, datetime.timedelta(days=0), is_start))

    def parse_date_var(var: StringVar, fallback: datetime.date) -> datetime.date:
        try:
            return datetime.datetime.strptime(var.get(), "%Y/%m/%d").date()
        except Exception:
            return fallback

    def can_adjust(is_start: bool, delta: datetime.timedelta) -> bool:
        start_dt = parse_date_var(start_date_var, two_months_ago)
        end_dt = parse_date_var(end_date_var, today)
        new_start = start_dt + delta if is_start else start_dt
        new_end = end_dt + delta if not is_start else end_dt
        if new_start > new_end:
            return False
        if new_start > today or new_end > today:
            return False
        return True

    def adjust_date(var: StringVar, is_start: bool, delta: datetime.timedelta):
        if not can_adjust(is_start, delta):
            return
        current = parse_date_var(var, today if is_start else two_months_ago)
        new_date = current + delta
        if new_date > today:
            new_date = today
        var.set(new_date.strftime("%Y/%m/%d"))

    layout_date_row("Start date (YYYY/MM/DD)", start_date_var, 0, True)
    layout_date_row("End date (YYYY/MM/DD)", end_date_var, 1, False)

    def parse_date_var(var: StringVar, fallback: datetime.date) -> datetime.date:
        try:
            return datetime.datetime.strptime(var.get(), "%Y/%m/%d").date()
        except Exception:
            return fallback

    def can_adjust(is_start: bool, delta: datetime.timedelta) -> bool:
        start_dt = parse_date_var(start_date_var, two_months_ago)
        end_dt = parse_date_var(end_date_var, today)
        new_start = start_dt + delta if is_start else start_dt
        new_end = end_dt + delta if not is_start else end_dt
        if new_start > new_end:
            return False
        if new_start > today or new_end > today:
            return False
        return True

    def adjust_date(var: StringVar, is_start: bool, delta: datetime.timedelta):
        if not can_adjust(is_start, delta):
            return
        current = parse_date_var(var, today if is_start else two_months_ago)
        new_date = current + delta
        # clamp to today
        if new_date > today:
            new_date = today
        var.set(new_date.strftime("%Y/%m/%d"))

    def refresh_date_buttons(*_):
        for btn, delta, is_start in date_button_sets:
            btn_state = "normal" if can_adjust(is_start, delta) else "disabled"
            btn.config(state=btn_state)

    start_date_var.trace_add("write", refresh_date_buttons)
    end_date_var.trace_add("write", refresh_date_buttons)
    refresh_date_buttons()

    # Align max results with date entry column
    max_frame = Frame(root)
    max_frame.grid(row=2, column=0, columnspan=3, padx=6, pady=6, sticky="w")
    for col in range(1, 4):
        max_frame.grid_columnconfigure(col, minsize=34)
    Label(max_frame, text="Max results").grid(row=0, column=0, padx=4, sticky="w")
    Entry(max_frame, textvariable=max_results_var, width=12).grid(row=0, column=4, padx=4, pady=2, sticky="w")

    proxy_thread = None
    proxy_port = PROXY_PORT
    def save_current_settings(*_args):
        try:
            max_val = int(max_results_var.get())
        except Exception:
            max_val = None
        save_settings(
            {
                "start_date": start_date_var.get(),
                "end_date": end_date_var.get(),
                "max_results": max_val if max_val is not None else "",
                "preload_embeds": bool(preload_embeds_var.get()),
            }
        )

    # Toggle defaults
    from tkinter import Checkbutton  # localized import to avoid polluting top
    Checkbutton(root, text="Preload BC players (fetch Bandcamp pages now)", variable=preload_embeds_var).grid(row=3, column=0, columnspan=2, padx=8, sticky="w")


    # Status box
    status_box = ScrolledText(root, width=80, height=12, state="disabled")
    status_box.grid(row=5, column=0, columnspan=3, padx=8, pady=8, sticky="nsew")

    class GuiLogger:
        def __init__(self, callback):
            self.callback = callback

        def write(self, msg):
            if msg.strip():
                self.callback(msg.rstrip())

        def flush(self):
            pass

    def append_log(msg):
        if isinstance(msg, bytes):
            try:
                msg = msg.decode("utf-8", errors="replace")
            except Exception:
                msg = str(msg)
        else:
            msg = str(msg)
        status_box.configure(state="normal")
        status_box.insert("end", msg + "\n")
        status_box.see("end")
        status_box.configure(state="disabled")

    def log(msg: str):
        # marshal to UI thread
        root.after(0, append_log, msg)

    # Persist settings whenever inputs change
    for var in (start_date_var, end_date_var):
        var.trace_add("write", save_current_settings)
    for var in (max_results_var, preload_embeds_var):
        var.trace_add("write", save_current_settings)

    def on_run():
        nonlocal proxy_thread, proxy_port
        try:
            max_results = int(max_results_var.get())
            if max_results > MAX_RESULTS_HARD:
                messagebox.showerror("Error", f"Max results cannot exceed {MAX_RESULTS_HARD}")
                return
        except ValueError:
            messagebox.showerror("Error", "Max results must be a number")
            return
        try:
            # validate dates
            for val in (start_date_var.get(), end_date_var.get()):
                datetime.datetime.strptime(val, "%Y/%m/%d")
        except ValueError:
            messagebox.showerror("Error", "Dates must be in YYYY/MM/DD format")
            return

        should_preload = bool(preload_embeds_var.get())
        if proxy_thread is None or not proxy_thread.is_alive():
            proxy_thread, proxy_port = start_proxy_thread()

        def worker():
            try:
                original_stdout = sys.stdout
                logger = GuiLogger(log)
                sys.stdout = logger
                
                log(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                log(f"Starting Bandcamp Release Dashboard generation...")
                log(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                log(f"")
                log(f"Running query from {start_date_var.get()} to {end_date_var.get()} with max {max_results} (proxy port {proxy_port}, preload {'on' if should_preload else 'off'})")
                
                try:
                    run_pipeline(start_date_var.get(), end_date_var.get(), max_results, proxy_port, should_preload, log=log)
                    log("Dashboard generated and opened in browser.")
                    log("")
                    root.after(0, lambda: messagebox.showinfo("Done", "Dashboard generated and opened in browser."))
                finally:
                    sys.stdout = original_stdout
            except Exception as exc:
                log(f"Error: {exc}")
                root.after(0, lambda exc=exc: messagebox.showerror("Error", str(exc)))

        if MULTITHREADING:
            threading.Thread(target=worker, daemon=True).start()
        else:
            worker()
            
    Button(root, text="Run", command=on_run).grid(row=4, column=0, columnspan=3, pady=12)

    from tkinter import Checkbutton  # localized import to avoid polluting top
    root.mainloop()


if __name__ == "__main__":
    main()
