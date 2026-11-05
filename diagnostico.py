# Diagnóstico da leitura das marcações e do Banco de Horas.
# O log não registra senha nem os horários individuais das marcações.

import functools
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlsplit, urlunsplit


_LOGGER_NAME = "pontomgs.diagnostico"
_LOCAL = threading.local()
_SENSITIVE_KEYS = {
    "senha", "password", "matricula", "credential", "credentials",
    "cookie", "token", "authorization", "secret",
}


def _log_path():
    """Log ao lado de diagnostico.py, independentemente da pasta de execução."""
    return Path(__file__).resolve().parent / "diagnostico_marcacoes.log"


def _build_logger():
    import sys as _sys
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(threadName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        path = _log_path()
        handler = RotatingFileHandler(
            path, maxBytes=4 * 1024 * 1024, backupCount=1, encoding="utf-8"
        )
        handler.setFormatter(formatter)
    except Exception as error:
        # Não muda silenciosamente o destino para APPDATA ou TEMP.
        # Mantém o app funcionando; a janela Sobre indica o estado indisponível.
        handler = logging.NullHandler()
        try:
            if _sys.stderr is not None:
                print("PontoMGS: não foi possível gravar o log na pasta do projeto: "
                      + str(error), file=_sys.stderr)
        except Exception:
            pass
    logger.addHandler(handler)
    return logger


LOGGER = _build_logger()


def caminho_log():
    """Retorna o caminho do arquivo de log principal."""
    for handler in LOGGER.handlers:
        if isinstance(handler, logging.FileHandler):
            return Path(handler.baseFilename)
    return _log_path()


def sanitizar(valor):
    """Remove query strings e padrões comuns de segredo de texto livre."""
    texto = str(valor)
    texto = re.sub(
        r"(?i)(https?://[^\s?#]+)\?[^\s#]*",
        r"\1?[parâmetros ocultos]",
        texto,
    )
    texto = re.sub(
        r"(?i)\b(password|senha|token|authorization)\s*[:=]\s*[^,\s;]+",
        r"\1=[oculto]",
        texto,
    )
    return texto[:900]


def resumir_url(url):
    """Mantém protocolo, host e rota; oculta query e fragmento."""
    try:
        partes = urlsplit(str(url))
        return urlunsplit((partes.scheme, partes.netloc, partes.path, "", ""))
    except Exception:
        return "[URL indisponível]"


def _safe_fields(fields):
    safe = []
    for key, value in fields.items():
        if key.lower() in _SENSITIVE_KEYS:
            continue
        if value is None or isinstance(value, (bool, int, float)):
            safe_value = value
        else:
            safe_value = sanitizar(value)
        safe.append(f"{key}={safe_value!r}")
    return " | ".join(safe)


def _emit(level, event, fields=None, exc_info=False):
    fields = fields or {}
    suffix = _safe_fields(fields)
    message = str(event) if not suffix else f"{event} | {suffix}"
    LOGGER.log(level, "%s", sanitizar(message), exc_info=exc_info)


def info(event, **fields):
    _emit(logging.INFO, event, fields)


def warning(event, **fields):
    _emit(logging.WARNING, event, fields)


def error(event, **fields):
    _emit(logging.ERROR, event, fields)


def registrar_excecao(area, etapa, **fields):
    """Grava traceback completo; chamar dentro de um bloco except."""
    _emit(
        logging.ERROR,
        f"{area} | exceção em {etapa}",
        fields,
        exc_info=True,
    )


def _incrementar(nome, quantidade=1):
    atual = getattr(_LOCAL, "operacao", None)
    if atual is not None:
        contadores = atual.setdefault("contadores", {})
        contadores[nome] = contadores.get(nome, 0) + quantidade


def resumir_resultado(area, resultado):
    """Registra estado/contagem sem despejar horários pessoais no log."""
    if isinstance(resultado, tuple):
        sucesso = bool(resultado[0]) if resultado else False
        detalhe = str(resultado[1]) if len(resultado) > 1 else ""
        if sucesso:
            info(
                f"{area} | resultado",
                sucesso=True,
                detalhe=sanitizar(detalhe)[:400],
            )
        else:
            warning(
                f"{area} | resultado",
                sucesso=False,
                detalhe=sanitizar(detalhe or "sem detalhe")[:500],
            )
        return

    if isinstance(resultado, str):
        texto = resultado.strip()
        erro_conhecido = (
            texto.lower().startswith("erro")
            or "falha" in texto.lower()
            or "não foi possível" in texto.lower()
        )
        contagem_horarios = len(re.findall(r"\b\d{2}:\d{2}\b", texto))
        fields = {
            "tipo": "texto",
            "vazio": not bool(texto),
            "quantidade_horarios_detectados": contagem_horarios,
            "tamanho": len(texto),
        }
        if erro_conhecido:
            fields["mensagem"] = sanitizar(texto)[:500]
            warning(f"{area} | resultado de erro", **fields)
        else:
            info(f"{area} | resultado", **fields)
        return

    if isinstance(resultado, bool):
        (info if resultado else warning)(
            f"{area} | resultado",
            sucesso=resultado,
            tipo="booleano",
        )
        return

    if resultado is None:
        info(f"{area} | resultado", tipo="None")
        return

    if isinstance(resultado, (list, tuple, dict, set)):
        info(
            f"{area} | resultado",
            tipo=type(resultado).__name__,
            quantidade=len(resultado),
        )
        return

    info(f"{area} | resultado", tipo=type(resultado).__name__)


def _contexto_para_funcao(nome, args, kwargs):
    contexto = {}
    if nome == "sync_mes_anterior_scraper":
        if len(args) > 2:
            contexto["periodo"] = args[2]
        elif "mes_ano" in kwargs:
            contexto["periodo"] = kwargs["mes_ano"]
    elif nome == "sync_mes_scraper":
        contexto["periodo"] = time.strftime("%m/%Y")
    elif nome == "buscar_marcacoes_selenium":
        contexto["data"] = time.strftime("%d/%m/%Y")
    return contexto


def _wrap_operacao(funcao, area, contexto_func=None):
    if getattr(funcao, "_diagnostico_wrapped", False):
        return funcao

    @functools.wraps(funcao)
    def wrapper(*args, **kwargs):
        contexto = contexto_func(args, kwargs) if contexto_func else {}
        anterior = getattr(_LOCAL, "operacao", None)
        registro = {"contadores": {}}
        _LOCAL.operacao = registro
        inicio = time.monotonic()
        info(f"{area} | início", **contexto)
        try:
            resultado = funcao(*args, **kwargs)
            resumir_resultado(area, resultado)
            return resultado
        except Exception:
            registrar_excecao(area, getattr(funcao, "__name__", "função"), **contexto)
            raise
        finally:
            duracao = round(time.monotonic() - inicio, 3)
            info(
                f"{area} | fim",
                duracao_segundos=duracao,
                **registro.get("contadores", {}),
            )
            _LOCAL.operacao = anterior

    wrapper._diagnostico_wrapped = True
    return wrapper


def instrumentar_scraper(modulo):
    """Adiciona observabilidade sem substituir regras de navegação/importação."""
    for nome, area in (
        ("buscar_marcacoes_selenium", "TELINHA"),
        ("sync_mes_scraper", "BANCO_MES_ATUAL"),
        ("sync_mes_anterior_scraper", "BANCO_HISTORICO"),
        ("_criar_driver_chrome", "DRIVER_HELPER"),
        ("criar_driver_chrome", "DRIVER_HELPER"),
    ):
        funcao = getattr(modulo, nome, None)
        if callable(funcao):
            setattr(
                modulo,
                nome,
                _wrap_operacao(
                    funcao,
                    area,
                    lambda args, kwargs, n=nome: _contexto_para_funcao(
                        n, args, kwargs
                    ),
                ),
            )

    webdriver_modulo = getattr(modulo, "webdriver", None)
    chrome = getattr(webdriver_modulo, "Chrome", None)
    if callable(chrome) and not getattr(chrome, "_diagnostico_wrapped", False):
        original_chrome = chrome

        @functools.wraps(original_chrome)
        def chrome_observado(*args, **kwargs):
            try:
                import sys
                local_driver = Path(__file__).resolve().parent / "chromedriver.exe"
                info(
                    "DRIVER | criando sessão Selenium",
                    chromedriver_local_existe=local_driver.is_file(),
                    python=sys.version.split()[0],
                )
                driver = original_chrome(*args, **kwargs)
            except Exception:
                registrar_excecao("DRIVER", "webdriver.Chrome")
                raise

            try:
                capacidades = getattr(driver, "capabilities", {}) or {}
                info(
                    "DRIVER | sessão iniciada",
                    versao_chrome=capacidades.get("browserVersion", "indisponível"),
                    versao_driver=(
                        (capacidades.get("chrome") or {}).get(
                            "chromedriverVersion", "indisponível"
                        )
                    ),
                )
            except Exception:
                info("DRIVER | sessão iniciada; capabilities indisponíveis")
            return driver

        chrome_observado._diagnostico_wrapped = True
        webdriver_modulo.Chrome = chrome_observado


def _metadata_database(nome, args, kwargs):
    if nome in ("update_dia_banco", "importar_marcacoes_relatorio"):
        data = args[0] if args else kwargs.get("data", "")
        fields = {"data": data}
        if nome == "update_dia_banco":
            manual = kwargs.get("is_manual", args[6] if len(args) > 6 else False)
            fields["manual"] = bool(manual)
            fields["campos_preenchidos"] = sum(
                bool(item) for item in args[1:5]
            )
        else:
            marcacoes = args[1] if len(args) > 1 else kwargs.get("marcacoes", [])
            try:
                fields["quantidade_marcacoes"] = len(marcacoes or [])
            except Exception:
                fields["quantidade_marcacoes"] = "indisponível"
        return fields

    if nome in ("get_banco_horas", "get_banco_horas_relatorio"):
        return {"periodo": args[0] if args else kwargs.get("mes_ano", "")}
    if nome == "check_dia_completo":
        return {"data": args[0] if args else kwargs.get("data", "")}
    if nome in ("garantir_dias_mes_banco", "garantir_dias_mes"):
        return {"periodo": args[0] if args else kwargs.get("mes_ano", "")}
    return {}


def instrumentar_database(modulo):
    nomes = (
        "update_dia_banco",
        "importar_marcacoes_relatorio",
        "check_dia_completo",
        "get_banco_horas",
        "get_banco_horas_relatorio",
        "get_meses_disponiveis",
        "garantir_dias_mes_banco",
        "garantir_dias_mes",
    )
    for nome in nomes:
        funcao = getattr(modulo, nome, None)
        if not callable(funcao) or getattr(funcao, "_diagnostico_wrapped", False):
            continue

        def make_wrapper(original, function_name):
            @functools.wraps(original)
            def wrapper(*args, **kwargs):
                contexto = _metadata_database(function_name, args, kwargs)
                info(f"BANCO_DADOS.{function_name} | início", **contexto)
                try:
                    resultado = original(*args, **kwargs)
                except Exception:
                    registrar_excecao(
                        "BANCO_DADOS",
                        function_name,
                        **contexto,
                    )
                    raise

                if function_name == "update_dia_banco":
                    _incrementar("chamadas_update_dia_banco")
                elif function_name == "importar_marcacoes_relatorio":
                    _incrementar("chamadas_importar_relatorio")
                elif function_name == "check_dia_completo":
                    _incrementar("consultas_dia_completo")
                    if resultado:
                        _incrementar("dias_pulados_por_completude")
                if isinstance(resultado, (list, tuple)):
                    info(
                        f"BANCO_DADOS.{function_name} | concluído",
                        quantidade=len(resultado),
                        **contexto,
                    )
                elif function_name == "check_dia_completo":
                    info(
                        f"BANCO_DADOS.{function_name} | concluído",
                        completo=bool(resultado),
                        **contexto,
                    )
                else:
                    info(f"BANCO_DADOS.{function_name} | concluído", **contexto)
                return resultado

            wrapper._diagnostico_wrapped = True
            return wrapper

        setattr(modulo, nome, make_wrapper(funcao, nome))


def _contexto_app(nome, args, kwargs):
    contexto = {}
    instancia = args[0] if args else None
    if nome == "sincronizar_banco" and instancia is not None:
        try:
            contexto["periodo_selecionado"] = (
                instancia.mes_selecionado_var.get().strip()
            )
        except Exception:
            contexto["periodo_selecionado"] = "indisponível"
        try:
            config = getattr(instancia, "config", {}) or {}
            contexto["credenciais_configuradas"] = bool(
                config.get("matricula") and config.get("senha")
            )
        except Exception:
            contexto["credenciais_configuradas"] = "indisponível"
    elif nome == "atualizar_lista_banco" and instancia is not None:
        try:
            contexto["periodo_selecionado"] = (
                instancia.mes_selecionado_var.get().strip()
            )
        except Exception:
            pass
    elif nome == "atualizar_interface_marcacoes" and len(args) > 1:
        resultado = args[1]
        contexto["resultado"] = type(resultado).__name__
    return contexto


def instrumentar_app(classe):
    for nome, area in (
        ("sincronizar_banco", "TELA_BANCO"),
        ("atualizar_lista_banco", "TELA_BANCO_LISTA"),
        ("atualizar_interface_marcacoes", "TELINHA_UI"),
        ("atualizar_marcacoes_loop", "TELINHA_THREAD"),
    ):
        funcao = getattr(classe, nome, None)
        if not callable(funcao) or getattr(funcao, "_diagnostico_wrapped", False):
            continue
        setattr(
            classe,
            nome,
            _wrap_operacao(
                funcao,
                area,
                lambda args, kwargs, n=nome: _contexto_app(n, args, kwargs),
            ),
        )


info(
    "DIAGNOSTICO | inicializado",
    arquivo=str(caminho_log()),
)
