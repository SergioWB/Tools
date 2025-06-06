from log_config import logger_config
import time

logger = logger_config("meli_insercion", r"/home/ubuntu/Documents/server-Tln/Tools/Tools/logs")

try:
    for i in range(0,9):
        print(f"{i+1}")
        time.sleep(1)

    raise ('Exception')
except Exception as e:
    logger.error(f'Error recupera_meli_token(): {str(e)}')
