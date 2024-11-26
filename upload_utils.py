import pandas as pd
import xml.etree.ElementTree as ET
import chardet

def is_valid_xml(file_path):
    try:
        ET.parse(file_path)
        return True
    except ET.ParseError:
        return False

def extract_xml_data(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Verificar se a tag raiz termina com 'nfeProc' e se o segundo nó é 'NFe'
    if not (root.tag.endswith('nfeProc') and root[0].tag.endswith('NFe')):
        return None    

    ide = root.find('.//{http://www.portalfiscal.inf.br/nfe}ide')
    ide_data = {child.tag.split('}', 1)[1]: child.text for child in ide}
    
    # Extract 'emit' fields
    emit = root.find('.//{http://www.portalfiscal.inf.br/nfe}emit')
    emit_data = {child.tag.split('}', 1)[1]: child.text for child in emit}

    # Extrair o UF de 'enderEmit' e adicionar a 'emit_data'
    ender_emit = emit.find('{http://www.portalfiscal.inf.br/nfe}enderEmit')
    if ender_emit is not None:
        uf = ender_emit.find('{http://www.portalfiscal.inf.br/nfe}UF')
        emit_data['emit_UF'] = uf.text if uf is not None else None
        xMun = ender_emit.find('{http://www.portalfiscal.inf.br/nfe}xMun')
        emit_data['emit_xMun'] = xMun.text if xMun is not None else None 
        cMun = ender_emit.find('{http://www.portalfiscal.inf.br/nfe}cMun')
        emit_data['emit_cMun'] = cMun.text if cMun is not None else None         
               
    # Verificar se o nó 'dest' existe
    dest = root.find('.//{http://www.portalfiscal.inf.br/nfe}dest')
    if dest is not None:
        # Verificar se 'enderDest' e 'UF' existem dentro de 'dest'
        ender_dest = dest.find('.//{http://www.portalfiscal.inf.br/nfe}enderDest')
        if ender_dest is not None:
            uf_dest = ender_dest.find('{http://www.portalfiscal.inf.br/nfe}UF').text if ender_dest.find('{http://www.portalfiscal.inf.br/nfe}UF') is not None else ''
        else:
            uf_dest = ''
    else:
        uf_dest = ''    
    
    # Encontrar o elemento infNFe
    inf_prot = root.find('.//{http://www.portalfiscal.inf.br/nfe}infProt')
    
    # Obter o atributo Id (chNFe)
    if inf_prot is not None:
        ch_nfe = inf_prot.find('{http://www.portalfiscal.inf.br/nfe}chNFe')
        ch_nfe = ch_nfe.text

    # Extract 'total' fields
    total = root.find('.//{http://www.portalfiscal.inf.br/nfe}total/{http://www.portalfiscal.inf.br/nfe}ICMSTot')
    total_data = {child.tag.split('}', 1)[1]: child.text for child in total} if total is not None else {}

    # Extract 'det' (product) fields
    det_data = []
    # Usando enumerate para obter o índice e o elemento ao mesmo tempo
    for index, det in enumerate(root.findall('.//{http://www.portalfiscal.inf.br/nfe}det'), start=1):
        prod = det.find('{http://www.portalfiscal.inf.br/nfe}prod')
        prod_data = {f"prod_{child.tag.split('}', 1)[1]}": child.text for child in prod} if prod else {}

        # Verificando se 'prod_vDesc' está presente, se não, adiciona com o valor '0'
        if 'prod_vDesc' not in prod_data:
            prod_data['prod_vDesc'] = 0
            
        if 'prod_vFrete' not in prod_data:
            prod_data['prod_vFrete'] = 0    

        if 'prod_vOutro' not in prod_data:
            prod_data['prod_vOutro'] = 0    
        
        # Adiciona a posição do produto
        prod_data["prod_NumItem"] = index  # Adiciona a coluna com a posição

        imposto = det.find('{http://www.portalfiscal.inf.br/nfe}imposto')
        
        # Para ICMS, vamos construir o dicionário
        icms_data = {}
        icms = imposto.find('.//{http://www.portalfiscal.inf.br/nfe}ICMS') if imposto is not None else None
        if icms is not None:
            # Extrai os dados de ICMS
            for child in icms:
                # Formata a chave como ICMS_<campo>
                for subchild in child:
                    icms_data[f"ICMS_{subchild.tag.split('}', 1)[1]}"] = subchild.text
                # Se não houver subelementos, também extraímos o campo direto
                if not list(child):  # Se não há subelementos
                    icms_data[f"ICMS_{child.tag.split('}', 1)[1]}"] = child.text

        # Verificando se 'ICMS_vICMSDeson' está presente; caso contrário, adiciona com valor '0'
        if 'ICMS_vICMSDeson' not in icms_data:
            icms_data['ICMS_vICMSDeson'] = 0 

        if 'ICMS_vFCP' not in icms_data:
            icms_data['ICMS_vFCP'] = 0     
            
        if 'ICMS_pRedBC' not in icms_data:
            icms_data['ICMS_pRedBC'] = 0
            
        if 'ICMS_vBCSTRet' not in icms_data:
            icms_data['ICMS_vBCSTRet'] = 0 
            
        if 'ICMS_pST' not in icms_data:
            icms_data['ICMS_pST'] = 0                           
            
        if 'ICMS_vICMSSubstituto' not in icms_data:
            icms_data['ICMS_vICMSSubstituto'] = 0                  
                
                                          

        # PIS
        pis_data = {
            "PIS_CST": None,
            "PIS_vBC": None,
            "PIS_pPIS": None,
            "PIS_vPIS": None
        }
        pis = imposto.find('{http://www.portalfiscal.inf.br/nfe}PIS') if imposto is not None else None
        if pis is not None:
            for child in pis:
                # Verifica se existe um subnó (como PISAliq ou PISNT) e coleta os dados
                for subchild in child:
                    pis_data[f"PIS_{subchild.tag.split('}', 1)[1]}"] = subchild.text
                # Caso o nó PIS não tenha subnós, pega o valor diretamente
                if not list(child):  # Se não há subelementos
                    pis_data[f"PIS_{child.tag.split('}', 1)[1]}"] = child.text

        # COFINS
        cofins_data = {
            "COFINS_CST": None,
            "COFINS_vBC": None,
            "COFINS_pCOFINS": None,
            "COFINS_vCOFINS": None
        }
        cofins = imposto.find('{http://www.portalfiscal.inf.br/nfe}COFINS') if imposto is not None else None
        if cofins is not None:
            for child in cofins:
                # Verifica se existe um subnó (como COFINSAliq ou COFINSNT) e coleta os dados
                for subchild in child:
                    cofins_data[f"COFINS_{subchild.tag.split('}', 1)[1]}"] = subchild.text
                # Caso o nó COFINS não tenha subnós, pega o valor diretamente
                if not list(child):  # Se não há subelementos
                    cofins_data[f"COFINS_{child.tag.split('}', 1)[1]}"] = child.text


        # Combine product and tax data for each 'det' item
        product_record = {'chNFe': ch_nfe, **ide_data, **emit_data, 'uf_dest': uf_dest, **total_data, **prod_data, **icms_data, **pis_data, **cofins_data}
        det_data.append(product_record)

    
    # Convert to DataFrame
    df = pd.DataFrame(det_data)
    return df  


def detect_file_encoding(file_path):
    """Detecta o encoding do arquivo."""
    with open(file_path, 'rb') as file:
        raw_data = file.read()
    result = chardet.detect(raw_data)
    return result['encoding']

def parse_sped_file(file_path="2spedsup2000.09.2024.txt"):
    encoding = detect_file_encoding(file_path)
    # Lista de dicionários para armazenar os dados dos registros selecionados
    records = []
    produtos = []

    # Dicionário temporário para capturar informações de um conjunto de registros
    current_record = {}
    
    # Variáveis para armazenar dados da empresa e dados iniciais de C100
    empresa_info = {}
    c100_info = {}
    produtos_info = {}
    line_number = 0

    # Defina o conjunto de registros que você quer capturar
    target_records = ['0000', '0005', '0200', 'C100', 'C170']
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            for line in file:
                line_number += 1
                # Divide a linha em campos pelo separador do SPED Fiscal (normalmente "|")
                fields = line.strip().split('|')
                
                # Identifique o tipo de registro (primeiro campo após "|")
                record_type = fields[1] if len(fields) > 1 else None
                
                if record_type == '0000':
                    # Captura dados do registro 0000 (Identificação da Empresa)
                    empresa_info = {
                        'CNPJ': fields[7],    # Ajuste o índice conforme o layout do arquivo SPED
                        'xNome': fields[6],
                        'emit_UF': fields[9],
                        'IE': fields[10],
                        'emit_cMun': fields[11],
                    }
                
                elif record_type == '0005':
                    # Captura dados do registro 0005 (Dados Complementares da Empresa)
                    empresa_info.update({
                        'xFant': fields[2],
                        'enderEmit': fields[4],
                        'emit_xMun': fields[6],
                        'CRT': '',
                        'uf_dest': '',
                    })
                
                elif record_type == '0200':
                    produtos_info = {  # Cria um novo dicionário a cada iteração
                        'codigo': fields[2],
                        'descricao': fields[3],
                        'ean': fields[4],
                        'unidade': fields[5],
                        'ncm': fields[8],
                        'cest': fields[13],
                    }
                    produtos.append(produtos_info)  # Adiciona uma cópia do dicionário à lista

                        
                elif record_type == 'C100':
                    # Captura dados de C100 (Nota Fiscal)
                    c100_info = {
                        'chNFe': fields[9],    # Ajuste o índice conforme o layout do arquivo SPED
                        'cUF': fields[2],
                        'cNF': fields[3],
                        'natOp': fields[6],
                        'mod': fields[5],
                        'serie': fields[7],
                        'nNF': fields[8],
                        'dhEmi': f"{fields[10][:2]}/{fields[10][2:4]}/{fields[10][4:]}",
                        'tpNF': fields[2],
                        'idDest': '',
                        'cMunFG': '',
                        'cDV': '',
                        'tpAmb': '',
                        'finNFe': '',
                        'indFinal': '',
                        'indPres': '',
                        'procEmi': '',                    
                        'verProc': '',
                        'vBC': '',
                        'vICMS': fields[22],
                        'vICMSDeson': '',
                        'vFCP': '',
                        'vBCST': '',
                        'vST': '',
                        'vFCPST': '',
                        'vFCPSTRet': '',
                        'vProd': fields[16],
                        'vFrete': fields[18],
                        'vSeg': fields[19],
                        'vDesc': fields[14],
                        'vII': '',
                        'vIPI': '',
                        'vIPIDevol': '',
                        'vPIS': fields[26],
                        'vCOFINS': fields[27],
                        'vOutro': fields[20],
                        'vNF': fields[12]
                    }
                    # Adiciona informações da empresa ao registro atual
                    c100_info.update(empresa_info)
                
                elif record_type == 'C170':
                    def safe_float(value, field_name):
                        try:
                            return float(value.replace(',', '.')) if value.strip() else 0.0
                        except ValueError:
                            raise ValueError(f"Erro ao converter o campo '{field_name}' para float. Linha {line_number}: {line}")

                    # Captura dados de C170 (Itens da Nota Fiscal)
                    item_record = {
                        'prod_cProd': fields[3],
                        'prod_cEAN': '',
                        'prod_xProd': fields[4],
                        'prod_NCM': '',
                        'prod_CEST': '',
                        'prod_indEscala': '',
                        'prod_CFOP': fields[11],
                        'prod_uCom': fields[6],
                        'prod_qCom': safe_float(fields[5], 'prod_qCom'),
                        'prod_vUnCom': fields[6],
                        'prod_vProd': safe_float(fields[7], 'prod_vProd'),
                        'prod_cEANTrib': '',
                        'prod_uTrib': '',
                        'prod_qTrib': '',
                        'prod_vUnTrib': '',
                        'prod_indTot': '',
                        'prod_vDesc': safe_float(fields[8], 'prod_vDesc'),
                        'prod_vFrete': 0,
                        'prod_vOutro': 0,
                        'prod_NumItem': fields[2],
                        'ICMS_orig': '',
                        'ICMS_CST': fields[10],
                        'ICMS_modBC': '',
                        'ICMS_vBC': safe_float(fields[13], 'ICMS_vBC'),
                        'ICMS_pICMS': fields[14], 
                        'ICMS_vICMS': safe_float(fields[15], 'ICMS_vICMS'),
                        'ICMS_vICMSDeson': 0, 
                        'ICMS_vFCP': 0, 
                        'ICMS_pRedBC': '',
                        'ICMS_vBCSTRet': 0,
                        'ICMS_pST': safe_float(fields[17], 'ICMS_pST'),
                        'ICMS_vICMSSubstituto': safe_float(fields[18], 'ICMS_vICMSSubstituto'),
                        'PIS_CST': fields[25], 
                        'PIS_vBC': safe_float(fields[16], 'PIS_vBC'),
                        'PIS_pPIS': safe_float(fields[27], 'PIS_pPIS'),
                        'PIS_vPIS': safe_float(fields[30], 'PIS_vPIS'),
                        'COFINS_CST': fields[31],
                        'COFINS_vBC': safe_float(fields[32], 'COFINS_vBC'),
                        'COFINS_pCOFINS': safe_float(fields[33], 'COFINS_pCOFINS'),
                        'COFINS_vCOFINS': safe_float(fields[36], 'COFINS_vCOFINS'),
                        'prod_cBenef': ''
                    }
                    # Adiciona dados de empresa e C100 ao registro do item
                    item_record.update(empresa_info)
                    item_record.update(c100_info)
                    
                    # Adiciona o registro do item à lista de registros
                    records.append(item_record)


        # Converte a lista de dicionários para um DataFrame
        df = pd.DataFrame(records)
        prod_df = pd.DataFrame(produtos)
                
        # Realizando o merge entre df e prod_df usando a coluna correspondente
        df = df.merge(
            prod_df, 
            how='left', 
            left_on='prod_cProd', 
            right_on='codigo'
        )

        # Preenchendo os campos no df com os valores do prod_df
        df['prod_cEAN'] = df['ean']
        df['prod_NCM'] = df['ncm']
        df['prod_CEST'] = df['cest']

        # Removendo colunas extras geradas pelo merge
        df = df.drop(columns=['codigo', 'ean', 'ncm', 'cest', 'descricao', 'unidade'])    
        # df.to_csv("saida.csv", index=False, encoding='utf-8')
        
        return df
                    
    except UnicodeDecodeError as e:
        print(f"Erro ao processar o arquivo: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio
    except Exception as e:
        print(f"Erro inesperado: {e}")    
        return pd.DataFrame()  # Retorna um DataFrame vazio


def rename_columns():
    # colunas = [
    #     "chave_nota", "numero_nota", "ncm", "modelo", "tipo_operacao", "natureza_operacao",
    #     "indicador_consumidor_final", "uf_emit", "uf_dest", "cnpj_emitente", "nome_emitente",
    #     "data_emissao", "quantidade", "cfop", "cst_icms", "base_icms", "percentual_reducao",
    #     "aliquota_icms", "valor_icms", "vl_fcp", "iva", "base_icms_st", "aliquota_icms_st", "valor_icms_st",
    #     "cst_pis", "base_pis", "aliquota_pis", "valor_pis", "cst_cofins", "base_cofins",
    #     "aliquota_cofins", "valor_cofins", "cest", "descricao_produto", "origem_prod",
    #     "codigo_barra", "valor_desconto", "valor_total_item", "valor_outros", "valor_frete",
    #     "identificador", "codigo_produto", "c_benef", "valor_icms_desonerado"
    # ]     
    return {
        "chNFe": "chave_nota",
        "nNF": "numero_nota",
        "prod_NCM": "ncm",
        "mod": "modelo",
        "tpNF": "tipo_operacao",
        "natOp": "natureza_operacao",
        "indFinal": "indicador_consumidor_final",
        "emit_UF": "uf_emit",
        "CNPJ": "cnpj_emitente",
        "xNome": "nome_emitente",
        "dhEmi": "data_emissao",
        "prod_qCom": "quantidade",
        "prod_CFOP": "cfop",
        "ICMS_CST": "cst_icms",
        "ICMS_pRedBC": "percentual_reducao",
        "ICMS_vICMS": "valor_icms",
        "ICMS_pICMS": "percentual_icms",
        "ICMS_vFCP": "vl_fcp",
        "ICMS_vBC": "base_icms",
        "ICMS_vBCSTRet": "base_icms_st",
        "ICMS_pST": "aliquota_icms_st",
        "ICMS_vICMSSubstituto": "valor_icms_st",
        "ICMS_vICMSDeson": "valor_icms_desonerado",
        "PIS_CST": "cst_pis",
        "PIS_vBC": "base_pis",
        "PIS_pPIS": "aliquota_pis",
        "PIS_vPIS": "valor_pis",
        "COFINS_CST": "cst_cofins",
        "COFINS_vBC": "base_cofins",
        "COFINS_pCOFINS": "aliquota_cofins",
        "COFINS_vCOFINS": "valor_cofins",
        "prod_CEST": "cest",
        "prod_xProd": "descricao_produto",
        "prod_cEAN": "codigo_barra",
        "prod_vDesc": "valor_desconto",
        "prod_vProd": "valor_total_item",
        "prod_vOutro": "valor_outros",
        "prod_vFrete": "valor_frete",
        "prod_cProd": "codigo_produto",
        "prod_cBenef": "c_benef",
    }