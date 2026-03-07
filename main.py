"""
GitPulse — Keep your graph alive.
Persistently links to a local Git repo and pushes timestamped
commits on a randomized 30-60 minute schedule.
"""

import json
import os
import random
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Button, Text, Scrollbar,
    filedialog, messagebox, END, DISABLED, NORMAL, RIGHT, LEFT,
    TOP, BOTTOM, BOTH, Y, X, W, E, N, S, StringVar
)

# ── Paths ────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # Built via PyInstaller: look next to the .exe
    APP_DIR = Path(sys.executable).parent
else:
    # Normal Python run: look next to the script
    APP_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = APP_DIR / "config.json"

# ── Colour palette (dark theme) ─────────────────────────────────────
BG           = "#1e1e1e"
BG_SECONDARY = "#262626"
BG_CARD      = "#2d2d2d"
FG           = "#e0e0e0"
FG_DIM       = "#808080"
GREEN        = "#39d353"     # GitHub contribution green
GREEN_HOVER  = "#2ea043"
GREEN_FAINT  = "#0e4429"
RED          = "#f85149"
YELLOW       = "#e3b341"
BORDER       = "#3d3d3d"
FONT_FAMILY  = "Segoe UI"


# ═══════════════════════════════════════════════════════════════════════
#  Config persistence
# ═══════════════════════════════════════════════════════════════════════
def load_config() -> dict | None:
    """Return saved config dict or None."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "repo_path" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


def save_config(repo_path: str) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"repo_path": repo_path}, f, indent=2)


def clear_config() -> None:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


# ═══════════════════════════════════════════════════════════════════════
#  Repository helpers
# ═══════════════════════════════════════════════════════════════════════
def is_git_repo(path: str) -> bool:
    return (Path(path) / ".git").is_dir()


def repo_display_name(path: str) -> str:
    return Path(path).name


# ═══════════════════════════════════════════════════════════════════════
#  Git operations
# ═══════════════════════════════════════════════════════════════════════
def run_git(args: list[str], cwd: str) -> tuple[bool, str]:
    """Run a git command; return (success, output)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except FileNotFoundError:
        return False, "git is not installed or not in PATH."
    except subprocess.TimeoutExpired:
        return False, "git command timed out."
    except Exception as exc:
        return False, str(exc)


def gitpulse_cycle(repo_path: str, log_callback) -> bool:
    """
    Perform one full pulse cycle:
      1. Append timestamp to activity_log.txt
      2. git pull → git add → git commit → git push
    Returns True on success.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    log_file = Path(repo_path) / "activity_log.txt"

    # Append timestamp
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] routine maintenance\n")
        log_callback(f"📝  Appended timestamp: {timestamp}")
    except OSError as exc:
        log_callback(f"❌  Failed to write activity_log.txt: {exc}")
        return False

    # Git sequence
    steps = [
        (["pull"],                                      "pull"),
        (["add", "activity_log.txt"],                   "add"),
        (["commit", "-m",
          f"update: routine maintenance {timestamp}"],  "commit"),
        (["push"],                                      "push"),
    ]

    for args, label in steps:
        ok, output = run_git(args, repo_path)
        if ok:
            log_callback(f"✅  git {label}")
        else:
            log_callback(f"⚠️  git {label} failed — {output}")
            if label == "commit" and "nothing to commit" in output.lower():
                log_callback("   (nothing new to commit, skipping push)")
                return True
            return False

    return True


# ═══════════════════════════════════════════════════════════════════════
#  GUI Application
# ═══════════════════════════════════════════════════════════════════════
class GitPulseApp:
    """Main application window."""

    def __init__(self):
        self.repo_path: str | None = None
        self.running: bool = False
        self._timer: threading.Timer | None = None
        self._next_run_epoch: float = 0
        self._countdown_after_id = None
        self._pulse_count = 0

        # ── Root window ──────────────────────────────────────────────
        self.root = Tk()
        self.root.title("GitPulse")
        self.root.configure(bg=BG)
        self.root.minsize(560, 480)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Try to load the icon
        icon_path = APP_DIR / "gitpulse_icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Centre the window
        w, h = 580, 500
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sx-w)//2}+{(sy-h)//2}")

        self._build_ui()

        # ── Load or request config ───────────────────────────────────
        cfg = load_config()
        if cfg and is_git_repo(cfg["repo_path"]):
            self.repo_path = cfg["repo_path"]
            self._set_repo_label()
            self._log("Loaded saved configuration.")
        else:
            if cfg:
                self._log("⚠️  Saved repo path is invalid. Please select a new one.")
            self.root.after(300, self._first_time_setup)

    # ── UI construction ──────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ───────────────────────────────────────────────────
        header = Frame(self.root, bg=BG_SECONDARY, pady=12, padx=18)
        header.pack(fill=X)

        # Pulse icon + title
        title_frame = Frame(header, bg=BG_SECONDARY)
        title_frame.pack(side=LEFT)

        pulse_dot = Label(
            title_frame, text="●", font=(FONT_FAMILY, 14),
            bg=BG_SECONDARY, fg=GREEN,
        )
        pulse_dot.pack(side=LEFT, padx=(0, 6))

        title_lbl = Label(
            title_frame, text="GitPulse", font=(FONT_FAMILY, 17, "bold"),
            bg=BG_SECONDARY, fg=FG,
        )
        title_lbl.pack(side=LEFT)

        tagline = Label(
            title_frame, text="Keep your graph alive.",
            font=(FONT_FAMILY, 9, "italic"), bg=BG_SECONDARY, fg=FG_DIM,
        )
        tagline.pack(side=LEFT, padx=(10, 0))

        self.settings_btn = Button(
            header, text="⚙  Settings", font=(FONT_FAMILY, 9),
            bg=BG_CARD, fg=FG_DIM, activebackground=BORDER,
            activeforeground=FG, bd=0, cursor="hand2",
            padx=10, pady=4, command=self._on_settings,
        )
        self.settings_btn.pack(side=RIGHT)

        # ── Status card ──────────────────────────────────────────────
        status_card = Frame(self.root, bg=BG_CARD, pady=10, padx=18,
                            highlightbackground=BORDER, highlightthickness=1)
        status_card.pack(fill=X, padx=16, pady=(10, 4))

        self.repo_var = StringVar(value="No repository linked")
        self.repo_lbl = Label(
            status_card, textvariable=self.repo_var,
            font=(FONT_FAMILY, 10), bg=BG_CARD, fg=FG_DIM, anchor=W,
        )
        self.repo_lbl.pack(fill=X, side=LEFT)

        self.pulse_count_var = StringVar(value="")
        pulse_count_lbl = Label(
            status_card, textvariable=self.pulse_count_var,
            font=(FONT_FAMILY, 9), bg=BG_CARD, fg=GREEN, anchor=E,
        )
        pulse_count_lbl.pack(side=RIGHT)

        # ── Bottom bar ───────────────────────────────────────────────
        bottom = Frame(self.root, bg=BG, pady=12, padx=16)
        bottom.pack(side=BOTTOM, fill=X)

        self.next_run_var = StringVar(value="")
        self.next_run_lbl = Label(
            bottom, textvariable=self.next_run_var,
            font=(FONT_FAMILY, 10), bg=BG, fg=YELLOW, anchor=W,
        )
        self.next_run_lbl.pack(side=LEFT)

        self.toggle_btn = Button(
            bottom, text="▶  Start", font=(FONT_FAMILY, 11, "bold"),
            bg=GREEN, fg=BG, activebackground=GREEN_HOVER,
            activeforeground=BG, bd=0, padx=24, pady=8,
            cursor="hand2", command=self._toggle,
        )
        self.toggle_btn.pack(side=RIGHT)

        # ── Log area ─────────────────────────────────────────────────
        log_frame = Frame(self.root, bg=BG, padx=16, pady=6)
        log_frame.pack(fill=BOTH, expand=True)

        self.log_text = Text(
            log_frame, bg=BG_SECONDARY, fg=FG, font=("Consolas", 9),
            insertbackground=FG, bd=0, wrap="word",
            highlightthickness=1, highlightbackground=BORDER,
            state=DISABLED, padx=10, pady=8,
        )
        scrollbar = Scrollbar(log_frame, command=self.log_text.yview,
                              bg=BG_SECONDARY, troughcolor=BG)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)

    # ── Repo label helper ────────────────────────────────────────────
    def _set_repo_label(self):
        name = repo_display_name(self.repo_path)
        self.repo_var.set(f"🔗  Linked to: {name}")
        self.repo_lbl.configure(fg=GREEN)

    # ── Logging ──────────────────────────────────────────────────────
    def _log(self, msg: str):
        """Thread-safe log append."""
        def _append():
            self.log_text.configure(state=NORMAL)
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(END, f"[{ts}]  {msg}\n")
            self.log_text.see(END)
            self.log_text.configure(state=DISABLED)

        if threading.current_thread() is threading.main_thread():
            _append()
        else:
            self.root.after(0, _append)

    # ── First time setup ─────────────────────────────────────────────
    def _first_time_setup(self):
        messagebox.showinfo(
            "Welcome to GitPulse",
            "Keep your graph alive.\n\n"
            "Select the folder of your existing GitHub repository to get started.",
        )
        self._select_repo()

    def _select_repo(self):
        while True:
            folder = filedialog.askdirectory(title="Select your Git repository folder")
            if not folder:
                if self.repo_path is None:
                    messagebox.showwarning(
                        "No Repository",
                        "GitPulse needs a linked repository to work.\n"
                        "The app will close.",
                    )
                    self.root.destroy()
                    return
                else:
                    return

            if is_git_repo(folder):
                self.repo_path = folder
                save_config(folder)
                self._set_repo_label()
                self._log(f"Repository set to: {folder}")
                return
            else:
                messagebox.showerror(
                    "Not a Valid Git Repository",
                    f"The selected folder does not contain a .git directory:\n\n"
                    f"{folder}\n\n"
                    "Please select a valid Git repository.",
                )

    # ── Start / Stop toggle ──────────────────────────────────────────
    def _toggle(self):
        if self.repo_path is None:
            messagebox.showwarning("No Repository", "Please link a repository first.")
            return

        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.running = True
        self._pulse_count = 0
        self._update_pulse_count()
        self.toggle_btn.configure(text="⏹  Stop", bg=RED)
        self._log("🚀  GitPulse started — your graph will stay alive.")
        self._schedule_next()

    def _stop(self):
        self.running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        if self._countdown_after_id is not None:
            self.root.after_cancel(self._countdown_after_id)
            self._countdown_after_id = None
        self.toggle_btn.configure(text="▶  Start", bg=GREEN)
        self.next_run_var.set("")
        self._log("⏸  GitPulse stopped.")

    def _schedule_next(self):
        if not self.running:
            return
        delay_minutes = random.randint(30, 60)
        delay_seconds = delay_minutes * 60
        self._next_run_epoch = time.time() + delay_seconds
        self._log(f"⏱  Next pulse in {delay_minutes} min.")
        self._update_countdown()
        self._timer = threading.Timer(delay_seconds, self._run_cycle)
        self._timer.daemon = True
        self._timer.start()

    def _update_countdown(self):
        if not self.running:
            return
        remaining = max(0, int(self._next_run_epoch - time.time()))
        mins, secs = divmod(remaining, 60)
        self.next_run_var.set(f"Next pulse in {mins:02d}:{secs:02d}")
        if remaining > 0:
            self._countdown_after_id = self.root.after(1000, self._update_countdown)
        else:
            self.next_run_var.set("Pulsing…")

    def _update_pulse_count(self):
        if self._pulse_count > 0:
            self.pulse_count_var.set(f"Pulses: {self._pulse_count}")
        else:
            self.pulse_count_var.set("")

    def _run_cycle(self):
        """Execute one pulse cycle (called from timer thread)."""
        if not self.running:
            return
        self._log("━━━ Pulse cycle started ━━━")
        success = gitpulse_cycle(self.repo_path, self._log)
        if success:
            self._pulse_count += 1
            self.root.after(0, self._update_pulse_count)
            self._log("✅  Pulse complete — commit pushed.")
        else:
            self._log("⚠️  Pulse finished with issues (will retry next cycle).")
        self._log("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if self.running:
            self.root.after(0, self._schedule_next)

    # ── Settings ─────────────────────────────────────────────────────
    def _on_settings(self):
        was_running = self.running
        if was_running:
            self._stop()

        answer = messagebox.askyesnocancel(
            "Settings",
            "Would you like to change the linked repository?\n\n"
            "• Yes — select a new repository\n"
            "• No — cancel",
        )
        if answer is True:
            clear_config()
            self.repo_path = None
            self.repo_var.set("No repository linked")
            self.repo_lbl.configure(fg=FG_DIM)
            self._log("🗑  Configuration cleared.")
            self._select_repo()
        elif was_running and self.repo_path:
            self._start()

    # ── Cleanup ──────────────────────────────────────────────────────
    def _on_close(self):
        self._stop()
        self.root.destroy()

    # ── Run ──────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = GitPulseApp()
    app.run()
