"""
Autor: Ismael Elói da Silveira Silva
Descrição: Arquivo principal de execução. Gerencia a Interface Gráfica (GUI) e as Threads em segundo plano.
"""

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox, filedialog
import time
import threading
import datetime
import ctypes
import pystray
from PIL import Image, ImageDraw
import re

# Importação dos Módulos Modulares Locais
import settings
import database
import scraper
import relatorio

# =============================================================================
# CONFIGURAÇÕES GERAIS DE TEXTOS E ESTILOS (ÁREA PARA ALTERAÇÕES MANUAIS)
# =============================================================================

# --- BORDAS E CORES DA JANELA ---
BORDER_COLOR = "#cccccc"      
BORDER_THICKNESS = 1          

# --- TEXTOS DA TELINHA PRINCIPAL ---
TEXT_TITLE_APP = "Assistente do PontoWeb MGS"
TEXT_BTN_MARCAR = "REGISTRAR PONTO"
TEXT_BUSCANDO = "Buscando marcações..."
TEXT_SEM_MARCACAO = "Nenhuma marcação no dia"
TEXT_PREFIX_JORNADA = ""
TEXT_PREFIX_ALMOCO = "Almoço: "

TEXT_BTN_CONFIG = "⚙"
TEXT_BTN_MINIMIZE = "—"
TEXT_BTN_RESET = "↺"

# --- TEXTOS DA TELA DE CONFIGURAÇÕES ---
TEXT_TITLE_CONFIG = "Configurações"
TEXT_LBL_MATRICULA = "Matrícula:"
TEXT_LBL_SENHA = "Senha:"
TEXT_LBL_SAIDA_ALMOCO = "Saída do almoço:"
TEXT_LBL_INTERVALO_ATUALIZACAO = "Aguardar após registrar (segundos):"
TEXT_BTN_SALVAR = "Salvar"
TEXT_MSG_SUCESSO_TITULO = "Sucesso"
TEXT_MSG_SUCESSO_CORPO = "Configurações salvas!"

# --- VARIÁVEIS E TEXTOS DOS LEMBRETES DINÂMICOS ---
TEXT_TITLE_LEMBRETES = "Lembretes"
TEXT_LBL_NOME_LEMBRETE = "Nome do Lembrete:"
TEXT_LBL_EVENTO_REF = "Evento de Referência:"
TEXT_LBL_TEMPO = "Tempo de diferença:"
TEXT_LBL_TEMPO_FIXO = "Horário exato:" 
TEXT_LBL_TIPO = "Momento:"
TEXT_LBL_MENSAGEM_LEMBRETE = "Mensagem:"
TEXT_BTN_ADICIONAR_LEMBRETE = "Adicionar"
TEXT_BTN_EXCLUIR_LEMBRETE = "Excluir"
TEXT_BTN_SALVAR_EDICAO = "Salvar"
TEXT_BTN_CANCELAR_EDICAO = "Cancelar"

# --- TEXTOS DO MENU DA BANDEJA (TRAY - RELÓGIO DO WINDOWS) ---
TEXT_TRAY_ABRIR = "Abrir/Ocultar"
TEXT_TRAY_ATUALIZAR = "Atualizar marcações"
TEXT_TRAY_ESQUECIMENTO = "Esquecimento de marcação"
TEXT_TRAY_CONFIG = "Configurações"
TEXT_TRAY_LEMBRETES = "Lembretes"
TEXT_TRAY_BANCO = "Banco de Horas"
TEXT_TRAY_RELATORIO = "Relatório"
TEXT_TRAY_SAIR = "Fechar"

# --- TEXTOS E CONF. DO BANCO DE HORAS ---
TEXT_TITLE_BANCO = "Banco de Horas"
TEXT_BTN_ATUALIZAR_BANCO = "Atualizar Marcações"
TEXT_BTN_LIMPAR_MES = "Limpar Mês"
TEXT_BTN_RELATORIO = "Relatório"
TEXT_TITLE_RELATORIO = "Relatório de Banco de Horas"
TEXT_LBL_PERIODO_RELATORIO = "Selecione o período:"
TEXT_BTN_GERAR_RELATORIO = "Gerar PDF"
TEXT_LBL_SALDO_MES = "Saldo do Mês:"
TEXT_LBL_BH_DATA = "Data:"
TEXT_LBL_BH_M1 = "M1:"
TEXT_LBL_BH_M2 = "M2:"
TEXT_LBL_BH_M3 = "M3:"
TEXT_LBL_BH_M4 = "M4:"
TEXT_BTN_SALVAR_BANCO = "Salvar Edição"
TEXT_BTN_CANCELAR_BANCO = "Cancelar"
TEXT_BTN_RESTAURAR_BANCO = "Restaurar Dia"

# Variáveis configuráveis de eventos para ancoragem dos lembretes
EVENTO_ENTRADA = "Horário de entrada"
EVENTO_PREV_SAIDA = "Horário previsto de saída"
EVENTO_PREV_ALMOCO = "Horário previsto de almoço"
EVENTO_INICIO_ALMOCO = "Horário de início de almoço"
EVENTO_PREV_FIM_ALMOCO = "Horário previsto de fim do almoço"
EVENTO_FIM_ALMOCO = "Horário de fim de almoço"
EVENTO_SAIDA = "Horário de saída"
EVENTO_FIXO = "Horário fixo"

EVENTOS_DISPONIVEIS = [
    EVENTO_ENTRADA, EVENTO_PREV_ALMOCO, EVENTO_INICIO_ALMOCO,
    EVENTO_PREV_FIM_ALMOCO, EVENTO_FIM_ALMOCO, EVENTO_PREV_SAIDA, EVENTO_SAIDA, EVENTO_FIXO
]
TIPOS_DISPONIVEIS = ["Antes", "Exatamente", "Depois"]

# Textos do Pop-Up
TEXT_TITLE_LEMBRETE_POPUP = "Lembrete de Ponto"
TEXT_LBL_ATENCAO = "⏳ Atenção!"
# Mensagem de fallback caso o usuário deixe o campo de mensagem vazio
TEXT_MENSAGEM_PADRAO = "Atenção ao horário configurado que é às {}." 
TEXT_BTN_CIENTE = "OK"

# --- ESTILOS E FONTES DA TELINHA ---
FONT_ICONS = ("Segoe UI", 12)
FONT_ICONS_BOLD = ("Segoe UI", 12, "bold")
FONT_MINIMIZE = ("Segoe UI", 10, "bold")
FONT_BTN_MARCAR = ("Segoe UI", 12, "bold")
FONT_CLOCK_SECUNDARIO = ("Segoe UI", 18, "normal") 
FONT_MARCACOES = ("Segoe UI", 14, "bold")         
FONT_BUSCANDO = ("Segoe UI", 12)

# --- ESTILOS E FONTES DA TELA DE CONFIGURAÇÃO E POP-UP ---
FONT_INPUTS = ("Segoe UI", 10)
FONT_BTN_SALVAR_CONF = ("Segoe UI", 10, "bold")
FONT_ATENCAO = ("Segoe UI", 14, "bold")
FONT_CORPO_LEMBRETE = ("Segoe UI", 11)
FONT_BTN_CIENTE = ("Segoe UI", 9, "bold")

# =============================================================================
# FIM DAS CONFIGURAÇÕES GERAIS
# =============================================================================


class PontoApp:
    def __init__(self):
        self.config = database.get_credentials()
        self.lembretes_db = database.get_lembretes()
        
        
        self.marca1 = None
        self.marca2 = None
        self.marca3 = None
        self.marca4 = None
        
        self.pad_y = 5 
        
        self.ui_state = {'tempo': False, 'almoco': False, 'progress': True}
        self.buscando_marcacoes = True
        self.is_default_position = True
        
        self.editando_lembrete_id = None 
        
        # Atributos para controle de instância única (Singleton) das janelas secundárias
        self.win_config = None
        self.win_lembretes = None
        self.win_banco = None
        self.win_relatorio = None
        
        self.atualizar_event = threading.Event()
        self.lembretes_exibidos = set()
        self.data_controle_lembretes = datetime.date.today()
        self.esquecimento_retorno_data = None
        
        self.setup_ui()
        
        threading.Thread(target=self.monitor_system, daemon=True).start()
        threading.Thread(target=self.update_clock_loop, daemon=True).start()
        threading.Thread(target=self.setup_tray, daemon=True).start()
        threading.Thread(target=self.atualizar_marcacoes_loop, daemon=True).start()

        if not self.config.get("matricula") or not self.config.get("senha"):
            self.show_config_window()
        else:
            self.show_main_window()

    def save_config(
        self,
        matricula,
        senha,
        saida_almoco,
        intervalo_atualizacao,
        window
    ):
        matricula = matricula.strip()
        senha = senha.strip()
        saida_almoco = saida_almoco.strip()

        if not matricula:
            messagebox.showwarning(
                "Atenção",
                "Informe a matrícula."
            )
            return

        if not senha:
            messagebox.showwarning(
                "Atenção",
                "Informe a senha."
            )
            return

        if not self.validar_horario(
            saida_almoco
        ):
            messagebox.showwarning(
                "Atenção",
                "Informe um horário de almoço válido "
                "no formato HH:MM."
            )
            return

        try:
            intervalo = int(
                str(intervalo_atualizacao).strip()
            )
        except (TypeError, ValueError):
            messagebox.showwarning(
                "Atenção",
                "Informe um intervalo válido em segundos."
            )
            return

        if intervalo < 0 or intervalo > 3600:
            messagebox.showwarning(
                "Atenção",
                "O intervalo deve estar entre "
                "0 e 3600 segundos."
            )
            return

        database.save_credentials(
            matricula,
            senha,
            saida_almoco,
            intervalo
        )

        self.config = database.get_credentials()

        if window and window.winfo_exists():
            window.destroy()

        self.atualizar_interface_marcacoes(
            TEXT_BUSCANDO
        )

        self.atualizar_event.set()
        self.show_main_window()

        messagebox.showinfo(
            TEXT_MSG_SUCESSO_TITULO,
            TEXT_MSG_SUCESSO_CORPO
        )

    def validar_horario(self, horario):
        if not horario:
            return False

        resultado = re.fullmatch(
            r"(\d{2}):(\d{2})",
            horario.strip()
        )

        if not resultado:
            return False

        hora = int(resultado.group(1))
        minuto = int(resultado.group(2))

        return (
            0 <= hora <= 23
            and 0 <= minuto <= 59
        )

    def validar_tempo_lembrete(self, tempo, evento):
        if not tempo:
            return False

        resultado = re.fullmatch(
            r"(\d{2}):(\d{2})",
            tempo.strip()
        )

        if not resultado:
            return False

        horas = int(resultado.group(1))
        minutos = int(resultado.group(2))

        if not 0 <= minutos <= 59:
            return False

        if evento == EVENTO_FIXO:
            return 0 <= horas <= 23

        return 0 <= horas <= 99

    def atualizar_texto_relogio(self, hora_str):
        try:
            if self.root.winfo_exists():
                self.lbl_relogio.config(
                    text=hora_str
                )

        except tk.TclError:
            pass

    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title(TEXT_TITLE_APP)
        self.root.configure(bg=settings.COLOR_BG)
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True) 
        self.root.pack_propagate(True) 
        
        self.master_frame = tk.Frame(self.root, bg=settings.COLOR_BG, highlightbackground=BORDER_COLOR, highlightthickness=BORDER_THICKNESS)
        self.master_frame.pack(fill=tk.BOTH, expand=True)
        
        self.frame_topo = tk.Frame(self.master_frame, bg=settings.COLOR_BG)
        self.frame_topo.pack(side=tk.TOP, fill=tk.X, pady=(15, 0))
        
        self.btn_config = tk.Label(self.frame_topo, text=TEXT_BTN_CONFIG, font=FONT_ICONS, bg=settings.COLOR_BG, fg="#888888", cursor="hand2")
        self.btn_config.pack(side=tk.LEFT, padx=15)
        self.btn_config.bind("<Button-1>", lambda e: self.show_config_window())
        
        self.btn_close = tk.Label(self.frame_topo, text=TEXT_BTN_MINIMIZE, font=FONT_MINIMIZE, bg=settings.COLOR_BG, fg="#888888", cursor="hand2")
        self.btn_close.pack(side=tk.RIGHT, padx=(5, 15))
        self.btn_close.bind("<Button-1>", lambda e: self.root.withdraw())

        self.btn_reset = tk.Label(self.frame_topo, text=TEXT_BTN_RESET, font=FONT_ICONS_BOLD, bg=settings.COLOR_BG, fg="#888888", cursor="hand2")
        self.btn_reset.pack(side=tk.RIGHT, padx=5)
        self.btn_reset.bind("<Button-1>", lambda e: self.reset_position())
        
        self.frame_topo.bind("<ButtonPress-1>", self.start_move)
        self.frame_topo.bind("<B1-Motion>", self.do_move)
        
        self.frame_central = tk.Frame(self.master_frame, bg=settings.COLOR_BG)
        self.frame_central.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.frame_central.bind("<ButtonPress-1>", self.start_move)
        self.frame_central.bind("<B1-Motion>", self.do_move)
        
        self.frame_content = tk.Frame(self.frame_central, bg=settings.COLOR_BG)
        self.frame_content.pack(expand=True) 

        self.lbl_relogio = tk.Label(self.frame_content, text="", font=settings.FONT_CLOCK, bg=settings.COLOR_BG, fg=settings.COLOR_TEXT_BLUE, justify="center")
        self.lbl_relogio.pack(side=tk.TOP, pady=(0, 0))

        self.lbl_tempo_restante = tk.Label(self.frame_content, text="", font=FONT_CLOCK_SECUNDARIO, bg=settings.COLOR_BG, justify="center")
        self.lbl_almoco_restante = tk.Label(self.frame_content, text="", font=FONT_CLOCK_SECUNDARIO, bg=settings.COLOR_BG, justify="center")

        self.text_marcacoes = tk.Text(self.frame_content, font=FONT_MARCACOES, bg=settings.COLOR_BG, fg=settings.COLOR_TEXT_BLUE, 
                                      height=1, width=28, borderwidth=0, highlightthickness=0, padx=0, pady=0)
        self.text_marcacoes.pack(side=tk.TOP, pady=self.pad_y)
        
        self.text_marcacoes.tag_configure("verde", foreground="#28a745")
        self.text_marcacoes.tag_configure("cinza", foreground="#999999")
        self.text_marcacoes.tag_configure("vermelho", foreground=settings.COLOR_BUTTON_RED)
        self.text_marcacoes.tag_configure("padrao", foreground=settings.COLOR_TEXT_BLUE)
        self.text_marcacoes.tag_configure("leve", font=FONT_BUSCANDO, foreground=settings.COLOR_TEXT_BLUE, justify="center")
        self.text_marcacoes.tag_configure("center", justify='center')
        
        self.progress_bar = ttk.Progressbar(self.frame_content, mode='indeterminate', length=200)

        self.btn_marcar = tk.Button(self.master_frame, text=TEXT_BTN_MARCAR, font=FONT_BTN_MARCAR, 
                                    bg=settings.COLOR_BUTTON_RED, fg="white", relief="flat", 
                                    command=self.registrar_ponto_action)
        self.btn_marcar.pack(side=tk.BOTTOM, pady=(10, 15), ipadx=20, ipady=5)

        self.atualizar_interface_marcacoes(TEXT_BUSCANDO)
        self.root.after(100, self.update_window_size_and_position)

    # =========================================================================
    # FUNÇÕES DE ARRASTAR E REDIMENSIONAR JANELA
    # =========================================================================
    def start_move(self, event):
        self.x_pre = event.x
        self.y_pre = event.y

    def do_move(self, event):
        self.is_default_position = False 
        deltax = event.x - self.x_pre
        deltay = event.y - self.y_pre
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def reset_position(self):
        self.is_default_position = True
        self.update_window_size_and_position()

    def update_window_size_and_position(self):
        self.root.update_idletasks()
        w = 350
        h = self.root.winfo_reqheight()
        
        if self.is_default_position:
            x = self.root.winfo_screenwidth() - w
            y = self.root.winfo_screenheight() - h - 50 
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        else:
            self.root.geometry(f"{w}x{h}") 

    # =========================================================================
    # ATUALIZAÇÃO DO DISPLAY DE MARCAÇÕES (TEXTO VERDE E CINZA)
    # =========================================================================
    def atualizar_interface_marcacoes(self, texto):
        self.text_marcacoes.config(
            state=tk.NORMAL
        )

        self.text_marcacoes.delete(
            "1.0",
            tk.END
        )

        state_changed = False

        self.buscando_marcacoes = (
            texto == TEXT_BUSCANDO
        )

        # Durante a busca, nenhum relógio secundário
        # deve permanecer visível.
        if self.buscando_marcacoes:
            if self.ui_state.get("tempo", False):
                self.lbl_tempo_restante.pack_forget()
                self.ui_state["tempo"] = False
                state_changed = True

            if self.ui_state.get("almoco", False):
                self.lbl_almoco_restante.pack_forget()
                self.ui_state["almoco"] = False
                state_changed = True

        if texto == TEXT_BUSCANDO:
            self.text_marcacoes.insert(
                tk.END,
                texto,
                "leve"
            )

            if not self.ui_state["progress"]:
                self.progress_bar.pack(
                    after=self.text_marcacoes,
                    pady=self.pad_y
                )

                self.ui_state["progress"] = True
                state_changed = True

            self.progress_bar.start(15)

        else:
            if self.ui_state["progress"]:
                self.progress_bar.stop()
                self.progress_bar.pack_forget()
                self.ui_state["progress"] = False
                state_changed = True

            mensagens_erro = [
                "Erro ao buscar marcações",
                "Sem marcações",
                "Erro: Usuário ou senha incorreta.",
                "Erro: Falha no login ou sessão expirada."
            ]

            if texto in mensagens_erro:
                self.marca1 = None
                self.marca2 = None
                self.marca3 = None
                self.marca4 = None

                if texto == "Sem marcações":
                    self.text_marcacoes.insert(
                        tk.END,
                        TEXT_SEM_MARCACAO,
                        "padrao"
                    )
                else:
                    self.text_marcacoes.insert(
                        tk.END,
                        texto,
                        "padrao"
                    )

            elif "Última" in texto:
                self.marca1 = None
                self.marca2 = None
                self.marca3 = None
                self.marca4 = None

                self.text_marcacoes.insert(
                    tk.END,
                    texto,
                    "padrao"
                )

            else:
                tempos = re.findall(
                    r'\d{2}:\d{2}',
                    texto
                )

                if not tempos:
                    self.marca1 = None
                    self.marca2 = None
                    self.marca3 = None
                    self.marca4 = None

                    self.text_marcacoes.insert(
                        tk.END,
                        texto,
                        "padrao"
                    )

                else:
                    def add_h(t_str, h):
                        try:
                            tempo = datetime.datetime.strptime(
                                t_str,
                                "%H:%M"
                            )

                            tempo += datetime.timedelta(
                                hours=h
                            )

                            return tempo.strftime("%H:%M")

                        except Exception:
                            return "--:--"

                    self.marca1 = (
                        tempos[0]
                        if len(tempos) > 0
                        else None
                    )

                    self.marca2 = (
                        tempos[1]
                        if len(tempos) > 1
                        else None
                    )

                    self.marca3 = (
                        tempos[2]
                        if len(tempos) > 2
                        else None
                    )

                    self.marca4 = (
                        tempos[3]
                        if len(tempos) > 3
                        else None
                    )

                    m1 = self.marca1
                    m2 = self.marca2
                    m3 = self.marca3
                    m4 = self.marca4

                    saida_almoco_padrao = self.config.get(
                        "saida_almoco",
                        "12:00"
                    )

                    espaco = "   "

                    if m1:
                        self.text_marcacoes.insert(
                            tk.END,
                            m1,
                            "verde"
                        )

                    self.text_marcacoes.insert(
                        tk.END,
                        espaco
                    )

                    if m2:
                        self.text_marcacoes.insert(
                            tk.END,
                            m2,
                            "verde"
                        )

                    elif m1 and m1 <= saida_almoco_padrao:
                        self.text_marcacoes.insert(
                            tk.END,
                            saida_almoco_padrao,
                            "cinza"
                        )

                    else:
                        self.text_marcacoes.insert(
                            tk.END,
                            "--:--",
                            "padrao"
                        )

                    self.text_marcacoes.insert(
                        tk.END,
                        espaco
                    )

                    if m3:
                        self.text_marcacoes.insert(
                            tk.END,
                            m3,
                            "verde"
                        )

                    elif m2:
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
                        )

                    elif m1 and m1 <= saida_almoco_padrao:
                        self.text_marcacoes.insert(
                            tk.END,
                            add_h(
                                saida_almoco_padrao,
                                1
                            ),
                            "cinza"
                        )

                    else:
                        self.text_marcacoes.insert(
                            tk.END,
                            "--:--",
                            "padrao"
                        )

                    self.text_marcacoes.insert(
                        tk.END,
                        espaco
                    )

                    if m4:
                        self.text_marcacoes.insert(
                            tk.END,
                            m4,
                            "verde"
                        )

                    elif m1:
                        self.text_marcacoes.insert(
                            tk.END,
                            add_h(m1, 9),
                            "cinza"
                        )

                    else:
                        self.text_marcacoes.insert(
                            tk.END,
                            "--:--",
                            "padrao"
                        )

        self.text_marcacoes.tag_add(
            "center",
            "1.0",
            tk.END
        )

        self.text_marcacoes.config(
            state=tk.DISABLED
        )

        if state_changed:
            self.update_window_size_and_position()

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

    def show_config_window(self):
        if (
            hasattr(self, 'win_config')
            and self.win_config
            and self.win_config.winfo_exists()
        ):
            self.win_config.lift()
            self.win_config.focus_force()
            return

        self.win_config = tk.Toplevel(self.root)
        self.win_config.title(TEXT_TITLE_CONFIG)
        self.win_config.geometry("360x350")
        self.win_config.configure(
            bg=settings.COLOR_BG
        )
        self.win_config.resizable(False, False)

        tk.Label(
            self.win_config,
            text=TEXT_LBL_MATRICULA,
            bg=settings.COLOR_BG,
            font=settings.FONT_LABEL
        ).pack(
            pady=(15, 0),
            anchor="center"
        )

        ent_m = tk.Entry(
            self.win_config,
            font=FONT_INPUTS,
            justify="center",
            relief="solid",
            bd=1
        )

        ent_m.insert(
            0,
            self.config.get("matricula", "")
        )

        ent_m.pack(
            pady=5,
            anchor="center"
        )

        tk.Label(
            self.win_config,
            text=TEXT_LBL_SENHA,
            bg=settings.COLOR_BG,
            font=settings.FONT_LABEL
        ).pack(
            pady=(5, 0),
            anchor="center"
        )

        ent_senha = tk.Entry(
            self.win_config,
            show="*",
            font=FONT_INPUTS,
            justify="center",
            relief="solid",
            bd=1
        )

        ent_senha.insert(
            0,
            self.config.get("senha", "")
        )

        ent_senha.pack(
            pady=5,
            anchor="center"
        )

        tk.Label(
            self.win_config,
            text=TEXT_LBL_SAIDA_ALMOCO,
            bg=settings.COLOR_BG,
            font=settings.FONT_LABEL
        ).pack(
            pady=(5, 0),
            anchor="center"
        )

        self.almoco_var = tk.StringVar()

        self.almoco_var.set(
            self.config.get(
                "saida_almoco",
                "12:00"
            )
        )

        self.almoco_var.trace_add(
            "write",
            lambda *args: self.formatar_tempo_generico(
                self.almoco_var,
                self.ent_almoco
            )
        )

        self.ent_almoco = tk.Entry(
            self.win_config,
            textvariable=self.almoco_var,
            font=FONT_INPUTS,
            justify="center",
            relief="solid",
            bd=1
        )

        self.ent_almoco.pack(
            pady=5,
            anchor="center"
        )

        self.configurar_campo_horario(self.ent_almoco, self.almoco_var)

        self.ent_almoco.bind(
            "<Button-1>",
            lambda event: self.ent_almoco.after(
                10,
                lambda: self.ent_almoco.icursor(tk.END)
            )
        )

        self.ent_almoco.bind(
            "<FocusIn>",
            lambda event: self.ent_almoco.after(
                10,
                lambda: self.ent_almoco.icursor(tk.END)
            )
        )

        tk.Label(
            self.win_config,
            text=TEXT_LBL_INTERVALO_ATUALIZACAO,
            bg=settings.COLOR_BG,
            font=settings.FONT_LABEL
        ).pack(
            pady=(5, 0),
            anchor="center"
        )

        intervalo_var = tk.StringVar()

        intervalo_var.set(
            str(
                self.config.get(
                    "intervalo_atualizacao",
                    10
                )
            )
        )

        ent_intervalo = tk.Spinbox(
            self.win_config,
            from_=0,
            to=3600,
            increment=1,
            textvariable=intervalo_var,
            font=FONT_INPUTS,
            justify="center",
            relief="solid",
            bd=1,
            width=10
        )

        ent_intervalo.pack(
            pady=5,
            anchor="center"
        )

        tk.Button(
            self.win_config,
            text=TEXT_BTN_SALVAR,
            bg=settings.COLOR_BUTTON_RED,
            fg="white",
            font=FONT_BTN_SALVAR_CONF,
            relief="flat",
            command=lambda: self.save_config(
                ent_m.get(),
                ent_senha.get(),
                self.ent_almoco.get(),
                ent_intervalo.get(),
                self.win_config
            )
        ).pack(
            pady=15,
            anchor="center"
        )

    def on_evento_change(self, event=None):
        if hasattr(self, 'cb_evento_lembrete'):
            if self.cb_evento_lembrete.get() == EVENTO_FIXO:
                self.lbl_tempo_form.config(text=TEXT_LBL_TEMPO_FIXO)
                self.cb_tipo_lembrete.set("Exatamente") 
                self.cb_tipo_lembrete.config(state=tk.DISABLED)
            else:
                self.lbl_tempo_form.config(text=TEXT_LBL_TEMPO)
                self.cb_tipo_lembrete.config(state="readonly")

    def show_lembretes_window(self):
        if hasattr(self, 'win_lembretes') and self.win_lembretes and self.win_lembretes.winfo_exists():
            self.win_lembretes.lift()
            self.win_lembretes.focus_force()
            return
            
        self.editando_lembrete_id = None
        
        self.win_lembretes = tk.Toplevel(self.root)
        self.win_lembretes.title(TEXT_TITLE_LEMBRETES)
        self.win_lembretes.geometry("700x530") 
        self.win_lembretes.configure(bg=settings.COLOR_BG)
        
        tree_frame = tk.Frame(self.win_lembretes, bg=settings.COLOR_BG)
        tree_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        columns = ("id", "nome", "evento", "tempo", "tipo", "mensagem")
        self.tree = ttk.Treeview(tree_frame, columns=columns, displaycolumns=("id", "nome", "mensagem"), show="headings", height=5)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("mensagem", text="Mensagem")
        
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("nome", width=150, anchor="w")
        self.tree.column("mensagem", width=450, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.atualizar_lista_lembretes()

        form_frame = tk.Frame(self.win_lembretes, bg=settings.COLOR_BG)
        form_frame.pack(pady=5, fill=tk.X, padx=20)
        
        tk.Label(form_frame, text=TEXT_LBL_NOME_LEMBRETE, bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=0, column=0, sticky="e", pady=2, padx=5)
        self.ent_nome_lembrete = tk.Entry(form_frame, font=FONT_INPUTS, width=40, relief="solid", bd=1)
        self.ent_nome_lembrete.grid(row=0, column=1, sticky="w", pady=2)

        tk.Label(form_frame, text=TEXT_LBL_EVENTO_REF, bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=1, column=0, sticky="e", pady=2, padx=5)
        self.cb_evento_lembrete = ttk.Combobox(form_frame, values=EVENTOS_DISPONIVEIS, font=FONT_INPUTS, width=38, state="readonly")
        self.cb_evento_lembrete.grid(row=1, column=1, sticky="w", pady=2)
        self.cb_evento_lembrete.bind("<<ComboboxSelected>>", self.on_evento_change)
        if EVENTOS_DISPONIVEIS:
            self.cb_evento_lembrete.current(0)

        self.lbl_tempo_form = tk.Label(form_frame, text=TEXT_LBL_TEMPO, bg=settings.COLOR_BG, font=FONT_INPUTS)
        self.lbl_tempo_form.grid(row=2, column=0, sticky="e", pady=2, padx=5)
        
        self.tempo_lembrete_var = tk.StringVar()
        self.tempo_lembrete_var.set("00:00")
        self.tempo_lembrete_var.trace_add("write", lambda *args: self.formatar_tempo_generico(self.tempo_lembrete_var, self.ent_tempo_lembrete))
        self.ent_tempo_lembrete = tk.Entry(form_frame, textvariable=self.tempo_lembrete_var, font=FONT_INPUTS, width=15, justify="center", relief="solid", bd=1)
        self.ent_tempo_lembrete.grid(row=2, column=1, sticky="w", pady=2)
        self.configurar_campo_horario(self.ent_tempo_lembrete, self.tempo_lembrete_var)
        self.ent_tempo_lembrete.bind("<Button-1>", lambda e: self.ent_tempo_lembrete.after(10, lambda: self.ent_tempo_lembrete.icursor(tk.END)))
        self.ent_tempo_lembrete.bind("<FocusIn>", lambda e: self.ent_tempo_lembrete.after(10, lambda: self.ent_tempo_lembrete.icursor(tk.END)))

        tk.Label(form_frame, text=TEXT_LBL_TIPO, bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=3, column=0, sticky="e", pady=2, padx=5)
        self.cb_tipo_lembrete = ttk.Combobox(form_frame, values=TIPOS_DISPONIVEIS, font=FONT_INPUTS, width=13, state="readonly")
        self.cb_tipo_lembrete.grid(row=3, column=1, sticky="w", pady=2)
        if TIPOS_DISPONIVEIS:
            self.cb_tipo_lembrete.current(0)
            
        tk.Label(form_frame, text=TEXT_LBL_MENSAGEM_LEMBRETE, bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=4, column=0, sticky="e", pady=2, padx=5)
        self.ent_mensagem_lembrete = tk.Entry(form_frame, font=FONT_INPUTS, width=40, relief="solid", bd=1)
        self.ent_mensagem_lembrete.grid(row=4, column=1, sticky="w", pady=2)

        btn_action_frame = tk.Frame(self.win_lembretes, bg=settings.COLOR_BG)
        btn_action_frame.pack(pady=(15, 20))

        self.btn_salvar_lembrete = tk.Button(btn_action_frame, text=TEXT_BTN_ADICIONAR_LEMBRETE, bg="#28a745", fg="white", font=FONT_BTN_SALVAR_CONF, 
                                             relief="flat", command=self.salvar_lembrete)
        self.btn_salvar_lembrete.pack(side=tk.LEFT, padx=10)
        
        self.btn_excluir_lembrete = tk.Button(btn_action_frame, text=TEXT_BTN_EXCLUIR_LEMBRETE, bg=settings.COLOR_BUTTON_RED, fg="white", font=FONT_BTN_SALVAR_CONF, 
                                              relief="flat", command=self.excluir_lembrete)
        
        self.btn_cancelar_edicao = tk.Button(btn_action_frame, text=TEXT_BTN_CANCELAR_EDICAO, bg="#6c757d", fg="white", font=FONT_BTN_SALVAR_CONF, 
                                             relief="flat", command=self.cancelar_edicao)
        
        self.tree.bind("<<TreeviewSelect>>", self.carregar_edicao)
        
        self.on_evento_change()

    def atualizar_lista_lembretes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lembretes_db = database.get_lembretes()
        for l in self.lembretes_db:
            self.tree.insert("", "end", values=l)

    def carregar_edicao(self, event=None):
        selected = self.tree.selection()
        if selected:
            item_values = self.tree.item(selected[0], 'values')
            self.editando_lembrete_id = item_values[0]
            
            self.ent_nome_lembrete.delete(0, tk.END)
            self.ent_nome_lembrete.insert(0, item_values[1])
            
            self.cb_evento_lembrete.set(item_values[2])
            self.tempo_lembrete_var.set(item_values[3])
            self.cb_tipo_lembrete.set(item_values[4])
            
            self.ent_mensagem_lembrete.delete(0, tk.END)
            msg = item_values[5] if item_values[5] != "None" else ""
            self.ent_mensagem_lembrete.insert(0, msg)
            
            self.btn_salvar_lembrete.config(text=TEXT_BTN_SALVAR_EDICAO, bg="#007bff")
            
            self.btn_excluir_lembrete.pack(side=tk.LEFT, padx=10)
            self.btn_cancelar_edicao.pack(side=tk.LEFT, padx=10)
            
            self.on_evento_change()

    def cancelar_edicao(self):
        self.editando_lembrete_id = None
        self.ent_nome_lembrete.delete(0, tk.END)
        self.cb_evento_lembrete.current(0)
        self.tempo_lembrete_var.set("00:00")
        self.cb_tipo_lembrete.current(0)
        self.ent_mensagem_lembrete.delete(0, tk.END)
        
        self.btn_salvar_lembrete.config(text=TEXT_BTN_ADICIONAR_LEMBRETE, bg="#28a745")
        self.btn_excluir_lembrete.pack_forget()
        self.btn_cancelar_edicao.pack_forget()
        
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        
        self.on_evento_change()

    def salvar_lembrete(self):
        nome = self.ent_nome_lembrete.get().strip()
        evento = self.cb_evento_lembrete.get().strip()
        tempo = self.ent_tempo_lembrete.get().strip()
        tipo = self.cb_tipo_lembrete.get().strip()
        mensagem = self.ent_mensagem_lembrete.get().strip()

        if not nome or not evento or not tempo or not tipo:
            messagebox.showwarning(
                "Atenção",
                "Preencha todos os campos obrigatórios "
                "do lembrete. O campo Mensagem é opcional."
            )
            return

        if not self.validar_tempo_lembrete(
            tempo,
            evento
        ):
            if evento == EVENTO_FIXO:
                descricao = (
                    "Informe um horário válido "
                    "entre 00:00 e 23:59."
                )

            else:
                descricao = (
                    "Informe uma diferença de tempo válida "
                    "no formato HH:MM."
                )

            messagebox.showwarning(
                "Tempo inválido",
                descricao
            )
            return

        if evento == EVENTO_FIXO:
            tipo = "Exatamente"

        if self.editando_lembrete_id:
            database.update_lembrete(
                self.editando_lembrete_id,
                nome,
                evento,
                tempo,
                tipo,
                mensagem
            )

        else:
            database.add_lembrete(
                nome,
                evento,
                tempo,
                tipo,
                mensagem
            )

        self.atualizar_lista_lembretes()
        self.cancelar_edicao()

    def excluir_lembrete(self):
        if self.editando_lembrete_id:
            database.delete_lembrete(self.editando_lembrete_id)
            self.atualizar_lista_lembretes()
            self.cancelar_edicao()

    # =========================================================================
    # BANCO DE HORAS (INTERFACE E COMUNICAÇÃO)
    # =========================================================================
    def show_banco_window(self):
        if hasattr(self, 'win_banco') and self.win_banco and self.win_banco.winfo_exists():
            self.win_banco.lift()
            self.win_banco.focus_force()
            return
            
        self.win_banco = tk.Toplevel(self.root)
        self.win_banco.title(TEXT_TITLE_BANCO)
        self.win_banco.geometry("820x550") 
        self.win_banco.configure(bg=settings.COLOR_BG)
        
        top_frame = tk.Frame(self.win_banco, bg=settings.COLOR_BG)
        top_frame.pack(pady=10, fill=tk.X, padx=10)
        
        self.meses_disponiveis = database.get_meses_disponiveis()
        self.mes_selecionado_var = tk.StringVar()
        
        self.cb_mes = ttk.Combobox(top_frame, textvariable=self.mes_selecionado_var, values=self.meses_disponiveis, state="readonly", width=9, font=FONT_INPUTS)
        self.cb_mes.pack(side=tk.LEFT, padx=(0, 10))
        if self.meses_disponiveis:
            self.cb_mes.current(0)
        self.cb_mes.bind("<<ComboboxSelected>>", lambda e: self.atualizar_lista_banco())
        
        self.btn_atualizar_banco = tk.Button(top_frame, text=TEXT_BTN_ATUALIZAR_BANCO, bg="#007bff", fg="white", font=FONT_BTN_SALVAR_CONF, 
                                             relief="flat", command=self.sincronizar_banco)
        self.btn_atualizar_banco.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_limpar_banco = tk.Button(top_frame, text=TEXT_BTN_LIMPAR_MES, bg=settings.COLOR_BUTTON_RED, fg="white", font=FONT_BTN_SALVAR_CONF, 
                                          relief="flat", command=self.limpar_mes_banco)
        self.btn_limpar_banco.pack(side=tk.LEFT)

        self.btn_relatorio_banco = tk.Button(
            top_frame,
            text=TEXT_BTN_RELATORIO,
            bg="#28a745",
            fg="white",
            font=FONT_BTN_SALVAR_CONF,
            relief="flat",
            command=self.gerar_relatorio_mes_selecionado
        )

        self.btn_relatorio_banco.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )
        
        self.progress_banco = ttk.Progressbar(top_frame, mode='indeterminate', length=100)
        
        self.lbl_saldo_mes = tk.Label(top_frame, text="", font=FONT_BTN_SALVAR_CONF, bg=settings.COLOR_BG)
        self.lbl_saldo_mes.pack(side=tk.RIGHT, padx=10)

        # Tabela do Banco de Horas
        tree_frame = tk.Frame(self.win_banco, bg=settings.COLOR_BG)
        tree_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        columns = ("data", "dia", "m1", "m2", "m3", "m4", "saldo", "justificativa", "manual")
        self.tree_banco = ttk.Treeview(tree_frame, columns=columns, displaycolumns=("data", "dia", "m1", "m2", "m3", "m4", "saldo", "justificativa"), show="headings", height=10)
        
        self.tree_banco.heading("data", text="Data")
        self.tree_banco.heading("dia", text="Dia")
        self.tree_banco.heading("m1", text="Entrada")
        self.tree_banco.heading("m2", text="Saída Almoço")
        self.tree_banco.heading("m3", text="Ret. Almoço")
        self.tree_banco.heading("m4", text="Saída")
        self.tree_banco.heading("saldo", text="Saldo Dia")
        self.tree_banco.heading("justificativa", text="Justificativa")
        
        self.tree_banco.tag_configure("possui_inserido", background="#F0F0F0")
        
        self.tree_banco.column("data", width=90, anchor="center")
        self.tree_banco.column("dia", width=50, anchor="center")
        self.tree_banco.column("m1", width=70, anchor="center")
        self.tree_banco.column("m2", width=70, anchor="center")
        self.tree_banco.column("m3", width=70, anchor="center")
        self.tree_banco.column("m4", width=70, anchor="center")
        self.tree_banco.column("saldo", width=80, anchor="center")
        self.tree_banco.column("justificativa", width=170, anchor="w")
            
        self.tree_banco.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_banco.yview)
        self.tree_banco.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_banco.bind("<<TreeviewSelect>>", self.carregar_edicao_banco)

        # LEGENDA_ORIGEM_MARCACOES_V3
        tk.Label(
            self.win_banco,
            text="* Horário inserido ou alterado manualmente",
            bg=settings.COLOR_BG,
            fg="#303030",
            font=("Segoe UI", 9, "bold")
        ).pack(
            pady=(0, 2)
        )

        # Campos para Edição Manual
        form_frame = tk.Frame(self.win_banco, bg=settings.COLOR_BG)
        form_frame.pack(pady=10, fill=tk.X, padx=20)
        
        tk.Label(form_frame, text=TEXT_LBL_BH_DATA, bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=0, column=0, pady=2, padx=(5,2), sticky="e")
        self.ent_banco_data = tk.Entry(form_frame, font=FONT_INPUTS, width=12, relief="solid", bd=1, state="readonly", justify="center")
        self.ent_banco_data.grid(row=0, column=1, pady=2, padx=2)
        
        self.banco_m1_var = tk.StringVar()
        self.banco_m2_var = tk.StringVar()
        self.banco_m3_var = tk.StringVar()
        self.banco_m4_var = tk.StringVar()
        
        self.banco_m1_var.trace_add("write", lambda *args: self.formatar_tempo_generico(self.banco_m1_var, self.ent_banco_m1))
        self.banco_m2_var.trace_add("write", lambda *args: self.formatar_tempo_generico(self.banco_m2_var, self.ent_banco_m2))
        self.banco_m3_var.trace_add("write", lambda *args: self.formatar_tempo_generico(self.banco_m3_var, self.ent_banco_m3))
        self.banco_m4_var.trace_add("write", lambda *args: self.formatar_tempo_generico(self.banco_m4_var, self.ent_banco_m4))
        
        tk.Label(form_frame, text=TEXT_LBL_BH_M1, bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=0, column=2, pady=2, padx=(10,2))
        self.ent_banco_m1 = tk.Entry(form_frame, textvariable=self.banco_m1_var, font=FONT_INPUTS, width=8, relief="solid", bd=1, justify="center")
        self.ent_banco_m1.grid(row=0, column=3, pady=2, padx=2)
        
        tk.Label(form_frame, text=TEXT_LBL_BH_M2, bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=0, column=4, pady=2, padx=(10,2))
        self.ent_banco_m2 = tk.Entry(form_frame, textvariable=self.banco_m2_var, font=FONT_INPUTS, width=8, relief="solid", bd=1, justify="center")
        self.ent_banco_m2.grid(row=0, column=5, pady=2, padx=2)
        
        tk.Label(form_frame, text=TEXT_LBL_BH_M3, bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=0, column=6, pady=2, padx=(10,2))
        self.ent_banco_m3 = tk.Entry(form_frame, textvariable=self.banco_m3_var, font=FONT_INPUTS, width=8, relief="solid", bd=1, justify="center")
        self.ent_banco_m3.grid(row=0, column=7, pady=2, padx=2)
        
        tk.Label(form_frame, text=TEXT_LBL_BH_M4, bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=0, column=8, pady=2, padx=(10,2))
        self.ent_banco_m4 = tk.Entry(form_frame, textvariable=self.banco_m4_var, font=FONT_INPUTS, width=8, relief="solid", bd=1, justify="center")
        self.ent_banco_m4.grid(row=0, column=9, pady=2, padx=2)

        # CAMPOS_HORARIO_BANCO_V4
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

        tk.Label(form_frame, text="Justificativa:", bg=settings.COLOR_BG, font=FONT_INPUTS).grid(row=1, column=0, pady=4, padx=(5,2), sticky="e")
        self.ent_banco_justificativa = tk.Entry(form_frame, font=FONT_INPUTS, width=65, relief="solid", bd=1)
        self.ent_banco_justificativa.grid(row=1, column=1, columnspan=9, pady=4, padx=2, sticky="w")

        # Botões de Ação do Formulário
        btn_action_frame = tk.Frame(self.win_banco, bg=settings.COLOR_BG)
        btn_action_frame.pack(pady=(5, 20))

        self.btn_salvar_banco = tk.Button(btn_action_frame, text=TEXT_BTN_SALVAR_BANCO, bg="#28a745", fg="white", font=FONT_BTN_SALVAR_CONF, 
                                          relief="flat", command=self.salvar_banco)
        self.btn_salvar_banco.pack(side=tk.LEFT, padx=10)
        
        self.btn_cancelar_banco = tk.Button(btn_action_frame, text=TEXT_BTN_CANCELAR_BANCO, bg="#6c757d", fg="white", font=FONT_BTN_SALVAR_CONF, 
                                            relief="flat", command=self.cancelar_edicao_banco)
        self.btn_cancelar_banco.pack(side=tk.LEFT, padx=10)
        self.btn_cancelar_banco.pack_forget() 
        
        self.btn_restaurar_banco = tk.Button(btn_action_frame, text=TEXT_BTN_RESTAURAR_BANCO, bg="#ffc107", fg="black", font=FONT_BTN_SALVAR_CONF, 
                                             relief="flat", command=self.restaurar_banco)
        self.btn_restaurar_banco.pack(side=tk.LEFT, padx=10)
        self.btn_restaurar_banco.pack_forget()

        self.atualizar_lista_banco()

    def gerar_relatorio_mes_selecionado(self):
        """
        Gera o relatório usando o mês selecionado
        na tela Banco de Horas.
        """

        mes_ano = self.mes_selecionado_var.get().strip()

        if not mes_ano:
            messagebox.showwarning(
                "Relatório",
                "Selecione um mês para gerar o relatório."
            )
            return

        self.gerar_relatorio_banco(mes_ano)

    def gerar_relatorio_banco(self, mes_ano):
        """
        Solicita o local de salvamento e gera o PDF mensal.
        """

        mes_ano = str(mes_ano).strip()

        if not re.fullmatch(
            r"\d{2}/\d{4}",
            mes_ano
        ):
            messagebox.showwarning(
                "Relatório",
                "O período selecionado é inválido."
            )
            return

        try:
            registros = (
                database.get_banco_horas_relatorio(
                    mes_ano
                )
            )

        except Exception as erro:
            messagebox.showerror(
                "Relatório",
                f"Não foi possível consultar os dados: {erro}"
            )
            return

        if not registros:
            messagebox.showwarning(
                "Relatório",
                (
                    "Não existem registros de banco de horas "
                    f"para o período {mes_ano}."
                )
            )
            return

        try:
            saldo_mes, _ = database.get_saldo_mes(
                mes_ano
            )

        except Exception:
            saldo_mes = "00:00"

        nome_padrao = (
            "relatorio_banco_horas_"
            + mes_ano.replace("/", "_")
            + ".pdf"
        )

        caminho = filedialog.asksaveasfilename(
            parent=(
                self.win_banco
                if (
                    self.win_banco
                    and self.win_banco.winfo_exists()
                )
                else self.root
            ),
            title="Salvar Relatório de Banco de Horas",
            defaultextension=".pdf",
            initialfile=nome_padrao,
            filetypes=[
                ("Arquivo PDF", "*.pdf")
            ]
        )

        if not caminho:
            return

        try:
            relatorio.gerar_pdf(
                caminho_arquivo=caminho,
                mes_ano=mes_ano,
                registros=registros,
                saldo_mes=saldo_mes,
                matricula=self.config.get(
                    "matricula",
                    ""
                )
            )

            messagebox.showinfo(
                "Relatório gerado",
                (
                    "O relatório foi gerado com sucesso.\n\n"
                    f"Arquivo:\n{caminho}"
                )
            )

        except Exception as erro:
            messagebox.showerror(
                "Erro ao gerar relatório",
                (
                    "Não foi possível gerar o arquivo PDF.\n\n"
                    f"Detalhes: {erro}"
                )
            )

    def show_relatorio_window(self):
        """
        Exibe a seleção de período para geração do relatório
        quando o acesso ocorrer pelo menu da bandeja.
        """

        if (
            self.win_relatorio
            and self.win_relatorio.winfo_exists()
        ):
            self.win_relatorio.lift()
            self.win_relatorio.focus_force()
            return

        meses = database.get_meses_disponiveis()

        self.win_relatorio = tk.Toplevel(
            self.root
        )

        self.win_relatorio.title(
            TEXT_TITLE_RELATORIO
        )

        self.win_relatorio.geometry(
            "390x190"
        )

        self.win_relatorio.configure(
            bg=settings.COLOR_BG
        )

        self.win_relatorio.resizable(
            False,
            False
        )

        self.win_relatorio.attributes(
            "-topmost",
            True
        )

        tk.Label(
            self.win_relatorio,
            text="Relatório de Banco de Horas",
            bg=settings.COLOR_BG,
            fg=settings.COLOR_TEXT_BLUE,
            font=("Segoe UI", 14, "bold")
        ).pack(
            pady=(20, 10)
        )

        tk.Label(
            self.win_relatorio,
            text=TEXT_LBL_PERIODO_RELATORIO,
            bg=settings.COLOR_BG,
            font=FONT_INPUTS
        ).pack(
            pady=(0, 5)
        )

        mes_relatorio_var = tk.StringVar()

        cb_relatorio_mes = ttk.Combobox(
            self.win_relatorio,
            textvariable=mes_relatorio_var,
            values=meses,
            state="readonly",
            width=12,
            justify="center",
            font=FONT_INPUTS
        )

        cb_relatorio_mes.pack(
            pady=(0, 15)
        )

        if meses:
            cb_relatorio_mes.current(0)

        def gerar():
            mes = mes_relatorio_var.get().strip()

            if not mes:
                messagebox.showwarning(
                    "Relatório",
                    "Selecione um mês.",
                    parent=self.win_relatorio
                )
                return

            self.gerar_relatorio_banco(mes)

        tk.Button(
            self.win_relatorio,
            text=TEXT_BTN_GERAR_RELATORIO,
            bg="#28a745",
            fg="white",
            font=FONT_BTN_SALVAR_CONF,
            relief="flat",
            command=gerar,
            width=18
        ).pack(
            pady=(0, 15)
        )

    def limpar_mes_banco(self):
        mes_sel = self.mes_selecionado_var.get()
        if not mes_sel:
            return
            
        confirmacao = messagebox.askyesno("Confirmar Limpeza", f"Tem certeza que deseja apagar TODAS as marcações salvas (incluindo edições manuais) do mês {mes_sel}?")
        if confirmacao:
            try:
                database.delete_mes_banco(mes_sel)
                self.atualizar_lista_banco()
                messagebox.showinfo("Sucesso", f"As marcações do mês {mes_sel} foram limpas do banco.")
            except Exception as e:
                messagebox.showerror("Erro", f"Ocorreu um erro ao limpar o mês: {e}")

    def atualizar_resumo_mes(self):
        mes_sel = self.mes_selecionado_var.get()
        if not mes_sel:
            return
            
        try:
            if hasattr(database, 'get_saldo_mes'):
                saldo_str, mins = database.get_saldo_mes(mes_sel)
                if mins > 0:
                    cor = settings.COLOR_GREEN
                elif mins < 0:
                    cor = settings.COLOR_BUTTON_RED
                else:
                    cor = "#999999"
                self.lbl_saldo_mes.config(text=f"{TEXT_LBL_SALDO_MES} {saldo_str}", fg=cor)
        except Exception:
            pass

    def atualizar_lista_banco(self):
        """
        Atualiza a tela Banco de Horas.

        Somente horários que não correspondem a uma ocorrência original do
        dia recebem *. A posição da marcação não interfere na comparação.
        """
        from collections import Counter

        for item in self.tree_banco.get_children():
            self.tree_banco.delete(item)

        mes_sel = self.mes_selecionado_var.get()
        if not mes_sel:
            return

        def normalizar(valor):
            if valor is None:
                return ""
            texto = str(valor).strip()
            if texto.lower() in ("", "-", "--:--", "none", "null"):
                return ""
            return texto

        try:
            registros = database.get_banco_horas(mes_sel)

            for registro in registros:
                atuais = list(registro[1:5])
                originais = list(registro[8:12]) if len(registro) >= 12 else []
                manual_linha = bool(registro[6]) if len(registro) > 6 else False

                contador = Counter(
                    normalizar(valor)
                    for valor in originais
                    if normalizar(valor)
                )
                existem_originais = bool(contador)
                horarios_exibicao = []
                possui_inserido = False

                for valor in atuais:
                    horario = normalizar(valor)
                    if not horario:
                        horarios_exibicao.append("")
                        continue

                    if contador[horario] > 0:
                        contador[horario] -= 1
                        horarios_exibicao.append(horario)
                    elif not existem_originais and not manual_linha:
                        # Compatibilidade com registros antigos que ainda não
                        # possuam cópia das marcações originais.
                        horarios_exibicao.append(horario)
                    else:
                        horarios_exibicao.append(f"* {horario}")
                        possui_inserido = True

                dia_str = database.get_dia_semana(registro[0])
                valores = (
                    registro[0],
                    dia_str,
                    horarios_exibicao[0],
                    horarios_exibicao[1],
                    horarios_exibicao[2],
                    horarios_exibicao[3],
                    registro[5],
                    registro[7],
                    registro[6]
                )

                tags = ("possui_inserido",) if possui_inserido else ()
                self.tree_banco.insert(
                    "",
                    "end",
                    values=valores,
                    tags=tags
                )

            self.atualizar_resumo_mes()

        except Exception as erro:
            messagebox.showerror(
                "Banco de Horas",
                f"Não foi possível carregar as marcações: {erro}"
            )

    def limpar_indicador_origem(self, valor):
        """Remove o asterisco visual antes de carregar o horário na edição."""
        if valor is None:
            return ""

        texto = str(valor).strip()
        if texto.lower() in ("", "-", "--:--", "none", "null"):
            return ""

        return re.sub(
            r"^(?:\*|R|I)\s*",
            "",
            texto
        ).strip()

    def carregar_edicao_banco(self, event=None):
        selected = self.tree_banco.selection()
        if not selected:
            return

        item_values = self.tree_banco.item(
            selected[0],
            "values"
        )

        self.ent_banco_data.config(state=tk.NORMAL)
        self.ent_banco_data.delete(0, tk.END)
        self.ent_banco_data.insert(0, item_values[0])
        self.ent_banco_data.config(state="readonly")

        self.banco_m1_var.set(
            self.limpar_indicador_origem(item_values[2])
        )
        self.banco_m2_var.set(
            self.limpar_indicador_origem(item_values[3])
        )
        self.banco_m3_var.set(
            self.limpar_indicador_origem(item_values[4])
        )
        self.banco_m4_var.set(
            self.limpar_indicador_origem(item_values[5])
        )

        self.ent_banco_justificativa.delete(0, tk.END)
        if len(item_values) > 7 and item_values[7] != "None":
            self.ent_banco_justificativa.insert(0, item_values[7])

        self.btn_cancelar_banco.pack(side=tk.LEFT, padx=10)
        self.btn_restaurar_banco.pack(side=tk.LEFT, padx=10)

    def cancelar_edicao_banco(self):
        self.ent_banco_data.config(state=tk.NORMAL)
        self.ent_banco_data.delete(0, tk.END)
        self.ent_banco_data.config(state="readonly")
        
        self.banco_m1_var.set("")
        self.banco_m2_var.set("")
        self.banco_m3_var.set("")
        self.banco_m4_var.set("")
        self.ent_banco_justificativa.delete(0, tk.END)
        
        self.btn_cancelar_banco.pack_forget()
        self.btn_restaurar_banco.pack_forget()
        
        if self.tree_banco.selection():
            self.tree_banco.selection_remove(self.tree_banco.selection())

    def salvar_banco(self):
        data = self.ent_banco_data.get().strip()

        if not data:
            messagebox.showwarning(
                "Atenção",
                "Selecione um dia na tabela para editar "
                "as marcações."
            )
            return

        m1 = self.banco_m1_var.get().strip()
        m2 = self.banco_m2_var.get().strip()
        m3 = self.banco_m3_var.get().strip()
        m4 = self.banco_m4_var.get().strip()

        justificativa = (
            self.ent_banco_justificativa
            .get()
            .strip()
        )

        marcacoes = {
            "M1": m1,
            "M2": m2,
            "M3": m3,
            "M4": m4
        }

        for nome_campo, horario in marcacoes.items():
            if (
                horario
                and not self.validar_horario(horario)
            ):
                messagebox.showwarning(
                    "Horário inválido",
                    f"O horário informado em "
                    f"{nome_campo} não é válido."
                )
                return

        preenchidos = []

        for indice, horario in enumerate(
            [m1, m2, m3, m4],
            start=1
        ):
            if horario:
                hora, minuto = map(
                    int,
                    horario.split(":")
                )

                preenchidos.append(
                    (
                        indice,
                        hora * 60 + minuto
                    )
                )

        for indice in range(
            1,
            len(preenchidos)
        ):
            campo_anterior, minutos_anteriores = (
                preenchidos[indice - 1]
            )

            campo_atual, minutos_atuais = (
                preenchidos[indice]
            )

            if minutos_atuais < minutos_anteriores:
                messagebox.showwarning(
                    "Sequência inválida",
                    "As marcações devem estar em ordem "
                    "cronológica. "
                    f"M{campo_atual} não pode ser anterior "
                    f"a M{campo_anterior}."
                )
                return

        try:
            database.update_dia_banco(
                data,
                m1,
                m2,
                m3,
                m4,
                justificativa=justificativa,
                is_manual=True
            )

            self.atualizar_lista_banco()
            self.cancelar_edicao_banco()

        except Exception as erro:
            messagebox.showerror(
                "Erro",
                f"Falha ao salvar: {erro}"
            )

    def restaurar_banco(self):
        data = self.ent_banco_data.get()
        if not data:
            return
        
        confirmacao = messagebox.askyesno("Confirmar Restauração", f"Deseja restaurar as marcações originais do sistema para o dia {data}?")
        if confirmacao:
            try:
                if hasattr(database, 'restaurar_dia_original'):
                    database.restaurar_dia_original(data)
                    self.atualizar_lista_banco()
                    self.cancelar_edicao_banco()
                    messagebox.showinfo("Sucesso", f"O dia {data} foi restaurado para os valores originais da importação.")
            except Exception as e:
                messagebox.showerror("Erro", f"Ocorreu um erro na restauração: {e}")

    def sincronizar_banco(self):
        self.btn_atualizar_banco.config(state=tk.DISABLED)
        self.btn_limpar_banco.config(state=tk.DISABLED)
        self.progress_banco.pack(side=tk.LEFT, padx=10)
        self.progress_banco.start(15)
        
        def run_sync():
            try:
                if hasattr(scraper, 'sync_mes_scraper') and self.config.get("matricula"):
                    scraper.sync_mes_scraper(self.config["matricula"], self.config["senha"])
                    
                    novos_meses = database.get_meses_disponiveis()
                    self.root.after(0, lambda: self.cb_mes.config(values=novos_meses))
                    self.root.after(0, self.atualizar_lista_banco)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", f"Falha na sincronização: {e}"))
            finally:
                self.root.after(0, self.progress_banco.stop)
                self.root.after(0, self.progress_banco.pack_forget)
                self.root.after(0, lambda: self.btn_atualizar_banco.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.btn_limpar_banco.config(state=tk.NORMAL))
                
        threading.Thread(target=run_sync, daemon=True).start()

    # =========================================================================
    # SISTEMA DE LEMBRETE E ALARME POP-UP
    # =========================================================================
    def mostrar_lembrete(self, nome, mensagem, horario):
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:
            pass

        top = tk.Toplevel(self.root)
        top.title(TEXT_TITLE_LEMBRETE_POPUP)
        top.attributes("-topmost", True)
        
        w = 360
        h = 180
        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int((sh - h) / 2)
        top.geometry(f"{w}x{h}+{x}+{y}")
        top.configure(bg=settings.COLOR_BG)
        top.resizable(False, False)
        
        if not mensagem or mensagem.strip() == "":
            mensagem_final = TEXT_MENSAGEM_PADRAO.format(horario)
        else:
            if "{}" in mensagem:
                mensagem_final = mensagem.replace("{}", horario)
            else:
                mensagem_final = mensagem
        
        tk.Label(top, text=nome.upper(), font=FONT_ATENCAO, bg=settings.COLOR_BG, fg=settings.COLOR_TEXT_BLUE, wraplength=320, justify="center").pack(pady=(20, 5), padx=20)
        tk.Label(top, text=mensagem_final, font=FONT_CORPO_LEMBRETE, bg=settings.COLOR_BG, fg="#333333", wraplength=320, justify="center").pack(pady=(0, 15), padx=20)
        tk.Button(top, text=TEXT_BTN_CIENTE, bg=settings.COLOR_BUTTON_RED, fg="white", font=FONT_BTN_CIENTE, relief="flat", command=top.destroy, width=15).pack(pady=(0, 20))

    # =========================================================================
    # MOTOR DE LAÇO DO RELÓGIO E EVENTOS DINÂMICOS
    # =========================================================================
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

    def update_clock_loop(self):
        while True:
            agora = datetime.datetime.now()
            data_atual = agora.date()

            if data_atual != self.data_controle_lembretes:
                self.lembretes_exibidos.clear()
                self.data_controle_lembretes = data_atual
            hora_str = agora.strftime("%H:%M:%S")
            self.root.after(
                0,
                lambda valor=hora_str: self.atualizar_texto_relogio(valor)
            )
                
            agora_normalizado = datetime.datetime(agora.year, agora.month, agora.day, agora.hour, agora.minute, 0)
            
            def calc_prev(t_str, h):
                try:
                    t = datetime.datetime.strptime(t_str, "%H:%M")
                    t += datetime.timedelta(hours=h)
                    return t.strftime("%H:%M")
                except:
                    return None

            event_times = {}
            saida_almoco_padrao = self.config.get("saida_almoco", "12:00")
            
            if self.marca1:
                event_times[EVENTO_ENTRADA] = self.marca1
                event_times[EVENTO_PREV_SAIDA] = calc_prev(self.marca1, 9)
                
                if self.marca2:
                    event_times[EVENTO_INICIO_ALMOCO] = self.marca2
                    event_times[EVENTO_PREV_FIM_ALMOCO] = calc_prev(self.marca2, 1)
                else:
                    if self.marca1 <= saida_almoco_padrao:
                        event_times[EVENTO_PREV_ALMOCO] = saida_almoco_padrao
                        event_times[EVENTO_PREV_FIM_ALMOCO] = calc_prev(saida_almoco_padrao, 1)
                        
                if self.marca3:
                    event_times[EVENTO_FIM_ALMOCO] = self.marca3
                    
                if self.marca4:
                    event_times[EVENTO_SAIDA] = self.marca4

            for lembrete in self.lembretes_db:
                l_id, nome, evento, tempo_str, tipo, mensagem = lembrete
                
                if evento == EVENTO_FIXO:
                    try:
                        partes = tempo_str.split(':')
                        if len(partes) == 2 and partes[0].isdigit() and partes[1].isdigit():
                            t_h, t_m = int(partes[0]), int(partes[1])
                            if 0 <= t_h <= 23 and 0 <= t_m <= 59:
                                dt_alerta = datetime.datetime(agora.year, agora.month, agora.day, t_h, t_m, 0)
                                if agora.hour == dt_alerta.hour and agora.minute == dt_alerta.minute:
                                    alerta_id = f"{agora.year}{agora.month}{agora.day}_{nome}_{dt_alerta.strftime('%H:%M')}"
                                    if alerta_id not in self.lembretes_exibidos:
                                        self.lembretes_exibidos.add(alerta_id)
                                        self.root.after(0, lambda n=nome, msg=mensagem, h=dt_alerta.strftime('%H:%M'): self.mostrar_lembrete(n, msg, h))
                    except Exception as e:
                        pass
                else:
                    horario_base = event_times.get(evento)
                    
                    if horario_base:
                        try:
                            hb_h, hb_m = map(int, horario_base.split(':'))
                            t_h, t_m = map(int, tempo_str.split(':'))
                            
                            dt_base = datetime.datetime(agora.year, agora.month, agora.day, hb_h, hb_m, 0)
                            delta = datetime.timedelta(hours=t_h, minutes=t_m)
                            
                            if tipo == "Antes":
                                dt_alerta = dt_base - delta
                            elif tipo == "Depois":
                                dt_alerta = dt_base + delta
                            else: 
                                dt_alerta = dt_base
                                
                            if agora.hour == dt_alerta.hour and agora.minute == dt_alerta.minute:
                                alerta_id = f"{agora.year}{agora.month}{agora.day}_{nome}_{dt_alerta.strftime('%H:%M')}"
                                if alerta_id not in self.lembretes_exibidos:
                                    self.lembretes_exibidos.add(alerta_id)
                                    self.root.after(0, lambda n=nome, msg=mensagem, h=dt_base.strftime('%H:%M'): self.mostrar_lembrete(n, msg, h))
                        except:
                            pass

            mostrar_tempo = False
            texto_tempo = ""
            cor_tempo = ""
            
            mostrar_almoco = False
            texto_almoco = ""
            cor_almoco = ""

            if self.marca4 and self.marca3 and self.marca2 and self.marca1:
                try:
                    h1, min1 = map(int, self.marca1.split(':'))
                    h2, min2 = map(int, self.marca2.split(':'))
                    h3, min3 = map(int, self.marca3.split(':'))
                    h4, min4 = map(int, self.marca4.split(':'))
                    
                    t1 = h1*60 + min1
                    t2 = h2*60 + min2
                    t3 = h3*60 + min3
                    t4 = h4*60 + min4
                    
                    total_trabalhado = (t4 - t3) + (t2 - t1)
                    h_w, m_w = divmod(total_trabalhado, 60)
                    
                    texto_tempo = f"{TEXT_PREFIX_JORNADA}{h_w:02d}:{m_w:02d}:00"
                    cor_tempo = "#999999"
                    mostrar_tempo = True
                except Exception:
                    pass
            elif self.marca1:
                try:
                    h_in, m_in = map(int, self.marca1.split(":"))
                    entrada_dt = datetime.datetime(agora.year, agora.month, agora.day, h_in, m_in, 0)
                    saida_dt = entrada_dt + datetime.timedelta(hours=9)
                    
                    diff = saida_dt - agora 
                    total_segundos = int(diff.total_seconds())
                    
                    if total_segundos > 0:
                        horas, resto = divmod(total_segundos, 3600)
                        mins, segs = divmod(resto, 60)
                        texto_tempo = f"{TEXT_PREFIX_JORNADA}-{horas:02d}:{mins:02d}:{segs:02d}"
                        cor_tempo = settings.COLOR_BUTTON_RED
                    else:
                        total_segundos_extra = abs(total_segundos)
                        horas, resto = divmod(total_segundos_extra, 3600)
                        mins, segs = divmod(resto, 60)
                        texto_tempo = f"{TEXT_PREFIX_JORNADA}+{horas:02d}:{mins:02d}:{segs:02d}"
                        cor_tempo = settings.COLOR_GREEN
                    mostrar_tempo = True
                    
                    if (
                        self.marca2
                        and not self.marca3
                        and not self.esquecimento_marcacao_ativo()
                    ):
                        h2, m2 = map(int, self.marca2.split(":"))
                        m2_dt = datetime.datetime(agora.year, agora.month, agora.day, h2, m2, 0)
                        
                        volta_almoco_dt = m2_dt + datetime.timedelta(hours=1)
                        
                        diff_almoco = volta_almoco_dt - agora
                        total_segundos_almoco = int(diff_almoco.total_seconds())
                        
                        if total_segundos_almoco > 0:
                            h_a, resto_a = divmod(total_segundos_almoco, 3600)
                            m_a, s_a = divmod(resto_a, 60)
                            texto_almoco = f"{TEXT_PREFIX_ALMOCO}-{h_a:02d}:{m_a:02d}:{s_a:02d}"
                            cor_almoco = settings.COLOR_YELLOW
                        else:
                            total_segundos_extra = abs(total_segundos_almoco)
                            h_a, resto_a = divmod(total_segundos_extra, 3600)
                            m_a, s_a = divmod(resto_a, 60)
                            texto_almoco = f"{TEXT_PREFIX_ALMOCO}+{h_a:02d}:{m_a:02d}:{s_a:02d}"
                            cor_almoco = settings.COLOR_BUTTON_RED
                        
                        mostrar_almoco = True
                        mostrar_tempo = False 
                        
                except Exception:
                    pass
            
            # Oculta os relógios secundários durante a busca
            if self.buscando_marcacoes:
                mostrar_tempo = False
                mostrar_almoco = False

            state_changed = False
            
            try:
                if mostrar_tempo:
                    self.lbl_tempo_restante.config(text=texto_tempo, fg=cor_tempo)
                    if not self.ui_state['tempo']:
                        self.lbl_tempo_restante.pack(after=self.lbl_relogio, pady=0)
                        self.ui_state['tempo'] = True
                        state_changed = True
                else:
                    if self.ui_state['tempo']:
                        self.lbl_tempo_restante.pack_forget() 
                        self.ui_state['tempo'] = False
                        state_changed = True
                    
                if mostrar_almoco:
                    self.lbl_almoco_restante.config(text=texto_almoco, fg=cor_almoco)
                    if not self.ui_state['almoco']:
                        ref_widget = self.lbl_tempo_restante if self.ui_state['tempo'] else self.lbl_relogio
                        self.lbl_almoco_restante.pack(after=ref_widget, pady=0)
                        self.ui_state['almoco'] = True
                        state_changed = True
                else:
                    if self.ui_state['almoco']:
                        self.lbl_almoco_restante.pack_forget() 
                        self.ui_state['almoco'] = False
                        state_changed = True
            except Exception:
                pass
            
            if state_changed:
                self.root.after(
                    0,
                    self.update_window_size_and_position
                )
                
            if hora_str == "06:00:00":
                self.root.after(0, lambda: self.atualizar_interface_marcacoes(TEXT_BUSCANDO))
                self.atualizar_event.set()
                
            time.sleep(1)

    # =========================================================================
    # THREADS DE AUTOMATIZAÇÃO DE RASPAGEM E EVENTOS DE APLICATIVO
    # =========================================================================
    def atualizar_marcacoes_loop(self):
        while True:
            if self.config.get("matricula") and self.config.get("senha"):
                resultado = scraper.buscar_marcacoes_selenium(self.config["matricula"], self.config["senha"])
                self.root.after(0, lambda m=resultado: self.atualizar_interface_marcacoes(m))
            
            self.atualizar_event.wait()
            self.atualizar_event.clear()

    def registrar_ponto_action(self):
        self.horario_clique_registrar = (
            time.monotonic()
        )

        self.root.withdraw()

        threading.Thread(
            target=self.automacao_registro,
            daemon=True
        ).start()

    def automacao_registro(self):
        matricula = (
            self.config
            .get("matricula", "")
            .strip()
        )

        senha = self.config.get(
            "senha",
            ""
        )

        if not matricula or not senha:
            self.root.after(
                0,
                lambda: messagebox.showwarning(
                    "Configuração necessária",
                    "Configure a matrícula e a senha "
                    "antes de registrar o ponto."
                )
            )

            self.root.after(
                0,
                self.show_main_window
            )
            return

        sucesso, msg = scraper.realizar_registro_ponto(
            matricula,
            senha
        )

        if not sucesso:
            self.root.after(
                0,
                lambda mensagem=msg: messagebox.showerror(
                    "Erro",
                    mensagem
                )
            )

            self.root.after(
                0,
                self.show_main_window
            )
            return

        try:
            intervalo = int(
                self.config.get(
                    "intervalo_atualizacao",
                    10
                )
            )
        except (TypeError, ValueError):
            intervalo = 10

        intervalo = max(
            0,
            min(intervalo, 3600)
        )

        momento_clique = getattr(
            self,
            "horario_clique_registrar",
            time.monotonic()
        )

        tempo_decorrido = (
            time.monotonic()
            - momento_clique
        )

        tempo_restante = max(
            0,
            intervalo - tempo_decorrido
        )

        if tempo_restante > 0:
            time.sleep(tempo_restante)

        # Marca imediatamente o estado da busca para impedir
        # que o relógio secundário reapareça.
        self.buscando_marcacoes = True

        self.root.after(
            0,
            lambda: self.atualizar_interface_marcacoes(
                TEXT_BUSCANDO
            )
        )

        self.atualizar_event.set()

        self.root.after(
            0,
            self.show_main_window
        )

    def monitor_system(self):
        user32 = ctypes.windll.user32
        was_locked = False

        while True:
            try:
                is_locked = (
                    user32.GetForegroundWindow() == 0
                )

                if was_locked and not is_locked:
                    em_almoco = bool(
                        self.marca2
                        and not self.marca3
                        and not self.marca4
                        and not self.esquecimento_marcacao_ativo()
                    )

                    if not em_almoco:
                        self.root.after(
                            0,
                            self.show_main_window
                        )

                was_locked = is_locked

            except Exception:
                pass

            time.sleep(1)

    def show_main_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.update_window_size_and_position()

    def toggle_main_window(self):
        if self.root.winfo_viewable():
            self.root.withdraw()
        else:
            self.show_main_window()

    def create_clock_icon(self):
        image = Image.new('RGBA', (64, 64), color=(255, 255, 255, 0))
        d = ImageDraw.Draw(image)
        d.ellipse((4, 4, 60, 60), outline=settings.COLOR_TEXT_BLUE, width=6, fill="white")
        d.line((32, 32, 32, 16), fill=settings.COLOR_TEXT_BLUE, width=5)
        d.line((32, 32, 46, 32), fill=settings.COLOR_BUTTON_RED, width=5)
        return image

    def setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem(TEXT_TRAY_ABRIR, self.tray_toggle_app, default=True),
            pystray.MenuItem(TEXT_TRAY_ATUALIZAR, self.tray_force_update),
            pystray.MenuItem(TEXT_TRAY_ESQUECIMENTO, self.tray_esquecimento_marcacao),
            pystray.MenuItem(TEXT_TRAY_CONFIG, self.tray_show_config),
            pystray.MenuItem(TEXT_TRAY_LEMBRETES, self.tray_show_lembretes),
            pystray.MenuItem(TEXT_TRAY_BANCO, self.tray_show_banco_horas),
            pystray.MenuItem(TEXT_TRAY_RELATORIO, self.tray_show_relatorio),
            pystray.MenuItem(TEXT_TRAY_SAIR, self.tray_exit_app)
        )
        self.tray_icon = pystray.Icon("PontoApp", self.create_clock_icon(), TEXT_TITLE_APP, menu)
        self.tray_icon.run()

    def tray_toggle_app(self, icon, item):
        self.root.after(0, self.toggle_main_window)
        
    def tray_force_update(self, icon, item):
        self.root.after(0, lambda: self.atualizar_interface_marcacoes(TEXT_BUSCANDO))
        self.atualizar_event.set()

    def tray_show_config(self, icon, item):
        self.root.after(0, self.show_config_window)
        
    def tray_show_lembretes(self, icon, item):
        self.root.after(0, self.show_lembretes_window)

    def tray_show_banco_horas(self, icon, item):
        self.root.after(0, self.show_banco_window)

    def tray_show_relatorio(self, icon, item):
        self.root.after(
            0,
            self.show_relatorio_window
        )

    def tray_exit_app(self, icon, item):
        self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

if __name__ == "__main__":
    app = PontoApp()
    app.root.mainloop()