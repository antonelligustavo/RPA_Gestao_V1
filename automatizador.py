import asyncio
import pandas as pd
import logging
import os
import json
from datetime import datetime
from playwright.async_api import async_playwright

from config import get_report_filename
from utils import verificar_sessao_ativa, validar_dados_planilha, obter_subgroup_id, obter_empresa_input_position
from navigation import fazer_login, navegar_para_incluir_acesso, voltar_para_gestao_acesso
from form_processor import configurar_grupo, preencher_dados_usuario, configurar_selects, finalizar_cadastro

logger = logging.getLogger(__name__)

class AutomatizadorGestao:
    def __init__(self):
        self.stats = {
            "total": 0,
            "sucessos": 0,
            "erros": 0,
            "usuarios_erro": []
        }

    async def processar_usuario(self, page, dados, frame_inicial):
        usuario = dados.get('usuario', 'USUÁRIO_DESCONHECIDO')
        
        try:
            logger.info(f"Iniciando processamento do usuário: {usuario}")
            
            subgroup_id = obter_subgroup_id(dados)
            empresa_position = obter_empresa_input_position(dados)
            logger.info(f"Usuário {usuario} - Tipo de Cliente: {subgroup_id}, Slot do Cliente: {empresa_position}")
            
            if not await verificar_sessao_ativa(page):
                logger.warning("Sessão não está ativa, tentando relogar...")
                frame_inicial = await fazer_login(page)
            
            frame_acesso = await navegar_para_incluir_acesso(page, frame_inicial)
            
            frame_grupo = await configurar_grupo(page, dados)
            
            await preencher_dados_usuario(frame_grupo, dados)
            
            await configurar_selects(frame_grupo)
            
            await finalizar_cadastro(frame_grupo, dados)
            
            await voltar_para_gestao_acesso(page, frame_inicial)
            
            logger.info(f"Usuário {usuario} criado com sucesso!")
            self.stats["sucessos"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar usuário {usuario}: {e}")
            self.stats["erros"] += 1
            self.stats["usuarios_erro"].append({
                "usuario": usuario,
                "erro": str(e),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return False

    async def gerar_relatorio(self):
        logger.info("=" * 50)
        logger.info("RELATÓRIO FINAL DE EXECUÇÃO")
        logger.info("=" * 50)
        logger.info(f"Total de usuários processados: {self.stats['total']}")
        logger.info(f"Sucessos: {self.stats['sucessos']}")
        logger.info(f"Erros: {self.stats['erros']}")
        logger.info(f"Taxa de sucesso: {(self.stats['sucessos']/self.stats['total']*100):.1f}%")
        
        if self.stats["usuarios_erro"]:
            logger.info("\nUsuários com erro:")
            for erro in self.stats["usuarios_erro"]:
                logger.info(f"  - {erro['usuario']}: {erro['erro']}")
        
        relatorio_arquivo = get_report_filename()
        with open(relatorio_arquivo, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\nRelatório detalhado salvo em: {relatorio_arquivo}")

    async def executar(self, arquivo_excel):
        browser = None
        try:
            if not os.path.exists(arquivo_excel):
                raise FileNotFoundError(f"Arquivo Excel não encontrado: {arquivo_excel}")
            
            logger.info(f"Carregando dados do arquivo: {arquivo_excel}")
            df = pd.read_excel(arquivo_excel)
            
            if df.empty:
                raise Exception("Arquivo Excel está vazio")
            
            self.stats["total"] = len(df)
            logger.info(f"Carregados {len(df)} usuários para processamento")
            
            validar_dados_planilha(df)
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                logger.info("Fazendo login inicial...")
                frame_inicial = await fazer_login(page)
                
                for idx, linha in df.iterrows():
                    logger.info(f"\n--- Processando usuário {idx + 1}/{len(df)} ---")
                    
                    try:
                        await self.processar_usuario(page, linha, frame_inicial)
                        
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Erro crítico no processamento do usuário {idx + 1}: {e}")
                        self.stats["erros"] += 1
                        self.stats["usuarios_erro"].append({
                            "usuario": linha.get('usuario', f'Linha_{idx + 1}'),
                            "erro": f"Erro crítico: {str(e)}",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
            
            await self.gerar_relatorio()
            
        except Exception as e:
            logger.error(f"Erro crítico na execução: {e}")
            raise