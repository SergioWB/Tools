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

logging.basicConfig(format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%Y-%d-%m %I:%M:%S %p',
                    level=logging.INFO)

def get_odoo_credentials(environment="test"):
    """ Obtiene las credenciales de Odoo según el entorno. """
    if environment == "test":
        return {
            "db": os.getenv("odoo_db_test"),
            "user": os.getenv("odoo_user_test"),
            "password": os.getenv("odoo_password_test"),
            "url": os.getenv("odoo_url_test"),
            "labels_path": "C:/Users/Sergio Gil Guerrero/Documents/WonderBrands/Repos/Tools/etiquetazpl/Etiquetas"
        }
    return {
        "db": os.getenv("odoo_db"),
        "user": os.getenv("odoo_user"),
        "password": os.getenv("odoo_password"),
        "url": os.getenv("odoo_url"),
        "labels_path": "/home/ubuntu/Documents/server-Tln/Tools/etiquetazpl/Etiquetas"
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
    for order in orders:
        print(order)
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


def search_pick_id(so_name, type='/PICK/'):
    """ Busca el ID del picking en Odoo relacionado con la orden. """
    try:
        search_domain = [['origin', '=', so_name], ['name', 'like', type]]
        pickings = models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                                     'stock.picking', 'search_read',
                                     [search_domain],
                                     {'fields': ['id', 'name', 'message_attachment_count']})
        if pickings:
            return pickings[0]['id']
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
        order_id = 2000010754620984 #order['channel_order_reference']
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
            pick_id = search_pick_id(so_name, type="/PICK/")
            upload_attachment(so_name, pick_id)
            logging.info(f'Se ha agregago la guia al PICK {pick_id} de la orden {so_name}')


if __name__ == "__main__":
    # Cargar variables de entorno
    load_dotenv()

    # ////////////////////////////////////////////////
    credentials = 'test' # production
    # ////////////////////////////////////////////////


    # Obtener credenciales del entorno
    odoo_env = get_odoo_credentials(os.getenv("ODOO_ENV", credentials))
    ODOO_DB_NAME = odoo_env["db"]
    ODOO_USER_ID = odoo_env["user"]
    ODOO_PASSWORD = odoo_env["password"]
    ODOO_URL = odoo_env["url"]
    labels_path = odoo_env["labels_path"]

    # Configuración del cliente XML-RPC
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB_NAME, ODOO_USER_ID, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    process_orders(1, local=True)  # Ordenes creadas en las ultimas N horas, Entorno local o Instancia

