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
    """
    Aguarda um elemento aparecer com sistema de retry mais robusto
    """
    max_tentativas = 3
    timeout_por_tentativa = timeout
    
    for tentativa in range(max_tentativas):
        try:
            logger.debug(f"Aguardando elemento '{seletor}' - tentativa {tentativa + 1}/{max_tentativas}")
            
            # Primeira tentativa: aguardar o elemento ficar visível
            await frame_ou_page.wait_for_selector(seletor, timeout=timeout_por_tentativa, state='visible')
            logger.debug(f"Elemento '{seletor}' encontrado e visível na tentativa {tentativa + 1}")
            return True
            
        except Exception as e:
            logger.warning(f"Tentativa {tentativa + 1} falhou para elemento '{seletor}': {e}")
            
            if tentativa < max_tentativas - 1:  # Se não é a última tentativa
                # Aguardar um pouco antes da próxima tentativa
                await asyncio.sleep(2)
                
                # Tentar verificar se o frame ainda está válido
                try:
                    await frame_ou_page.wait_for_load_state("domcontentloaded", timeout=5000)
                    logger.debug(f"Frame/página recarregado, tentando novamente...")
                except:
                    logger.debug(f"Frame pode estar instável, mas continuando tentativa {tentativa + 2}")
                
                # Aumentar o timeout para as próximas tentativas
                timeout_por_tentativa = min(timeout_por_tentativa * 1.5, 20000)
                logger.debug(f"Aumentando timeout para {timeout_por_tentativa}ms na próxima tentativa")
            else:
                # Última tentativa: tentar métodos alternativos
                logger.warning(f"Última tentativa para elemento '{seletor}', usando métodos alternativos...")
                
                try:
                    # Tentar aguardar apenas a existência do elemento (não necessariamente visível)
                    await frame_ou_page.wait_for_selector(seletor, timeout=5000, state='attached')
                    logger.debug(f"Elemento '{seletor}' encontrado (attached) na última tentativa")
                    return True
                except:
                    # Tentar verificar se o elemento existe no DOM
                    try:
                        elementos = frame_ou_page.locator(seletor)
                        count = await elementos.count()
                        if count > 0:
                            logger.debug(f"Elemento '{seletor}' existe no DOM ({count} elementos encontrados)")
                            return True
                    except:
                        pass
    
    logger.error(f"Timeout aguardando elemento {seletor} após {max_tentativas} tentativas")
    return False

async def aguardar_elemento_com_polling(frame_ou_page, seletor, timeout=30000, intervalo_polling=1000):
    """
    Versão alternativa com polling manual - use esta se a função principal falhar
    """
    tempo_inicial = asyncio.get_event_loop().time()
    timeout_segundos = timeout / 1000
    intervalo_segundos = intervalo_polling / 1000
    
    while (asyncio.get_event_loop().time() - tempo_inicial) < timeout_segundos:
        try:
            elementos = frame_ou_page.locator(seletor)
            count = await elementos.count()
            
            if count > 0:
                # Verificar se pelo menos um elemento está visível
                for i in range(count):
                    try:
                        elemento = elementos.nth(i)
                        if await elemento.is_visible():
                            logger.debug(f"Elemento '{seletor}' encontrado via polling")
                            return True
                    except:
                        continue
            
            await asyncio.sleep(intervalo_segundos)
            
        except Exception as e:
            logger.debug(f"Erro no polling para '{seletor}': {e}")
            await asyncio.sleep(intervalo_segundos)
    
    logger.error(f"Timeout no polling para elemento {seletor}")
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