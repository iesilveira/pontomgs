"""Janela Sobre: consultas locais, sem downloads nem abrir o navegador."""
import importlib.metadata
import os
from pathlib import Path
import platform
import queue
import sqlite3
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from versao import APP_NAME, APP_VERSION


def _dependency(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "não identificado neste ambiente"
    except Exception:
        return "não foi possível consultar"


def coletar_informacoes(tk_version="", tcl_version=""):
    """Executada fora da thread gráfica; não inicia sessões Selenium."""
    project = Path(__file__).resolve().parent
    lines = [
        APP_NAME,
        "Versão do aplicativo: " + APP_VERSION,
        "",
        "NAVEGADOR EXCLUSIVO DO PONTOMGS",
    ]
    try:
        import chrome_gerenciado as managed
        pair = managed.current()
        if pair:
            # current() verifica os dois executáveis contra a mesma versão.
            lines.extend([
                "Chrome for Testing: " + str(pair["version"]),
                "ChromeDriver: " + str(pair["version"]),
                "Estado: par local validado pelo gerenciador",
                "Chrome: " + str(pair["chrome"]),
                "ChromeDriver: " + str(pair["chromedriver"]),
            ])
        else:
            lines.extend([
                "Chrome for Testing: versão não confirmada",
                "ChromeDriver: versão não confirmada",
                "Estado: gerenciador não encontrou um par local válido.",
                "Nenhum download ou reparo foi iniciado pela janela Sobre.",
            ])
    except Exception as error:
        lines.extend([
            "Chrome for Testing: indisponível para consulta",
            "ChromeDriver: indisponível para consulta",
            "Falha na consulta: " + type(error).__name__,
        ])
    lines.extend([
        "",
        "COMPONENTES",
        "Python: " + platform.python_version() + " (" + platform.python_implementation() + ")",
        "Tk: " + str(tk_version or "não identificado"),
        "Tcl: " + str(tcl_version or "não identificado"),
        "SQLite: " + sqlite3.sqlite_version,
    ])
    for label, distribution in (
        ("Selenium", "selenium"),
        ("Pillow", "Pillow"),
        ("pystray", "pystray"),
        ("ReportLab", "reportlab"),
    ):
        lines.append(label + ": " + _dependency(distribution))
    lines.extend([
        "",
        "AMBIENTE",
        "Sistema: " + platform.platform(),
        "Arquitetura: " + platform.machine(),
        "Python: " + sys.executable,
        "Projeto: " + str(project),
        "",
        "DIAGNÓSTICO",
    ])
    expected = project / "diagnostico_marcacoes.log"
    try:
        import logging
        import diagnostico
        actual = Path(diagnostico.caminho_log())
        handlers = getattr(diagnostico, "LOGGER", logging.getLogger("pontomgs.diagnostico")).handlers
        active = any(isinstance(h, logging.FileHandler) for h in handlers)
        lines.append("Arquivo: " + str(actual))
        lines.append("Estado: " + ("registro em arquivo ativo" if active else "registro em arquivo indisponível; verifique permissões"))
    except Exception:
        lines.extend([
            "Arquivo esperado: " + str(expected),
            "Estado: não foi possível consultar o diagnóstico",
        ])
    lines.extend([
        "Rotação: 4 MB, com uma cópia anterior (.1).",
        "",
        "As versões são consultadas localmente ao abrir esta janela.",
        "O Chrome pessoal não é utilizado nem alterado nesta consulta.",
    ])
    return "\n".join(lines)


def mostrar(app):
    """Chamar na thread do Tk, inclusive quando originado no menu da bandeja."""
    existing = getattr(app, "win_sobre", None)
    try:
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_force()
            return
    except tk.TclError:
        pass
    window = tk.Toplevel(app.root)
    app.win_sobre = window
    window.title("Sobre — " + APP_NAME)
    width = min(760, max(320, window.winfo_screenwidth() - 60))
    height = min(660, max(300, window.winfo_screenheight() - 100))
    window.geometry("{}x{}".format(width, height))
    window.minsize(min(440, width), min(300, height))
    try:
        window.attributes("-topmost", True)
    except tk.TclError:
        pass
    frame = ttk.Frame(window, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=APP_NAME + "  " + APP_VERSION,
              font=("Segoe UI", 15, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Versões e informações de diagnóstico").pack(anchor="w", pady=(2, 10))
    text = ScrolledText(frame, wrap="word", font=("Segoe UI", 10), height=18)
    text.pack(fill="both", expand=True)
    bar = ttk.Frame(frame)
    bar.pack(fill="x", pady=(12, 0))
    status = tk.StringVar(value="Consultando componentes locais...")
    ttk.Label(frame, textvariable=status).pack(anchor="w", pady=(8, 0))
    messages = queue.Queue()
    state = {"busy": False, "closed": False}

    def set_text(value):
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("1.0", value)
        text.configure(state="disabled")

    def copy():
        window.clipboard_clear()
        window.clipboard_append(text.get("1.0", "end-1c"))
        status.set("Informações copiadas.")

    def open_log():
        path = Path(__file__).resolve().parent / "diagnostico_marcacoes.log"
        try:
            import diagnostico
            path = Path(diagnostico.caminho_log())
        except Exception:
            pass
        if not path.is_file():
            messagebox.showinfo("Log", "O arquivo ainda não existe ou não pôde ser criado:\n" + str(path), parent=window)
            return
        try:
            if os.name != "nt":
                raise RuntimeError("A abertura automática do log está disponível no Windows.")
            os.startfile(str(path))
        except Exception as error:
            messagebox.showerror("Não foi possível abrir o log", str(error), parent=window)

    def refresh():
        if state["busy"]:
            return
        state["busy"] = True
        refresh_button.configure(state="disabled")
        status.set("Consultando componentes locais...")
        # Somente a thread gráfica acessa o interpretador Tcl.
        tk_version = str(window.tk.call("package", "provide", "Tk"))
        tcl_version = str(window.tk.call("info", "patchlevel"))
        def worker():
            try:
                result = coletar_informacoes(tk_version, tcl_version)
                messages.put((True, result))
            except Exception as error:
                messages.put((False, "Falha ao consultar componentes: " + type(error).__name__ + ": " + str(error)))
        threading.Thread(target=worker, name="PontoMGS-Sobre", daemon=True).start()

    def poll():
        if state["closed"]:
            return
        try:
            success, value = messages.get_nowait()
            set_text(value)
            state["busy"] = False
            refresh_button.configure(state="normal")
            status.set("Consulta local concluída." if success else "Não foi possível concluir a consulta.")
        except queue.Empty:
            pass
        try:
            window.after(150, poll)
        except tk.TclError:
            pass

    def close():
        state["closed"] = True
        app.win_sobre = None
        window.destroy()

    ttk.Button(bar, text="Copiar informações", command=copy).pack(side="left", padx=(0, 8))
    ttk.Button(bar, text="Abrir log", command=open_log).pack(side="left", padx=(0, 8))
    refresh_button = ttk.Button(bar, text="Atualizar versões", command=refresh)
    refresh_button.pack(side="left")
    ttk.Button(bar, text="Fechar", command=close).pack(side="right")
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda event: close())
    set_text("Consultando versões instaladas...")
    refresh()
    window.after(150, poll)
    window.lift()
