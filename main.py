import os
import flet as ft
import requests
from utils import (
    remover_textos, 
    criptografar_dados, 
    descriptografar_dados, 
    gerar_chave,
    get_host)
from upload_section import upload_section, validate_upload, validate_export_base, exportar_consolidado
import session


def abrir_tela_principal(page: ft.Page, first_name, config, config_file):
    page.appbar = ft.AppBar(
        title=ft.Text("OrionTax - Importador de XML", color=ft.colors.WHITE),
        bgcolor=ft.colors.BLUE_GREY_900,
        actions=[
            ft.Container(
                content=ft.Text(f"Bem-vindo, {first_name}", color=ft.colors.WHITE, size="small"),
                margin=ft.margin.only(left=0, top=0, right=20, bottom=0)
            )
        ]   
    )
    page.clean()
       
    def sair():
        page.appbar = None  # Remove a appbar
        page.clean()
        abrir_tela_login(page, config, config_file)  # Chama a função de abrir tela de login    

    def atualizar_conteudo(index):
        if index == 0:
            container_conteudo.content = upload_section(page)
        elif index == 1: 
            validate_export_base(page)
        elif index == 2: 
            exportar_consolidado(page)                        
        elif index == 3: 
            validate_upload(page)
        elif index == 4: 
            salvar_config(page, config, config_file)            
        else:  
            conteudo_text = {
                0: "Home - Bem-vindo à Home!",
                1: "Exportar Período CSV - Aqui você pode exportar.",
                2: "Configurações - Modifique suas preferências.",
            }
            container_conteudo.content = ft.Text(conteudo_text.get(index, "Selecione uma opção do menu."), style="headlineMedium")
        page.update()
                
    def on_destination_change(e):
        if e.control.selected_index == 5:  # Verifica se o índice é o da opção "Sair"
            sair()
        else:
            atualizar_conteudo(e.control.selected_index)
                        

    navigation = ft.NavigationRail(
        destinations=[
            ft.NavigationRailDestination(icon=ft.icons.HOME, label="Home"),
            ft.NavigationRailDestination(icon=ft.icons.ARCHIVE, label="Exportar base"),
            ft.NavigationRailDestination(icon=ft.icons.FILE_DOWNLOAD, label="Exportar consolidado"),
            ft.NavigationRailDestination(icon=ft.icons.CLOUD_UPLOAD, label="Fazer upload ao servidor"),
            ft.NavigationRailDestination(icon=ft.icons.SETTINGS, label="Configurações"),
            ft.NavigationRailDestination(icon=ft.icons.EXIT_TO_APP, label="Sair"),
        ],
        selected_index=0,
        on_change=on_destination_change
    )
    
    container_conteudo = ft.Container(
        content=upload_section(page),
        expand=True
    )

    page.add(
        ft.Row(
            [
                navigation,
                ft.VerticalDivider(width=1),
                container_conteudo
            ],
            expand=True,
        )
    )

def abrir_tela_login(page, config, config_file):
    def efetuar_login(e):
        remover_textos(page, ["Login falhou!", "Carregando..."])
                
        api_url = get_host()
        
        if api_url is None:
            page.add(ft.Text("Não foi possível carregar as informações do host.", color="red"))
        else:
            api_url = config['DEFAULT']['HOST']
            page.add(ft.Text("Carregando...", text_align=ft.TextAlign.CENTER))            
            usuario = usuario_field.value
            senha = senha_field.value
            try:
                response = requests.post(f"{api_url}/login/", json={"username": usuario, "password": senha})
                
                # Verifica se a requisição foi bem-sucedida
                if response.status_code == 200:
                    response_data = response.json()
                    first_name = response_data.get('first_name', '') 
                    session.user_id = response_data.get('user_id', '') 
                    session.token = response_data.get('token', '') 
                    
                    if lembrar_me_field.value:
                        dados_criptografados = criptografar_dados(f"{usuario},{senha}")
                        with open("credenciais.enc", "wb") as f:
                            f.write(dados_criptografados)
                    else:
                        try:
                            os.remove("credenciais.enc")
                        except FileNotFoundError:
                            print("Arquivo credenciais.enc não existe, nada para excluir.")                    

                    abrir_tela_principal(page, first_name, config, config_file)
                else:
                    # Resposta com erro, pode ser que as credenciais estejam erradas
                    remover_textos(page, ["Carregando..."])
                    error_message = response_data.get("error", "Erro desconhecido.")
                    page.add(ft.Text(f"Login falhou: {error_message}", color="red"))

            except requests.exceptions.ConnectionError:
                # Caso ocorra uma falha na conexão
                remover_textos(page, ["Carregando..."])
                page.add(ft.Text("Falha na conexão com o servidor. Verifique sua internet e tente novamente.", color="red"))
            except requests.exceptions.Timeout:
                # Caso a requisição ultrapasse o tempo limite
                remover_textos(page, ["Carregando..."])
                page.add(ft.Text("O servidor não respondeu a tempo. Tente novamente.", color="red"))
            except requests.exceptions.RequestException as e:
                # Captura qualquer outro erro de requisição
                remover_textos(page, ["Carregando..."])
                page.add(ft.Text(f"Erro ao se conectar ao servidor: {e}", color="red"))            

            # response = requests.post(f"{api_url}/login/", json={"username": usuario, "password": senha})
            # if response.status_code == 200: 
            #     response_data = response.json()
            #     first_name = response_data.get('first_name', '') 
            #     session.user_id = response_data.get('user_id', '') 
            #     session.token = response_data.get('token', '') 
            #     if lembrar_me_field.value:
            #         dados_criptografados = criptografar_dados(f"{usuario},{senha}")
            #         with open("credenciais.enc", "wb") as f:
            #             f.write(dados_criptografados)
            #     else:
            #         try:
            #             os.remove("credenciais.enc")
            #         except FileNotFoundError:
            #             print("Arquivo credenciais.enc não existe, nada para excluir.")                    

            #     abrir_tela_principal(page, first_name, config, config_file)
            # else:
            #     remover_textos(page, ["Carregando..."])
            #     page.add(ft.Text("Login falhou!", color="red"))

    def carregar_credenciais():
        if os.path.exists("credenciais.enc"):
            with open("credenciais.enc", "rb") as f:
                dados_criptografados = f.read()
            dados = descriptografar_dados(dados_criptografados)
            usuario, senha = dados.split(",")
            usuario_field.value = usuario
            senha_field.value = senha
            lembrar_me_field.value = True
            
    # Carrega o arquivo de configuração para obter o `API_URL`
    config.read(config_file)

    # Cria os campos da tela de login
    # Verifica se o logo existe e imprime o caminho absoluto
    logo_path = "assets/img/logo-login.png"
    abs_logo_path = os.path.abspath(logo_path)
    
    if os.path.exists(abs_logo_path):
        logo = ft.Image(src=abs_logo_path, width=300)  # Usando o caminho absoluto
    else:
        logo = ft.Text("Logo não disponível")  # Alternativa para o logo

    usuario_field = ft.TextField(label="Usuário", on_submit=efetuar_login)
    senha_field = ft.TextField(label="Senha", password=True, on_submit=efetuar_login)
    lembrar_me_field = ft.Checkbox(label="Lembrar-me")
    login_button = ft.FilledButton(text="Login", on_click=efetuar_login)

    carregar_credenciais()

    # Limpa a página e adiciona o formulário de login
    page.clean()
    page.add(
        ft.Column(
            [
                ft.Row([logo], alignment=ft.MainAxisAlignment.CENTER),
                usuario_field,
                senha_field,
                lembrar_me_field,
                login_button
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )
    )

def salvar_config(page: ft.Page, config, config_file):
    # Lê o arquivo de configuração
    if os.path.exists(config_file):
        config.read(config_file)
    
    # Obtém a URL da API ou define um valor padrão
    api_url = config['DEFAULT'].get('HOST', 'http://127.0.0.1:8000/api/v1')

    # Campo para atualizar o URL da API
    api_url_field = ft.TextField(value=api_url, label="Host")

    # Função para fechar o diálogo
    def close_dialog(e):
        dialog.open = False
        page.update()

    # Função para atualizar o config.ini
    def atualizar_config(e):
        config['DEFAULT']['HOST'] = api_url_field.value
        with open(config_file, 'w') as configfile:
            config.write(configfile)
        close_dialog(e)

    # Criação do diálogo de alerta com dois botões
    dialog = ft.AlertDialog(
        title=ft.Text("Configuração"),
        content=ft.Column([ft.Text("Dados do host"), api_url_field]),
        actions=[
            ft.TextButton("Cancelar", on_click=close_dialog),  # Fecha o diálogo
            ft.TextButton("Atualizar Configurações", on_click=atualizar_config)  # Atualiza o HOST
        ],
    )

    page.dialog = dialog  # Define o diálogo na página
    dialog.open = True    # Abre o diálogo
    page.update()         # Atualiza a página para exibir o diálogo
