"""
Autor: Ismael Elói da Silveira Silva
Descrição: Atualizador do Assistente do PontoWeb MGS.

Versão: 2026.09.03-08

Alterações:
- Adiciona "Esquecimento de marcação" ao menu da bandeja.
- Exibe a terceira marcação prevista em vermelho quando o retorno do almoço
  tiver sido esquecido.
- O ajuste é somente visual, vale apenas no dia corrente e não grava no banco.
- Interrompe o contador de almoço quando o esquecimento estiver ativado.
- Corrige todos os campos de horário para digitação da direita para a esquerda.
- Cria backup e restaura o arquivo original em caso de falha.
"""

import os
import re
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path


VERSAO = "2026.09.03-08"
BASE_DIR = Path(__file__).resolve().parent
IDENTIFICADOR = datetime.now().strftime("%Y%m%d_%H%M%S")
PASTA_BACKUP = BASE_DIR / f"backup_atualizacao_{IDENTIFICADOR}"
RELATORIO = BASE_DIR / f"relatorio_atualizacao_{IDENTIFICADOR}.txt"


METODOS_ESQUECIMENTO = r'''
    def esquecimento_marcacao_ativo(self):
        """
        Informa se a previsão visual do retorno deve ser tratada como
        uma marcação esquecida no dia corrente.

        O estado não é persistido e não altera self.marca3 nem o banco.
        """

        hoje = datetime.date.today()

        if self.esquecimento_retorno_data != hoje:
            self.esquecimento_retorno_data = None
            return False

        if self.marca3 or self.marca4 or not self.marca2:
            self.esquecimento_retorno_data = None
            return False

        return True

    def ativar_esquecimento_marcacao(self):
        """
        Ativa somente na telinha, e apenas hoje, a previsão vermelha
        da terceira marcação, uma hora após a segunda marcação.
        """

        if not self.marca2:
            messagebox.showwarning(
                "Esquecimento de marcação",
                "Não existe uma marcação de saída para o almoço hoje."
            )
            return

        if self.marca3:
            messagebox.showinfo(
                "Esquecimento de marcação",
                "A marcação de retorno do almoço já foi registrada."
            )
            return

        if self.marca4:
            messagebox.showinfo(
                "Esquecimento de marcação",
                "O dia já possui uma marcação de saída."
            )
            return

        self.esquecimento_retorno_data = datetime.date.today()

        marcacoes_atuais = [
            horario
            for horario in (
                self.marca1,
                self.marca2,
                self.marca3,
                self.marca4
            )
            if horario
        ]

        self.atualizar_interface_marcacoes(
            " ".join(marcacoes_atuais)
        )

        self.show_main_window()

    def tray_esquecimento_marcacao(self, icon, item):
        self.root.after(
            0,
            self.ativar_esquecimento_marcacao
        )
'''


METODOS_HORARIO = r'''
    def formatar_tempo_generico(self, string_var, entry_widget):
        """
        Mantém o valor no formato HH:MM sem deslocar o cursor durante
        a digitação. A atualização do cursor ocorre somente após o Tk
        concluir o processamento do evento atual.
        """

        if getattr(string_var, "_formatando_horario", False):
            return

        texto = string_var.get()
        digitos = "".join(
            caractere
            for caractere in texto
            if caractere.isdigit()
        )[-4:]

        if not digitos:
            formatado = ""
        else:
            digitos = digitos.zfill(4)
            formatado = f"{digitos[:2]}:{digitos[2:]}"

        if texto != formatado:
            try:
                string_var._formatando_horario = True
                string_var.set(formatado)
            finally:
                string_var._formatando_horario = False

        if entry_widget:
            try:
                entry_widget.after_idle(
                    lambda widget=entry_widget: (
                        widget.icursor(tk.END)
                        if widget.winfo_exists()
                        else None
                    )
                )
            except tk.TclError:
                pass

    def digitar_horario_direita_esquerda(
        self,
        event,
        string_var,
        entry_widget
    ):
        """
        Implementa entrada no estilo calculadora:

            1 -> 00:01
            2 -> 00:12
            3 -> 01:23
            4 -> 12:34

        Backspace remove o último dígito e desloca os demais para a direita.
        """

        # Mantém atalhos como Ctrl+C, Ctrl+V, Ctrl+X e Ctrl+A.
        if event.state & 0x4:
            entry_widget.after_idle(
                lambda: self.formatar_tempo_generico(
                    string_var,
                    entry_widget
                )
            )
            return None

        if event.char and event.char.isdigit():
            atuais = "".join(
                caractere
                for caractere in string_var.get()
                if caractere.isdigit()
            ).zfill(4)[-4:]

            novos = (atuais + event.char)[-4:]
            string_var.set(
                f"{novos[:2]}:{novos[2:]}"
            )
            entry_widget.after_idle(
                lambda: entry_widget.icursor(tk.END)
            )
            return "break"

        if event.keysym in ("BackSpace", "Delete"):
            atuais = "".join(
                caractere
                for caractere in string_var.get()
                if caractere.isdigit()
            ).zfill(4)[-4:]

            novos = ("0" + atuais[:-1])[-4:]
            string_var.set(
                f"{novos[:2]}:{novos[2:]}"
            )
            entry_widget.after_idle(
                lambda: entry_widget.icursor(tk.END)
            )
            return "break"

        if event.keysym in (
            "Tab",
            "ISO_Left_Tab",
            "Return",
            "KP_Enter",
            "Escape",
            "Left",
            "Right",
            "Home",
            "End"
        ):
            return None

        if event.char:
            return "break"

        return None

    def configurar_campo_horario(
        self,
        entry_widget,
        string_var
    ):
        """Configura um campo para digitação de horário da direita para a esquerda."""

        entry_widget.bind(
            "<KeyPress>",
            lambda event: self.digitar_horario_direita_esquerda(
                event,
                string_var,
                entry_widget
            )
        )

        entry_widget.bind(
            "<Button-1>",
            lambda event: entry_widget.after_idle(
                lambda: entry_widget.icursor(tk.END)
            )
        )

        entry_widget.bind(
            "<FocusIn>",
            lambda event: entry_widget.after_idle(
                lambda: entry_widget.icursor(tk.END)
            )
        )
'''


def localizar_arquivo():
    for nome in ("main.pyw", "main.py"):
        caminho = BASE_DIR / nome
        if caminho.exists() and caminho.is_file():
            return caminho
    raise RuntimeError("main.pyw ou main.py não foi encontrado na pasta do atualizador.")


def ler_arquivo(caminho):
    dados = caminho.read_bytes()
    bom = dados.startswith(b"\xef\xbb\xbf")
    try:
        texto = dados.decode("utf-8-sig")
        codificacao = "utf-8"
    except UnicodeDecodeError:
        texto = dados.decode("latin-1")
        codificacao = "latin-1"
        bom = False

    quebra = "\r\n" if "\r\n" in texto else "\n"
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    return texto, codificacao, bom, quebra


def gravar_arquivo(caminho, texto, codificacao, bom, quebra):
    saida = texto if quebra == "\n" else texto.replace("\n", quebra)
    dados = saida.encode(codificacao)
    if codificacao == "utf-8" and bom:
        dados = b"\xef\xbb\xbf" + dados

    temporario = caminho.with_name(caminho.name + ".atualizando")
    temporario.write_bytes(dados)
    os.replace(str(temporario), str(caminho))


def validar(texto, nome):
    try:
        compile(texto, nome, "exec")
    except SyntaxError as erro:
        raise RuntimeError(
            f"Erro de sintaxe em {nome}, linha {erro.lineno}, "
            f"coluna {erro.offset}: {erro.msg}"
        ) from erro


def localizar_metodo(texto, nome):
    inicio_match = re.search(
        rf"(?m)^    def {re.escape(nome)}\s*\(",
        texto
    )
    if not inicio_match:
        raise RuntimeError(f"Método {nome} não encontrado.")

    fim_match = re.search(
        r"(?m)^(?:    def |if __name__)",
        texto[inicio_match.end():]
    )
    fim = (
        inicio_match.end() + fim_match.start()
        if fim_match
        else len(texto)
    )
    return inicio_match.start(), fim


def substituir_metodo(texto, nome, codigo):
    inicio, fim = localizar_metodo(texto, nome)
    return texto[:inicio] + codigo.strip("\n") + "\n\n" + texto[fim:]


def inserir_antes_metodo(texto, nome, codigo):
    inicio, _ = localizar_metodo(texto, nome)
    return texto[:inicio] + codigo.strip("\n") + "\n\n" + texto[inicio:]


def alterar_metodo(texto, nome, transformador):
    inicio, fim = localizar_metodo(texto, nome)
    metodo = texto[inicio:fim]
    atualizado = transformador(metodo)
    if atualizado == metodo:
        raise RuntimeError(f"Nenhuma alteração foi aplicada ao método {nome}.")
    return texto[:inicio] + atualizado + texto[fim:]


def atualizar_interface_marcacoes(metodo):
    antigo = '''                    elif m2:
                        self.text_marcacoes.insert(
                            tk.END,
                            add_h(m2, 1),
                            "cinza"
                        )'''

    novo = '''                    elif m2:
                        horario_retorno_previsto = add_h(m2, 1)
                        tag_retorno_previsto = (
                            "vermelho"
                            if self.esquecimento_marcacao_ativo()
                            else "cinza"
                        )

                        self.text_marcacoes.insert(
                            tk.END,
                            horario_retorno_previsto,
                            tag_retorno_previsto
                        )'''

    if antigo not in metodo:
        if "tag_retorno_previsto" in metodo:
            return metodo
        raise RuntimeError("Bloco da previsão da terceira marcação não encontrado.")

    return metodo.replace(antigo, novo, 1)


def atualizar_clock(metodo):
    antigo = "if self.marca2 and not self.marca3:"
    novo = (
        "if (\n"
        "                        self.marca2\n"
        "                        and not self.marca3\n"
        "                        and not self.esquecimento_marcacao_ativo()\n"
        "                    ):"
    )

    if novo in metodo:
        return metodo
    if antigo not in metodo:
        raise RuntimeError("Contador do almoço não encontrado em update_clock_loop.")
    return metodo.replace(antigo, novo, 1)


def atualizar_monitor(metodo):
    antigo = '''                    em_almoco = bool(
                        self.marca2
                        and not self.marca3
                        and not self.marca4
                    )'''

    novo = '''                    em_almoco = bool(
                        self.marca2
                        and not self.marca3
                        and not self.marca4
                        and not self.esquecimento_marcacao_ativo()
                    )'''

    if novo in metodo:
        return metodo
    if antigo not in metodo:
        raise RuntimeError("Controle de almoço não encontrado em monitor_system.")
    return metodo.replace(antigo, novo, 1)


def atualizar_main(texto):
    # Texto do menu.
    if "TEXT_TRAY_ESQUECIMENTO" not in texto:
        marcador = 'TEXT_TRAY_ATUALIZAR = "Atualizar marcações"'
        if marcador not in texto:
            raise RuntimeError("Constante TEXT_TRAY_ATUALIZAR não encontrada.")
        texto = texto.replace(
            marcador,
            marcador + '\nTEXT_TRAY_ESQUECIMENTO = "Esquecimento de marcação"',
            1
        )

    # Estado exclusivamente em memória e limitado ao dia atual.
    if "self.esquecimento_retorno_data = None" not in texto:
        marcador = "        self.data_controle_lembretes = datetime.date.today()"
        if marcador not in texto:
            raise RuntimeError("Estado de controle de data não encontrado.")
        texto = texto.replace(
            marcador,
            marcador + "\n        self.esquecimento_retorno_data = None",
            1
        )

    # Cor da terceira marcação prevista esquecida.
    if 'tag_configure("vermelho"' not in texto:
        marcador = '        self.text_marcacoes.tag_configure("cinza", foreground="#999999")'
        if marcador not in texto:
            raise RuntimeError("Configuração da tag cinza não encontrada.")
        texto = texto.replace(
            marcador,
            marcador + '\n        self.text_marcacoes.tag_configure("vermelho", foreground=settings.COLOR_BUTTON_RED)',
            1
        )

    # Métodos do estado visual.
    if "def esquecimento_marcacao_ativo(" not in texto:
        texto = inserir_antes_metodo(
            texto,
            "update_clock_loop",
            METODOS_ESQUECIMENTO
        )

    # Exibição vermelha da terceira marcação prevista.
    inicio, fim = localizar_metodo(texto, "atualizar_interface_marcacoes")
    metodo = texto[inicio:fim]
    if "tag_retorno_previsto" not in metodo:
        texto = alterar_metodo(
            texto,
            "atualizar_interface_marcacoes",
            atualizar_interface_marcacoes
        )

    # Campos de horário.
    texto = substituir_metodo(
        texto,
        "formatar_tempo_generico",
        METODOS_HORARIO
    )

    # Configuração do campo de almoço.
    if "self.configurar_campo_horario(self.ent_almoco, self.almoco_var)" not in texto:
        marcador = '''        self.ent_almoco.bind(
            "<Button-1>",'''
        if marcador not in texto:
            raise RuntimeError("Campo de horário do almoço não encontrado.")
        texto = texto.replace(
            marcador,
            "        self.configurar_campo_horario(self.ent_almoco, self.almoco_var)\n\n" + marcador,
            1
        )

    # Configuração do campo de horário do lembrete.
    if "self.configurar_campo_horario(self.ent_tempo_lembrete, self.tempo_lembrete_var)" not in texto:
        marcador = '        self.ent_tempo_lembrete.bind("<Button-1>",'
        if marcador not in texto:
            raise RuntimeError("Campo de horário do lembrete não encontrado.")
        texto = texto.replace(
            marcador,
            "        self.configurar_campo_horario(self.ent_tempo_lembrete, self.tempo_lembrete_var)\n" + marcador,
            1
        )

    # Configuração dos quatro horários do Banco de Horas.
    if "CAMPOS_HORARIO_BANCO_V4" not in texto:
        padrao = re.compile(
            r'''        # Forçar digitação limpa no final do campo para Inputs de tempo\n'''
            r'''        for ent in \[self\.ent_banco_m1, self\.ent_banco_m2, self\.ent_banco_m3, self\.ent_banco_m4\]:\n'''
            r'''            ent\.bind\("<Button-1>",[^\n]+\n'''
            r'''            ent\.bind\("<FocusIn>",[^\n]+\n'''
        )
        bloco = '''        # CAMPOS_HORARIO_BANCO_V4
        for entry_widget, string_var in (
            (self.ent_banco_m1, self.banco_m1_var),
            (self.ent_banco_m2, self.banco_m2_var),
            (self.ent_banco_m3, self.banco_m3_var),
            (self.ent_banco_m4, self.banco_m4_var)
        ):
            self.configurar_campo_horario(
                entry_widget,
                string_var
            )
'''
        texto, quantidade = padrao.subn(bloco, texto, count=1)
        if quantidade != 1:
            raise RuntimeError("Bloco dos horários do Banco de Horas não encontrado.")

    # Contador de almoço e reabertura após desbloqueio.
    inicio, fim = localizar_metodo(texto, "update_clock_loop")
    if "and not self.esquecimento_marcacao_ativo()" not in texto[inicio:fim]:
        texto = alterar_metodo(texto, "update_clock_loop", atualizar_clock)

    inicio, fim = localizar_metodo(texto, "monitor_system")
    if "and not self.esquecimento_marcacao_ativo()" not in texto[inicio:fim]:
        texto = alterar_metodo(texto, "monitor_system", atualizar_monitor)

    # Item no menu da bandeja.
    item = "pystray.MenuItem(TEXT_TRAY_ESQUECIMENTO, self.tray_esquecimento_marcacao),"
    if item not in texto:
        marcador = "            pystray.MenuItem(TEXT_TRAY_ATUALIZAR, self.tray_force_update),"
        if marcador not in texto:
            raise RuntimeError("Item Atualizar marcações não encontrado no menu.")
        texto = texto.replace(
            marcador,
            marcador + "\n            " + item,
            1
        )

    obrigatorios = (
        "TEXT_TRAY_ESQUECIMENTO",
        "self.esquecimento_retorno_data = None",
        'tag_configure("vermelho"',
        "def esquecimento_marcacao_ativo(",
        "def ativar_esquecimento_marcacao(",
        "def tray_esquecimento_marcacao(",
        "tag_retorno_previsto",
        "def digitar_horario_direita_esquerda(",
        "def configurar_campo_horario(",
        item
    )

    ausentes = [item for item in obrigatorios if item not in texto]
    if ausentes:
        raise RuntimeError("Atualização incompleta: " + ", ".join(ausentes))

    return texto


def main():
    caminho = localizar_arquivo()
    texto_original, codificacao, bom, quebra = ler_arquivo(caminho)
    validar(texto_original, caminho.name)

    texto_atualizado = atualizar_main(texto_original)
    validar(texto_atualizado, caminho.name)

    if texto_atualizado == texto_original:
        mensagem = (
            f"{caminho.name}: já contém todas as alterações da versão {VERSAO}."
        )
        print(mensagem)
        RELATORIO.write_text(mensagem, encoding="utf-8")
        return 0

    PASTA_BACKUP.mkdir(parents=True, exist_ok=True)
    backup = PASTA_BACKUP / caminho.name
    shutil.copy2(str(caminho), str(backup))

    try:
        gravar_arquivo(
            caminho,
            texto_atualizado,
            codificacao,
            bom,
            quebra
        )

        confirmacao, _, _, _ = ler_arquivo(caminho)
        validar(confirmacao, caminho.name)

        if confirmacao != texto_atualizado:
            raise RuntimeError("O conteúdo gravado não corresponde ao conteúdo preparado.")

        linhas = [
            "=" * 72,
            "ATUALIZAÇÃO CONCLUÍDA COM SUCESSO",
            "=" * 72,
            f"Versão: {VERSAO}",
            f"Arquivo atualizado: {caminho.name}",
            f"Backup: {backup}",
            "",
            "Alterações:",
            "- Item 'Esquecimento de marcação' adicionado ao menu da bandeja.",
            "- Terceira marcação prevista passa a vermelho quando ativada.",
            "- Estado apenas visual, apenas no dia atual e sem gravação no banco.",
            "- Contador de almoço é interrompido após a ativação.",
            "- Digitação de todos os horários corrigida para direita para esquerda.",
            "=" * 72
        ]
        relatorio = "\n".join(linhas)
        print(relatorio)
        RELATORIO.write_text(relatorio, encoding="utf-8")
        return 0

    except Exception:
        shutil.copy2(str(backup), str(caminho))
        raise


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Atualização cancelada pelo usuário.")
        sys.exit(130)
    except Exception as erro:
        print(f"Falha na atualização: {type(erro).__name__}: {erro}")
        traceback.print_exc()
        sys.exit(1)
