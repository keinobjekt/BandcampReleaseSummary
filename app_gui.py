"""
Simple GUI wrapper to run the Bandcamp release dashboard generator with
date pickers and a built-in embed proxy.
"""

from __future__ import annotations

import argparse
import datetime
import threading
import webbrowser
from pathlib import Path
from tkinter import Tk, StringVar, IntVar, Toplevel, Button, Label, Entry, messagebox

from tkcalendar import Calendar

from embed_proxy import app as proxy_app
from BandcampReleaseSummary import construct_release_list, write_release_dashboard
from gmail import gmail_authenticate, search_messages, get_messages


PROXY_PORT = 5050

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


def run_pipeline(after_date: str, before_date: str, max_results: int, proxy_port: int):
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_dir_name = OUTPUT_DIR / f'bandcamp_listings_{after_date.replace("/","-")}_to_{before_date.replace("/","-")}_max_{max_results}'
    output_dir_name.mkdir(exist_ok=True)

    service = gmail_authenticate()
    search_query = f"from:noreply@bandcamp.com subject:'New release from' before:{before_date} after:{after_date}"
    message_ids = search_messages(service, search_query, max_results=max_results)
    emails = get_messages(service, [msg["id"] for msg in message_ids], "full", batch_size=20)
    releases = construct_release_list(emails)
    output_file = write_release_dashboard(
        releases=releases,
        output_path=output_dir_name / "output.html",
        title="Bandcamp Release Dashboard",
        fetch_missing_ids=False,
        embed_proxy_url=f"http://localhost:{proxy_port}/embed-meta",
    )
    webbrowser.open_new_tab(output_file.resolve().as_uri())


def main():
    root = Tk()
    root.title("Bandcamp Release Dashboard")

    start_date_var = StringVar(value=datetime.date.today().strftime("%Y/%m/%d"))
    end_date_var = StringVar(value=datetime.date.today().strftime("%Y/%m/%d"))
    max_results_var = IntVar(value=500)

    def label_row(text, var, row):
        Label(root, text=text).grid(row=row, column=0, padx=8, pady=6, sticky="w")
        Entry(root, textvariable=var, width=15).grid(row=row, column=1, padx=8, pady=6, sticky="w")

    label_row("Start date (YYYY/MM/DD)", start_date_var, 0)
    Button(root, text="Pick", command=lambda: start_date_var.set(pick_date("Select start date", datetime.date.today()))).grid(row=0, column=2, padx=8)

    label_row("End date (YYYY/MM/DD)", end_date_var, 1)
    Button(root, text="Pick", command=lambda: end_date_var.set(pick_date("Select end date", datetime.date.today()))).grid(row=1, column=2, padx=8)

    label_row("Max results (<=2000)", max_results_var, 2)

    proxy_thread = None
    proxy_port = PROXY_PORT

    def on_run():
        nonlocal proxy_thread, proxy_port
        try:
            max_results = min(int(max_results_var.get()), MAX_RESULTS_HARD)
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

        if proxy_thread is None or not proxy_thread.is_alive():
            proxy_thread, proxy_port = start_proxy_thread()

        try:
            run_pipeline(start_date_var.get(), end_date_var.get(), max_results, proxy_port)
            messagebox.showinfo("Done", "Dashboard generated and opened in browser.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    Button(root, text="Run", command=on_run).grid(row=3, column=0, columnspan=3, pady=12)

    root.mainloop()


if __name__ == "__main__":
    main()
