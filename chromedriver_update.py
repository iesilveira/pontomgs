"""Interface compatível com main.pyw; atualiza Chrome e ChromeDriver juntos."""
import json
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import chrome_gerenciado as managed

REMINDER_SECONDS = 3 * 60 * 60
CHECK_SECONDS = 3 * 60 * 60


def _state_path():
    return managed.base_dir() / "update_state.json"


def _read_state():
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_state(data):
    managed._atomic_json(_state_path(), data)


def _safe_after(app, delay, callback):
    try:
        app.root.after(delay, callback)
    except (RuntimeError, tk.TclError):
        pass


def agendar_verificacao(app):
    """Toda interação Tk ocorre na thread principal através de uma fila."""
    if getattr(app, "_managed_check_scheduled", False):
        return
    app._managed_check_scheduled = True
    app._managed_queue = queue.Queue()
    app._managed_check_running = False
    app._managed_installing = False
    app.chromedriver_update_popup = None
    _safe_after(app, 200, lambda: _poll(app))
    _safe_after(app, 5000, lambda: _check(app))


def _poll(app):
    try:
        for _ in range(100):
            kind, value = app._managed_queue.get_nowait()
            if kind == "check":
                _checked(app, value)
            elif kind == "progress":
                if getattr(app, "_managed_status", None) is not None:
                    app._managed_status.set(value)
            elif kind == "installed":
                _installed(app, value)
    except queue.Empty:
        pass
    _safe_after(app, 150, lambda: _poll(app))


def _check(app):
    if app._managed_check_running or app._managed_installing:
        _safe_after(app, 60000, lambda: _check(app))
        return
    app._managed_check_running = True
    def worker():
        try:
            pair = managed.current()
            metadata = managed.stable()
            result = (pair, metadata, None)
        except Exception as error:
            result = (None, None, str(error))
        app._managed_queue.put(("check", result))
    threading.Thread(target=worker, name="chrome-managed-check", daemon=True).start()


def _checked(app, result):
    app._managed_check_running = False
    pair, metadata, error = result
    if error:
        managed._log("verificação online indisponível")
        _safe_after(app, CHECK_SECONDS * 1000, lambda: _check(app))
        return
    if pair and tuple(map(int, pair["version"].split("."))) >= tuple(map(int, metadata["version"].split("."))):
        _safe_after(app, CHECK_SECONDS * 1000, lambda: _check(app))
        return
    state = _read_state()
    try:
        remaining = float(state.get("defer_until", 0)) - time.time()
    except (TypeError, ValueError):
        remaining = 0
    # Adiamento é persistente mesmo se o catálogo mudar no intervalo.
    if remaining > 0:
        _safe_after(app, max(1000, int(remaining * 1000)), lambda: _check(app))
        return
    _popup(app, metadata, pair)


def _close(app):
    popup = getattr(app, "chromedriver_update_popup", None)
    if popup is not None:
        try:
            popup.destroy()
        except tk.TclError:
            pass
    app.chromedriver_update_popup = None
    app._managed_status = None


def _popup(app, metadata, pair):
    popup = getattr(app, "chromedriver_update_popup", None)
    if popup is not None:
        try:
            if popup.winfo_exists():
                popup.lift()
                return
        except tk.TclError:
            pass
    popup = tk.Toplevel(app.root)
    app.chromedriver_update_popup = popup
    popup.title("Navegador exclusivo do PontoMGS")
    popup.resizable(False, False)
    popup.attributes("-topmost", True)
    frame = ttk.Frame(popup, padding=18)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Chrome + ChromeDriver", font=("Segoe UI", 13, "bold")).pack(anchor="w")
    description = ("Disponível: " + metadata["version"] + "\nInstalado: " +
                   (pair["version"] if pair else "ainda não instalado") +
                   "\n\nO download instala os dois componentes juntos.\n"
                   "Seu Chrome pessoal não será alterado.")
    ttk.Label(frame, text=description, justify="left").pack(anchor="w", pady=12)
    app._managed_status = tk.StringVar(value="O download pode levar alguns minutos.")
    ttk.Label(frame, textvariable=app._managed_status, wraplength=430).pack(anchor="w", pady=6)
    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=(10, 0))
    def later():
        try:
            _write_state({"version": metadata["version"], "defer_until": time.time() + REMINDER_SECONDS})
        except Exception as error:
            messagebox.showerror("Não foi possível adiar", str(error), parent=popup)
            return
        _close(app)
        _safe_after(app, REMINDER_SECONDS * 1000, lambda: _check(app))
    def start():
        if app._managed_installing:
            return
        app._managed_installing = True
        now_button.configure(state="disabled")
        later_button.configure(state="disabled")
        popup.protocol("WM_DELETE_WINDOW", lambda: None)
        app._managed_status.set("Preparando download...")
        def worker():
            try:
                pair_result = managed.install(metadata, progress=lambda text: app._managed_queue.put(("progress", text)))
                result = (pair_result, None)
            except Exception as error:
                result = (None, str(error))
            app._managed_queue.put(("installed", result))
        # Não daemon: a publicação atômica deve terminar mesmo se a UI for fechada.
        threading.Thread(target=worker, name="chrome-managed-install", daemon=False).start()
    now_button = ttk.Button(buttons, text="Atualizar agora" if pair else "Instalar agora", command=start)
    now_button.pack(side="left", padx=(0, 8))
    later_button = ttk.Button(buttons, text="Atualizar depois", command=later)
    later_button.pack(side="left")
    popup.protocol("WM_DELETE_WINDOW", later)


def _installed(app, result):
    app._managed_installing = False
    pair, error = result
    parent = getattr(app, "chromedriver_update_popup", None) or app.root
    if error:
        messagebox.showerror("Não foi possível atualizar",
                             error + "\n\nO par anterior não foi substituído.", parent=parent)
        _close(app)
        _safe_after(app, 60000, lambda: _check(app))
        return
    try:
        _write_state({})
    except Exception:
        pass
    messagebox.showinfo("Navegador pronto",
                        "Chrome e ChromeDriver " + pair["version"] +
                        " instalados e testados.\nAs próximas buscas usarão esse par.",
                        parent=parent)
    _close(app)
    # Versões imutáveis permitem trocar o par sem encerrar sessões em andamento.
    event = getattr(app, "atualizar_event", None)
    if event is not None:
        event.set()
    _safe_after(app, CHECK_SECONDS * 1000, lambda: _check(app))
