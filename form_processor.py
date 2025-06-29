import asyncio
import logging
import pandas as pd
from config import CONFIG
from utils import encontrar_frame, aguardar_elemento, obter_subgroup_id, obter_empresa_input_position

logger = logging.getLogger(__name__)

async def configurar_grupo(page, dados):
    try:
        logger.debug("Configurando grupo...")
        
        target_frame = await encontrar_frame(page, "usuarios_incluiGrupo.do")
        
        subgroup_id = obter_subgroup_id(dados)
        logger.debug(f"Usando subgroup_id: {subgroup_id}")
        
        await target_frame.select_option(CONFIG["selectors"]["subgroup_select"], subgroup_id)
        
        logger.debug("Grupo configurado com sucesso")
        return target_frame
        
    except Exception as e:
        logger.error(f"Erro na configuração do grupo: {e}")
        raise

async def preencher_dados_usuario(frame, dados):
    try:
        logger.debug(f"Preenchendo dados do usuário: {dados.get('usuario', 'N/A')}")
        
        if 'loginGestor' in dados and pd.notna(dados['loginGestor']):
            await frame.fill(CONFIG["selectors"]["login_gestor"], str(dados["loginGestor"]))
        
        if 'emailGestor' in dados and pd.notna(dados['emailGestor']):
            await frame.fill(CONFIG["selectors"]["email_gestor"], str(dados["emailGestor"]))
        
        if 'loginGestor2' in dados and pd.notna(dados['loginGestor2']):
            await frame.fill(CONFIG["selectors"]["login_gestor2"], str(dados["loginGestor2"]))
        
        if 'emailGestor2' in dados and pd.notna(dados['emailGestor2']):
            await frame.fill(CONFIG["selectors"]["email_gestor2"], str(dados["emailGestor2"]))
        
        campos_obrigatorios = ['nome', 'usuario', 'email', 'filtro_cliente']
        
        for campo in campos_obrigatorios:
            if campo not in dados or pd.isna(dados[campo]):
                raise Exception(f"Campo obrigatório '{campo}' não encontrado ou vazio")
            
            seletor = CONFIG["selectors"][campo]
            valor = str(dados[campo])
            await frame.fill(seletor, valor)
        
        await frame.fill(CONFIG["selectors"]["obs"], CONFIG["values"]["obs_text"])
        
        logger.debug("Dados do usuário preenchidos com sucesso")
        
    except Exception as e:
        logger.error(f"Erro no preenchimento dos dados: {e}")
        raise

async def configurar_selects(frame):
    try:
        logger.debug("Configurando campos select...")
        
        await frame.select_option(CONFIG["selectors"]["tipo_pes_select"], CONFIG["values"]["tipo_pes_id"])
        await frame.select_option(CONFIG["selectors"]["cargo_select"], CONFIG["values"]["cargo_id"])
        await frame.select_option(CONFIG["selectors"]["setor_select"], CONFIG["values"]["setor_id"])
        
        logger.debug("Campos select configurados")
        
    except Exception as e:
        logger.error(f"Erro na configuração dos selects: {e}")
        raise

async def finalizar_cadastro(frame, dados):
    try:
        logger.debug("Finalizando cadastro...")
        
        await frame.click(CONFIG["selectors"]["lupa_button"])
        
        if await aguardar_elemento(frame, CONFIG["selectors"]["empresa_input"]):
            inputs = frame.locator(CONFIG["selectors"]["empresa_input"])
            
            posicao_input = obter_empresa_input_position(dados)
            logger.debug(f"Usando empresa_input_position: {posicao_input}")
            
            await inputs.nth(posicao_input).click()
        
        await asyncio.sleep(1.0)
        
        await frame.evaluate("checkAll()")
        
        await frame.click(CONFIG["selectors"]["submit_button"])
        
        logger.debug("Cadastro finalizado")
        
    except Exception as e:
        logger.error(f"Erro na finalização do cadastro: {e}")
        raise