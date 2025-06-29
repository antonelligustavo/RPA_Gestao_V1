import asyncio
import logging
import pandas as pd
from config import CONFIG

logger = logging.getLogger(__name__)

async def encontrar_frame(page, url_pattern, max_tentativas=10, timeout=0.5):
    logger.debug(f"Procurando frame com padrão: {url_pattern}")
    
    for tentativa in range(max_tentativas):
        try:
            frame = next((f for f in page.frames if url_pattern in f.url), None)
            if frame:
                logger.debug(f"Frame encontrado na tentativa {tentativa + 1}")
                return frame
        except Exception as e:
            logger.warning(f"Erro ao procurar frame (tentativa {tentativa + 1}): {e}")
        
        await asyncio.sleep(timeout)
    
    raise RuntimeError(f"Frame com padrão '{url_pattern}' não encontrado após {max_tentativas} tentativas")

async def aguardar_elemento(frame_ou_page, seletor, timeout=10000):
    try:
        await frame_ou_page.wait_for_selector(seletor, timeout=timeout)
        return True
    except Exception as e:
        logger.error(f"Timeout aguardando elemento {seletor}: {e}")
        return False

async def verificar_sessao_ativa(page):
    try:
        current_url = page.url
        if "login" in current_url.lower() or "erro" in current_url.lower():
            logger.warning("Sessão pode ter expirado, tentando relogar...")
            return False
        return True
    except:
        return False

def obter_subgroup_id(dados):
    mapeamento_subgroup = {
        "Cliente ADM": "32",
        "Rastreio/TMK": "113",
        "Rastreio/Consulta": "133"
    }
    
    if 'subgroup_id' in dados and pd.notna(dados['subgroup_id']):
        valor = str(dados['subgroup_id']).strip()
        
        if valor in mapeamento_subgroup:
            id_retornado = mapeamento_subgroup[valor]
            logger.debug(f"Tipo de cliente '{valor}' mapeado para ID: {id_retornado}")
            return id_retornado
        
        logger.debug(f"Usando subgroup_id direto: {valor}")
        return valor
    else:
        return CONFIG["defaults"]["subgroup_id"]

def obter_empresa_input_position(dados):
    if 'empresa_input_position' in dados and pd.notna(dados['empresa_input_position']):
        return int(dados['empresa_input_position'])
    else:
        return CONFIG["defaults"]["empresa_input_position"]

def validar_dados_planilha(df):
    try:
        logger.info("Validando dados da planilha...")
        
        colunas_obrigatorias = ['nome', 'usuario', 'email', 'filtro_cliente']
        colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]
        
        if colunas_faltando:
            raise Exception(f"Colunas obrigatórias faltando no Excel: {colunas_faltando}")
        
        colunas_opcionais = ['subgroup_id', 'empresa_input_position']
        
        for coluna in colunas_opcionais:
            if coluna in df.columns:
                valores_nao_nulos = df[df[coluna].notna()][coluna]
                
                if coluna == 'subgroup_id':
                    for idx, valor in valores_nao_nulos.items():
                        try:
                            str(valor)
                            logger.debug(f"Linha {idx + 1}: subgroup_id = {valor}")
                        except:
                            logger.warning(f"Linha {idx + 1}: subgroup_id inválido ({valor}), será usado valor padrão")
                
                elif coluna == 'empresa_input_position':
                    for idx, valor in valores_nao_nulos.items():
                        try:
                            int(valor)
                            if int(valor) < 0:
                                logger.warning(f"Linha {idx + 1}: empresa_input_position negativo ({valor}), será usado valor padrão")
                            else:
                                logger.debug(f"Linha {idx + 1}: empresa_input_position = {valor}")
                        except:
                            logger.warning(f"Linha {idx + 1}: empresa_input_position inválido ({valor}), será usado valor padrão")
            else:
                logger.info(f"Coluna '{coluna}' não encontrada, será usado valor padrão para todos os usuários")
        
        logger.info("Validação da planilha concluída com sucesso")
        
    except Exception as e:
        logger.error(f"Erro na validação da planilha: {e}")
        raise