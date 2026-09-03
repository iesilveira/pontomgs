"""
Autor: Ismael Elói da Silveira Silva
Descrição: Arquivo de configurações de constantes e identidade visual do sistema.
"""
import os

# Configurações de Caminho
APP_DIR = os.path.join(os.environ['APPDATA'], 'PontoApp')
DB_FILE = os.path.join(APP_DIR, 'database.db')

# Identidade Visual
COLOR_BG = "#FFFFFF"
COLOR_TEXT_BLUE = "#00205B"
COLOR_BUTTON_RED = "#ae1917"
COLOR_GREEN = "#28a745"
COLOR_YELLOW = "#D4A017"

# Fontes
FONT_CLOCK = ("Segoe UI", 36, "bold")
FONT_RESTANTE = ("Segoe UI Light", 16)
FONT_MARCACOES = ("Segoe UI", 16, "bold")
FONT_LABEL = ("Segoe UI", 12)