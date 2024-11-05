import flet as ft
import os
import configparser
from utils import gerar_chave
from main import abrir_tela_login

# Gera a chave na primeira execução
if not os.path.exists("chave.key"):
    gerar_chave()

def main(page: ft.Page):
    page.title = "OrionTax - Sistema de Importação de XML v.1.0.0"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT
    icon_path = "assets/img/icon.png"
    abs_icon_path = os.path.abspath(icon_path)    
    page.window.icon = abs_icon_path
    page.window.width = 1200
    page.window.height = 700
    page.window.min_width = 1200
    page.window.min_height = 700
    page.window.center()
    
    config_file = "config.ini"
    config = configparser.ConfigParser()
    
    def handle_window_event(e):
        if e.data == "close":
            page.open(confirm_dialog)

    page.window.prevent_close = True
    page.window.on_event = handle_window_event

    def yes_click(e):
        page.window.destroy()

    def no_click(e):
        page.close(confirm_dialog)

    confirm_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirma?"),
        content=ft.Text("Você deseja encerrar o sistema?"),
        actions=[
            ft.ElevatedButton("Sim", on_click=yes_click),
            ft.OutlinedButton("Não", on_click=no_click),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )    

    if not os.path.exists(config_file):
        def salvar_config(e):
            config['DEFAULT'] = {'HOST': api_url.value}
            with open(config_file, 'w') as configfile:
                config.write(configfile)
            abrir_tela_login(page, config, config_file)

        # Configuração inicial: pede a URL da API
        api_url = ft.TextField(label="Host", autofocus=True)
        salvar_button = ft.FilledButton(text="Salvar", on_click=salvar_config)
        page.add(ft.Column([api_url, salvar_button]))
    else:
        abrir_tela_login(page, config, config_file)

ft.app(target=main)
