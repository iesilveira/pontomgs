"""Chrome for Testing e ChromeDriver exclusivos do PontoMGS (Windows x64).

Não usa Chrome pessoal, PATH, Selenium Manager ou chromedriver.exe do projeto.
Downloads oficiais, instalação por versão, publicação atômica do par validado.
"""
import contextlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

CATALOG_URL = ("https://googlechromelabs.github.io/chrome-for-testing/"
               "last-known-good-versions-with-downloads.json")
_THREAD_LOCK = threading.RLock()
_VERSION = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
_verified = set()


def _log(event, **fields):
    # Reutiliza somente o diagnóstico já instalado, sem criar logs adicionais.
    try:
        import diagnostico
        diagnostico.info("CHROME_GERENCIADO | " + event, **fields)
    except Exception:
        pass


def base_dir():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "PontoMGS" / "ChromeForTesting"


def _windows():
    if os.name != "nt" or not (os.environ.get("PROCESSOR_ARCHITEW6432") or
                              os.environ.get("PROCESSOR_ARCHITECTURE", platform.machine())).lower() in ("amd64", "x86_64", "arm64"):
        raise RuntimeError("O navegador gerenciado requer Windows de 64 bits.")


def _atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        name.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(str(name), str(path))
    finally:
        with contextlib.suppress(OSError):
            name.unlink()


def _url(url, expected=None):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "storage.googleapis.com"
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError("Endereço de download não autorizado.")
    if expected and parsed.path != expected:
        raise ValueError("Caminho de download diferente do catálogo esperado.")
    return url


def stable():
    req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "PontoMGS-CfT/2.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.geturl() != CATALOG_URL:
            raise ValueError("Redirecionamento inesperado do catálogo.")
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Catálogo excessivamente grande.")
    item = json.loads(raw.decode("utf-8"))["channels"]["Stable"]
    version = str(item["version"])
    if not _VERSION.fullmatch(version):
        raise ValueError("Versão inválida no catálogo.")
    metadata = {"version": version}
    for binary in ("chrome", "chromedriver"):
        asset = next(x for x in item["downloads"][binary] if x["platform"] == "win64")
        expected = "/chrome-for-testing-public/{}/win64/{}-win64.zip".format(version, binary)
        metadata[binary] = _url(str(asset["url"]), expected)
    return metadata


@contextlib.contextmanager
def installation_lock():
    """Lock de SO liberado inclusive se o processo terminar inesperadamente."""
    with _THREAD_LOCK:
        base_dir().mkdir(parents=True, exist_ok=True)
        lock = (base_dir() / "installation.lock").open("a+b")
        try:
            lock.seek(0, 2)
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            import msvcrt
            deadline = time.monotonic() + 1200
            while True:
                try:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Outra instalação do navegador ainda está em andamento.")
                    time.sleep(.4)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            lock.close()


def _paths(folder):
    return folder / "chrome-win64" / "chrome.exe", folder / "chromedriver-win64" / "chromedriver.exe"


def _run(args, timeout=25):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("Não foi possível verificar o executável do navegador.")
    return result.stdout.strip()


def _verify_files(folder, version):
    chrome, driver = _paths(folder)
    if not chrome.is_file() or not driver.is_file():
        raise RuntimeError("O par Chrome/ChromeDriver está incompleto.")
    key = (str(folder), chrome.stat().st_mtime_ns, chrome.stat().st_size,
           driver.stat().st_mtime_ns, driver.stat().st_size)
    if key in _verified:
        return
    output = _run([str(driver), "--version"])
    match = re.search(r"ChromeDriver\s+(\d+\.\d+\.\d+\.\d+)", output)
    if not match or match.group(1) != version:
        raise RuntimeError("ChromeDriver não corresponde à versão do pacote.")
    # Lê metadados do EXE; não inicia janela do navegador.
    ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    literal = str(chrome).replace("'", "''")
    output = _run([str(ps), "-NoProfile", "-NonInteractive", "-Command",
                   "(Get-Item -LiteralPath '{}').VersionInfo.ProductVersion".format(literal)])
    match = re.search(r"\d+\.\d+\.\d+\.\d+", output)
    if not match or match.group(0) != version:
        raise RuntimeError("Chrome não corresponde à versão do pacote.")
    _verified.add(key)


def current():
    """Consulta local; nenhuma conexão é necessária com um par instalado."""
    try:
        data = json.loads((base_dir() / "current.json").read_text(encoding="utf-8"))
        version = data["version"]
        folder_name = data["folder"]
        if not _VERSION.fullmatch(version):
            return None
        if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+-[a-f0-9]{32}", folder_name):
            return None
        folder = base_dir() / "versions" / folder_name
        _verify_files(folder, version)
        chrome, driver = _paths(folder)
        return {"version": version, "folder": str(folder),
                "chrome": str(chrome), "chromedriver": str(driver)}
    except Exception as error:
        _log("par local indisponível", erro=type(error).__name__)
        return None


def _download(url, path, progress, label):
    _url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "PontoMGS-CfT/2.0"})
    with urllib.request.urlopen(req, timeout=60) as response, path.open("wb") as dest:
        # Os objetos oficiais não precisam de redirecionamento para outro host.
        if response.geturl() != url:
            raise ValueError("Redirecionamento inesperado do download.")
        total = int(response.headers.get("Content-Length", "0"))
        if total > 1024 * 1024 * 1024:
            raise ValueError("Arquivo excede o limite de download.")
        count = 0
        last_notice = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            if count > 1024 * 1024 * 1024:
                raise ValueError("Download excede o limite permitido.")
            dest.write(chunk)
            now = time.monotonic()
            if now - last_notice > .25:
                progress("{}: {:.1f} MB{}".format(label, count / 1048576,
                         " / {:.1f} MB".format(total / 1048576) if total else ""))
                last_notice = now
        if not count or (total and total != count):
            raise RuntimeError("Download incompleto: " + label)


def _extract(archive, dest, binary):
    expected_root = binary + "-win64"
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if sum(x.file_size for x in entries) > 3 * 1024 ** 3:
            raise ValueError("Pacote descompactado excessivamente grande.")
        for item in entries:
            name = item.filename.replace("\\", "/")
            parts = name.split("/")
            if (not name or name.startswith("/") or ":" in name or ".." in parts
                    or parts[0] != expected_root or ((item.external_attr >> 16) & 0o170000) == 0o120000):
                raise ValueError("Caminho inseguro no arquivo ZIP.")
        # ZipFile verifica CRC ao ler e extrair os dados.
        z.extractall(dest)


def _smoke(folder, version):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    chrome, driver_path = _paths(folder)
    options = webdriver.ChromeOptions()
    options.binary_location = str(chrome)
    options.add_argument("--headless=new")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(str(driver_path)), options=options)
        capabilities = driver.capabilities or {}
        browser = capabilities.get("browserVersion", "")
        actual = (capabilities.get("chrome") or {}).get("chromedriverVersion", "").split(" ")[0]
        if browser != version or actual != version:
            raise RuntimeError("O teste Selenium detectou versões diferentes no par.")
    finally:
        if driver is not None:
            driver.quit()


def install(metadata=None, progress=None, force=False):
    _windows()
    progress = progress or (lambda text: None)
    with installation_lock():
        installed = current()
        if metadata is None and installed and not force:
            return installed
        progress("Consultando catálogo oficial...")
        metadata = metadata or stable()
        version = str(metadata["version"])
        if not _VERSION.fullmatch(version):
            raise ValueError("Versão inválida.")
        if installed and installed["version"] == version and not force:
            return installed
        for binary in ("chrome", "chromedriver"):
            expected = "/chrome-for-testing-public/{}/win64/{}-win64.zip".format(version, binary)
            _url(metadata[binary], expected)
        versions = base_dir() / "versions"
        versions.mkdir(parents=True, exist_ok=True)
        # Mesmo volume do destino: rename e manifesto atômicos.
        work = Path(tempfile.mkdtemp(prefix=".install-", dir=str(base_dir())))
        published = None
        try:
            payload = work / "payload"
            payload.mkdir()
            for binary, label in (("chrome", "Chrome for Testing"), ("chromedriver", "ChromeDriver")):
                archive = work / (binary + ".zip")
                _download(metadata[binary], archive, progress, label)
                progress("Extraindo " + label + "...")
                _extract(archive, payload, binary)
                archive.unlink()
            progress("Validando versões e testando Selenium sem janela...")
            _verify_files(payload, version)
            _smoke(payload, version)
            folder_name = version + "-" + uuid.uuid4().hex
            published = versions / folder_name
            os.replace(str(payload), str(published))
            _atomic_json(base_dir() / "current.json",
                         {"version": version, "folder": folder_name})
            _log("par instalado e validado", versao=version)
            # O par anterior permanece utilizável por sessões em andamento.
            # Não apagamos executáveis que outro processo possa estar usando.
            return {"version": version, "folder": str(published),
                    "chrome": str(_paths(published)[0]), "chromedriver": str(_paths(published)[1])}
        except Exception as error:
            _log("instalação não concluída; par anterior preservado", erro=type(error).__name__)
            raise
        finally:
            shutil.rmtree(work, ignore_errors=True)


def criar_driver(options=None, **kwargs):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    _windows()
    if options is None:
        options = kwargs.pop("chrome_options", None)
    if options is None:
        options = kwargs.pop("opcoes", None)
    if options is None:
        options = webdriver.ChromeOptions()
    visible = kwargs.pop("visivel", kwargs.pop("visible", None))
    headless = kwargs.pop("headless", None)
    if visible is None and headless is not None:
        visible = not bool(headless)
    if visible is True:
        for arg in list(options.arguments):
            if str(arg).startswith("--headless"):
                options.arguments.remove(arg)
    elif visible is False and not any(str(x).startswith("--headless") for x in options.arguments):
        options.add_argument("--headless=new")
    # Caminhos antigos são intencionalmente ignorados: nunca misturar o par.
    for key in ("driver_path", "executable_path", "service"):
        kwargs.pop(key, None)
    pair = current()
    if pair is None:
        _log("preparando primeira instalação")
        pair = install()
    options.binary_location = pair["chrome"]
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    _log("criando sessão", versao=pair["version"])
    # Usa o webdriver normal para preservar os wrappers de diagnóstico existentes.
    return webdriver.Chrome(service=Service(pair["chromedriver"]), options=options, **kwargs)
