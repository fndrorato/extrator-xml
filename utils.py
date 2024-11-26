import flet as ft
from cryptography.fernet import Fernet
import os
import configparser

# Gera uma chave e a salva em um arquivo
def gerar_chave():
    chave = Fernet.generate_key()
    with open("chave.key", "wb") as chave_file:
        chave_file.write(chave)

# Carrega a chave a partir do arquivo
def carregar_chave():
    return open("chave.key", "rb").read()

# Função para criptografar os dados
def criptografar_dados(dados):
    chave = carregar_chave()
    fernet = Fernet(chave)
    dados_criptografados = fernet.encrypt(dados.encode())
    return dados_criptografados

# Função para descriptografar os dados
def descriptografar_dados(dados_criptografados):
    chave = carregar_chave()
    fernet = Fernet(chave)
    dados = fernet.decrypt(dados_criptografados).decode()
    return dados

def remover_textos(page, values):
    for control in page.controls:
        if isinstance(control, ft.Text) and control.value in values:
            page.controls.remove(control)
    page.update()
    
def get_host():
    config_file = "config.ini"
    config = configparser.ConfigParser()    
    if not os.path.exists(config_file):
        return None
    else:
        config.read(config_file)
        return config['DEFAULT']['HOST']        

def close_alert(alert_dialog, page):
    alert_dialog.open = False
    page.update()  
    
def close_dialog(page: ft.Page, dialog: ft.AlertDialog):
    dialog.open = False  # Fecha o diálogo
    page.update()  # Atualiza a página para refletir a mudança 
       