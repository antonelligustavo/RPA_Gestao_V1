import os
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from config import EXCEL_FILE, LOGS_FOLDER
from automatizador import AutomatizadorGestao

# Configurar logging para o monitor
monitor_log = os.path.join(LOGS_FOLDER, f'monitor_{datetime.now().strftime("%Y%m%d")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(monitor_log, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MonitorPlanilha:
    def __init__(self, arquivo_excel, intervalo_verificacao=60):
        """
        Inicializa o monitor de planilha
        
        Args:
            arquivo_excel: Caminho completo para o arquivo Excel
            intervalo_verificacao: Intervalo em segundos entre verificações (padrão: 60)
        """
        self.arquivo_excel = arquivo_excel
        self.intervalo_verificacao = intervalo_verificacao
        self.ultima_modificacao = None
        self.processando = False
        self.total_execucoes = 0
        
    def obter_timestamp_modificacao(self):
        """Retorna o timestamp da última modificação do arquivo"""
        try:
            if os.path.exists(self.arquivo_excel):
                return os.path.getmtime(self.arquivo_excel)
            else:
                logger.warning(f"Arquivo não encontrado: {self.arquivo_excel}")
                return None
        except Exception as e:
            logger.error(f"Erro ao obter timestamp do arquivo: {e}")
            return None
    
    def verificar_modificacao(self):
        """Verifica se o arquivo foi modificado desde a última verificação"""
        timestamp_atual = self.obter_timestamp_modificacao()
        
        if timestamp_atual is None:
            return False
        
        # Primeira verificação - apenas armazena o timestamp
        if self.ultima_modificacao is None:
            self.ultima_modificacao = timestamp_atual
            logger.info(f"Monitor inicializado. Aguardando modificações em: {self.arquivo_excel}")
            return False
        
        # Verifica se houve modificação
        if timestamp_atual > self.ultima_modificacao:
            data_modificacao = datetime.fromtimestamp(timestamp_atual).strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"📝 Modificação detectada! Data: {data_modificacao}")
            self.ultima_modificacao = timestamp_atual
            return True
        
        return False
    
    async def executar_rpa(self):
        """Executa o RPA quando detecta modificação"""
        if self.processando:
            logger.warning("⚠️ RPA já está em execução. Ignorando nova modificação.")
            return
        
        try:
            self.processando = True
            self.total_execucoes += 1
            
            logger.info("=" * 70)
            logger.info(f"🚀 INICIANDO EXECUÇÃO #{self.total_execucoes} DO RPA")
            logger.info("=" * 70)
            
            automatizador = AutomatizadorGestao()
            await automatizador.executar(self.arquivo_excel)
            
            logger.info("=" * 70)
            logger.info(f"✅ EXECUÇÃO #{self.total_execucoes} CONCLUÍDA COM SUCESSO!")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"❌ Erro na execução #{self.total_execucoes} do RPA: {e}")
            logger.error("=" * 70)
        finally:
            self.processando = False
    
    async def iniciar(self):
        """Inicia o monitoramento contínuo"""
        logger.info("=" * 70)
        logger.info("🔍 MONITOR DE PLANILHA INICIADO")
        logger.info("=" * 70)
        logger.info(f"📁 Arquivo monitorado: {self.arquivo_excel}")
        logger.info(f"⏱️  Intervalo de verificação: {self.intervalo_verificacao} segundos")
        logger.info(f"📊 Logs salvos em: {monitor_log}")
        logger.info("=" * 70)
        logger.info("💡 Para parar o monitor, pressione Ctrl+C")
        logger.info("=" * 70)
        
        try:
            while True:
                try:
                    if self.verificar_modificacao():
                        await self.executar_rpa()
                    else:
                        # Mostrar mensagem a cada verificação
                        timestamp_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if hasattr(self, '_verificacoes'):
                            self._verificacoes += 1
                        else:
                            self._verificacoes = 1
                        
                        logger.info(f"🔍 [{timestamp_atual}] Nenhuma modificação detectada. Aguardando... (Verificação #{self._verificacoes})")
                    
                    await asyncio.sleep(self.intervalo_verificacao)
                    
                except Exception as e:
                    logger.error(f"Erro durante verificação: {e}")
                    await asyncio.sleep(self.intervalo_verificacao)
                    
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 70)
            logger.info("🛑 MONITOR INTERROMPIDO PELO USUÁRIO")
            logger.info(f"📈 Total de execuções realizadas: {self.total_execucoes}")
            logger.info("=" * 70)
        except Exception as e:
            logger.error(f"Erro crítico no monitor: {e}")
            raise

async def main():
    """Função principal para iniciar o monitor"""
    # Verificar se o arquivo existe
    if not os.path.exists(EXCEL_FILE):
        logger.error(f"❌ Arquivo não encontrado: {EXCEL_FILE}")
        logger.error("💡 Certifique-se de que o arquivo 'usuarios.xlsx' está na pasta 'Arquivos'")
        return
    
    # Você pode ajustar esse valor conforme necessário:
    # - 30 segundos: mais rápido, mas consome mais recursos
    # - 60 segundos: balanceado (recomendado)
    # - 120 segundos: mais econômico, mas menos responsivo
    monitor = MonitorPlanilha(
        arquivo_excel=EXCEL_FILE,
        intervalo_verificacao=1800  # Verifica a cada 30 minutos
    )
    
    await monitor.iniciar()

if __name__ == "__main__":
    asyncio.run(main())