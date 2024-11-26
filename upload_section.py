import flet as ft
import os
import io
import requests
import time
import zipfile
import shutil
import numpy as np
import pandas as pd
import tempfile
from typing import Dict
from flet import FilePicker, FilePickerResultEvent, FilePickerUploadEvent, FilePickerUploadFile, Ref, ProgressRing, ElevatedButton, Column, Row, Text, icons, DataTable, Container, DataColumn, DataRow
from upload_utils import extract_xml_data, is_valid_xml, parse_sped_file, rename_columns
from utils import get_host, close_dialog
from concurrent.futures import ThreadPoolExecutor
from session import get_token
from datetime import datetime
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor


prog_bars: Dict[str, ProgressRing] = {}
files_selected = Ref[Text]()
upload_button = Ref[ElevatedButton]()
clear_button = Ref[ElevatedButton]()
data_table_ref = Ref[DataTable]() 
row_ref = Ref[Row]()

export_csv_button = Ref[ElevatedButton]()
upload_server_button = Ref[ElevatedButton]()
csv_file_picker = Ref[FilePicker]()
# Variável global para armazenar o DataFrame
global_df = pd.DataFrame()
base_df = pd.DataFrame()
consolidado_df = pd.DataFrame()

# Variável global para armazenar os valores selecionados
cfop_filter = {}  

# Definindo o indicador global
# loading_indicator = None
# Inicialização do ProgressRing
loading_indicator = ft.ProgressRing(width=16, height=16, stroke_width=2)
current_dialog = None

# Função para criar e mostrar o AlertDialog com o ProgressRing
def create_loading_indicator(page: ft.Page):
    global current_dialog
    # Criar um AlertDialog com o ProgressRing dentro dele
    
    # Fechar o diálogo atual, se houver
    if current_dialog is not None:
        current_dialog.open = False
        page.update()
            
    alert_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Processando..."),
        content=loading_indicator  # Conteúdo do AlertDialog é o ProgressRing
    )
    
    # Definir como o diálogo atual
    current_dialog = alert_dialog    
    
    # Adiciona o AlertDialog à página
    page.dialog = alert_dialog
    alert_dialog.open = True
    page.update()

# Função para mostrar o indicador de carregamento (ProgressRing)
def show_loading_indicator(page: ft.Page):
    global loading_indicator
    global current_dialog
    if current_dialog is not None:
        current_dialog.open = True
        loading_indicator.visible = True  # Torna o ProgressRing visível
        page.update()

# Função para esconder o indicador de carregamento
def hide_loading_indicator(page: ft.Page):
    global loading_indicator
    global current_dialog
    if current_dialog is not None:
        loading_indicator.visible = False  # Torna o ProgressRing invisível
        current_dialog.open = False
        page.update()


def clear_data(page: ft.Page):
    global global_df, base_df, consolidado_df, cfop_filter
    
    # Resetar os DataFrames globais
    global_df = pd.DataFrame()
    base_df = pd.DataFrame()
    consolidado_df = pd.DataFrame()

    # Resetar o filtro CFOP
    cfop_filter = {}

    # Atualizar a tabela na interface para refletir a remoção dos dados
    df_vazio = pd.DataFrame(columns=[' '])  # DataFrame vazio
    if data_table_ref.current is not None:
        data_table_ref.current.columns = [DataColumn(ft.Text(col)) for col in df_vazio.columns]
        data_table_ref.current.rows = [
            DataRow(cells=[ft.DataCell(ft.Text(str(item))) for item in row]) 
            for row in df_vazio.values
        ]
        data_table_ref.current.update()

    # Atualizar outros elementos da interface
    row_ref.current.expand = False
    row_ref.current.update()
    page.update()


def update_cfop_filter(e, cfop):
    global cfop_filter
    cfop_filter[cfop] = e.control.value  # Atualiza com True/False

def open_cfop_filter_window(page: ft.Page):
    global current_dialog, cfop_filter
    
    # Fechar o diálogo atual, se houver
    if current_dialog is not None:
        current_dialog.open = False
        page.update()    

    # Ordena os CFOPs em ordem alfabética
    sorted_cfops = sorted(cfop_filter.keys())

    # Conteúdo da janela: lista de checkboxes
    checkboxes = [
        ft.Checkbox(
            label=str(cfop),
            value=cfop_filter.get(cfop, True),
            on_change=lambda e, c=cfop: update_cfop_filter(e, c),  # Callback atualizado
        )
        for cfop in sorted_cfops
    ]

    # Função para fechar o diálogo após aplicar o filtro
    def apply_and_close_dialog(e):
        page.close(cfop_dialog)
        page.update()

    # Define a janela de diálogo
    cfop_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Selecione os CFOPs para filtrar"),
        content=ft.Column(checkboxes, scroll="adaptive"),
        actions=[
            ft.TextButton("Aplicar Filtro", on_click=apply_and_close_dialog),  # Botão com lógica atualizada
            ft.TextButton("Fechar", on_click=lambda e: page.close(cfop_dialog)),
        ],
    )
    
    # Definir como o diálogo atual
    current_dialog = cfop_dialog    

    # Mostra a janela
    page.dialog = cfop_dialog
    cfop_dialog.open = True
    page.update()


def close_dialog(page, dialog):
    dialog.open = False
    page.update()

def update_cfop_filter(event, cfop):
    global cfop_filter, global_df

    # Atualiza a variável global cfop_filter com base no estado do checkbox
    cfop_filter[cfop] = event.control.value

    # Filtra os CFOPs com base nos que estão como True
    selected_cfops = [cf for cf, selected in cfop_filter.items() if selected]

    # Atualiza o DataFrame filtrado
    if selected_cfops:
        filtered_df = global_df[global_df['prod_CFOP'].isin(selected_cfops)]
    else:
        filtered_df = pd.DataFrame()  # Caso nenhum CFOP esteja selecionado

    # Atualiza o DataFrame a ser exibido
    df_to_display = filtered_df.head(100)
    df_to_display = df_to_display.rename(columns=rename_columns()) 

    # Atualiza o DataTable com o novo DataFrame filtrado
    if data_table_ref.current is not None:
        if not df_to_display.empty:
            data_table_ref.current.columns = [DataColumn(ft.Text(col)) for col in df_to_display.columns]
            data_table_ref.current.rows = [
                DataRow(cells=[ft.DataCell(ft.Text(str(item))) for item in row])
                for row in df_to_display.values
            ]
        else:
            # Caso o DataFrame esteja vazio
            data_table_ref.current.columns = []
            data_table_ref.current.rows = []
        
        data_table_ref.current.update()

def file_picker_result(e: FilePickerResultEvent, page: ft.Page, file_picker):
    global global_df
    # global_df = pd.DataFrame()  # Limpa o DataFrame antes de começar o novo processamento
    
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
    
    if e.files is None:
        files_selected.current.value = ""
        upload_button.current.disabled = True
    else:
        show_loading_indicator(page)
        create_loading_indicator(page) 
        # files_selected.current.value = f"{len(e.files)} arquivos selecionados"
        upload_button.current.disabled = False

        # Processa todos os arquivos ZIP simultaneamente
        zip_files = [f for f in e.files if f.name.endswith('.zip')]
        num_zip_files = len(zip_files)
        other_files = [f for f in e.files if not f.name.endswith('.zip')]

        # Processa os arquivos não ZIP
        
        for f in other_files:
            upload_files(e, file_picker, page)

        # Processa arquivos ZIP em paralelo
        if zip_files:
            with ThreadPoolExecutor(max_workers=4) as executor:         
                futures = [executor.submit(process_zip_file, f.path, file_picker, page, num_zip_files) for f in zip_files]
                for future in futures:
                    future.result()  # Aguarda o término de cada processo
                    
        
        hide_loading_indicator(page)                                   

    page.update()

def on_upload_progress(e: FilePickerUploadEvent, page: ft.Page):
    prog_bars[e.file_name].value = e.progress
    prog_bars[e.file_name].update()
   
def process_zip_file(zip_path, file_picker, page, num_zip_files):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        xml_files = [name for name in zip_ref.namelist() if name.endswith('.xml')]
        
        if not xml_files:
            print("Nenhum arquivo XML encontrado no ZIP.")    
            return    

        # Cria um diretório temporário exclusivo para este ZIP
        temp_dir = tempfile.mkdtemp(prefix="temp_xml_files_")

        xml_file_paths = []
        for xml_file in xml_files:
            zip_ref.extract(xml_file, temp_dir)
            xml_file_paths.append(os.path.join(temp_dir, xml_file))        
            
        # Processa os arquivos XML e depois limpa o diretório temporário
        try:
            upload_files_from_zip(None, xml_file_paths, page, num_zip_files)
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir) 
            
def upload_files_from_zip(e, xml_files, page: ft.Page, num_zip_files):
    global global_df
    global cfop_filter
    all_data = []
    
    if xml_files:

        # total_files = len(xml_files)
        # files_selected.current.value = f"{total_files} arquivos dentro do ZIP"

        def process_single_file(file_path):
            """Processa um único arquivo XML"""
            if is_valid_xml(file_path):
                data = extract_xml_data(file_path)
                if data is not None:
                    return data
            else:
                print(f"Arquivo inválido ignorado: {file_path}")
            return None

        try:
            # Processar arquivos em paralelo
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_file = {executor.submit(process_single_file, file): file for file in xml_files}

                for index, future in enumerate(future_to_file.keys()):
                    result = future.result()
                    if result is not None:
                        all_data.append(result)

            # Verifica se há dados para concatenar
            if not all_data:
                raise ValueError("Nenhum dado válido foi processado.")            
            
            # Concatena os dados do ZIP atual ao `global_df`
            if global_df.empty:
                global_df = pd.concat(all_data, ignore_index=True)
            else:
                global_df = pd.concat([global_df] + all_data, ignore_index=True)
            
            unique_values = global_df['prod_CFOP'].unique()
            cfop_filter = {cfop: True for cfop in unique_values}
            
            create_base_df()            
            df_to_display = global_df.head(100)
            df_to_display = df_to_display.rename(columns=rename_columns())  
            
            # Atualiza o DataTable
            if data_table_ref.current is not None:
                data_table_ref.current.columns = [DataColumn(ft.Text(col)) for col in df_to_display.columns]
                data_table_ref.current.rows = [
                    DataRow(cells=[ft.DataCell(ft.Text(str(item))) for item in row]) 
                    for row in df_to_display.values
                ]
                data_table_ref.current.update()

            row_ref.current.expand = True
            row_ref.current.update()

        except Exception as error:
            # Em caso de erro, exibe mensagem
            hide_loading_indicator(page)

            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Erro ao processar arquivos ZIP: {error}", color="white"),
                bgcolor="red"
            )
            page.snack_bar.open = True
            page.update()

        finally:
            # Fecha o AlertDialog
            if num_zip_files == 1:
                hide_loading_indicator(page)            
            
def upload_files(e, file_picker: FilePicker, page: ft.Page):
    global global_df
    global cfop_filter
    all_data = []

    if file_picker.result is not None and file_picker.result.files is not None:

        for index, f in enumerate(file_picker.result.files):
            file_path = f.path
            file_type = 'xml'
            
            # Processa o arquivo XML apenas se for bem-formado
            if file_path.lower().endswith(".txt"):
                file_type = 'txt'
                # INTERPRETA COMO UM SPED FISCAL
                data = parse_sped_file(file_path)
                if data is not None:
                    all_data.append(data)                
            elif file_path.endswith(".xml") and is_valid_xml(file_path):
                data = extract_xml_data(file_path)
                if data is not None:
                    all_data.append(data)
            else:
                print(f"Arquivo inválido ou não XML ignorado: {file_path}") 
        
        # Exibe todas as colunas do DataFrame
        if global_df.empty:
            global_df = pd.concat(all_data, ignore_index=True)
        else:
            global_df = pd.concat([global_df] + all_data, ignore_index=True)
        
        create_base_df(file_type)

        # Obter valores únicos da coluna 'prod_CFOP'
        unique_values = global_df['prod_CFOP'].unique()
        cfop_filter = {cfop: True for cfop in unique_values}


        # Selecionar os primeiros 100 valores do DataFrame filtrado       
        df_to_display = global_df.head(100)
        df_to_display = df_to_display.rename(columns=rename_columns())        
        
        if data_table_ref.current is not None:  
            data_table_ref.current.columns = [DataColumn(ft.Text(col)) for col in df_to_display.columns]  
            data_table_ref.current.rows = [
                DataRow(cells=[ft.DataCell(ft.Text(str(item))) for item in row]) 
                for row in df_to_display.values
            ]
            data_table_ref.current.update()     
        
        row_ref.current.expand = True
        row_ref.current.update()  
        
        hide_loading_indicator(page) 


def create_base_df(file_type='xml'):
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
    
    # Converta as colunas relevantes para float, substituindo erros por NaN
    global_df["ICMS_vICMS"] = pd.to_numeric(global_df["ICMS_vICMS"], errors='coerce').fillna(0)
    global_df["ICMS_pICMS"] = pd.to_numeric(global_df["ICMS_pICMS"], errors='coerce').fillna(0)
    global_df["ICMS_vFCP"] = pd.to_numeric(global_df["ICMS_vFCP"], errors='coerce').fillna(0)
    global_df["ICMS_vBC"] = pd.to_numeric(global_df["ICMS_vBC"], errors='coerce').fillna(0)    
    
    if file_type == 'xml':
        novo_df["data_emissao"] = pd.to_datetime(global_df["dhEmi"]).dt.strftime('%d/%m/%Y')
    else:
        novo_df["data_emissao"] = global_df["dhEmi"]
        
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
    # novo_df["aliquota_icms"] = (
    #     (global_df["ICMS_vFCP"] / global_df["ICMS_vBC"].replace(0, 1)) * 100 +
    #     global_df["ICMS_pICMS"]
    # ).round(2)

    novo_df["aliquota_icms"] = (
        ((global_df["ICMS_vFCP"] / global_df["ICMS_vBC"].replace(0, 1)) * 100 +
        global_df["ICMS_pICMS"])
        .round(2)
        .apply(lambda x: f"{int(x)}" if x.is_integer() else f"{x:.1f}".replace('.', ','))
    )



    novo_df["valor_icms"] = (global_df["ICMS_vICMS"] + global_df["ICMS_vFCP"]).astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["vl_fcp"] = global_df["ICMS_vFCP"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))

    novo_df["iva"] = 0
    
    # VERIFICAR A PARTE DE ICMS ST
    novo_df["base_icms_st"] = global_df["ICMS_vBCSTRet"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["aliquota_icms_st"] = global_df["ICMS_pST"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))
    novo_df["valor_icms_st"] = global_df["ICMS_vICMSSubstituto"].astype(float).map(lambda x: f"{x:.2f}".replace('.', ','))

    global_df["PIS_vBC"] = pd.to_numeric(global_df["PIS_vBC"], errors='coerce').fillna(0)
    global_df["PIS_pPIS"] = pd.to_numeric(global_df["PIS_pPIS"], errors='coerce').fillna(0)
    global_df["PIS_vPIS"] = pd.to_numeric(global_df["PIS_vPIS"], errors='coerce').fillna(0)
    global_df["COFINS_vBC"] = pd.to_numeric(global_df["COFINS_vBC"], errors='coerce').fillna(0)
    global_df["COFINS_pCOFINS"] = pd.to_numeric(global_df["COFINS_pCOFINS"], errors='coerce').fillna(0)
    global_df["COFINS_vCOFINS"] = pd.to_numeric(global_df["COFINS_vCOFINS"], errors='coerce').fillna(0) 

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
    global cfop_filter, base_df, consolidado_df
    if base_df.empty:
        return
    
    allowed_cfops = [cfop for cfop, selected in cfop_filter.items() if selected]
    
    # Cria o DataFrame temporário para exportação
    if tipo == 'base':
        export_df = base_df[base_df["cfop"].isin(allowed_cfops)]
        file_name_csv = 'reg_0000D.csv'
    else:
        export_df = consolidado_df[consolidado_df["cfop"].isin(allowed_cfops)]
        file_name_csv = 'reg_0000.csv'
    
    # Progress bar para exportação
    progress_bar = ft.ProgressBar(width=400, height=40, color="blue", bgcolor="#eeeeee", value=0)
    alert_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Exportando CSV..."),
        content=progress_bar,
    )

    # Configurar o FilePicker para salvar o CSV
    def save_file_result(e: FilePickerResultEvent):
        if not e.path:  # Se o usuário cancelar
            page.close(alert_dialog)
            page.update()
            return
        
        progress_bar.value = 0.5  # Atualiza progresso
        page.update()
        
        # Exporta o DataFrame filtrado para CSV
        export_df.to_csv(e.path, index=False, sep=';', encoding='utf-8-sig')
        
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
    # file_picker.save_file(file_name=file_name_csv)
    # Propriedades para garantir que o arquivo tenha a extensão correta
    # Configuração do FilePicker para salvar com a extensão .csv
    file_picker.save_file(
        file_name=file_name_csv,  # Nome do arquivo com extensão
        dialog_title="Escolha o local para salvar o arquivo",
        file_type=ft.FilePickerFileType.CUSTOM,  # Tipo de arquivo personalizado
        allowed_extensions=[".csv"]  # Permite apenas arquivos com a extensão .csv
    )  



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
    # upload_server_button.current.disabled = True
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
    
    create_loading_indicator(page)
    time.sleep(1)
    hide_loading_indicator(page)

    page.overlay.append(file_picker)
    
    # Criar um DataTable com 0 colunas e 0 linhas
    data_table = DataTable(
        bgcolor="white",
        columns=[DataColumn(ft.Text(" "))],  # Coluna inicial vazia
        rows=[],  # Inicialmente sem linhas
        heading_row_height=30,  # Altura da linha de cabeçalho
        data_row_max_height=35,  # Altura das linhas de dados
        # divider_thickness=0.1,  # Espessura do divisor entre linhas
        heading_row_color="#d7e3f7",  # Cor de fundo do cabeçalho
        column_spacing=10, 
    ) 
    
    data_table_ref.current = data_table  # Armazena a referência do DataTable

    # Configurar um Container para ocupar todo o espaço restante
    data_table_container = Container(
        alignment=ft.alignment.top_left,
        content=data_table,
        expand=True,
        # padding=2,
        # border_radius=0,
        # bgcolor="#B0BEC5",
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
                        "Filtrar",
                        ref=upload_button,
                        icon=icons.FILTER_ALT_OUTLINED,
                        on_click=lambda e: open_cfop_filter_window(page),
                        disabled=True,
                    ),
                    ElevatedButton(
                        "Limpar Dados",
                        ref=clear_button,
                        icon=icons.CLEAR_OUTLINED,
                        on_click=lambda e: clear_data(page),
                        disabled=False,
                    ),                    
                                                        
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            # Text(ref=files_selected),
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

