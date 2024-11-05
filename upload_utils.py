import pandas as pd
import xml.etree.ElementTree as ET

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
