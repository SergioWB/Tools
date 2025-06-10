from log_config import logger_config
import time

logger = logger_config("meli_insercion", r"/home/ubuntu/Documents/server-Tln/Tools/Tools/logs/meli_insercion.log")
#logger = logger_config("meli_insercion", r"C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\Tools\Tools\logs\meli_insercion.log")

try:
    for i in range(0,9):
        print(f"{i+1}")
        time.sleep(1)

        if i == 7:
            raise ('Exception')

except Exception as e:
    logger.error(f'Error recupera_meli_token(): {str(e)}')
