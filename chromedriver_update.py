# Verificação e interface de atualização do ChromeDriver.
# O catálogo JSON oficial é consultado em segundo plano; nenhuma página é aberta.

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import settings


CATALOG_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "last-known-good-versions-with-downloads.json"
)
REMINDER_SECONDS = 3 * 60 * 60
CHECK_RETRY_SECONDS = 3 * 60 * 60
WINDOW_TITLE = "Atualização do ChromeDriver"


def _project_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _driver_path():
    return _project_dir() / "chromedriver.exe"


def _version_tuple(version):
    numbers = tuple(int(part) for part in re.findall(r"\d+", str(version)))
    return (numbers + (0, 0, 0, 0))[:4]


def _parse_driver_version(text):
    match = re.search(r"ChromeDriver\s+(\d+(?:\.\d+){1,3})", text or "", re.I)
    if not match:
        match = re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b", text or "")
    return match.group(1) if match else None


def _installed_version():
    executable = _driver_path()
    if not executable.is_file():
        return None
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            [str(executable), "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=flags,
            check=False,
        )
    except Exception:
        return None
    return _parse_driver_version((result.stdout or "") + "\n" + (result.stderr or ""))


def _fetch_stable():
    request = urllib.request.Request(
        CATALOG_URL,
        headers={"User-Agent": "PontoMGS-ChromeDriver-Updater/1.0"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))

    stable = payload["channels"]["Stable"]
    version = str(stable["version"])
    assets = stable["downloads"]["chromedriver"]
    asset = next(item for item in assets if item.get("platform") == "win64")
    url = str(asset["url"])

    parsed = urllib.parse.urlsplit(url)
    expected_path = (
        f"/chrome-for-testing-public/{version}/win64/"
        "chromedriver-win64.zip"
    )
    if parsed.scheme != "https" or parsed.netloc.lower() != "storage.googleapis.com":
        raise ValueError("O catálogo retornou um host de download inesperado.")
    if parsed.path != expected_path:
        raise ValueError("O catálogo retornou um caminho de download inesperado.")

    return {
        "version": version,
        "binary": "chromedriver",
        "platform": "win64",
        "url": url,
    }


def _state_path():
    app_dir = Path(
        getattr(settings, "APP_DIR", os.path.join(
            os.environ.get("APPDATA", str(Path.home())),
            "PontoApp",
        ))
    )
    return app_dir / "chromedriver_update_state.json"


def _read_state():
    try:
        with _state_path().open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _write_state(data):
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file)
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink()
        except OSError:
            pass


def _clear_state():
    try:
        _state_path().unlink()
    except OSError:
        pass


def _safe_after(app, callback, delay=0):
    try:
        app.root.after(delay, callback)
    except Exception:
        pass


def agendar_verificacao(app):
    """Agenda uma verificação não bloqueante após a inicialização da interface."""
    if getattr(app, "_chromedriver_check_scheduled", False):
        return
    app._chromedriver_check_scheduled = True
    app.chromedriver_update_popup = None
    _safe_after(app, lambda: _iniciar_verificacao(app), 5000)


def _iniciar_verificacao(app):
    if getattr(app, "_chromedriver_check_running", False):
        return
    app._chromedriver_check_running = True

    def worker():
        try:
            metadata = _fetch_stable()
            installed = _installed_version()
            result = {"metadata": metadata, "installed": installed, "error": None}
        except Exception as error:
            result = {"metadata": None, "installed": None, "error": error}
        _safe_after(app, lambda: _processar_resultado(app, result))

    threading.Thread(target=worker, name="chromedriver-update-check", daemon=True).start()


def _processar_resultado(app, result):
    app._chromedriver_check_running = False
    if result.get("error") is not None:
        _safe_after(
            app,
            lambda: _iniciar_verificacao(app),
            CHECK_RETRY_SECONDS * 1000,
        )
        return

    metadata = result["metadata"]
    installed = result["installed"]
    latest = metadata["version"]

    if installed and _version_tuple(installed) >= _version_tuple(latest):
        _clear_state()
        return

    state = _read_state()
    deferred_version = str(state.get("version", ""))
    try:
        defer_until = float(state.get("defer_until", 0))
    except (TypeError, ValueError):
        defer_until = 0

    if deferred_version == latest and defer_until > time.time():
        remaining_ms = max(1000, int((defer_until - time.time()) * 1000))
        _safe_after(
            app,
            lambda: _iniciar_verificacao(app),
            remaining_ms,
        )
        return

    _mostrar_aviso(app, metadata, installed)


def _popup_existe(app):
    popup = getattr(app, "chromedriver_update_popup", None)
    try:
        return popup is not None and bool(popup.winfo_exists())
    except Exception:
        return False


def _fechar_popup(app):
    popup = getattr(app, "chromedriver_update_popup", None)
    try:
        if popup is not None and popup.winfo_exists():
            popup.destroy()
    except Exception:
        pass
    app.chromedriver_update_popup = None


def _mostrar_aviso(app, metadata, installed):
    if _popup_existe(app):
        try:
            app.chromedriver_update_popup.lift()
            app.chromedriver_update_popup.attributes("-topmost", True)
        except Exception:
            pass
        return

    popup = tk.Toplevel(app.root)
    app.chromedriver_update_popup = popup
    popup.title("Componente do sistema")
    popup.configure(bg=settings.COLOR_BG)
    popup.resizable(False, False)
    popup.attributes("-topmost", True)
    try:
        popup.transient(app.root)
    except Exception:
        pass

    width, height = 410, 225
    x = max(0, (popup.winfo_screenwidth() - width) // 2)
    y = max(0, (popup.winfo_screenheight() - height) // 2)
    popup.geometry(f"{width}x{height}+{x}+{y}")

    tk.Label(
        popup,
        text="⏳ Atualização necessária",
        font=("Segoe UI", 14, "bold"),
        fg=settings.COLOR_TEXT_BLUE,
        bg=settings.COLOR_BG,
    ).pack(pady=(15, 7))

    installed_text = installed or "não detectada"
    tk.Label(
        popup,
        text=(
            "Há uma nova versão do ChromeDriver Stable.\n"
            f"Instalada: {installed_text}\n"
            f"Disponível: {metadata['version']}\n\n"
            "Atualize para manter a automação funcionando."
        ),
        font=("Segoe UI", 10),
        fg="#222222",
        bg=settings.COLOR_BG,
        justify="center",
        wraplength=370,
    ).pack(padx=15, pady=(0, 10))

    buttons = tk.Frame(popup, bg=settings.COLOR_BG)
    buttons.pack(pady=(0, 13))

    def later():
        _write_state({
            "version": metadata["version"],
            "defer_until": time.time() + REMINDER_SECONDS,
        })
        _fechar_popup(app)
        _safe_after(
            app,
            lambda: _iniciar_verificacao(app),
            REMINDER_SECONDS * 1000,
        )

    def now():
        _fechar_popup(app)
        _iniciar_atualizador(app)

    tk.Button(
        buttons,
        text="Atualizar agora",
        command=now,
        font=("Segoe UI", 9, "bold"),
        bg=settings.COLOR_BUTTON_RED,
        fg="white",
        activebackground=settings.COLOR_BUTTON_RED,
        activeforeground="white",
        relief="flat",
        padx=13,
        pady=6,
    ).pack(side="left", padx=7)

    tk.Button(
        buttons,
        text="Atualizar depois",
        command=later,
        font=("Segoe UI", 9, "bold"),
        bg="#e5e5e5",
        fg="#222222",
        activebackground="#d8d8d8",
        relief="flat",
        padx=13,
        pady=6,
    ).pack(side="left", padx=7)

    popup.protocol("WM_DELETE_WINDOW", later)
    try:
        popup.grab_set()
        popup.focus_force()
    except Exception:
        pass


def _pythonw_path():
    executable = Path(sys.executable)
    if not getattr(sys, "frozen", False) and executable.name.lower() == "python.exe":
        candidate = executable.with_name("pythonw.exe")
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _restart_command():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    script = Path(sys.argv[0]).resolve()
    return [_pythonw_path(), str(script)]


def _iniciar_atualizador(app):
    project_dir = _project_dir()
    updater = project_dir / "chromedriver_updater.pyw"
    if not updater.is_file():
        messagebox.showerror(
            "Atualizador indisponível",
            "O módulo chromedriver_updater.pyw não foi encontrado na pasta do projeto.",
            parent=app.root,
        )
        return

    command = [
        _pythonw_path(),
        str(updater),
        "--project-dir",
        str(project_dir),
        "--restart-command",
        json.dumps(_restart_command()),
    ]
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            command,
            cwd=str(project_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=flags,
        )
    except Exception as error:
        messagebox.showerror(
            "Falha ao iniciar atualização",
            f"Não foi possível abrir o atualizador:\n{error}",
            parent=app.root,
        )
        return

    try:
        tray_icon = getattr(app, "tray_icon", None)
        if tray_icon is not None:
            tray_icon.stop()
    except Exception:
        pass
    _safe_after(app, app.root.destroy)
