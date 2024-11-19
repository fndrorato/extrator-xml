import pandas as pd
import sys

def parse_sped_file(file_path="2spedsup2000.09.2024.txt"):
    # Lista de dicionários para armazenar os dados dos registros selecionados
    records = []
    produtos = []

    # Dicionário temporário para capturar informações de um conjunto de registros
    current_record = {}
    
    # Variáveis para armazenar dados da empresa e dados iniciais de C100
    empresa_info = {}
    c100_info = {}
    produtos_info = {}

    # Defina o conjunto de registros que você quer capturar
    target_records = ['0000', '0005', '0200', 'C100', 'C170']
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
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
                    'ncm': fields[7],
                    'cest': fields[12],
                }
                produtos.append(produtos_info)  # Adiciona uma cópia do dicionário à lista

                    
            elif record_type == 'C100':
                # Captura dados de C100 (Nota Fiscal)
                c100_info = {
                    'chNFe': fields[9],    # Ajuste o índice conforme o layout do arquivo SPED
                    'cUF': fields[2],
                    'cNF': fields[3],
                    'natOp': fields[4],
                    'mod': fields[5],
                    'serie': fields[6],
                    'nNF': fields[7],
                    'dhEmi': f"{fields[10][:2]}/{fields[10][2:4]}/{fields[10][4:]}",
                    'tpNF': fields[10],
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
                    'prod_qCom': fields[5],
                    'prod_vUnCom': fields[6],
                    'prod_vProd': fields[7],
                    'prod_cEANTrib': '',
                    'prod_uTrib': '',
                    'prod_qTrib': '',
                    'prod_vUnTrib': '',
                    'prod_indTot': '',
                    'prod_vDesc': fields[8],
                    'prod_vFrete': '',
                    'prod_vOutro': '',
                    'prod_NumItem': fields[2],
                    'ICMS_orig': '',
                    'ICMS_CST': fields[10],
                    'ICMS_modBC': '',
                    'ICMS_vBC': fields[13],
                    'ICMS_pICMS': fields[14], 
                    'ICMS_vICMS': fields[15], 
                    'ICMS_vICMSDeson': '', 
                    'ICMS_vFCP': '', 
                    'ICMS_pRedBC': '',
                    'ICMS_vBCSTRet': '',
                    'ICMS_pST': fields[17], 
                    'ICMS_vICMSSubstituto': fields[18], 
                    'PIS_CST': fields[25], 
                    'PIS_vBC': fields[26],
                    'PIS_pPIS': fields[27],
                    'PIS_vPIS': fields[30],
                    'COFINS_CST': fields[31],
                    'COFINS_vBC': fields[32],
                    'COFINS_pCOFINS': fields[33],
                    'COFINS_vCOFINS': fields[36],
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
    print(prod_df.head(10))
    
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
    df.to_csv("saida.csv", index=False, encoding='utf-8')
    
    return df

if __name__ == "__main__":
    # Executa a função com o caminho do arquivo fornecido
    df = parse_sped_file()
    print("DF criado com sucesso")