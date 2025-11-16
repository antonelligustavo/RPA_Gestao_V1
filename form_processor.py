import asyncio
import logging
import pandas as pd
from config import CONFIG
from utils import encontrar_frame, aguardar_elemento, aguardar_elemento_com_polling, obter_subgroup_id, obter_empresa_input_position

logger = logging.getLogger(__name__)

async def configurar_grupo(page, dados):
    try:
        logger.debug("Configurando grupo...")
        
        target_frame = await encontrar_frame(page, "usuarios_incluiGrupo.do")
        
        subgroup_id = obter_subgroup_id(dados)
        logger.debug(f"Usando subgroup_id: {subgroup_id}")
        
        # Aguardar o select estar disponível
        await target_frame.wait_for_selector(CONFIG["selectors"]["subgroup_select"], state="visible", timeout=10000)
        
        # Aguardar um pouco para garantir que as opções foram carregadas
        await asyncio.sleep(1.5)
        
        # Verificar se o select tem opções disponíveis
        try:
            opcoes_html = await target_frame.evaluate("""
                (selector) => {
                    const select = document.querySelector(selector);
                    if (!select) return null;
                    return Array.from(select.options).map(opt => ({
                        value: opt.value,
                        text: opt.text
                    }));
                }
            """, CONFIG["selectors"]["subgroup_select"])
            
            if opcoes_html:
                logger.debug(f"Opções disponíveis no select: {opcoes_html}")
                
                # Verificar se o subgroup_id existe nas opções
                valores_disponiveis = [opt['value'] for opt in opcoes_html]
                
                if subgroup_id not in valores_disponiveis:
                    logger.warning(f"Valor '{subgroup_id}' não encontrado nas opções disponíveis: {valores_disponiveis}")
                    
                    # Tentar limpar espaços do subgroup_id
                    subgroup_id_limpo = subgroup_id.strip()
                    if subgroup_id_limpo in valores_disponiveis:
                        logger.info(f"Valor encontrado após limpeza: '{subgroup_id_limpo}'")
                        subgroup_id = subgroup_id_limpo
                    else:
                        # Tentar encontrar valor similar (com ou sem espaços)
                        for valor in valores_disponiveis:
                            if valor.strip() == subgroup_id.strip():
                                logger.info(f"Valor similar encontrado: '{valor}'")
                                subgroup_id = valor
                                break
                        else:
                            raise Exception(f"Valor '{subgroup_id}' não existe nas opções do select. Opções disponíveis: {valores_disponiveis}")
            else:
                logger.warning("Não foi possível verificar as opções do select")
        
        except Exception as check_error:
            logger.warning(f"Erro ao verificar opções do select: {check_error}")
        
        # Tentar selecionar a opção
        try:
            logger.debug(f"Tentando selecionar opção: '{subgroup_id}'")
            await target_frame.select_option(CONFIG["selectors"]["subgroup_select"], subgroup_id, timeout=10000)
            logger.debug("Grupo configurado com sucesso")
        except Exception as select_error:
            logger.error(f"Erro ao selecionar opção: {select_error}")
            
            # Tentar método alternativo via JavaScript
            logger.warning("Tentando método alternativo via JavaScript...")
            try:
                await target_frame.evaluate("""
                    (selector, value) => {
                        const select = document.querySelector(selector);
                        if (select) {
                            select.value = value;
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }
                """, CONFIG["selectors"]["subgroup_select"], subgroup_id)
                logger.debug("Grupo configurado via JavaScript")
            except Exception as js_error:
                logger.error(f"Método alternativo também falhou: {js_error}")
                raise
        
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
        
        # Aguardar o elemento empresa_input com timeout estendido e retry
        logger.debug("Aguardando elemento empresa_input aparecer...")
        
        # Primeira tentativa com a função melhorada
        elemento_encontrado = await aguardar_elemento(frame, CONFIG["selectors"]["empresa_input"], timeout=15000)
        
        if not elemento_encontrado:
            logger.warning("Elemento empresa_input não encontrado com método padrão, tentando polling...")
            # Tentativa com polling manual
            elemento_encontrado = await aguardar_elemento_com_polling(frame, CONFIG["selectors"]["empresa_input"], timeout=20000)
        
        if elemento_encontrado:
            logger.debug("Elemento empresa_input encontrado, prosseguindo...")
            inputs = frame.locator(CONFIG["selectors"]["empresa_input"])
            
            # Aguardar um pouco para garantir que o elemento está totalmente carregado
            await asyncio.sleep(1)
            
            # Verificar se os inputs estão disponíveis
            try:
                count = await inputs.count()
                logger.debug(f"Encontrados {count} inputs de empresa")
                
                if count > 0:
                    posicao_input = obter_empresa_input_position(dados)
                    logger.debug(f"Usando empresa_input_position: {posicao_input}")
                    
                    # Garantir que a posição não excede o número de inputs disponíveis
                    if posicao_input >= count:
                        logger.warning(f"Posição {posicao_input} excede número de inputs ({count}), usando posição 0")
                        posicao_input = 0
                    
                    # Aguardar o input específico ficar visível
                    input_especifico = inputs.nth(posicao_input)
                    await input_especifico.wait_for(state="visible", timeout=5000)
                    
                    await input_especifico.click()
                    logger.debug(f"Clique realizado no input de empresa na posição {posicao_input}")
                else:
                    logger.error("Nenhum input de empresa encontrado")
                    raise Exception("Nenhum input de empresa disponível")
                    
            except Exception as input_error:
                logger.error(f"Erro ao processar inputs de empresa: {input_error}")
                raise
        else:
            logger.error("Elemento empresa_input não foi encontrado após todas as tentativas")
            raise Exception("Timeout crítico: elemento empresa_input não encontrado")
        
        await asyncio.sleep(1.0)
        
        # Executar checkAll() com tratamento de erro
        try:
            await frame.evaluate("checkAll()")
            logger.debug("Função checkAll() executada")
        except Exception as check_error:
            logger.warning(f"Erro ao executar checkAll(): {check_error}")
            # Tentar método alternativo se checkAll() falhar
            try:
                await frame.evaluate("document.querySelectorAll('input[type=\"checkbox\"]').forEach(cb => cb.checked = true)")
                logger.debug("Checkboxes marcados via método alternativo")
            except Exception as alt_error:
                logger.warning(f"Método alternativo para checkboxes também falhou: {alt_error}")
        
        await frame.click(CONFIG["selectors"]["submit_button"])
        
        logger.debug("Cadastro finalizado")
        
    except Exception as e:
        logger.error(f"Erro na finalização do cadastro: {e}")
        raise