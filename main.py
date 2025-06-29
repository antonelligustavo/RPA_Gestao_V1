import asyncio
import logging
import os
from config import get_log_filename, CONFIG, EXCEL_FILE, LOGS_FOLDER
from automatizador import AutomatizadorGestao

log_file = get_log_filename()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    try:
        logger.info(f"Logs serão salvos em: {log_file}")
        logger.info(f"Pasta de logs: {LOGS_FOLDER}")
        
        automatizador = AutomatizadorGestao()
        await automatizador.executar(EXCEL_FILE)
        
        logger.info("Processamento concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro na execução principal: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())