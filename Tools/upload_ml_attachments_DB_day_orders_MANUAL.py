import base64
import time
import zipfile
import requests
import json
import logging
import os
import xmlrpc.client
from datetime import datetime, timedelta
from dotenv import load_dotenv
import tokens_meli as tk_meli
import gspread
import time as tm
import mysql.connector


CARD_NAME_TO_EXTRACT = ['Mañana', 'Martes']


# Ajustar la hora manualmente restando 6 horas (UTC → CDMX)
def get_cdmx_time():
    return (datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')

def get_local_utc_range():
    """ Obtiene el rango de fecha en UTC 0 basado en la hora local de CDMX (UTC-6). """

    now_cdmx = datetime.strptime(get_cdmx_time(), '%Y-%m-%d %H:%M:%S')

    # Calcular inicio y fin del día en horario CDMX
    start_date_cdmx = now_cdmx.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date_cdmx = now_cdmx.replace(hour=23, minute=59, second=59, microsecond=0)

    # Convertir a UTC 0 sumando 6 horas
    start_date_utc = start_date_cdmx + timedelta(hours=6)
    end_date_utc = end_date_cdmx + timedelta(hours=6)

    return start_date_utc.strftime('%Y-%m-%d %H:%M:%S'), end_date_utc.strftime('%Y-%m-%d %H:%M:%S')


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

# /////// Fecha mas actualizada pra ejecucion //////////
lastest_date_path = "latest_date.json"


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

def get_odoo_model(environment='test'):
    global uid, models, ODOO_DB_NAME, ODOO_PASSWORD
    # Cargar variables de entorno
    load_dotenv()

    # Obtener credenciales del entorno
    odoo_env = get_odoo_credentials(os.getenv("ODOO_ENV", environment))
    ODOO_DB_NAME = odoo_env["db"]
    ODOO_USER_ID = odoo_env["user"]
    ODOO_PASSWORD = odoo_env["password"]
    ODOO_URL = odoo_env["url"]

    # Configuración del cliente XML-RPC
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB_NAME, ODOO_USER_ID, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    #return uid, models, ODOO_DB_NAME, ODOO_PASSWORD

def get_orders_from_odoo(filter_date, today_date):
    """ Obtiene las órdenes de Odoo en las últimas 'hours' horas. """

    # --------------------------------------------------------
    # filter_date = '2025-06-10 00:00:00'
    # --------------------------------------------------------

    # ----------------------------------------------------------------------------------------------
    # **** Cambio 17-06-2025 para garantizar que ordenes migran a WMS hasta tener guia adjunta en pick. ****


    # search_domain = [
    #     ('team_id', '=', 'Team_MercadoLibre'),
    #     ('yuju_carrier_tracking_ref', 'in', ['Colecta', 'Flex', 'Drop Off', 'Cross Docking con Drop Off']),
    #     #('date_order', '>=', filter_date),
    #     ('write_date', '>=', filter_date),
    #     ('state', '=', 'done'),
    #     ('yuju_carrier_tracking_ref', 'not ilike', ' / '),
    #     ('effective_date', '=', False)
    # ]

    search_domain = [
        ('team_id', '=', 'Team_MercadoLibre'),
        '|', '|', '|',  # 4 ORs
        ('yuju_carrier_tracking_ref', 'ilike', 'Colecta'),
        ('yuju_carrier_tracking_ref', 'ilike', 'Flex'),
        ('yuju_carrier_tracking_ref', 'ilike', 'Drop Off'),
        ('yuju_carrier_tracking_ref', 'ilike', 'Cross Docking con Drop Off'),
        ('write_date', '>=', filter_date),
        ('state', '=', 'done'),
        ('yuju_carrier_tracking_ref', 'not ilike', ' / '),
        ('effective_date', '=', False)
    ]

    # ----------------------------------------------------------------------------------------------

    orders = models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                               'sale.order', 'search_read',
                               [search_domain],
                               {'fields': ['channel_order_reference', 'yuju_pack_id', 'id', 'name', 'yuju_seller_id','create_date', 'date_order', 'yuju_carrier_tracking_ref', 'write_date']})

    logging.info(f"{len(orders)} órdenes actualizadas en Odoo")
    print(f"{len(orders)} órdenes actualizadas en Odoo")

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

        #if so_name == 'SO3566499':
        #    print(r.content)

        try:
            response_json = r.json()
            if "failed_shipments" in response_json and response_json["failed_shipments"]:
                for failed in response_json["failed_shipments"]:
                    message = failed.get("message", "Motivo desconocido")  # Extrae el motivo o usa un valor por defecto
                    #logging.info(f"No se pudo extraer guía para {so_name}: {message}
                return {'ml_api_message':f'Advertencia. No se pudo extraer guía: {message}"', 'zpl_response':None}
        except Exception as e:
            pass


        open('Etiqueta.zip', 'wb').write(r.content)
        with zipfile.ZipFile("Etiqueta.zip", "r") as zip_ref:
            zip_ref.extractall(f"{labels_path}/Etiqueta_{so_name}")

        #///////////////// Obtener zpl /////////////////
        path_attachment = f'{labels_path}/Etiqueta_{so_name}/Etiqueta de envio.txt'
        if os.path.exists(path_attachment):
            with open(path_attachment, 'rb') as file:
                file_content = base64.b64encode(file.read()).decode('utf-8')
        else:
            logging.error("El archivo no existe: " + path_attachment)
            file_content = None
        # //////////////////////////////////////////////

        return {'ml_api_message': f'Se procesó el archivo ZPL de la Orden: {so_name} con éxito', 'zpl_response': file_content}
    except Exception as e:
        return {'ml_api_message': f'Error get_zpl_meli: {str(e)}', 'zpl_response': None}


def search_pick_id(so_name, type='/PICK/', count_attachments = False):
    """ Busca el ID del picking en Odoo relacionado con la orden. """
    try:
        search_domain = [['origin', '=', so_name], ['name', 'like', type], ['state', 'in', ['assigned', 'confirmed', 'done']]]  #Cambio para tomar en cuenta el PICK que si está activo y no cancelado
        pickings = models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                                     'stock.picking', 'search_read',
                                     [search_domain],
                                     {'fields': ['id', 'name', 'message_attachment_count', 'state']})

        if pickings:
            attatchments_number = pickings[0]['message_attachment_count']
            pick_id = pickings[0]['id']
            state = pickings[0]['state']

            if state == 'confirmed':
                logging.info(f'El PICK {pick_id} de la orden {so_name} está en espera para procesarse.')
                pass # Aunque el pick no esté "Listo", se procesará normal, se inserta guia.
                #return pick_id, 'PICK en espera'
            elif state == 'done':
                return pick_id, 'PICK ya hecho'

            if count_attachments:
                if attatchments_number == 0:
                    return (pick_id, 'NO ATTACHMENTS')
                else:
                    return (pick_id, 'THERE ARE ATTACHMENTS')
            else:
                return pick_id, 'ERROR count_attachments'

        else:
            logging.error(f"No se encontró el PICK para la orden: {so_name}.")
            return (False, False)
    except Exception as e:
        logging.error(f'Error en search_pick_id: {str(e)}')
        return (False, False)

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
        #logging.info(f'Se ha cargado la guía al pick: {pick_id} de la orden: {so_name} con éxito.')
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

def process_orders(local=True):
    """
    Primero se procesan las órdenes pendientes de la DB y descarga las etiquetas de Mercado Libre.
    Si no hay guia disponible, se guarda el estado de la respuesta de ML.
    Si la hay, se actualiza el registro de la DB.

     Despues procesa las órdenes de Odoo y descarga las etiquetas de Mercado Libre.
    Si no hay guia disponible, se guarda el estado de la respuesta de ML.
    La informacion ser carga a la tabla ml_guide_insertion de la db tools.

    """

    tk_meli.get_all_tokens()

    now_date = datetime.now()
    today_date = now_date.strftime('%Y-%m-%d %H:%M:%S')
    # filter_date = (now_date - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')

    # El filtro ahora es con la fecha de la ultima orden desde la DB
    # filter_date = lastest_date_path_json(lastest_date_path)   # Con en json
    # latest_date_db = get_latest_date_from_db().strftime('%Y-%m-%d %H:%M:%S')

    latest_date_db = get_latest_date_from_db()
    if latest_date_db:
        lastest_date = latest_date_db - timedelta(days=20)
        filter_date = lastest_date.strftime('%Y-%m-%d %H:%M:%S')
    else:
        filter_date = '2025-07-10 00:00:00'

    print(f'Filter date (ml_insertion_guide DB):    {filter_date} \nNow:                                    {today_date}')
    logging.info(f'Filter date (ml_insertion_guide DB): {filter_date} / Now: {today_date}')
    logging.info('--------------------------------------------------------------------------------')


    # ---------- Actualizamos el estado de las ordenes de la DB ------------------------------
    update_orders_from_crawl()
    # ---------- Procesamos las ordenes pendientes de obtener su guia en ML------------------
    db_orders = get_orders_info_DB()
    procces_db_orders(db_orders, local)
    # --------------------------------------------------------------------------------------

    logging.info(f'------------------------------------------------------------------------------------------------------------------------------')

    # --------------------------------------------------------------------------------------
    # Rango de busqueda de ordenes del día. Busca desde las 00:00 hrs a las 23:59 hrs del dia actual
    start_date, end_date = get_local_utc_range()

    # Obtenemos las nuevas ordenes de Odoo sin guia de ML
    new_orders_odoo = get_orders_from_odoo(filter_date,today_date)

    # Obtenemos las ordenes que deben ser procesadas el dia actual
    orders_day_DB_crawl = get_orders_day_info_crawl(start_date, end_date)

    # Hacer un INNER JOIN (trabajamos con conjuuntos) para matchear las ordenes
    orders_to_process = filter_matching_orders(odoo_orders=new_orders_odoo, db_ML_orders=orders_day_DB_crawl)

    # Procesamos esas ordenes. La info viene de Odoo pero solo son las que si deben procesarse ne el dia actual
    procces_new_orders(orders_to_process, local)

    # --------------------------------------------------------------------------------------

def delete_attachments_with_name_contains(pick_id, keyword='empty'):
    """
    Elimina adjuntos del picking cuyo nombre contengaun string en especifico.

    Parámetros:
    - pick_id: ID del picking (`stock.picking`).
    - keyword: Cadena que debe estar contenida en el nombre del archivo para ser eliminado.

    Retorna:
    - True si se eliminó al menos uno, False si no se eliminó ninguno.
    """
    try:
        # Buscar IDs de adjuntos del picking
        attachment_ids = models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                                           'ir.attachment', 'search',
                                           [[['res_model', '=', 'stock.picking'], ['res_id', '=', pick_id]]])

        if not attachment_ids:
            # print(f"No hay adjuntos en picking ID {pick_id}")
            return False

        # Leer los nombres de los adjuntos
        attachments = models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                                        'ir.attachment', 'read',
                                        [attachment_ids],
                                        {'fields': ['id', 'name']})

        # Filtrar los que contengan la palabra clave
        to_delete_ids = [att['id'] for att in attachments if keyword.lower() in att['name'].lower()]

        if not to_delete_ids:
            # print(f"No se encontraron adjuntos con la palabra '{keyword}' en el nombre.")
            return False

        # Eliminar solo esos adjuntos
        models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                          'ir.attachment', 'unlink',
                          [to_delete_ids])

        # print(f"Se eliminaron {len(to_delete_ids)} adjuntos con '{keyword}' en el nombre.")
        return True

    except Exception as e:
        # print(f"Error al eliminar adjuntos: {e}")
        return False

#/////////////////////////////////////////////////////////////////////////////////
# /////////////////////// Funciones de procesamiento por orden ///////////////////

def procces_db_orders(orders, local):
    count = 0
    total_ = len(orders)

    cdmx_time = datetime.strptime(get_cdmx_time(), "%Y-%m-%d %H:%M:%S")
    limit_hour = cdmx_time.replace(hour=14, minute=0, second=0, microsecond=0)  # 4pm CDMX

    print(f'cdmx_time: {cdmx_time}')

    for order in orders:
        count += 1
        #print(f'Orden desde DB {count} de {total_}')

        record_id = order["id"] # Registro de la DB

        order_id = order['order_id'] # Ya viene como int
        so_name = order['so_name']
        marketplace_reference = order['marketplace_reference']
        seller_marketplace = order['seller_marketplace']
        carrier_tracking_ref = order['carrier_tracking_ref']  # Colecta

        # ----------------------------------------------------------------------------------------------
        # **** Cambio 17-06-2025 para garantizar que ordenes migran a WMS hasta tener guia adjunta en pick. ****
        # carrier_selection_relational = order['carrier_selection']  # Se añadio el campo carrier_selection a la DB "tools.ml_guide_insertion"
        # ----------------------------------------------------------------------------------------------

        pick_id = order['pick_id'] # Ya viene como int
        # print(so_name, pick_id, type(pick_id))

        # --------------------------------------
        ml_crawl_status = order["ml_status"]
        card_name = order["card_name"]
        # --------------------------------------

        user_id_ = get_seller_user_id(seller_marketplace)
        if not user_id_:
            logging.info(f'DB: Orden {so_name} no procesable, id del Marketplace desconocido.')
            continue

        access_token = recupera_meli_token(user_id_, local)
        # Volvemos a consultar la info de la orden en MercadoLibre porque es muy posible que la informacion haya cambiado
        order_meli = get_order_meli(marketplace_reference, access_token)

        if not order_meli:
            logging.info(f'DB: La orden {so_name} no se encuentra en MercadoLibre')
            continue

        shipment_ids = order_meli['shipping_id']
        ml_order_status = order_meli['status']
        if ml_order_status in ['cancelled', 'delivered']:
            logging.info(f'DB: La orden {so_name} esta en estado {ml_order_status}, no se procesa')
            update_log_db(record_id,
                          processed_successfully=0,
                          status=ml_order_status,
                          card_name=card_name,
                          already_printed=0,
                          ml_status=ml_crawl_status)
            continue


        # # --------- Logica para colecta mañana 09/octubre/2025 ------------------
        # # if cdmx_time >= limit_hour and 'Mañana' in card_name:
        # if card_name and cdmx_time >= limit_hour and any(keyword in card_name for keyword in CARD_NAME_TO_EXTRACT):
        #     get_label_for_tomorrow = True
        #     message_for_tomorrow = 'Guía de Mañana ADELANTADA // '
        # else:
        #     get_label_for_tomorrow = False
        #     message_for_tomorrow = ''
        # # -------------------------------------------------------------------------

        # --------- Logica para colecta mañana/dias siguientes MARTES ------------------
        get_label_for_tomorrow = False
        message_for_tomorrow = ''

        if card_name and cdmx_time >= limit_hour:
            # Iteramos para encontrar QUÉ keyword coincide
            for keyword in CARD_NAME_TO_EXTRACT:
                if keyword in card_name:
                    get_label_for_tomorrow = True
                    message_for_tomorrow = f'Guía de {keyword} ADELANTADA // '
                    break  # Salimos del bucle en cuanto encontramos la primera coincidencia
        # -------------------------------------------------------------------------

        if ml_crawl_status == 'Envíos de hoy' or get_label_for_tomorrow:
            zpl_meli_response = get_zpl_meli(shipment_ids, so_name, access_token)
            message_response = zpl_meli_response['ml_api_message']
            zpl_data = zpl_meli_response['zpl_response']

            status_map = {
                "status is picked_up": "picked_up",
                "status is shipped": "shipped",
                "status is delivered": "delivered",
                "status is pending": "pending",
                "éxito": "guide_obtained"
            }
            status = next((value for key, value in status_map.items() if key in message_response), None)

            if ('Error' not in message_response) and ('Advertencia' not in message_response):
                empty_file = delete_attachments_with_name_contains(pick_id,'empty')

                if empty_file:
                    meessage_empty_file = 'Archivo dummy eliminado /'
                else:
                    meessage_empty_file = ''

                upload_attachment(so_name, pick_id)
                carrier_traking_response = insert_carrier_tracking_ref_odoo_backup(order_id, so_name, carrier_tracking_ref)
                insert_log_message_pick(pick_id, so_name)
                update_log_db(record_id,
                              processed_successfully=1,
                              status=status,
                              card_name=card_name,
                              zpl=zpl_data,
                              already_printed=0,
                              ml_status=ml_crawl_status)
                if "Flex" in carrier_tracking_ref:
                    carrier_option_response = insert_LOIN_carrier_odoo(order_id, so_name)
                    logging.info(
                        f'DB: {message_for_tomorrow}{meessage_empty_file}. Se ha agregago la guia al PICK {pick_id} de la orden {so_name}. {carrier_traking_response}. FLEX: {carrier_option_response}')
                else:
                    logging.info(
                        f'DB: {message_for_tomorrow}{meessage_empty_file}. Se ha agregago la guia al PICK {pick_id} de la orden {so_name}. {carrier_traking_response}')
            else:
                logging.info(f'DB: No se pudo obtener ZPL / {message_response} para la orden {so_name}')
                if status == 'picked_up' or status == 'shipped' or status == 'delivered':
                    update_log_db(record_id,
                                  processed_successfully=0,
                                  status=status,
                                  card_name=card_name,
                                  failure_reason=f"Failed to obtain ZPL: {message_response}",
                                  already_printed=1,
                                  ml_status=ml_crawl_status)
                else:
                    update_log_db(record_id,
                                  processed_successfully=0,
                                  status=status,
                                  card_name=card_name,
                                  failure_reason=f"Failed to obtain ZPL: {message_response}",
                                  already_printed=0,
                                  ml_status=ml_crawl_status)

        else:
            # El status en ML dice que NO es para hoy:
            status = 'not_for_today'
            update_log_db(record_id,
                          processed_successfully=0,
                          status=status,
                          card_name=card_name,
                          failure_reason=f"Esta orden aun no es procesable para hoy [ACT]",
                          already_printed=0,
                          ml_status=ml_crawl_status)


def procces_new_orders(orders, local):

    count = 0
    total_ = len(orders)

    process_coun = 0

    # Inicializamos lastest_date_value = False en caso de que no haya habido ordenes a procesar
    lastest_date_value = False

    cdmx_time = datetime.strptime(get_cdmx_time(), "%Y-%m-%d %H:%M:%S")
    limit_hour = cdmx_time.replace(hour=16, minute=0, second=0, microsecond=0) # 4pm CDMX

    for order in orders:
        count += 1
        print(f'Orden desde Odoo {count} de {total_}')
        marketplace_reference = order['channel_order_reference']
        pack_id = order['yuju_pack_id']
        seller_marketplace = order['yuju_seller_id']
        so_name = order['name']

        order_id = order['id']

        # ----------------------------------------------------------------------------------------------
        # **** Cambio 17-06-2025 para garantizar que ordenes migran a WMS hasta tener guia adjunta en pick. ****

        # carrier_tracking_ref = order['yuju_carrier_tracking_ref']   # Colecta
        # carrier_tracking_ref, carrier_selection_relational = [x.strip() for x in order['yuju_carrier_tracking_ref'].split('|')]
        # carrier_tracking_ref, carrier_selection_relational = parse_tracking_and_carrier(order['yuju_carrier_tracking_ref'])
        # ----------------------------------------------------------------------------------------------

        # Eric inserta carrier.  cambio 15/julio/2025
        carrier_tracking_ref = order['yuju_carrier_tracking_ref']   # Colecta
        # ----------------------------------------------------------------------------------------------


        last_update_odoo = order['write_date']
        date_order_odoo = order['date_order']

        # --------------------------------------
        ml_crawl_status = order["status_name"]
        card_name = order['card_name']
        # --------------------------------------

        # Obtenemos la fecha de consulta mas reciente dentro de las ordenes procesadas en el for actual.
        lastest_date_value = update_latest_date_json(last_update_odoo)

        user_id_ = get_seller_user_id(seller_marketplace)
        if not user_id_:
            logging.info(f'Orden {so_name} no procesable, id del Marketplace desconocido.')
            continue

        access_token = recupera_meli_token(user_id_, local)
        order_meli = get_order_meli(marketplace_reference, access_token)
        #print(access_token, order_meli)
        if not order_meli:
            logging.info(f'La orden {so_name} no se encuentra en MercadoLibre')
            continue

        shipment_ids = order_meli['shipping_id']
        ml_order_status = order_meli['status']
        if ml_order_status in ['cancelled', 'delivered']:
            logging.info(f'La orden {so_name} esta en estado {ml_order_status}, no se procesa')
            continue


        pick_id, are_there_attachments = search_pick_id(so_name, type="/PICK/", count_attachments=True)

        # # --------- Logica para colecta mañana 09/octubre/2025 ------------------
        # if cdmx_time >= limit_hour and 'Mañana' in card_name:
        #     get_label_for_tomorrow = True
        #     message_for_tomorrow = 'Guía de Mañana ADELANTADA // '
        # else:
        #     get_label_for_tomorrow = False
        #     message_for_tomorrow = ''
        # # -------------------------------------------------------------------------



        # --------- Logica para colecta mañana/dias siguientes MARTES ------------------
        get_label_for_tomorrow = False
        message_for_tomorrow = ''

        if card_name and cdmx_time >= limit_hour:
            # Iteramos para encontrar QUÉ keyword coincide
            for keyword in CARD_NAME_TO_EXTRACT:
                if keyword in card_name:
                    get_label_for_tomorrow = True
                    message_for_tomorrow = f'Guía de {keyword} ADELANTADA // '
                    break  # Salimos del bucle en cuanto encontramos la primera coincidencia
        # -------------------------------------------------------------------------


        if ml_crawl_status == 'Envíos de hoy' or get_label_for_tomorrow:
            if are_there_attachments == 'NO ATTACHMENTS':
                zpl_meli_response = get_zpl_meli(shipment_ids, so_name, access_token)
                message_response = zpl_meli_response['ml_api_message']
                zpl_data = zpl_meli_response['zpl_response']

                status_map = {
                    "status is picked_up": "picked_up",
                    "status is shipped": "shipped",
                    "status is delivered": "delivered",
                    "status is pending": "pending",
                    "éxito": "guide_obtained"
                }
                status = next((value for key, value in status_map.items() if key in message_response), None)

                if ('Error' not in message_response) and ('Advertencia' not in message_response):
                    upload_attachment(so_name, pick_id)
                    carrier_traking_response = insert_carrier_tracking_ref_odoo_backup(order_id, so_name, carrier_tracking_ref)
                    insert_log_message_pick(pick_id, so_name)
                    save_log_db(
                        order_id=order_id,
                        so_name=so_name,
                        marketplace_reference=marketplace_reference,
                        seller_marketplace=seller_marketplace,
                        pack_id=pack_id,
                        ml_status=ml_crawl_status,
                        card_name=card_name,
                        carrier_tracking_ref=carrier_tracking_ref,
                        carrier_selection='NULL', # No se utiliza este campo, Eric inserta carrier.  cambio 15/julio/2025
                        date_order_odoo=date_order_odoo,
                        last_update_odoo=last_update_odoo,
                        processed_successfully=1,
                        pick_id=pick_id,
                        zpl=zpl_data,
                        status=status,
                        already_printed=0
                    )
                    if "Flex" in carrier_tracking_ref:
                        carrier_option_response = insert_LOIN_carrier_odoo(order_id, so_name)
                        logging.info(f'{message_for_tomorrow}Se ha agregago la guia al PICK {pick_id} de la orden {so_name}. {carrier_traking_response}. FLEX: {carrier_option_response}')
                        process_coun += 1
                    else:
                        logging.info(f'{message_for_tomorrow}Se ha agregago la guia al PICK {pick_id} de la orden {so_name}. {carrier_traking_response}')
                        process_coun += 1
                else:
                    logging.info(f'No se pudo obtener ZPL / {message_response} para la orden {so_name}')
                    if status == 'picked_up' or status == 'shipped' or status == 'delivered':
                        save_log_db(
                            order_id=order_id,
                            so_name=so_name,
                            marketplace_reference=marketplace_reference,
                            pack_id=pack_id,
                            seller_marketplace=seller_marketplace,
                            ml_status=ml_crawl_status,
                            card_name=card_name,
                            carrier_tracking_ref=carrier_tracking_ref,
                            carrier_selection='NULL', # No se utiliza este campo, Eric inserta carrier.  cambio 15/julio/2025
                            date_order_odoo=date_order_odoo,
                            last_update_odoo=last_update_odoo,
                            processed_successfully=0,
                            pick_id=pick_id,
                            failure_reason=f"Failed to obtain ZPL: {message_response}",
                            status=status,
                            already_printed=1
                        )
                    else:
                        save_log_db(
                            order_id=order_id,
                            so_name=so_name,
                            marketplace_reference=marketplace_reference,
                            pack_id=pack_id,
                            seller_marketplace=seller_marketplace,
                            ml_status=ml_crawl_status,
                            card_name=card_name,
                            carrier_tracking_ref=carrier_tracking_ref,
                            carrier_selection='NULL', # No se utiliza este campo, Eric inserta carrier.  cambio 15/julio/2025
                            date_order_odoo=date_order_odoo,
                            last_update_odoo=last_update_odoo,
                            processed_successfully=0,
                            pick_id=pick_id,
                            failure_reason=f"Failed to obtain ZPL: {message_response}",
                            status=status,
                            already_printed=0
                        )
            elif are_there_attachments == 'THERE ARE ATTACHMENTS':
                insert_carrier_tracking_ref_odoo_backup(order_id, so_name, carrier_tracking_ref)
                logging.info(f'El PICK: {pick_id} de la orden {so_name} YA tiene guia adjunta, no se consulta ML ni se agrega guia.')
            else:
                #Los logs del resto de casos están en la funcion search_pick_id
                pass

        else:
            # El status en ML dice que NO es para hoy:
            status = 'not_for_today'
            save_log_db(
                order_id=order_id,
                so_name=so_name,
                marketplace_reference=marketplace_reference,
                pack_id=pack_id,
                seller_marketplace=seller_marketplace,
                ml_status=ml_crawl_status,
                card_name=card_name,
                carrier_tracking_ref=carrier_tracking_ref,
                carrier_selection='NULL', # No se utiliza este campo, Eric inserta carrier.  cambio 15/julio/2025
                date_order_odoo=date_order_odoo,
                last_update_odoo=last_update_odoo,
                processed_successfully=0,
                pick_id=pick_id,
                failure_reason=f"Esta orden aun no es procesable para hoy",
                status=status,
                already_printed=0
            )

    logging.info('-----------------------------------------------------------------------------------------------------------------------------------------')
    logging.info(f'Se ha agregado guía a {process_coun} órdenes de {total_} posibles. / {total_ - process_coun} órdenes quedan pendientes y se agregan a la base de datos')

    if lastest_date_value:
        update_latest_date_in_db(lastest_date_value)
        logging.info(f'---------------- Actualizando la fecha de búsqueda en DB: {lastest_date_value} ----------------')

#/////////////////////////////////////////////////////////////////////////////////

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

# -----------------------------------------------------------------------------------------------------
def parse_tracking_and_carrier(value):
    parts = [x.strip() for x in value.split('|')]

    if len(parts) == 1:
        return parts[0], 'DEFINED'
    else:
        return parts[0], parts[1]
def insert_carrier_and_tracking_ref_odoo(order_id, so_name, carrier_tracking_ref, carrier_selection='CMEL'):
    """
    Actualiza en Odoo el número de guía (yuju_carrier_tracking_ref) y el carrier (carrier_selection_relational)
    para una orden de venta dada.
    """
    try:
        new_carrier_tracking_ref = carrier_tracking_ref + ' / ' + so_name

        carrier_map = {
            'CMEL': 10,
            'FDX': 1,
            'PQX': 4,
            'JTE': 19
        }

        if carrier_selection == 'DEFINED':
            # Solo actualiza el número de guía
            values = {
                'yuju_carrier_tracking_ref': new_carrier_tracking_ref
            }
        else:
            carrier_selection_relational = carrier_map.get(carrier_selection)
            values = {
                'yuju_carrier_tracking_ref': new_carrier_tracking_ref,
                'carrier_selection_relational': carrier_selection_relational
            }

        models.execute_kw(
            ODOO_DB_NAME, uid, ODOO_PASSWORD,
            'sale.order', 'write',
            [[order_id], values]
        )

        return 'Número de guía y carrier actualizado correctamente'

    except Exception as e:
        return f'Error al actualizar número de guía o carrier: {e}'

def insert_carrier_tracking_ref_odoo_backup(order_id, so_name, carrier_tracking_ref):
    try:
        new_carrier_tracking_ref = carrier_tracking_ref + ' / ' + so_name

        models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                          'sale.order', 'write',
                          [[order_id], {'yuju_carrier_tracking_ref': new_carrier_tracking_ref}])

        return 'Número de guia actualizado '

    except Exception as e:
        return f'No se ha podido actualizar el número de guía / {e} '
# -----------------------------------------------------------------------------------------------------
def insert_LOIN_carrier_odoo(order_id, so_name):
    try:
        carriers = models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                                        'carriers.list', 'search',
                                        [[['name', '=', 'Logistica interna']]])

        if carriers:
            carrier_id = carriers[0]

            models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                              'sale.order', 'write',
                              [[order_id], {'carrier_selection_relational': carrier_id}])

            return f"Carrier asignado correctamente a la orden {so_name} "
        else:
            return f"No se ecncontró el carrier "

    except Exception as e:
        return f"No se pudo modificar el carrier para la orden {so_name} / {e} "

def insert_log_message_pick(pick_id, so_name):
    current_utc_time = datetime.now()
    cdmx_time = current_utc_time - timedelta(hours=6)
    current_datetime = cdmx_time.strftime('%Y-%m-%d %H:%M:%S')
    models.execute_kw(
        ODOO_DB_NAME, uid, ODOO_PASSWORD,
        'stock.picking', 'message_post',
        [[pick_id]],
        {'body': f'{current_datetime}. Se insertó la guía de MercadoLibre para la orden {so_name}.'}
    )

def lastest_date_path_json(path):
    if os.path.exists(path):
        with open(path, "r") as file:
            try:
                data = json.load(file)
                stored_date_str = data.get("latest_date")
                if stored_date_str:
                    return stored_date_str
            except (json.JSONDecodeError, ValueError):
                pass


def update_latest_date_json(new_date_str):
    """
    Recibe una fecha en formato 'YYYY-MM-DD HH:MM:SS', la compara con la almacenada
    en latest_date.json y guarda la más reciente.
    """
    new_date = datetime.strptime(new_date_str, "%Y-%m-%d %H:%M:%S")

    stored_date_str = lastest_date_path_json(lastest_date_path)
    if stored_date_str:
        stored_date = datetime.strptime(stored_date_str, "%Y-%m-%d %H:%M:%S")
        if new_date <= stored_date:
            return stored_date_str  # No se actualiza, se retorna la última guardada

    # Guardamos la nueva fecha si es más reciente
    with open(lastest_date_path, "w") as file:
        json.dump({"latest_date": new_date_str}, file)

    return new_date_str  # Retornamos la nueva fecha guardada


#///////////////////////////// Conexion a base de datos /////////////////////////
def get_db_connection():
    """Establece y devuelve una conexión a la base de datos."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def save_log_db(order_id, so_name, marketplace_reference, pack_id, seller_marketplace, ml_status, card_name, carrier_tracking_ref, carrier_selection, date_order_odoo, last_update_odoo, processed_successfully, pick_id=None, zpl=None, failure_reason=None, status=None, already_printed=None):
    """Guarda la información de una orden procesada o no procesada en ml_guide_insertion."""
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute('''
        INSERT INTO ml_guide_insertion (
            order_id, so_name, marketplace_reference, pack_id, seller_marketplace, ml_status, card_name, carrier_tracking_ref, carrier_selection, date_order_odoo, last_update_odoo, processed_successfully, pick_id, zpl, failure_reason, status, already_printed
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (order_id, so_name, marketplace_reference, pack_id, seller_marketplace, ml_status, card_name, carrier_tracking_ref, carrier_selection, date_order_odoo, last_update_odoo, processed_successfully, pick_id, zpl, failure_reason, status, already_printed))

    connection.commit()
    cursor.close()
    connection.close()

def update_log_db(record_id, processed_successfully, status=None, card_name=None, failure_reason=None, zpl=None, already_printed=None, ml_status=None):
    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        UPDATE ml_guide_insertion
        SET processed_successfully = %s, ml_status = %s, status = %s, card_name = %s, failure_reason = %s, zpl = %s, already_printed = %s, last_update_DB = NOW()
        WHERE id = %s;
        """
    values = (processed_successfully, ml_status, status, card_name, failure_reason, zpl, already_printed, record_id)

    cursor.execute(query, values)
    connection.commit()

    cursor.close()
    connection.close()

def get_latest_date_from_db():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Fecha más reciente
    cursor.execute("SELECT MAX(latest_date) FROM ml_latest_date_orders")
    result = cursor.fetchone()
    connection.close()
    return result[0] if result and result[0] else None

def update_latest_date_in_db(new_date_str):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO ml_latest_date_orders (latest_date)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE latest_date = %s
    """, (new_date_str, new_date_str))
    connection.commit()
    connection.close()

def get_orders_info_DB():
    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        SELECT id, order_id, so_name, marketplace_reference, seller_marketplace, carrier_tracking_ref, pick_id
        FROM ml_guide_insertion
        WHERE status = 'pending' 
            AND processed_successfully = 0
            AND marketplace_reference IS NOT NULL AND marketplace_reference != ''
            AND seller_marketplace IS NOT NULL AND seller_marketplace != ''
            AND carrier_tracking_ref IS NOT NULL AND carrier_tracking_ref != '';
        """

    query = """
        WITH valid_orders AS (
            SELECT order_id, so_name
            FROM ml_guide_insertion
            GROUP BY order_id, so_name
            HAVING SUM(CASE WHEN status IN ('picked_up', 'shipped', 'delivered', 'guide_obtained', 'not_for_today', 'cancelled', 'delivered') THEN 1 ELSE 0 END) = 0
        )
        SELECT id, order_id, so_name, marketplace_reference, seller_marketplace, ml_status, card_name, carrier_tracking_ref, carrier_selection, pick_id, status
        FROM ml_guide_insertion mgi
        WHERE status = 'pending' 
            AND processed_successfully = 0
            AND marketplace_reference IS NOT NULL AND marketplace_reference != ''
            AND seller_marketplace IS NOT NULL AND seller_marketplace != ''
            AND carrier_tracking_ref IS NOT NULL AND carrier_tracking_ref != ''
            AND EXISTS (SELECT 1 FROM valid_orders vo WHERE vo.order_id = mgi.order_id AND vo.so_name = mgi.so_name)
        ORDER BY id;
    """

    cursor.execute(query)
    results = cursor.fetchall()

    orders = [
        {
            "id": row[0],
            "order_id": int(row[1]),
            "so_name": row[2],
            "marketplace_reference": row[3],
            "seller_marketplace": row[4],
            "ml_status": row[5],
            "card_name": row[6],
            "carrier_tracking_ref": row[7],
            "carrier_selection": row[8],
            "pick_id": int(row[9]),
            "status": row[10]
        }
        for row in results
    ]

    cursor.close()
    connection.close()

    logging.info(f" {len(orders)} órdenes pendientes en DB")
    print(f" {len(orders)} órdenes pendientes en DB")

    return orders

# //////////////////// Server 0////////////////////////////

def get_db_connection_server0():
    """Establece y devuelve una conexión a la base de datos."""
    return mysql.connector.connect(
        host=os.getenv("DB0_HOST"),
        user=os.getenv("DB0_USER"),
        password=os.getenv("DB0_PASSWORD"),
        database=os.getenv("DB0_NAME")
    )

def get_orders_day_info_crawl(start_date, end_date):
    connection = get_db_connection_server0()
    cursor = connection.cursor()

    # V1
    query = f"""
            SELECT DISTINCT status_name, sub_status_name, txn_id_mp, inserted_at
            FROM ml_sr_orders_h
            WHERE inserted_at > '{start_date}'
            AND inserted_at < '{end_date}'
            AND status_name = 'Envíos de hoy';
            """

    # V2
    query = f"""
            SELECT status_name, sub_status_name, txn_id_mp, inserted_at
            FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY txn_id_mp ORDER BY inserted_at DESC) AS rn
                FROM ml_sr_orders_h
                WHERE inserted_at >= '{start_date}'
                AND inserted_at < '{end_date}'
                AND status_name = 'Envíos de hoy'
            ) t
            WHERE rn = 1;
            """

    # V3
    query = f"""
                SELECT status_name, sub_status_name, card_name, txn_id_mp, inserted_at
                FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY txn_id_mp ORDER BY inserted_at DESC) AS rn
                    FROM ml_sales_hist
                    WHERE inserted_at >= '{start_date}'
                    AND inserted_at < '{end_date}'
                    AND status_name IN ('Envíos de hoy', 'Próximos días')
                ) t
                WHERE rn = 1;
                """
    # #ml_sales_hist, ml_sr_orders_h

    cursor.execute(query)
    results = cursor.fetchall()

    orders = [
        {
            "status_name": row[0],
            "sub_status_name": row[1],
            "card_name": row[2],
            "txn_id_mp": row[3],
            "inserted_at": row[4],
        }
        for row in results
    ]

    cursor.close()
    connection.close()

    logging.info(f"{len(orders)} registros en la DB ML (Tabla de crawlers)")
    print(f"{len(orders)} registros en la DB ML (Tabla de crawlers)")

    return orders


#//////////////////// Funcion para hacer el INNER JOIN /////////////////////////

def filter_matching_orders_v0(odoo_orders, db_orders):
    """ Filtra las órdenes de Odoo que también existen en la base de datos crawl. """


    # Crear un conjunto con los IDs de la base de datos para búsqueda rápida (hash lookup)
    db_order_ids = {order["txn_id_mp"] for order in db_orders}

    # Filtrar las órdenes de Odoo cuyo 'channel_order_reference' existe en la DB
    matching_orders = [
        order for order in odoo_orders
        if order["channel_order_reference"] in db_order_ids or order["yuju_pack_id"] in db_order_ids
    ]

    logging.info("-------------------------------------------------------------------------------")
    logging.info(f"Órdenes encontradas en Odoo y en ML (órdenes nuevas): {len(matching_orders)}")
    print(f"Órdenes encontradas en Odoo y en ML (órdenes nuevas): {len(matching_orders)}")

    return matching_orders


def filter_matching_orders(odoo_orders, db_ML_orders):
    """
    Filtra las órdenes de Odoo que también existen en la base de datos ML (crawl DB),
    añade `status_name`, pero no los agrega si ya estan en la tabla `ml_guide_insertion`.
    """

    if odoo_orders and db_ML_orders: # Que no sean listas vacias

        # Extraer los posibles valores que pueden coincidir en la BD
        candidate_ids = {order["channel_order_reference"] for order in odoo_orders} | \
                        {order["yuju_pack_id"] for order in odoo_orders if order.get("yuju_pack_id")}

        candidate_ids_list = list(candidate_ids)

        # Conectar a la base de datos para verificar duplicados
        connection = get_db_connection()
        cursor = connection.cursor()

        # Crear la cadena de placeholders para IN
        placeholders = ', '.join(['%s'] * len(candidate_ids_list))

        # Obtener SOLO los txn_id_mp que coincidan con los posibles valores en candidate_ids
        cursor.execute(f"""
                                SELECT marketplace_reference 
                                FROM ml_guide_insertion
                                WHERE marketplace_reference IN ({placeholders});
                            """, tuple(candidate_ids_list))

        existing_mkp_ids = {row[0] for row in cursor.fetchall()}  # Convertir a conjunto para búsqueda rápida

        # Cerrar conexión a la base de datos
        cursor.close()
        connection.close()

        # Crear un diccionario {txn_id_mp: {'status_name': ..., 'card_name': ...}} para búsqueda rápida
        db_orders_dict = {
            order["txn_id_mp"]: {
                "status_name": order["status_name"],
                "card_name": order["card_name"]
            } for order in db_ML_orders
        }

        # Lista de órdenes que tienen coincidencia con ML
        matching_orders = []

        for order in odoo_orders:
            channel_ref = order.get("channel_order_reference")
            yuju_pack_id = order.get("yuju_pack_id")

            # Obtener el diccionario de datos si alguna de las claves está en db_orders_dict
            order_data = db_orders_dict.get(channel_ref) or db_orders_dict.get(yuju_pack_id)

            # Verificar si la orden ya existe en la base de datos
            if order_data and (channel_ref not in existing_mkp_ids and yuju_pack_id not in existing_mkp_ids):
                # Añadimos los datos extraídos a la orden de Odoo
                order["status_name"] = order_data["status_name"]
                order["card_name"] = order_data["card_name"]
                matching_orders.append(order)

    else:
        matching_orders = []


    match_count = len(matching_orders)
    logging.info(f"Órdenes encontradas en Odoo y en ML (órdenes nuevas): {match_count}")
    print(f"Órdenes encontradas en Odoo y en ML (órdenes nuevas): {match_count}")

    return matching_orders

def filter_matching_orders_backup(odoo_orders, db_ML_orders):
    """
    Filtra las órdenes de Odoo que también existen en la base de datos ML (crawl DB),
    añade `status_name`, pero no los agrega si ya estan en la tabla `ml_guide_insertion`.
    """

    if odoo_orders and db_ML_orders: # Que no sean listas vacias

        # Extraer los posibles valores que pueden coincidir en la BD
        candidate_ids = {order["channel_order_reference"] for order in odoo_orders} | \
                        {order["yuju_pack_id"] for order in odoo_orders if order.get("yuju_pack_id")}

        candidate_ids_list = list(candidate_ids)

        # Conectar a la base de datos para verificar duplicados
        connection = get_db_connection()
        cursor = connection.cursor()

        # Crear la cadena de placeholders para IN
        placeholders = ', '.join(['%s'] * len(candidate_ids_list))

        # Obtener SOLO los txn_id_mp que coincidan con los posibles valores en candidate_ids
        cursor.execute(f"""
                                SELECT marketplace_reference 
                                FROM ml_guide_insertion
                                WHERE marketplace_reference IN ({placeholders});
                            """, tuple(candidate_ids_list))

        existing_mkp_ids = {row[0] for row in cursor.fetchall()}  # Convertir a conjunto para búsqueda rápida

        # Cerrar conexión a la base de datos
        cursor.close()
        connection.close()

        # Crear un diccionario {txn_id_mp: status_name} para búsqueda rápida
        db_orders_dict = {order["txn_id_mp"]: order["status_name"] for order in db_ML_orders}

        # Lista de órdenes que tienen coincidencia con ML
        matching_orders = []

        for order in odoo_orders:
            channel_ref = order.get("channel_order_reference")
            yuju_pack_id = order.get("yuju_pack_id")

            # Obtener el status_name si alguna de las claves está en db_orders_dict
            status_name = db_orders_dict.get(channel_ref) or db_orders_dict.get(yuju_pack_id)

            # Verificar si la orden ya existe en la base de datos
            if status_name and (channel_ref not in existing_mkp_ids and yuju_pack_id not in existing_mkp_ids):
                order["status_name"] = status_name
                matching_orders.append(order)

    else:
        matching_orders = []


    match_count = len(matching_orders)
    logging.info(f"Órdenes encontradas en Odoo y en ML (órdenes nuevas): {match_count}")
    print(f"Órdenes encontradas en Odoo y en ML (órdenes nuevas): {match_count}")

    return matching_orders


# //////// Funcion para actualizar el estado de ML para ordenes pendientes en la base de datos /////////

def update_orders_from_crawl():
    print("En: update_orders_from_crawl")
    """
    Actualiza el `status`, `ml_status` y `card_name` de las órdenes en `tools.ml_guide_insertion`
    con la información más reciente de `crawl.ml_sales_hist`.
    """

    # Conectar a la base de datos de inserción de guías (tools)
    connection_tools = get_db_connection()
    cursor_tools = connection_tools.cursor()

    actual_date = datetime.strptime(get_cdmx_time(), "%Y-%m-%d %H:%M:%S")
    limit_date = actual_date - timedelta(days=60)

    # Obtener órdenes con `status = 'not_for_today'`
    cursor_tools.execute(f"""
        SELECT id, marketplace_reference, pack_id
        FROM ml_guide_insertion
        WHERE status = 'not_for_today'
        AND ml_status in ('Próximos días')
        AND last_update_odoo >= '{limit_date}';
    """)
    orders = cursor_tools.fetchall()  # Lista de (id, txn_id_mp)
    print(len(orders))

    if not orders:
        logging.info("------------------------------- No hay órdenes con status 'not_for_today' -------------------------------")
        print("------------------------------- No hay órdenes con status 'not_for_today' -------------------------------")
        cursor_tools.close()
        connection_tools.close()
        return

    # Conectar a la base de datos de Mercado Libre (crawl)
    connection_crawl = get_db_connection_server0()
    cursor_crawl = connection_crawl.cursor()

    # Diccionario para mapear txn_id_mp -> status_name más reciente
    status_map = {}

    # Extraer los valores de marketplace_reference y pack_id, excluyendo los `None`
    mkp_ids = tuple(order[1] for order in orders if order[1] is not None)
    pack_ids = tuple(order[2] for order in orders if order[2] is not None)

    # Placeholders
    placeholders_mkp = ','.join(['%s'] * len(mkp_ids)) if mkp_ids else "NULL"
    placeholders_pack = ','.join(['%s'] * len(pack_ids)) if pack_ids else "NULL"

    query = f"""
            SELECT txn_id_mp, status_name, card_name
            FROM (
                SELECT txn_id_mp, status_name, card_name, ROW_NUMBER() OVER (PARTITION BY txn_id_mp ORDER BY inserted_at DESC) AS rn
                FROM ml_sales_hist
                WHERE txn_id_mp IN ({placeholders_mkp}) OR txn_id_mp IN ({placeholders_pack})
            ) t
            WHERE rn = 1;
        """

    query_params = mkp_ids + pack_ids
    cursor_crawl.execute(query, query_params)
    results = cursor_crawl.fetchall()  # Lista de (txn_id_mp, status_name, card_name)

    # Construir diccionario {txn_id_mp: status_name}
    #status_map = {row[0]: row[1] for row in results}
    crawl_data_map = {row[0]: {"status_name": row[1], "card_name": row[2]} for row in results}

    # Cerrar conexión con `crawl`
    cursor_crawl.close()
    connection_crawl.close()

    # Actualizar `ml_status`, `card_name` y `status` en `tools.ml_guide_insertion`
    for_today_count = 0
    for_tomorrow_count = 0
    for record_id, mkp_id, pack_id in orders:
        # Se busca el diccionario de datos del crawl
        crawl_data = crawl_data_map.get(mkp_id) or crawl_data_map.get(pack_id)

        if crawl_data:
            new_status_name = crawl_data.get("status_name", "unknown")
            new_card_name = crawl_data.get("card_name")
        else:
            new_status_name = "unknown"
            new_card_name = None

        is_for_next_day = new_card_name and any(keyword in new_card_name for keyword in CARD_NAME_TO_EXTRACT)
        new_status = "pending" if new_status_name == "Envíos de hoy" or is_for_next_day else "not_for_today"
        #new_status = "pending" if new_status_name == "Envíos de hoy" or 'Mañana' in new_card_name else "not_for_today"

        if new_status_name == "Envíos de hoy":
            for_today_count += 1
        #if 'Mañana' in new_card_name:
        if is_for_next_day:
            for_tomorrow_count += 1

        # Se pasa el nuevo card_name a la función de actualización
        update_log_db(
            record_id,
            processed_successfully=0,
            status=new_status,
            card_name=new_card_name,
            failure_reason=None,
            zpl=None,
            already_printed=None,
            ml_status=new_status_name
        )

    # Cerrar conexión con `tools`
    cursor_tools.close()
    connection_tools.close()

    logging.info(f" Órdenes de tools con ml_status actualizado: {len(orders)} / Pendientes (Envíos para hoy): {for_today_count} / Próximos días: {for_tomorrow_count}")
    logging.info('----------------------------------------------------------')

    print(f" Órdenes de tools con ml_status actualizado: {len(orders)} / Pendientes (Envíos para hoy): {for_today_count} / Próximos días: {for_tomorrow_count}")


if __name__ == "__main__":
    logging.info("///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////")
    print("////////////////////////////////////////////////////")

    start = tm.time()
    # Cargar variables de entorno
    load_dotenv()

    # ////////////////////////////////////////////////
    enviroment = 'production' # production / test
    # ////////////////////////////////////////////////

    labels_path = "/home/ubuntu/Documents/server-Tln/Tools/etiquetazpl/Etiquetas"
    #labels_path = "C:/Users/Sergio Gil Guerrero/Documents/WonderBrands/Repos/Tools/etiquetazpl/Etiquetas"

    #uid, models, ODOO_DB_NAME, ODOO_PASSWORD = get_odoo_model()

    # Setea las variables del modelo para Odoo globales
    get_odoo_model(enviroment)

    process_orders(local=False)  # Ordenes creadas en las ultimas N horas, Entorno local o Instancia

    end = tm.time()

    logging.info(f"  ////////////////////////////////// Terminando la ejecución. Tiempo: {round(end - start, 2)} [s] ////////////////////////////////// \n")

    file_id = "1foh4wRPgGGT46BBYPjl9lJ2bQFjY7fHVfzptNAVoQZ8"
    credentials_json = "/home/ubuntu/Documents/server-Tln/Tools/Tools/google_cred.json"
    #credentials_json = r"C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\Tools\Tools\google_cred.json"
    try:
        insert_log_in_sheets(log_filename, file_id, credentials_json)
    finally:
        logging.shutdown()
        delete_log_file(log_filename)

