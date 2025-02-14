import base64
import zipfile
import requests
import json
import logging
import os
import xmlrpc.client
from datetime import datetime, timedelta
from dotenv import load_dotenv
import tokens_meli as tk_meli
import time as tm
import gspread

# Ajustar la hora manualmente restando 6 horas (UTC → CDMX)
def get_cdmx_time():
    return (datetime.now() - timedelta(hours=6)).strftime('%Y-%d-%m %I:%M:%S %p')

class CustomFormatter(logging.Formatter):
    """ Formatea el log con la hora de CDMX manualmente """
    def formatTime(self, record, datefmt=None):
        return get_cdmx_time()

# Nombre del log con la hora UTC-6
log_filename = (datetime.now() - timedelta(hours=6)).strftime("log_%Y-%m-%d_%H-%M-%S.log")

# Configurar logging
formatter = CustomFormatter('%(asctime)s|%(name)s|%(levelname)s|%(message)s')
handler = logging.FileHandler(log_filename)
handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[handler])


def get_odoo_credentials(environment="test"):
    """ Obtiene las credenciales de Odoo según el entorno. """
    if environment == "test":
        return {
            "db": os.getenv("odoo_db_test"),
            "user": os.getenv("odoo_user_test"),
            "password": os.getenv("odoo_password_test"),
            "url": os.getenv("odoo_url_test"),
        }
    return {
        "db": os.getenv("odoo_db"),
        "user": os.getenv("odoo_user"),
        "password": os.getenv("odoo_password"),
        "url": os.getenv("odoo_url"),
    }

def get_orders_from_odoo(hours):
    """ Obtiene las órdenes de Odoo en las últimas 'hours' horas. """

    filter_date = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    print(filter_date)

    search_domain = [('team_id', '=', 'Team_MercadoLibre'),
                     ('yuju_carrier_tracking_ref', 'in', ['Colecta', 'Flex', 'Drop off']),
                     ('date_order', '>=', filter_date)]

    orders = models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                               'sale.order', 'search_read',
                               [search_domain],
                               {'fields': ['channel_order_reference', 'name', 'yuju_seller_id','create_date', 'date_order']})

    logging.info(f" Intentando obtener guia de {len(orders)} órdenes")

    # for order in orders:
    #     print(order)
    return orders

def recupera_meli_token(user_id, local):
    """ Recupera el token de Mercado Libre según el usuario. """
    try:
        if local:
            token_files = {
                25523702: r'C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\Tools\Tools\tokens_meli.txt',
                160190870: r'C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\Tools\Tools\tokens_meli_oficiales.txt',
                1029905409: r'C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\Tools\Tools\tokens_meli_skyBrands.txt'
            }
        else:
            token_files = {
                25523702: '/home/ubuntu/Documents/server-Tln/Tools/meli/tokens_meli.txt',
                160190870: '/home/ubuntu/Documents/server-Tln/Tools/meli/tokens_meli_oficiales.txt',
                1029905409: '/home/ubuntu/Documents/server-Tln/Tools/meli/tokens_meli_skyBrands.txt'
            }


        token_dir = token_files.get(user_id, '')
        if not token_dir:
            return False

        with open(token_dir, 'r') as file:
            tokens_meli = json.load(file)
        return tokens_meli['access_token']
    except Exception as e:
        logging.error(f'Error recupera_meli_token() {str(e)}: ')
        return False

def get_order_meli(order_id, access_token):
    """ Obtiene información de la orden en Mercado Libre. """
    try:
        url = f'https://api.mercadolibre.com/orders/{order_id}?access_token={access_token}'
        r = requests.get(url)
        data = r.json()
        # print(json.dumps(data, indent=4, ensure_ascii=False))
        return {
            'shipping_id': data['shipping']['id'],
            'seller_id': data['seller']['id'],
            'status': data['status']
        }
    except Exception as e:
        logging.error(f'Error get_order_meli: {str(e)}')
        return False

def get_zpl_meli(shipment_ids, so_name, access_token):
    """ Obtiene la etiqueta de envío en formato ZPL desde Mercado Libre. """
    try:
        url = f'https://api.mercadolibre.com/shipment_labels?shipment_ids={shipment_ids}&response_type=zpl2&access_token={access_token}'
        r = requests.get(url)
        response_json = r.json()

        try:
            if "failed_shipments" in response_json and response_json["failed_shipments"]:
                for failed in response_json["failed_shipments"]:
                    message = failed.get("message", "Motivo desconocido")  # Extrae el motivo o usa un valor por defecto
                    logging.info(f"No se pudo extraer guía para {so_name}: {message}")
                return f'Error. No se pudo extraer guía: {message}"'
        except Exception as e:
            pass


        open('Etiqueta.zip', 'wb').write(r.content)
        with zipfile.ZipFile("Etiqueta.zip", "r") as zip_ref:
            zip_ref.extractall(f"{labels_path}/Etiqueta_{so_name}")
        return f'Se procesó el archivo ZPL de la Orden: {so_name} con éxito'
    except Exception as e:
        return f'Error get_zpl_meli: {str(e)}'


def search_pick_id(so_name, type='/PICK/', count_attachments = False):
    """ Busca el ID del picking en Odoo relacionado con la orden. """
    try:
        search_domain = [['origin', '=', so_name], ['name', 'like', type]]
        pickings = models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                                     'stock.picking', 'search_read',
                                     [search_domain],
                                     {'fields': ['id', 'name', 'message_attachment_count']})

        attatchments_number = pickings['result'][0]['message_attachment_count']
        pick_id = pickings[0]['id']

        if pickings:
            if count_attachments:
                if attatchments_number == 0:
                    return (pick_id, 'NO ATTACHMENTS')
                else:
                    return (pick_id, 'THERE ARE ATTACHMENTS')
            else:
                return pick_id

        else:
            logging.error("No se encontró el picking para la orden: " + so_name)
            return False
    except Exception as e:
        logging.error(f'Error en search_pick_id: {str(e)}')
        return False

def upload_attachment(so_name, pick_id):
    """ Adjunta la etiqueta de envío en Odoo. """
    path_attachment = f'{labels_path}/Etiqueta_{so_name}/Etiqueta de envio.txt'

    try:
        if os.path.exists(path_attachment):
            with open(path_attachment, 'rb') as file:
                file_content = base64.b64encode(file.read()).decode('utf-8')
        else:
            logging.error("El archivo no existe: " + path_attachment)
            return False

        attachment_data = {
            'name': f"{so_name}.txt",
            'res_model': 'stock.picking',
            'res_id': pick_id,
            'type': 'binary',
            'datas': file_content
        }
        models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD, 'ir.attachment', 'create', [attachment_data])
        logging.info(f'Se ha cargado la guía al pick: {pick_id} de la orden: {so_name} con éxito.')
        return True
    except Exception as e:
        logging.error(f"Error en upload_attachment: {str(e)}")
        return False


def get_seller_user_id(seller_marketplace):
    """Mapea seller_marketplace a user_id de Mercado Libre."""
    seller_map = {
        '160190870': 160190870,
        '25523702': 25523702,
        '1029905409': 1029905409
    }
    return seller_map.get(seller_marketplace)

def process_orders(hours=12, local=True):
    """ Procesa las órdenes de Odoo y descarga las etiquetas de Mercado Libre. """
    orders = get_orders_from_odoo(hours)

    tk_meli.get_all_tokens()

    for order in orders:
        order_id = order['channel_order_reference']
        seller_marketplace = order['yuju_seller_id']
        so_name = order['name']
        logging.info(f'Orden {so_name}')

        user_id_ = get_seller_user_id(seller_marketplace)
        if not user_id_:
            logging.info(f'Orden {so_name} no procesable, id del Marketplace desconocido.')
            continue

        access_token = recupera_meli_token(user_id_, local)
        order_meli = get_order_meli(order_id, access_token)
        if not order_meli:
            logging.info(f'La orden {so_name} no se encuentra en MercadoLibre')
            continue

        shipment_ids = order_meli['shipping_id']
        status = order_meli['status']
        if status in ['cancelled', 'delivered']:
            logging.info(f'La orden {so_name} esta en estato {status}, no se procesa')
            continue

        zpl_response = get_zpl_meli(shipment_ids, so_name, access_token)
        if 'Error' not in zpl_response:
            pick_id, are_there_attachments = search_pick_id(so_name, type="/PICK/", count_attachments=True)
            if are_there_attachments == 'NO ATTACHMENTS':
                upload_attachment(so_name, pick_id)
                logging.info(f'Se ha agregago la guia al PICK {pick_id} de la orden {so_name}.')
            else:
                logging.info(f'El PICK: {pick_id} de la orden {so_name} YA tiene guia adjunta, no se agrega.')

def insert_log_in_sheets(log_file, file_id, credentials_json):
    """
    Sube un archivo de log a una hoja de Google Sheets.
    """
    print("Subiendo log a Google Sheets...")
    gc = gspread.service_account(filename=credentials_json)
    sh = gc.open_by_key(file_id)
    try:
        worksheet = sh.worksheet("log")  # Intenta abrir la hoja "log"
    except gspread.exceptions.WorksheetNotFound:
        print("La hoja 'log' no existe. Creando una nueva hoja...")
        worksheet = sh.add_worksheet(title="log", rows="1000", cols="1")  # Crear la hoja si no existe

    # Lee el archivo de logs .log
    with open(log_file, 'r') as file:
        lines = file.readlines()
        lines.reverse()  # Invierte el orden de las líneas para que las más recientes aparezcan al principio

    # Obtén los datos actuales de la hoja de Google Sheets
    current_data = worksheet.get_all_values()
    # Prepara los nuevos datos para actualizar la hoja
    updated_data = [[line.strip()] for line in lines] + current_data
    # Borra el contenido actual de la hoja de Google Sheets
    worksheet.clear()
    # Actualiza la hoja de Google Sheets con los nuevos datos
    worksheet.update(range_name='A1', values=updated_data)
    print("Log actualizado en Google Sheets.")

def delete_log_file(file_path):
    """
    Elimina el archivo de log local.
    """
    try:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            handler.close()

        os.remove(file_path)
        print(f"Archivo de log eliminado: {file_path}")
    except FileNotFoundError:
        print(f"Archivo no encontrado: {file_path}")
    except PermissionError:
        print(f"No se pudo eliminar el archivo, puede estar en uso: {file_path}")






if __name__ == "__main__":
    logging.info("///////////////////////////////////////////////////////////////////////////////")

    # Cargar variables de entorno
    load_dotenv()

    # ////////////////////////////////////////////////
    credentials = 'production' # production / test
    # ////////////////////////////////////////////////


    # Obtener credenciales del entorno
    odoo_env = get_odoo_credentials(os.getenv("ODOO_ENV", credentials))
    ODOO_DB_NAME = odoo_env["db"]
    ODOO_USER_ID = odoo_env["user"]
    ODOO_PASSWORD = odoo_env["password"]
    ODOO_URL = odoo_env["url"]
    labels_path = "/home/ubuntu/Documents/server-Tln/Tools/etiquetazpl/Etiquetas"
    #labels_path = "C:/Users/Sergio Gil Guerrero/Documents/WonderBrands/Repos/Tools/etiquetazpl/Etiquetas"

    # Configuración del cliente XML-RPC
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB_NAME, ODOO_USER_ID, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    process_orders(168, local=False)  # Ordenes creadas en las ultimas N horas, Entorno local o Instancia


    file_id = "1foh4wRPgGGT46BBYPjl9lJ2bQFjY7fHVfzptNAVoQZ8"
    credentials_json = "/home/ubuntu/Documents/server-Tln/Tools/Tools/google_cred.json"
    #credentials_json = r"C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\Tools\Tools\google_cred.json"
    try:
        insert_log_in_sheets(log_filename, file_id, credentials_json)
    finally:
        logging.shutdown()
        delete_log_file(log_filename)