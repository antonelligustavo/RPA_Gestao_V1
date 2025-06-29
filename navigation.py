import asyncio
import logging
import os
from dotenv import load_dotenv
from config import CONFIG, ENV_PATH
from utils import encontrar_frame, aguardar_elemento, verificar_sessao_ativa

load_dotenv(dotenv_path=ENV_PATH)
logger = logging.getLogger(__name__)

async def fazer_login(page):
    try:
        logger.info("Iniciando processo de login...")
        
        await page.goto(CONFIG["url"])
        await page.wait_for_load_state("load")
        
        frame = await encontrar_frame(page, CONFIG["selectors"]["login_frame_pattern"])
        
        if not await aguardar_elemento(frame, CONFIG["selectors"]["username_field"]):
            raise Exception("Campo de usuário não encontrado")
        
        username = os.getenv('APP_USERNAME', 'rpa.gestaoac')
        password = os.getenv('APP_PASSWORD')
        
        if not password:
            raise Exception("Senha não encontrada nas variáveis de ambiente. Configure APP_PASSWORD no arquivo .env")
        
        await frame.fill(CONFIG["selectors"]["username_field"], username)
        await frame.fill(CONFIG["selectors"]["password_field"], password)
        await frame.click(CONFIG["selectors"]["login_button"])
        
        await page.wait_for_timeout(CONFIG["timeouts"]["page_load"])
        
        logger.info("Login realizado com sucesso")
        return frame
        
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        raise

async def voltar_para_gestao_acesso(page, frame):
    try:
        logger.debug("Voltando para o menu principal...")
        
        await page.wait_for_timeout(CONFIG["timeouts"]["frame_stability"])
        await page.wait_for_load_state("domcontentloaded")
        
        tentativas_maximas = 3
        selectors_alternativos = [
            'a[href="menu.do"]',
            'a[href*="menu.do"]',
            'a:has-text("Menu")',
            'a:has-text("Voltar")',
            'a:has-text("Principal")',
        ]
        
        for tentativa in range(tentativas_maximas):
            logger.debug(f"Tentativa {tentativa + 1} de voltar ao menu")
            
            await asyncio.sleep(1)
            
            frames = page.frames
            link_clicado = False
            
            for seletor in selectors_alternativos:
                if link_clicado:
                    break
                    
                for current_frame in frames:
                    try:
                        await current_frame.wait_for_load_state("domcontentloaded", timeout=5000)
                        
                        links = current_frame.locator(seletor)
                        count = await links.count()
                        
                        if count > 0:
                            logger.debug(f"Encontrados {count} links com seletor '{seletor}' no frame: {current_frame.url}")
                            
                            for i in range(count):
                                link = links.nth(i)
                                try:
                                    await link.wait_for(state="visible", timeout=3000)
                                    
                                    if await link.is_visible() and await link.is_enabled():
                                        try:
                                            await link.click(timeout=5000)
                                            logger.debug(f"Clique realizado com sucesso usando seletor '{seletor}' no link {i+1}")
                                        except:
                                            await link.evaluate("element => element.click()")
                                            logger.debug(f"Clique via JavaScript realizado no link {i+1}")
                                        
                                        link_clicado = True
                                        break
                                        
                                except Exception as click_error:
                                    logger.debug(f"Erro ao clicar no link {i+1} com seletor '{seletor}': {click_error}")
                                    continue
                        
                        if link_clicado:
                            break
                            
                    except Exception as frame_error:
                        logger.debug(f"Erro ao processar frame {current_frame.url} com seletor '{seletor}': {frame_error}")
                        continue
            
            if link_clicado:
                break
            else:
                logger.debug(f"Tentativa {tentativa + 1} falhou, aguardando antes da próxima...")
                await asyncio.sleep(CONFIG["timeouts"]["retry_delay"] / 1000)
        
        if not link_clicado:
            logger.warning("Tentando navegação direta pela URL como último recurso...")
            try:
                current_url = page.url
                base_url = current_url.split('/')[0] + '//' + current_url.split('/')[2]
                menu_url = f"{base_url}/menu.do"
                
                await page.goto(menu_url)
                await page.wait_for_load_state("domcontentloaded")
                logger.debug("Navegação direta para menu.do realizada com sucesso")
                link_clicado = True
                
            except Exception as url_error:
                logger.warning(f"Erro na navegação direta: {url_error}")
        
        if link_clicado:
            await page.wait_for_timeout(CONFIG["timeouts"]["page_load"])
            await page.wait_for_load_state("domcontentloaded")
            
            try:
                menu_frame = await encontrar_frame(page, CONFIG["selectors"]["login_frame_pattern"], max_tentativas=5)
                if menu_frame:
                    await menu_frame.wait_for_selector(CONFIG["selectors"]["access_link"], timeout=5000)
                    logger.debug("Confirmado: voltou ao menu principal com sucesso")
                else:
                    logger.warning("Não foi possível confirmar se voltou ao menu principal")
            except:
                logger.warning("Não foi possível verificar se voltou ao menu, mas continuando...")
            
        else:
            logger.warning("Não foi possível encontrar/clicar em nenhum link para voltar ao menu")
            logger.warning("Tentando continuar o processamento...")
            
            if not await verificar_sessao_ativa(page):
                raise Exception("Sessão possivelmente expirou")
        
    except Exception as e:
        logger.error(f"Erro ao voltar para o menu: {e}")
        logger.warning("Continuando processamento mesmo com erro no retorno ao menu")
        pass

async def navegar_para_incluir_acesso(page, frame):
    max_tentativas = 3
    
    for tentativa in range(max_tentativas):
        try:
            logger.debug(f"Navegando para incluir acesso... (tentativa {tentativa + 1}/{max_tentativas})")
            
            try:
                await frame.wait_for_load_state("domcontentloaded", timeout=5000)
            except:
                logger.warning("Frame pode estar instável, procurando novo frame...")
                frame = await encontrar_frame(page, CONFIG["selectors"]["login_frame_pattern"])
            
            if not await aguardar_elemento(frame, CONFIG["selectors"]["access_link"], timeout=10000):
                raise Exception(f"Link de acesso não encontrado na tentativa {tentativa + 1}")
            
            await frame.click(CONFIG["selectors"]["access_link"], timeout=10000)
            await page.wait_for_timeout(CONFIG["timeouts"]["page_load"])
            await page.wait_for_load_state("domcontentloaded")
            
            target_frame = await encontrar_frame(page, "usuarios_incluiAcesso.do")
            
            await target_frame.select_option(CONFIG["selectors"]["frequency_select"], CONFIG["values"]["frequency_id"])
            await target_frame.click(CONFIG["selectors"]["submit_button"])
            
            await asyncio.sleep(2)
            
            logger.debug("Navegação para incluir acesso concluída")
            return target_frame
            
        except Exception as e:
            logger.warning(f"Erro na tentativa {tentativa + 1} de navegar para incluir acesso: {e}")
            
            if tentativa < max_tentativas - 1:
                logger.info(f"Tentando recuperar a sessão... (tentativa {tentativa + 1}/{max_tentativas})")
                
                try:
                    await voltar_para_gestao_acesso(page, frame)
                    
                    await asyncio.sleep(CONFIG["timeouts"]["retry_delay"] / 1000)
                    
                    if not await verificar_sessao_ativa(page):
                        logger.warning("Sessão pode ter expirado, tentando relogar...")
                        frame = await fazer_login(page)
                    else:
                        frame = await encontrar_frame(page, CONFIG["selectors"]["login_frame_pattern"])
                    
                except Exception as recovery_error:
                    logger.warning(f"Erro na tentativa de recuperação: {recovery_error}")
                    if tentativa == max_tentativas - 1:
                        raise Exception(f"Falha crítica após {max_tentativas} tentativas. Último erro: {e}. Erro de recuperação: {recovery_error}")
            else:
                logger.error(f"Erro na navegação para incluir acesso após {max_tentativas} tentativas: {e}")
                raise Exception(f"Falha crítica na navegação para incluir acesso após {max_tentativas} tentativas: {e}")
    
    raise Exception(f"Não foi possível navegar para incluir acesso após {max_tentativas} tentativas")