import flet as ft
import os
import io
import requests
import time
import zipfile
import shutil
import numpy as np
from typing import Dict
from flet import FilePicker, FilePickerResultEvent, FilePickerUploadEvent, FilePickerUploadFile, Ref, ProgressRing, ElevatedButton, Column, Row, Text, icons, DataTable, Container, DataColumn, DataRow
from upload_utils import extract_xml_data, is_valid_xml
from utils import get_host, close_dialog
import pandas as pd
from session import get_token
from datetime import datetime
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor


prog_bars: Dict[str, ProgressRing] = {}
files_selected = Ref[Text]()
upload_button = Ref[ElevatedButton]()
data_table_ref = Ref[DataTable]() 
row_ref = Ref[Row]()

export_csv_button = Ref[ElevatedButton]()
upload_server_button = Ref[ElevatedButton]()
csv_file_picker = Ref[FilePicker]()
# Variável global para armazenar o DataFrame
global_df = pd.DataFrame()
base_df = pd.DataFrame()
consolidado_df = pd.DataFrame()

def file_picker_result(e: FilePickerResultEvent, page: ft.Page, file_picker):
    global global_df
    global_df = pd.DataFrame()  # Limpa o DataFrame antes de começar o novo processamento
    
    row_ref.current.expand = False
    row_ref.current.update()   
     
    df_vazio = pd.DataFrame(columns=[' '])
    if data_table_ref.current is not None:
        data_table_ref.current.columns = [DataColumn(ft.Text(col)) for col in df_vazio.columns]
        data_table_ref.current.rows = [
            DataRow(cells=[ft.DataCell(ft.Text(str(item))) for item in row]) 
            for row in df_vazio.values
        ]
        data_table_ref.current.update()    

    
    upload_button.current.disabled = True if e.files is None else False
    prog_bars.clear()
    if e.files is not None:
        for f in e.files:
            if f.name.endswith('.zip'):
                process_zip_file(f.path, file_picker, page)
            else:
                files_selected.current.value = f"{len(e.files)} arquivos selecionados"
    else:
        files_selected.current.value = ""
        
    page.update()

def on_upload_progress(e: FilePickerUploadEvent, page: ft.Page):
    prog_bars[e.file_name].value = e.progress
    prog_bars[e.file_name].update()
   
def process_zip_file(zip_path, file_picker, page):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        xml_files = [name for name in zip_ref.namelist() if name.endswith('.xml')]
        
        if not xml_files:
            print("Nenhum arquivo XML encontrado no ZIP.")    
            return    
        
        temp_dir = 'temp_xml_files'
        os.makedirs(temp_dir, exist_ok=True)

        xml_file_paths = []
        for xml_file in xml_files:
            zip_ref.extract(xml_file, temp_dir)
            xml_file_paths.append(os.path.join(temp_dir, xml_file))        
            
        # Processa os arquivos XML e depois limpa o diretório temporário
        try:
            upload_files_from_zip(None, xml_file_paths, page)
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)  # Certifica-se de remover o diretório temporário
            
def upload_files_from_zip(e, xml_files, page: ft.Page):
    global global_df
    global_df = pd.DataFrame()
    all_data = []
    
    if xml_files:
        progress_bar = ft.ProgressBar(width=400, height=40, color="amber", bgcolor="#eeeeee", value=0)
        alert_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Processando arquivos..."),
            content=progress_bar,
        )
        
        page.dialog = alert_dialog
        alert_dialog.open = True
        page.update()

        total_files = len(xml_files)
        files_selected.current.value = f"{total_files} arquivos dentro do ZIP"

        for index, file_path in enumerate(xml_files):
            # Processa o arquivo XML apenas se for bem-formado
            if is_valid_xml(file_path):
                data = extract_xml_data(file_path)                 
                if data is not None:
                    all_data.append(data) 
            else:
                print(f"Arquivo inválido ignorado: {file_path}")
            
            progress_bar.value = (index + 1) / (total_files * 2)
            page.update()
        
        # Finaliza a barra de progresso
        global_df = pd.concat(all_data, ignore_index=True)
        create_base_df()
        df_to_display = global_df.head(100)
        progress_bar.value = 0.75
        page.update()        
        
        if data_table_ref.current is not None:
            data_table_ref.current.columns = [DataColumn(ft.Text(col)) for col in df_to_display.columns]
            data_table_ref.current.rows = [
                DataRow(cells=[ft.DataCell(ft.Text(str(item))) for item in row]) 
                for row in df_to_display.values
            ]
            data_table_ref.current.update()

        progress_bar.value = 0.95
        page.update()        

        row_ref.current.expand = True
        row_ref.current.update()
        
        export_csv_button.current.disabled = False
        upload_server_button.current.disabled = False

        progress_bar.value = 1.0
        page.update()        

        page.close(alert_dialog)
        page.update()

def upload_files(e, file_picker: FilePicker, page: ft.Page):
    global global_df
    all_data = []

    if file_picker.result is not None and file_picker.result.files is not None:
        # Criar um AlertDialog para mostrar a barra de progresso
        progress_bar = ft.ProgressBar(width=400, height=40, color="amber", bgcolor="#eeeeee", value=0)

        alert_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Processando arquivos..."),
            content=progress_bar,
        )
        
        page.dialog = alert_dialog
        alert_dialog.open = True
        page.update()

        total_files = len(file_picker.result.files)  # Total de arquivos

        for index, f in enumerate(file_picker.result.files):
            file_path = f.path
            
            # Processa o arquivo XML apenas se for bem-formado
            if file_path.endswith(".xml") and is_valid_xml(file_path):
                data = extract_xml_data(file_path)
                if data is not None:
                    all_data.append(data)
            else:
                print(f"Arquivo inválido ou não XML ignorado: {file_path}")
                        
            # progress_bar.value = (index + 1) / (total_files * 2)
            # page.update()  # Atualiza a página para refletir a barra de progresso
        
        progress_bar.value = 0.5
        page.update()        
        
        # Exibe todas as colunas do DataFrame
        global_df = pd.concat(all_data, ignore_index=True)
        create_base_df()
        progress_bar.value = 0.75
        page.update()
        df_to_display = global_df.head(100)
        progress_bar.value = 0.8
        page.update()        
        
        # Atualiza o DataTable com os nomes das colunas do DataFrame e aplica a cor de fundo                # Atualiza o DataTable com os nomes das colunas do DataFrame
        if data_table_ref.current is not None:  # Verifica se o DataTable foi inicializado
            data_table_ref.current.columns = [DataColumn(ft.Text(col)) for col in df_to_display.columns]  # Atualiza as colunas
            data_table_ref.current.rows = [
                DataRow(cells=[ft.DataCell(ft.Text(str(item))) for item in row]) 
                for row in df_to_display.values
            ]
            data_table_ref.current.update()  # Atualiza a visualização do DataTable
        
        progress_bar.value = 0.95
        page.update()        
        
        row_ref.current.expand = True
        row_ref.current.update()  
        
        export_csv_button.current.disabled = False
        upload_server_button.current.disabled = False

        progress_bar.value = 1.0
        page.update()        

        # Remover o AlertDialog após a conclusão
        page.close(alert_dialog)
        page.update()

def create_base_df():
    global base_df
    
    base_df = pd.DataFrame()
    
    colunas = [
        "chave_nota", "numero_nota", "ncm", "modelo", "tipo_operacao", "natureza_operacao",
        "indicador_consumidor_final", "uf_emit", "uf_dest", "cnpj_emitente", "nome_emitente",
        "data_emissao", "quantidade", "cfop", "cst_icms", "base_icms", "percentual_reducao",
        "aliquota_icms", "valor_icms", "vl_fcp", "iva", "base_icms_st", "aliquota_icms_st", "valor_icms_st",
        "cst_pis", "base_pis", "aliquota_pis", "valor_pis", "cst_cofins", "base_cofins",
        "aliquota_cofins", "valor_cofins", "cest", "descricao_produto", "origem_prod",
        "codigo_barra", "valor_desconto", "valor_total_item", "valor_outros", "valor_frete",
        "identificador", "codigo_produto", "c_benef", "valor_icms_desonerado"
    ] 
    
    novo_df = pd.DataFrame(columns=colunas)
    
    # Populando o DataFrame de destino com dados do global_df
    novo_df["chave_nota"] = global_df["chNFe"]
    novo_df["numero_nota"] = global_df["nNF"]
    novo_df["ncm"] = global_df["prod_NCM"]
    novo_df["modelo"] = global_df["mod"]
    novo_df["tipo_operacao"] = global_df["tpNF"]
    novo_df["natureza_operacao"] = global_df["natOp"]
    novo_df["indicador_consumidor_final"] = global_df["indFinal"]
    novo_df["uf_emit"] = global_df["emit_UF"]
    novo_df["uf_dest"] = np.where(global_df["uf_dest"] == 'GO', '', global_df["uf_dest"].str.strip())
    novo_df["cnpj_emitente"] = global_df["CNPJ"]
    novo_df["nome_emitente"] = global_df["xNome"]
    novo_df["data_emissao"] = pd.to_datetime(global_df["dhEmi"]).dt.strftime('%d/%m/%Y')
    novo_df["quantidade"] = global_df["prod_qCom"].astype(float).map(lambda x: f"{x:.3f}".replace('.', ','))
    
    novo_df["cfop"] = global_df["prod_CFOP"]
    
    novo_df["cst_icms"] = global_df["ICMS_CST"]
    novo_df["base_icms"] = global_df["ICMS_vBC"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    
    # Certifique-se de que a coluna esteja no formato numérico
    global_df["ICMS_pRedBC"] = pd.to_numeric(global_df["ICMS_pRedBC"], errors='coerce').fillna(0)

    # Calcule percentual_reducao
    novo_df["percentual_reducao"] = np.where(global_df["ICMS_pRedBC"] == 0, 0.0, 100 - global_df["ICMS_pRedBC"])

    # Converta para string com vírgula como decimal
    novo_df["percentual_reducao"] = novo_df["percentual_reducao"].map(lambda x: f"{x:.2f}".replace('.', ','))
    
    # novo_df["aliquota_icms"] = global_df["ICMS_pICMS"]
    # Converta as colunas relevantes para float, substituindo erros por NaN
    global_df["ICMS_vICMS"] = pd.to_numeric(global_df["ICMS_vICMS"], errors='coerce').fillna(0)
    global_df["ICMS_pICMS"] = pd.to_numeric(global_df["ICMS_pICMS"], errors='coerce').fillna(0)
    global_df["ICMS_vFCP"] = pd.to_numeric(global_df["ICMS_vFCP"], errors='coerce').fillna(0)
    global_df["ICMS_vBC"] = pd.to_numeric(global_df["ICMS_vBC"], errors='coerce').fillna(0)

    # Calcule 'aliquota_icms'
    novo_df["aliquota_icms"] = (
        (global_df["ICMS_vFCP"] / global_df["ICMS_vBC"].replace(0, 1)) * 100 +
        global_df["ICMS_pICMS"]
    ).round(2)


    novo_df["valor_icms"] = (global_df["ICMS_vICMS"] + global_df["ICMS_vFCP"]).astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["vl_fcp"] = global_df["ICMS_vFCP"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))

    novo_df["iva"] = 0
    
    # VERIFICAR A PARTE DE ICMS ST
    novo_df["base_icms_st"] = global_df["ICMS_vBCSTRet"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["aliquota_icms_st"] = global_df["ICMS_pST"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["valor_icms_st"] = global_df["ICMS_vICMSSubstituto"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))

    novo_df["cst_pis"] = global_df["PIS_CST"]
    novo_df["base_pis"] = global_df["PIS_vBC"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["aliquota_pis"] = global_df["PIS_pPIS"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["valor_pis"] = global_df["PIS_vPIS"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))

    novo_df["cst_cofins"] = global_df["COFINS_CST"]
    novo_df["base_cofins"] = global_df["COFINS_vBC"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["aliquota_cofins"] = global_df["COFINS_pCOFINS"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["valor_cofins"] = global_df["COFINS_vCOFINS"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    			
    novo_df["cest"] = global_df["prod_CEST"]			
    novo_df["descricao_produto"] = global_df["prod_xProd"]
    # VER SOBRE ORIGEM PRODUTO
    novo_df["origem_prod"] = 0
    novo_df["codigo_barra"] = global_df["prod_cEAN"]
    
    novo_df["valor_desconto"] = global_df["prod_vDesc"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["valor_total_item"] = global_df["prod_vProd"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["valor_outros"] = global_df["prod_vOutro"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["valor_frete"] = global_df["prod_vFrete"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["identificador"] = global_df["ICMS_CST"]
    
    novo_df["codigo_produto"] = global_df["prod_cProd"]
    novo_df["c_benef"] = global_df["prod_cBenef"]  
    novo_df["valor_icms_desonerado"] = global_df["ICMS_vICMSDeson"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    
    base_df = novo_df

def export_to_csv(page: ft.Page, tipo):
    if base_df.empty:
        return
    
    # Progress bar para exportação
    progress_bar = ft.ProgressBar(width=400, height=40, color="blue", bgcolor="#eeeeee", value=0)
    alert_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Exportando CSV..."),
        content=progress_bar,
    )

    # Configurar o FilePicker para salvar o CSV
    def save_file_result(e: FilePickerResultEvent):
        if e.path:
            progress_bar.value = 0.5  # Atualiza progresso
            page.update()
            if tipo == 'base':
                base_df.to_csv(e.path, index=False, sep=';', encoding='utf-8-sig')
            else:
                consolidado_df.to_csv(e.path, index=False, sep=';', encoding='utf-8-sig')
                
            progress_bar.value = 1
            page.close(alert_dialog)
            page.snack_bar = ft.SnackBar(Text("Exportação concluída com sucesso!"))
            page.snack_bar.open = True
            page.update()

    # Configuração do FilePicker para salvar
    file_picker = FilePicker(on_result=save_file_result)
    page.overlay.append(file_picker)

    page.dialog = alert_dialog
    alert_dialog.open = True
    page.update()

    # Abrir o FilePicker para que o usuário selecione onde salvar o arquivo
    file_picker.save_file(file_name="data.csv")  # Aqui você inicia o diálogo para salvar o arquivo com o nome padrão "data.csv".

def upload_to_server_working(e, page: ft.Page):

    def close_dialog(e):
        alert_dialog.open = False
        page.update()

    def show_alert_dialog(title, content):
        page.update()
        alert_dialog.title = ft.Text(title)  # Removendo as chaves
        alert_dialog.content = ft.Text(content)  # Removendo as chaves
        alert_dialog.actions = [ft.ElevatedButton("OK", on_click=close_dialog)]
        page.update()  

    # Atualiza o botão e barra de progresso
    upload_server_button.current.disabled = True
    # Progress bar para exportação
    progress_bar = ft.ProgressBar(width=400, height=40, color="blue", bgcolor="#eeeeee", value=0)
    alert_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Enviando arquivo..."),
        content=progress_bar,
    )    
    page.dialog = alert_dialog
    alert_dialog.open = True
    page.update()

    try:
        # 1. Gerar o CSV do DataFrame
        csv_buffer = io.StringIO()
        global_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 2. Compactar em um arquivo ZIP em memória
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{timestamp}.csv", csv_buffer.getvalue())
        zip_buffer.seek(0)

        # 3. Configurar o upload para a API com barra de progresso
        api_url = get_host()
        if api_url is None:
            show_alert_dialog("Erro no upload", "Erro ao enviar o arquivo. Verifique os dados e tente novamente.")
            return None
        
        url = f"{api_url}/upload-zip/"
        headers = {
            "Authorization": f"Token {get_token()}"  # Use o token do módulo session
        }
        files = {
            "file": (f"{timestamp}.zip", zip_buffer, "application/zip")
        }

        # Atualiza a barra de progresso enquanto faz upload
        with requests.Session() as s:
            response = s.post(url, headers=headers, files=files, stream=True)

            if response.status_code == 201:
                # Sucesso no upload
                progress_bar.value = 1
                show_alert_dialog("Upload bem-sucedido", "Arquivo enviado com sucesso!")
            elif response.status_code == 400:
                # Erro ao enviar o arquivo
                progress_bar.value = 0
                show_alert_dialog("Erro no upload", "Erro ao enviar o arquivo. Verifique os dados e tente novamente.")
            elif response.status_code == 401:
                # Erro de autenticação
                progress_bar.value = 0
                show_alert_dialog("Erro de Autenticação", "Token inválido ou não autorizado. Faça login novamente.")
            else:
                # Outro tipo de erro
                progress_bar.value = 0
                show_alert_dialog("Erro desconhecido", "Ocorreu um erro. Tente novamente mais tarde.")

    except requests.exceptions.ConnectionError:
        # Sem conexão com o servidor
        progress_bar.value = 0
        show_alert_dialog("Erro de Conexão", "Não foi possível conectar ao servidor.")

    finally:
        # Habilita o botão novamente
        upload_server_button.current.disabled = False

def upload_to_server(page: ft.Page):

    def close_dialog(e):
        alert_dialog.open = False
        page.update()

    def show_alert_dialog(title, content):
        alert_dialog.title = ft.Text(title)
        alert_dialog.content = ft.Text(content)
        alert_dialog.actions = [ft.ElevatedButton("OK", on_click=close_dialog)]
        page.update()  

    def progress_callback(monitor):
        progress = monitor.bytes_read / monitor.len
        progress_bar.value = progress
        page.update()

    # Atualiza o botão e barra de progresso
    upload_server_button.current.disabled = True
    # Progress bar para exportação
    progress_bar = ft.ProgressBar(width=400, height=40, color="blue", bgcolor="#eeeeee", value=0)
    alert_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Enviando arquivo..."),
        content=progress_bar,
    )    
    page.dialog = alert_dialog
    alert_dialog.open = True
    page.update()

    try:
        # 1. Gerar o CSV do DataFrame
        csv_buffer = io.StringIO()
        global_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 2. Compactar em um arquivo ZIP em memória
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{timestamp}.csv", csv_buffer.getvalue())
        zip_buffer.seek(0)

        # 3. Configurar o upload para a API com barra de progresso
        api_url = get_host()
        if api_url is None:
            show_alert_dialog("Erro no upload", "Erro ao enviar o arquivo. Verifique os dados e tente novamente.")
            return None
        
        url = f"{api_url}/upload-zip/"
        headers = {
            "Authorization": f"Token {get_token()}"  # Use o token do módulo session
        }

        encoder = MultipartEncoder(
            fields={
                "file": (f"{timestamp}.zip", zip_buffer, "application/zip")
            }
        )
        monitor = MultipartEncoderMonitor(encoder, progress_callback)

        headers['Content-Type'] = monitor.content_type  # Definir corretamente o tipo de conteúdo

        with requests.Session() as s:
            response = s.post(url, headers=headers, data=monitor, stream=True)
            print(f"Response Status Code: {response.status_code}")  # Adicionado para depuração

            if response.status_code == 201:
                # Sucesso no upload
                progress_bar.value = 1
                show_alert_dialog("Upload bem-sucedido", "Arquivo enviado com sucesso!")
            elif response.status_code == 400:
                # Erro ao enviar o arquivo
                progress_bar.value = 0
                show_alert_dialog("Erro no upload", "Erro ao enviar o arquivo. Verifique os dados e tente novamente.")
            elif response.status_code == 401:
                # Erro de autenticação
                progress_bar.value = 0
                show_alert_dialog("Erro de Autenticação", "Token inválido ou não autorizado. Faça login novamente.")
            else:
                # Outro tipo de erro
                progress_bar.value = 0
                show_alert_dialog("Erro desconhecido", "Ocorreu um erro. Tente novamente mais tarde.")

    except requests.exceptions.ConnectionError:
        # Sem conexão com o servidor
        progress_bar.value = 0
        show_alert_dialog("Erro de Conexão", "Não foi possível conectar ao servidor.")

    finally:
        # Habilita o botão novamente
        upload_server_button.current.disabled = False
        page.update()


        page.update()

def validate_upload(page: ft.Page):
    # Verifica se o global_df está vazio
    if global_df is None or global_df.empty:
        # Se estiver vazio, exibe um AlertDialog com a mensagem apropriada
        dialog = ft.AlertDialog(
            title=ft.Text("Atenção"),  # Aqui mudamos para um componente Text
            content=ft.Text("Não há nada para ser salvo no servidor."),
            actions=[
                ft.TextButton("OK", on_click=lambda e: close_dialog(page, dialog))
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    else:
        upload_to_server(page)

def validate_export_base(page: ft.Page):
    # Verifica se o global_df está vazio
    if global_df is None or global_df.empty:
        # Se estiver vazio, exibe um AlertDialog com a mensagem apropriada
        dialog = ft.AlertDialog(
            title=ft.Text("Atenção"),  # Aqui mudamos para um componente Text
            content=ft.Text("Não há nada para ser exportado."),
            actions=[
                ft.TextButton("OK", on_click=lambda e: close_dialog(page, dialog))
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    else:
        export_to_csv(page, 'base')

def exportar_consolidado(page: ft.Page):
    global global_df  
    global base_df  
    global consolidado_df  
    consolidado_df = pd.DataFrame() 
    
    # Verifica se o global_df está vazio
    if global_df is None or global_df.empty:
        # Se estiver vazio, exibe um AlertDialog com a mensagem apropriada
        dialog = ft.AlertDialog(
            title=ft.Text("Atenção"),  # Aqui mudamos para um componente Text
            content=ft.Text("Não há nada para ser exportado."),
            actions=[
                ft.TextButton("OK", on_click=lambda e: close_dialog(page, dialog))
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    else:    

        # Listas de colunas para garantir a conversão para numérico
        num_cols = [
            "valor_total_item", "valor_outros", "base_icms", "percentual_reducao", 
            "aliquota_icms", "valor_icms", "quantidade", "valor_desconto", 
            "valor_frete", "iva", "base_icms_st", "aliquota_icms_st", "valor_icms_st",
            "base_pis", "aliquota_pis", "valor_pis", "base_cofins", "valor_cofins", 
            "vl_fcp", "valor_icms_desonerado"
        ]

        # Verifica a existência das colunas antes da conversão
        for col in num_cols:
            if col in base_df.columns:
                base_df[col] = pd.to_numeric(base_df[col], errors='coerce').fillna(0)

        # Recriação da coluna 'identificador'
        def create_identifier(row):
            return ''.join([
                str(row['ncm']).strip(),
                str(row['modelo']).strip(),
                str(row['natureza_operacao']).strip(),
                str(row['uf_dest']).strip(),
                str(row['cest']).strip() if not pd.isna(row['cest']) else '',
                str(row['codigo_barra']).strip(),
                str(row['descricao_produto']).strip(),
                str(row['cfop']).strip(),
                str(row['cst_icms']).strip(),
                str(row['aliquota_icms']).strip(),
                str(row['aliquota_icms_st']).strip(),
                str(row['cst_pis']).strip() if not pd.isna(row['cst_pis']) else '',
                str(row['aliquota_pis']).strip()
            ])

        base_df['identificador'] = base_df.apply(create_identifier, axis=1)

        # Ajusta o groupby e as agregações
        novo_df = base_df.groupby([
            "modelo", "tipo_operacao", "natureza_operacao", "nome_emitente",
            "indicador_consumidor_final", "cnpj_emitente", "uf_emit", "uf_dest",
            "ncm", "cfop", "cst_icms", "valor_icms_desonerado", 
            "cst_pis", "cst_cofins", "cest", 
            "descricao_produto", "origem_prod", "codigo_barra",
            "codigo_produto", "c_benef"  # Não inclui 'identificador' aqui
        ]).agg({
            "numero_nota": "min",
            "data_emissao": "min",
            "valor_total_item": "mean",
            "valor_outros": "mean",
            "base_icms": "mean",
            "percentual_reducao": "mean",
            "aliquota_icms": lambda x: round(((base_df['vl_fcp'].sum() / base_df['base_icms'].replace(0, 1).sum()) * 100) + base_df['aliquota_icms'].mean(), 2),
            "valor_icms": lambda x: (base_df['valor_icms'].mean() + base_df['vl_fcp'].mean()),
            "quantidade": "count",
            "valor_desconto": "mean",
            "valor_frete": "mean",
            "iva": "mean",
            "base_icms_st": "mean",
            "aliquota_icms_st": "mean",
            "valor_icms_st": "mean",
            "base_pis": "mean",
            "aliquota_pis": "mean",
            "valor_pis": "mean",
            "aliquota_cofins": lambda x: pd.to_numeric(x, errors='coerce').mean(),
            "base_cofins": "mean",
            "valor_cofins": "mean"
        }).reset_index()

        # Adiciona a coluna 'identificador' ao novo_df
        novo_df['identificador'] = base_df.groupby([
            "modelo", "tipo_operacao", "natureza_operacao", "nome_emitente",
            "indicador_consumidor_final", "cnpj_emitente", "uf_emit", "uf_dest",
            "ncm", "cfop", "cst_icms", "valor_icms_desonerado", 
            "cst_pis", "cst_cofins", "cest", 
            "descricao_produto", "origem_prod", "codigo_barra",
            "codigo_produto", "c_benef"
        ])['identificador'].first().values  # Use o primeiro valor do grupo para cada grupo

        # Converte as colunas calculadas para o tipo desejado se necessário
        for col in num_cols:
            if col in novo_df.columns:
                novo_df[col] = novo_df[col].astype(float).round(2)                  

        consolidado_df = novo_df
        export_to_csv(page, 'consolidado')


def upload_section(page: ft.Page):
    # file_picker = FilePicker(on_result=lambda e: file_picker_result(e, page), on_upload=lambda e: on_upload_progress(e, page))
    file_picker = FilePicker(
        on_result=lambda e: file_picker_result(e, page, file_picker),
        on_upload=lambda e: on_upload_progress(e, page)
    )    

    page.overlay.append(file_picker)
    
    # Criar um DataTable com 0 colunas e 0 linhas
    data_table = DataTable(
        bgcolor="white",
        columns=[DataColumn(ft.Text(" "))],  # Coluna inicial vazia
        rows=[],  # Inicialmente sem linhas
        heading_row_height=25,  # Altura da linha de cabeçalho
        data_row_max_height=25,  # Altura das linhas de dados
        divider_thickness=0.1,  # Espessura do divisor entre linhas
        heading_row_color="#B0BEC5",  # Cor de fundo do cabeçalho
        column_spacing=5, 
    ) 
    
    data_table_ref.current = data_table  # Armazena a referência do DataTable

    # Configurar um Container para ocupar todo o espaço restante
    data_table_container = Container(
        alignment=ft.alignment.top_left,
        content=data_table,
        expand=True,
        padding=2,
        border_radius=0,
        bgcolor="#B0BEC5",
    ) 

    return ft.Column(
        [
            ft.Row(
                [
                    ElevatedButton(
                        "Selecionar arquivos...",
                        icon=icons.FOLDER_OPEN,
                        on_click=lambda _: file_picker.pick_files(allow_multiple=True),
                    ),
                    ElevatedButton(
                        "Processar",
                        ref=upload_button,
                        icon=icons.START_ROUNDED,
                        on_click=lambda e: upload_files(e, file_picker, page),
                        disabled=True,
                    ),                                                           
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            Text(ref=files_selected),
            ft.Row(
                [
                    Column(
                        [data_table_container],
                        scroll=ft.ScrollMode.ALWAYS,
                        expand=False,
                        
                    ),
                ],
                scroll=ft.ScrollMode.ALWAYS,  
                expand=False,
                ref=row_ref
            ),            
        ]
    )

