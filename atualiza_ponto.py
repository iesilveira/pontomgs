"""
Aplica verificação automática de atualização do ChromeDriver ao PontoMGS.

Execute este arquivo na pasta do projeto:
    py atualiza_ponto.py

O patch modifica main.pyw (ou main.py) e instala:
    chromedriver_update.py
    chromedriver_updater.pyw

Não altera scraper.py nem as rotinas de importação histórica/mensal.
Não cria backups, relatórios ou logs.
"""

import ast
import os
import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MODULE_UPDATE = '# Verificação e interface de atualização do ChromeDriver.\n# O catálogo JSON oficial é consultado em segundo plano; nenhuma página é aberta.\n\nimport json\nimport os\nimport re\nimport subprocess\nimport sys\nimport threading\nimport time\nimport urllib.parse\nimport urllib.request\nfrom pathlib import Path\nimport tkinter as tk\nfrom tkinter import messagebox\nimport settings\n\n\nCATALOG_URL = (\n    "https://googlechromelabs.github.io/chrome-for-testing/"\n    "last-known-good-versions-with-downloads.json"\n)\nREMINDER_SECONDS = 3 * 60 * 60\nCHECK_RETRY_SECONDS = 3 * 60 * 60\nWINDOW_TITLE = "Atualização do ChromeDriver"\n\n\ndef _project_dir():\n    if getattr(sys, "frozen", False):\n        return Path(sys.executable).resolve().parent\n    return Path(__file__).resolve().parent\n\n\ndef _driver_path():\n    return _project_dir() / "chromedriver.exe"\n\n\ndef _version_tuple(version):\n    numbers = tuple(int(part) for part in re.findall(r"\\d+", str(version)))\n    return (numbers + (0, 0, 0, 0))[:4]\n\n\ndef _parse_driver_version(text):\n    match = re.search(r"ChromeDriver\\s+(\\d+(?:\\.\\d+){1,3})", text or "", re.I)\n    if not match:\n        match = re.search(r"\\b(\\d+\\.\\d+\\.\\d+\\.\\d+)\\b", text or "")\n    return match.group(1) if match else None\n\n\ndef _installed_version():\n    executable = _driver_path()\n    if not executable.is_file():\n        return None\n    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)\n    try:\n        result = subprocess.run(\n            [str(executable), "--version"],\n            capture_output=True,\n            text=True,\n            timeout=8,\n            creationflags=flags,\n            check=False,\n        )\n    except Exception:\n        return None\n    return _parse_driver_version((result.stdout or "") + "\\n" + (result.stderr or ""))\n\n\ndef _fetch_stable():\n    request = urllib.request.Request(\n        CATALOG_URL,\n        headers={"User-Agent": "PontoMGS-ChromeDriver-Updater/1.0"},\n    )\n    with urllib.request.urlopen(request, timeout=15) as response:\n        payload = json.loads(response.read().decode("utf-8"))\n\n    stable = payload["channels"]["Stable"]\n    version = str(stable["version"])\n    assets = stable["downloads"]["chromedriver"]\n    asset = next(item for item in assets if item.get("platform") == "win64")\n    url = str(asset["url"])\n\n    parsed = urllib.parse.urlsplit(url)\n    expected_path = (\n        f"/chrome-for-testing-public/{version}/win64/"\n        "chromedriver-win64.zip"\n    )\n    if parsed.scheme != "https" or parsed.netloc.lower() != "storage.googleapis.com":\n        raise ValueError("O catálogo retornou um host de download inesperado.")\n    if parsed.path != expected_path:\n        raise ValueError("O catálogo retornou um caminho de download inesperado.")\n\n    return {\n        "version": version,\n        "binary": "chromedriver",\n        "platform": "win64",\n        "url": url,\n    }\n\n\ndef _state_path():\n    app_dir = Path(\n        getattr(settings, "APP_DIR", os.path.join(\n            os.environ.get("APPDATA", str(Path.home())),\n            "PontoApp",\n        ))\n    )\n    return app_dir / "chromedriver_update_state.json"\n\n\ndef _read_state():\n    try:\n        with _state_path().open("r", encoding="utf-8") as file:\n            data = json.load(file)\n        if isinstance(data, dict):\n            return data\n    except Exception:\n        pass\n    return {}\n\n\ndef _write_state(data):\n    path = _state_path()\n    path.parent.mkdir(parents=True, exist_ok=True)\n    temporary = path.with_name(path.name + ".tmp")\n    try:\n        with temporary.open("w", encoding="utf-8") as file:\n            json.dump(data, file)\n        os.replace(str(temporary), str(path))\n    finally:\n        try:\n            temporary.unlink()\n        except OSError:\n            pass\n\n\ndef _clear_state():\n    try:\n        _state_path().unlink()\n    except OSError:\n        pass\n\n\ndef _safe_after(app, callback, delay=0):\n    try:\n        app.root.after(delay, callback)\n    except Exception:\n        pass\n\n\ndef agendar_verificacao(app):\n    """Agenda uma verificação não bloqueante após a inicialização da interface."""\n    if getattr(app, "_chromedriver_check_scheduled", False):\n        return\n    app._chromedriver_check_scheduled = True\n    app.chromedriver_update_popup = None\n    _safe_after(app, lambda: _iniciar_verificacao(app), 5000)\n\n\ndef _iniciar_verificacao(app):\n    if getattr(app, "_chromedriver_check_running", False):\n        return\n    app._chromedriver_check_running = True\n\n    def worker():\n        try:\n            metadata = _fetch_stable()\n            installed = _installed_version()\n            result = {"metadata": metadata, "installed": installed, "error": None}\n        except Exception as error:\n            result = {"metadata": None, "installed": None, "error": error}\n        _safe_after(app, lambda: _processar_resultado(app, result))\n\n    threading.Thread(target=worker, name="chromedriver-update-check", daemon=True).start()\n\n\ndef _processar_resultado(app, result):\n    app._chromedriver_check_running = False\n    if result.get("error") is not None:\n        _safe_after(\n            app,\n            lambda: _iniciar_verificacao(app),\n            CHECK_RETRY_SECONDS * 1000,\n        )\n        return\n\n    metadata = result["metadata"]\n    installed = result["installed"]\n    latest = metadata["version"]\n\n    if installed and _version_tuple(installed) >= _version_tuple(latest):\n        _clear_state()\n        return\n\n    state = _read_state()\n    deferred_version = str(state.get("version", ""))\n    try:\n        defer_until = float(state.get("defer_until", 0))\n    except (TypeError, ValueError):\n        defer_until = 0\n\n    if deferred_version == latest and defer_until > time.time():\n        remaining_ms = max(1000, int((defer_until - time.time()) * 1000))\n        _safe_after(\n            app,\n            lambda: _iniciar_verificacao(app),\n            remaining_ms,\n        )\n        return\n\n    _mostrar_aviso(app, metadata, installed)\n\n\ndef _popup_existe(app):\n    popup = getattr(app, "chromedriver_update_popup", None)\n    try:\n        return popup is not None and bool(popup.winfo_exists())\n    except Exception:\n        return False\n\n\ndef _fechar_popup(app):\n    popup = getattr(app, "chromedriver_update_popup", None)\n    try:\n        if popup is not None and popup.winfo_exists():\n            popup.destroy()\n    except Exception:\n        pass\n    app.chromedriver_update_popup = None\n\n\ndef _mostrar_aviso(app, metadata, installed):\n    if _popup_existe(app):\n        try:\n            app.chromedriver_update_popup.lift()\n            app.chromedriver_update_popup.attributes("-topmost", True)\n        except Exception:\n            pass\n        return\n\n    popup = tk.Toplevel(app.root)\n    app.chromedriver_update_popup = popup\n    popup.title("Componente do sistema")\n    popup.configure(bg=settings.COLOR_BG)\n    popup.resizable(False, False)\n    popup.attributes("-topmost", True)\n    try:\n        popup.transient(app.root)\n    except Exception:\n        pass\n\n    width, height = 410, 225\n    x = max(0, (popup.winfo_screenwidth() - width) // 2)\n    y = max(0, (popup.winfo_screenheight() - height) // 2)\n    popup.geometry(f"{width}x{height}+{x}+{y}")\n\n    tk.Label(\n        popup,\n        text="⏳ Atualização necessária",\n        font=("Segoe UI", 14, "bold"),\n        fg=settings.COLOR_TEXT_BLUE,\n        bg=settings.COLOR_BG,\n    ).pack(pady=(15, 7))\n\n    installed_text = installed or "não detectada"\n    tk.Label(\n        popup,\n        text=(\n            "Há uma nova versão do ChromeDriver Stable.\\n"\n            f"Instalada: {installed_text}\\n"\n            f"Disponível: {metadata[\'version\']}\\n\\n"\n            "Atualize para manter a automação funcionando."\n        ),\n        font=("Segoe UI", 10),\n        fg="#222222",\n        bg=settings.COLOR_BG,\n        justify="center",\n        wraplength=370,\n    ).pack(padx=15, pady=(0, 10))\n\n    buttons = tk.Frame(popup, bg=settings.COLOR_BG)\n    buttons.pack(pady=(0, 13))\n\n    def later():\n        _write_state({\n            "version": metadata["version"],\n            "defer_until": time.time() + REMINDER_SECONDS,\n        })\n        _fechar_popup(app)\n        _safe_after(\n            app,\n            lambda: _iniciar_verificacao(app),\n            REMINDER_SECONDS * 1000,\n        )\n\n    def now():\n        _fechar_popup(app)\n        _iniciar_atualizador(app)\n\n    tk.Button(\n        buttons,\n        text="Atualizar agora",\n        command=now,\n        font=("Segoe UI", 9, "bold"),\n        bg=settings.COLOR_BUTTON_RED,\n        fg="white",\n        activebackground=settings.COLOR_BUTTON_RED,\n        activeforeground="white",\n        relief="flat",\n        padx=13,\n        pady=6,\n    ).pack(side="left", padx=7)\n\n    tk.Button(\n        buttons,\n        text="Atualizar depois",\n        command=later,\n        font=("Segoe UI", 9, "bold"),\n        bg="#e5e5e5",\n        fg="#222222",\n        activebackground="#d8d8d8",\n        relief="flat",\n        padx=13,\n        pady=6,\n    ).pack(side="left", padx=7)\n\n    popup.protocol("WM_DELETE_WINDOW", later)\n    try:\n        popup.grab_set()\n        popup.focus_force()\n    except Exception:\n        pass\n\n\ndef _pythonw_path():\n    executable = Path(sys.executable)\n    if not getattr(sys, "frozen", False) and executable.name.lower() == "python.exe":\n        candidate = executable.with_name("pythonw.exe")\n        if candidate.is_file():\n            return str(candidate)\n    return sys.executable\n\n\ndef _restart_command():\n    if getattr(sys, "frozen", False):\n        return [sys.executable]\n    script = Path(sys.argv[0]).resolve()\n    return [_pythonw_path(), str(script)]\n\n\ndef _iniciar_atualizador(app):\n    project_dir = _project_dir()\n    updater = project_dir / "chromedriver_updater.pyw"\n    if not updater.is_file():\n        messagebox.showerror(\n            "Atualizador indisponível",\n            "O módulo chromedriver_updater.pyw não foi encontrado na pasta do projeto.",\n            parent=app.root,\n        )\n        return\n\n    command = [\n        _pythonw_path(),\n        str(updater),\n        "--project-dir",\n        str(project_dir),\n        "--restart-command",\n        json.dumps(_restart_command()),\n    ]\n    try:\n        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)\n        subprocess.Popen(\n            command,\n            cwd=str(project_dir),\n            stdin=subprocess.DEVNULL,\n            stdout=subprocess.DEVNULL,\n            stderr=subprocess.DEVNULL,\n            close_fds=True,\n            creationflags=flags,\n        )\n    except Exception as error:\n        messagebox.showerror(\n            "Falha ao iniciar atualização",\n            f"Não foi possível abrir o atualizador:\\n{error}",\n            parent=app.root,\n        )\n        return\n\n    try:\n        tray_icon = getattr(app, "tray_icon", None)\n        if tray_icon is not None:\n            tray_icon.stop()\n    except Exception:\n        pass\n    _safe_after(app, app.root.destroy)\n'
MODULE_UPDATER = '# Atualizador gráfico autônomo do ChromeDriver para Windows.\n# Obtém o Stable e o URL win64 do catálogo JSON oficial do Chrome for Testing.\n\nimport argparse\nimport json\nimport os\nimport re\nimport shutil\nimport subprocess\nimport sys\nimport tempfile\nimport threading\nimport time\nimport urllib.parse\nimport urllib.request\nimport zipfile\nfrom pathlib import Path\nimport tkinter as tk\nfrom tkinter import ttk\n\n\nCATALOG_URL = (\n    "https://googlechromelabs.github.io/chrome-for-testing/"\n    "last-known-good-versions-with-downloads.json"\n)\nCHUNK_SIZE = 128 * 1024\n\n\ndef _version_tuple(version):\n    numbers = tuple(int(part) for part in re.findall(r"\\d+", str(version)))\n    return (numbers + (0, 0, 0, 0))[:4]\n\n\ndef _parse_driver_version(text):\n    match = re.search(r"ChromeDriver\\s+(\\d+(?:\\.\\d+){1,3})", text or "", re.I)\n    if not match:\n        match = re.search(r"\\b(\\d+\\.\\d+\\.\\d+\\.\\d+)\\b", text or "")\n    return match.group(1) if match else None\n\n\ndef _fetch_stable():\n    request = urllib.request.Request(\n        CATALOG_URL,\n        headers={"User-Agent": "PontoMGS-ChromeDriver-Updater/1.0"},\n    )\n    with urllib.request.urlopen(request, timeout=20) as response:\n        payload = json.loads(response.read().decode("utf-8"))\n\n    stable = payload["channels"]["Stable"]\n    version = str(stable["version"])\n    asset = next(\n        item for item in stable["downloads"]["chromedriver"]\n        if item.get("platform") == "win64"\n    )\n    url = str(asset["url"])\n\n    parsed = urllib.parse.urlsplit(url)\n    expected_path = (\n        f"/chrome-for-testing-public/{version}/win64/"\n        "chromedriver-win64.zip"\n    )\n    if parsed.scheme != "https" or parsed.netloc.lower() != "storage.googleapis.com":\n        raise ValueError("O catálogo retornou um host de download inesperado.")\n    if parsed.path != expected_path:\n        raise ValueError("O catálogo retornou um caminho de download inesperado.")\n\n    return {\n        "version": version,\n        "binary": "chromedriver",\n        "platform": "win64",\n        "url": url,\n    }\n\n\nclass ChromeDriverUpdater:\n    def __init__(self, project_dir, restart_command):\n        self.project_dir = Path(project_dir).resolve()\n        self.driver_path = self.project_dir / "chromedriver.exe"\n        self.restart_command = restart_command\n        self.cancel_requested = threading.Event()\n        self.restarting = False\n\n        self.root = tk.Tk()\n        self.root.title("Atualização do ChromeDriver")\n        self.root.configure(bg="white")\n        self.root.resizable(False, False)\n        self.root.attributes("-topmost", True)\n        self.root.protocol("WM_DELETE_WINDOW", self.request_cancel)\n\n        width, height = 520, 255\n        x = max(0, (self.root.winfo_screenwidth() - width) // 2)\n        y = max(0, (self.root.winfo_screenheight() - height) // 2)\n        self.root.geometry(f"{width}x{height}+{x}+{y}")\n\n        tk.Label(\n            self.root,\n            text="Atualizando componente do sistema",\n            font=("Segoe UI", 14, "bold"),\n            fg="#00205B",\n            bg="white",\n        ).pack(pady=(18, 7))\n\n        self.status = tk.StringVar(value="Consultando a versão Stable oficial...")\n        tk.Label(\n            self.root,\n            textvariable=self.status,\n            font=("Segoe UI", 10),\n            fg="#222222",\n            bg="white",\n            wraplength=470,\n            justify="center",\n        ).pack(padx=20, pady=8)\n\n        self.details = tk.StringVar(value="")\n        tk.Label(\n            self.root,\n            textvariable=self.details,\n            font=("Segoe UI", 9),\n            fg="#555555",\n            bg="white",\n            wraplength=470,\n            justify="center",\n        ).pack(padx=20, pady=4)\n\n        self.progress = ttk.Progressbar(\n            self.root,\n            orient="horizontal",\n            mode="determinate",\n            length=420,\n            maximum=100,\n        )\n        self.progress.pack(pady=12)\n\n        self.button = tk.Button(\n            self.root,\n            text="Aguarde...",\n            state="disabled",\n            command=self.restart_now,\n            font=("Segoe UI", 9, "bold"),\n            bg="#e5e5e5",\n            relief="flat",\n            padx=16,\n            pady=6,\n        )\n        self.button.pack(pady=(0, 12))\n\n        threading.Thread(\n            target=self.worker,\n            name="chromedriver-update-download",\n            daemon=True,\n        ).start()\n\n    def set_ui(self, status=None, details=None, progress=None, button=None):\n        def apply():\n            if status is not None:\n                self.status.set(status)\n            if details is not None:\n                self.details.set(details)\n            if progress is not None:\n                self.progress["value"] = max(0, min(100, progress))\n            if button is not None:\n                self.button.configure(text=button, state="normal")\n        try:\n            self.root.after(0, apply)\n        except Exception:\n            pass\n\n    def request_cancel(self):\n        self.cancel_requested.set()\n        self.set_ui(\n            status="Cancelando com segurança; o sistema será reaberto...",\n            button="Reabrir sistema",\n        )\n\n    def _check_cancel(self):\n        if self.cancel_requested.is_set():\n            raise RuntimeError("Atualização cancelada pelo usuário.")\n\n    def _download(self, metadata, zip_path):\n        request = urllib.request.Request(\n            metadata["url"],\n            headers={"User-Agent": "PontoMGS-ChromeDriver-Updater/1.0"},\n        )\n        with urllib.request.urlopen(request, timeout=30) as response:\n            total = int(response.headers.get("Content-Length", "0") or "0")\n            downloaded = 0\n            last_percent = -1\n            with zip_path.open("wb") as output:\n                while True:\n                    self._check_cancel()\n                    block = response.read(CHUNK_SIZE)\n                    if not block:\n                        break\n                    output.write(block)\n                    downloaded += len(block)\n                    if total > 0:\n                        percent = int(downloaded * 100 / total)\n                        if percent != last_percent:\n                            last_percent = percent\n                            self.set_ui(\n                                status=f"Baixando ChromeDriver Stable {metadata[\'version\']}...",\n                                progress=percent,\n                            )\n        if not zip_path.is_file() or zip_path.stat().st_size == 0:\n            raise RuntimeError("O download terminou sem um arquivo válido.")\n\n    def _extract_and_validate(self, zip_path, staging_dir, expected_version):\n        with zipfile.ZipFile(zip_path, "r") as archive:\n            member = None\n            for name in archive.namelist():\n                normalized = name.replace("\\\\", "/")\n                if normalized == "chromedriver-win64/chromedriver.exe":\n                    member = name\n                    break\n            if member is None:\n                raise RuntimeError(\n                    "O ZIP oficial não contém chromedriver-win64/chromedriver.exe."\n                )\n            candidate = staging_dir / "chromedriver.exe"\n            with archive.open(member, "r") as source, candidate.open("wb") as target:\n                shutil.copyfileobj(source, target)\n\n        if not candidate.is_file() or candidate.stat().st_size == 0:\n            raise RuntimeError("O executável extraído está vazio.")\n\n        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)\n        result = subprocess.run(\n            [str(candidate), "--version"],\n            capture_output=True,\n            text=True,\n            timeout=12,\n            creationflags=flags,\n            check=False,\n        )\n        found = _parse_driver_version(\n            (result.stdout or "") + "\\n" + (result.stderr or "")\n        )\n        if result.returncode != 0 or found != expected_version:\n            raise RuntimeError(\n                "A versão do executável baixado não corresponde ao catálogo "\n                f"(esperada {expected_version}; encontrada {found or \'desconhecida\'})."\n            )\n        return candidate\n\n    def _replace_driver(self, candidate):\n        last_error = None\n        for attempt in range(40):\n            self._check_cancel()\n            try:\n                os.replace(str(candidate), str(self.driver_path))\n                return\n            except PermissionError as error:\n                last_error = error\n                time.sleep(1)\n            except OSError as error:\n                last_error = error\n                time.sleep(1)\n        raise RuntimeError(\n            "Não foi possível substituir chromedriver.exe. "\n            "Verifique se o aplicativo foi encerrado e se a pasta permite gravação. "\n            f"Detalhe: {last_error}"\n        )\n\n    def worker(self):\n        staging = None\n        try:\n            self._check_cancel()\n            metadata = _fetch_stable()\n            self.set_ui(\n                status=f"Versão Stable encontrada: {metadata[\'version\']}",\n                details=(\n                    "Binary: chromedriver  |  Plataforma: win64\\n"\n                    f"Origem oficial: {metadata[\'url\']}"\n                ),\n                progress=0,\n            )\n            self._check_cancel()\n\n            current = None\n            if self.driver_path.is_file():\n                try:\n                    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)\n                    result = subprocess.run(\n                        [str(self.driver_path), "--version"],\n                        capture_output=True,\n                        text=True,\n                        timeout=8,\n                        creationflags=flags,\n                        check=False,\n                    )\n                    current = _parse_driver_version(\n                        (result.stdout or "") + "\\n" + (result.stderr or "")\n                    )\n                except Exception:\n                    current = None\n\n            if current and _version_tuple(current) >= _version_tuple(metadata["version"]):\n                self.finish(\n                    True,\n                    f"O ChromeDriver já está atualizado ({current}).",\n                )\n                return\n\n            self.project_dir.mkdir(parents=True, exist_ok=True)\n            staging = Path(tempfile.mkdtemp(\n                prefix=".chromedriver_update_",\n                dir=str(self.project_dir),\n            ))\n            zip_path = staging / "chromedriver-win64.zip"\n\n            self.set_ui(status="Baixando o pacote oficial...", progress=0)\n            self._download(metadata, zip_path)\n            self._check_cancel()\n\n            self.set_ui(status="Validando o executável baixado...", progress=100)\n            candidate = self._extract_and_validate(\n                zip_path,\n                staging,\n                metadata["version"],\n            )\n            self._check_cancel()\n\n            self.set_ui(status="Instalando ChromeDriver na pasta do projeto...")\n            self._replace_driver(candidate)\n            self.finish(\n                True,\n                f"ChromeDriver {metadata[\'version\']} atualizado com sucesso.",\n            )\n\n        except Exception as error:\n            self.finish(False, str(error) or type(error).__name__)\n        finally:\n            if staging is not None:\n                try:\n                    shutil.rmtree(staging, ignore_errors=True)\n                except Exception:\n                    pass\n\n    def finish(self, success, message):\n        if success:\n            status = message + "\\nReabrindo o sistema..."\n            delay = 1800\n        else:\n            status = (\n                "A atualização não foi concluída.\\n"\n                f"{message}\\nO sistema será reaberto."\n            )\n            delay = 10000\n        self.set_ui(\n            status=status,\n            button="Reabrir sistema agora",\n        )\n        try:\n            self.root.after(delay, self.restart_now)\n        except Exception:\n            pass\n\n    def restart_now(self):\n        if self.restarting:\n            return\n        self.restarting = True\n        try:\n            if self.restart_command and all(\n                isinstance(part, str) for part in self.restart_command\n            ):\n                subprocess.Popen(\n                    self.restart_command,\n                    cwd=str(self.project_dir),\n                    close_fds=True,\n                )\n        except Exception as error:\n            self.status.set(\n                "Não foi possível reabrir automaticamente o sistema.\\n"\n                f"Detalhe: {error}"\n            )\n            self.restarting = False\n            return\n        try:\n            self.root.destroy()\n        except Exception:\n            pass\n\n    def run(self):\n        self.root.mainloop()\n\n\ndef _parse_args():\n    parser = argparse.ArgumentParser()\n    parser.add_argument("--project-dir", required=True)\n    parser.add_argument("--restart-command", required=True)\n    return parser.parse_args()\n\n\ndef main():\n    args = _parse_args()\n    try:\n        restart_command = json.loads(args.restart_command)\n        if not isinstance(restart_command, list) or not restart_command:\n            raise ValueError("Comando de reinício inválido.")\n        restart_command = [str(part) for part in restart_command]\n    except Exception:\n        restart_command = []\n\n    updater = ChromeDriverUpdater(args.project_dir, restart_command)\n    updater.run()\n\n\nif __name__ == "__main__":\n    main()\n'


def read_source(path):
    raw = path.read_bytes()
    has_bom = raw.startswith(bytes((239, 187, 191)))
    encoding = "utf-8"
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        encoding = "latin-1"
        has_bom = False
        text = raw.decode(encoding)
    newline = "\r\n" if "\r\n" in text else "\n"
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return raw, normalized, encoding, has_bom, newline


def patch_main(source):
    source = source.replace("\r\n", "\n").replace("\r", "\n")

    if not re.search(r"(?m)^import[ \t]+chromedriver_update(?:[ \t]|$)", source):
        pattern = re.compile(r"(?m)^import[ \t]+scraper[ \t]*$")
        match = pattern.search(source)
        if not match:
            raise RuntimeError("Não encontrei 'import scraper' no arquivo principal.")
        source = (
            source[:match.end()]
            + "\nimport chromedriver_update"
            + source[match.end():]
        )

    if "chromedriver_update.agendar_verificacao(self)" not in source:
        tree = ast.parse(source)
        setup_line = None
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name != "PontoApp":
                continue
            for method in node.body:
                if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if method.name != "__init__":
                    continue
                for statement in method.body:
                    if not isinstance(statement, ast.Expr):
                        continue
                    call = statement.value
                    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
                        continue
                    if (
                        isinstance(call.func.value, ast.Name)
                        and call.func.value.id == "self"
                        and call.func.attr == "setup_ui"
                    ):
                        setup_line = statement.end_lineno
                        break
            if setup_line is not None:
                break

        if setup_line is None:
            raise RuntimeError(
                "Não localizei PontoApp.__init__ chamando self.setup_ui()."
            )

        lines = source.splitlines(keepends=True)
        addition = (
            "        self.chromedriver_update_popup = None\n"
            "        chromedriver_update.agendar_verificacao(self)\n"
        )
        lines.insert(setup_line, addition)
        source = "".join(lines)

    ast.parse(source)
    compile(source, "main.pyw", "exec")
    return source


def atomic_write(path, text, encoding="utf-8", has_bom=False, newline="\n"):
    if newline != "\n":
        text = text.replace("\n", newline)
    data = text.encode(encoding)
    if encoding == "utf-8" and has_bom:
        data = bytes((239, 187, 191)) + data
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(data)
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink()
        except OSError:
            pass


def main():
    main_path = BASE_DIR / "main.pyw"
    if not main_path.is_file():
        main_path = BASE_DIR / "main.py"
    if not main_path.is_file():
        raise FileNotFoundError("Não encontrei main.pyw nem main.py na pasta do projeto.")

    update_path = BASE_DIR / "chromedriver_update.py"
    updater_path = BASE_DIR / "chromedriver_updater.pyw"

    compile(MODULE_UPDATE, str(update_path), "exec")
    compile(MODULE_UPDATER, str(updater_path), "exec")

    original_main, main_source, encoding, has_bom, newline = read_source(main_path)
    patched_main = patch_main(main_source)

    targets = {
        main_path: original_main,
        update_path: update_path.read_bytes() if update_path.exists() else None,
        updater_path: updater_path.read_bytes() if updater_path.exists() else None,
    }

    try:
        atomic_write(main_path, patched_main, encoding, has_bom, newline)
        atomic_write(update_path, MODULE_UPDATE)
        atomic_write(updater_path, MODULE_UPDATER)

        # Confere o que foi efetivamente gravado.
        for path in (main_path, update_path, updater_path):
            compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
    except Exception:
        # Restauração em memória, sem criar cópias/arquivos de backup.
        for path, content in targets.items():
            try:
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)
            except Exception:
                pass
        raise

    print("Verificação automática do ChromeDriver aplicada.")
    print("Arquivos atualizados: " + main_path.name + ", chromedriver_update.py, chromedriver_updater.pyw")
    print("O verificador consulta o catálogo oficial em segundo plano.")
    print("Nenhuma rotina de importação foi alterada.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("Falha ao aplicar atualização: " + type(error).__name__ + ": " + str(error))
        sys.exit(1)
