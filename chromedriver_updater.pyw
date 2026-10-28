# Atualizador gráfico autônomo do ChromeDriver para Windows.
# Obtém o Stable e o URL win64 do catálogo JSON oficial do Chrome for Testing.

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk


CATALOG_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "last-known-good-versions-with-downloads.json"
)
CHUNK_SIZE = 128 * 1024


def _version_tuple(version):
    numbers = tuple(int(part) for part in re.findall(r"\d+", str(version)))
    return (numbers + (0, 0, 0, 0))[:4]


def _parse_driver_version(text):
    match = re.search(r"ChromeDriver\s+(\d+(?:\.\d+){1,3})", text or "", re.I)
    if not match:
        match = re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b", text or "")
    return match.group(1) if match else None


def _fetch_stable():
    request = urllib.request.Request(
        CATALOG_URL,
        headers={"User-Agent": "PontoMGS-ChromeDriver-Updater/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    stable = payload["channels"]["Stable"]
    version = str(stable["version"])
    asset = next(
        item for item in stable["downloads"]["chromedriver"]
        if item.get("platform") == "win64"
    )
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


class ChromeDriverUpdater:
    def __init__(self, project_dir, restart_command):
        self.project_dir = Path(project_dir).resolve()
        self.driver_path = self.project_dir / "chromedriver.exe"
        self.restart_command = restart_command
        self.cancel_requested = threading.Event()
        self.restarting = False

        self.root = tk.Tk()
        self.root.title("Atualização do ChromeDriver")
        self.root.configure(bg="white")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.request_cancel)

        width, height = 520, 255
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        tk.Label(
            self.root,
            text="Atualizando componente do sistema",
            font=("Segoe UI", 14, "bold"),
            fg="#00205B",
            bg="white",
        ).pack(pady=(18, 7))

        self.status = tk.StringVar(value="Consultando a versão Stable oficial...")
        tk.Label(
            self.root,
            textvariable=self.status,
            font=("Segoe UI", 10),
            fg="#222222",
            bg="white",
            wraplength=470,
            justify="center",
        ).pack(padx=20, pady=8)

        self.details = tk.StringVar(value="")
        tk.Label(
            self.root,
            textvariable=self.details,
            font=("Segoe UI", 9),
            fg="#555555",
            bg="white",
            wraplength=470,
            justify="center",
        ).pack(padx=20, pady=4)

        self.progress = ttk.Progressbar(
            self.root,
            orient="horizontal",
            mode="determinate",
            length=420,
            maximum=100,
        )
        self.progress.pack(pady=12)

        self.button = tk.Button(
            self.root,
            text="Aguarde...",
            state="disabled",
            command=self.restart_now,
            font=("Segoe UI", 9, "bold"),
            bg="#e5e5e5",
            relief="flat",
            padx=16,
            pady=6,
        )
        self.button.pack(pady=(0, 12))

        threading.Thread(
            target=self.worker,
            name="chromedriver-update-download",
            daemon=True,
        ).start()

    def set_ui(self, status=None, details=None, progress=None, button=None):
        def apply():
            if status is not None:
                self.status.set(status)
            if details is not None:
                self.details.set(details)
            if progress is not None:
                self.progress["value"] = max(0, min(100, progress))
            if button is not None:
                self.button.configure(text=button, state="normal")
        try:
            self.root.after(0, apply)
        except Exception:
            pass

    def request_cancel(self):
        self.cancel_requested.set()
        self.set_ui(
            status="Cancelando com segurança; o sistema será reaberto...",
            button="Reabrir sistema",
        )

    def _check_cancel(self):
        if self.cancel_requested.is_set():
            raise RuntimeError("Atualização cancelada pelo usuário.")

    def _download(self, metadata, zip_path):
        request = urllib.request.Request(
            metadata["url"],
            headers={"User-Agent": "PontoMGS-ChromeDriver-Updater/1.0"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            total = int(response.headers.get("Content-Length", "0") or "0")
            downloaded = 0
            last_percent = -1
            with zip_path.open("wb") as output:
                while True:
                    self._check_cancel()
                    block = response.read(CHUNK_SIZE)
                    if not block:
                        break
                    output.write(block)
                    downloaded += len(block)
                    if total > 0:
                        percent = int(downloaded * 100 / total)
                        if percent != last_percent:
                            last_percent = percent
                            self.set_ui(
                                status=f"Baixando ChromeDriver Stable {metadata['version']}...",
                                progress=percent,
                            )
        if not zip_path.is_file() or zip_path.stat().st_size == 0:
            raise RuntimeError("O download terminou sem um arquivo válido.")

    def _extract_and_validate(self, zip_path, staging_dir, expected_version):
        with zipfile.ZipFile(zip_path, "r") as archive:
            member = None
            for name in archive.namelist():
                normalized = name.replace("\\", "/")
                if normalized == "chromedriver-win64/chromedriver.exe":
                    member = name
                    break
            if member is None:
                raise RuntimeError(
                    "O ZIP oficial não contém chromedriver-win64/chromedriver.exe."
                )
            candidate = staging_dir / "chromedriver.exe"
            with archive.open(member, "r") as source, candidate.open("wb") as target:
                shutil.copyfileobj(source, target)

        if not candidate.is_file() or candidate.stat().st_size == 0:
            raise RuntimeError("O executável extraído está vazio.")

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            [str(candidate), "--version"],
            capture_output=True,
            text=True,
            timeout=12,
            creationflags=flags,
            check=False,
        )
        found = _parse_driver_version(
            (result.stdout or "") + "\n" + (result.stderr or "")
        )
        if result.returncode != 0 or found != expected_version:
            raise RuntimeError(
                "A versão do executável baixado não corresponde ao catálogo "
                f"(esperada {expected_version}; encontrada {found or 'desconhecida'})."
            )
        return candidate

    def _replace_driver(self, candidate):
        last_error = None
        for attempt in range(40):
            self._check_cancel()
            try:
                os.replace(str(candidate), str(self.driver_path))
                return
            except PermissionError as error:
                last_error = error
                time.sleep(1)
            except OSError as error:
                last_error = error
                time.sleep(1)
        raise RuntimeError(
            "Não foi possível substituir chromedriver.exe. "
            "Verifique se o aplicativo foi encerrado e se a pasta permite gravação. "
            f"Detalhe: {last_error}"
        )

    def worker(self):
        staging = None
        try:
            self._check_cancel()
            metadata = _fetch_stable()
            self.set_ui(
                status=f"Versão Stable encontrada: {metadata['version']}",
                details=(
                    "Binary: chromedriver  |  Plataforma: win64\n"
                    f"Origem oficial: {metadata['url']}"
                ),
                progress=0,
            )
            self._check_cancel()

            current = None
            if self.driver_path.is_file():
                try:
                    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    result = subprocess.run(
                        [str(self.driver_path), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=8,
                        creationflags=flags,
                        check=False,
                    )
                    current = _parse_driver_version(
                        (result.stdout or "") + "\n" + (result.stderr or "")
                    )
                except Exception:
                    current = None

            if current and _version_tuple(current) >= _version_tuple(metadata["version"]):
                self.finish(
                    True,
                    f"O ChromeDriver já está atualizado ({current}).",
                )
                return

            self.project_dir.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(
                prefix=".chromedriver_update_",
                dir=str(self.project_dir),
            ))
            zip_path = staging / "chromedriver-win64.zip"

            self.set_ui(status="Baixando o pacote oficial...", progress=0)
            self._download(metadata, zip_path)
            self._check_cancel()

            self.set_ui(status="Validando o executável baixado...", progress=100)
            candidate = self._extract_and_validate(
                zip_path,
                staging,
                metadata["version"],
            )
            self._check_cancel()

            self.set_ui(status="Instalando ChromeDriver na pasta do projeto...")
            self._replace_driver(candidate)
            self.finish(
                True,
                f"ChromeDriver {metadata['version']} atualizado com sucesso.",
            )

        except Exception as error:
            self.finish(False, str(error) or type(error).__name__)
        finally:
            if staging is not None:
                try:
                    shutil.rmtree(staging, ignore_errors=True)
                except Exception:
                    pass

    def finish(self, success, message):
        if success:
            status = message + "\nReabrindo o sistema..."
            delay = 1800
        else:
            status = (
                "A atualização não foi concluída.\n"
                f"{message}\nO sistema será reaberto."
            )
            delay = 10000
        self.set_ui(
            status=status,
            button="Reabrir sistema agora",
        )
        try:
            self.root.after(delay, self.restart_now)
        except Exception:
            pass

    def restart_now(self):
        if self.restarting:
            return
        self.restarting = True
        try:
            if self.restart_command and all(
                isinstance(part, str) for part in self.restart_command
            ):
                subprocess.Popen(
                    self.restart_command,
                    cwd=str(self.project_dir),
                    close_fds=True,
                )
        except Exception as error:
            self.status.set(
                "Não foi possível reabrir automaticamente o sistema.\n"
                f"Detalhe: {error}"
            )
            self.restarting = False
            return
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--restart-command", required=True)
    return parser.parse_args()


def main():
    args = _parse_args()
    try:
        restart_command = json.loads(args.restart_command)
        if not isinstance(restart_command, list) or not restart_command:
            raise ValueError("Comando de reinício inválido.")
        restart_command = [str(part) for part in restart_command]
    except Exception:
        restart_command = []

    updater = ChromeDriverUpdater(args.project_dir, restart_command)
    updater.run()


if __name__ == "__main__":
    main()
