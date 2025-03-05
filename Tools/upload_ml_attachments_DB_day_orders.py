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
import gspread
import time as tm
import mysql.connector

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

    print(f'Filter date (DB):    {filter_date} \nNow:               {today_date}')

    search_domain = [
        ('team_id', '=', 'Team_MercadoLibre'),
        ('yuju_carrier_tracking_ref', 'in', ['Colecta', 'Flex', 'Drop Off']),
        #('date_order', '>=', filter_date),
        ('write_date', '>=', filter_date),
        ('state', '=', 'done'),
        ('yuju_carrier_tracking_ref', 'not ilike', ' / '),
        ('effective_date', '=', False)
    ]

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
                return pick_id, 'PICK en espera'
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
    filter_date = get_latest_date_from_db().strftime('%Y-%m-%d %H:%M:%S')


    # Primero procesamos las ordenes pendientes de obtener su guia en ML
    db_orders = get_orders_info_DB()
    procces_db_orders(db_orders, local)

    logging.info(f'*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-')
    print(f'*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-')
    start_date, end_date = get_local_utc_range()

    # Obtenemos las nuevas ordenes de ODoo sin guia de ML
    new_orders_odoo = get_orders_from_odoo(filter_date,today_date)

    # Obtenemos las ordenes que deben ser procesadas el dia actual
    orders_day_DB_crawl = get_orders_day_info_crawl(start_date, end_date)

    # Hacer un INNER JOIN (trabajamos con conjuuntos) para matchear las ordenes
    orders_to_process = filter_matching_orders(odoo_orders=new_orders_odoo, db_orders=orders_day_DB_crawl)

    # Procesamos esas ordenes. La info viene de Odoo pero solo son las que si deben procesarse ne el dia actual
    procces_new_orders(orders_to_process, local)



#/////////////////////////////////////////////////////////////////////////////////
# /////////////////////// Funciones de procesamiento por orden ///////////////////

def procces_db_orders(orders, local):
    count = 0
    total_ = len(orders)
    for order in orders:
        count += 1
        print(f'Orden desde DB {count} de {total_}')

        record_id = order["id"] # Registro de la DB

        order_id = order['order_id']
        so_name = order['so_name']
        marketplace_reference = order['marketplace_reference']
        seller_marketplace = order['seller_marketplace']
        carrier_tracking_ref = order['carrier_tracking_ref']  # Colecta
        pick_id = int(order['pick_id'])
        # print(so_name, pick_id, type(pick_id))


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
            continue

        #pick_id, are_there_attachments = search_pick_id(so_name, type="/PICK/", count_attachments=True)

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
            carrier_traking_response = insert_carrier_tracking_ref_odoo(order_id, so_name, carrier_tracking_ref)
            insert_log_message_pick(pick_id, so_name)
            update_log_db(record_id,
                          processed_successfully=1,
                          status=status,
                          zpl=zpl_data,
                          already_printed=0)
            if "Flex" in carrier_tracking_ref:
                carrier_option_response = insert_LOIN_carrier_odoo(order_id, so_name)
                logging.info(
                    f'DB: Se ha agregago la guia al PICK {pick_id} de la orden {so_name}. {carrier_traking_response}. FLEX: {carrier_option_response}')
            else:
                logging.info(
                    f'DB: Se ha agregago la guia al PICK {pick_id} de la orden {so_name}. {carrier_traking_response}')
        else:
            logging.info(f'DB: No se pudo obtener ZPL / {message_response} para la orden {so_name}')
            if status == 'picked_up' or status == 'shipped' or status == 'delivered':
                update_log_db(record_id,
                              processed_successfully=0,
                              status=status,
                              failure_reason=f"Failed to obtain ZPL: {message_response}",
                              already_printed=1)
            else:
                update_log_db(record_id,
                              processed_successfully=0,
                              status=status,
                              failure_reason=f"Failed to obtain ZPL: {message_response}",
                              already_printed=0)


def procces_new_orders(orders, local):

    count = 0
    total_ = len(orders)
    for order in orders:
        count += 1
        print(f'Orden desde Odoo {count} de {total_}')
        marketplace_reference = order['channel_order_reference']
        seller_marketplace = order['yuju_seller_id']
        so_name = order['name']

        order_id = order['id']
        carrier_tracking_ref = order['yuju_carrier_tracking_ref']   # Colecta

        last_update_odoo = order['write_date']
        date_order_odoo = order['date_order']
        lastest_date_value = update_latest_date_json(last_update_odoo)

        #logging.info(f'Orden {so_name}')
        #print(f'Orden {so_name}')

        user_id_ = get_seller_user_id(seller_marketplace)
        #print(user_id_)
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
                carrier_traking_response = insert_carrier_tracking_ref_odoo(order_id, so_name, carrier_tracking_ref)
                insert_log_message_pick(pick_id, so_name)
                save_log_db(
                    order_id=order_id,
                    so_name=so_name,
                    marketplace_reference=marketplace_reference,
                    seller_marketplace=seller_marketplace,
                    carrier_tracking_ref=carrier_tracking_ref,
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
                    logging.info(f'Se ha agregago la guia al PICK {pick_id} de la orden {so_name}. {carrier_traking_response}. FLEX: {carrier_option_response}')
                else:
                    logging.info(f'Se ha agregago la guia al PICK {pick_id} de la orden {so_name}. {carrier_traking_response}')
            else:
                logging.info(f'No se pudo obtener ZPL / {message_response} para la orden {so_name}')
                if status == 'picked_up' or status == 'shipped' or status == 'delivered':
                    save_log_db(
                        order_id=order_id,
                        so_name=so_name,
                        marketplace_reference=marketplace_reference,
                        seller_marketplace=seller_marketplace,
                        carrier_tracking_ref=carrier_tracking_ref,
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
                        seller_marketplace=seller_marketplace,
                        carrier_tracking_ref=carrier_tracking_ref,
                        date_order_odoo=date_order_odoo,
                        last_update_odoo=last_update_odoo,
                        processed_successfully=0,
                        pick_id=pick_id,
                        failure_reason=f"Failed to obtain ZPL: {message_response}",
                        status=status,
                        already_printed=0
                    )
        elif are_there_attachments == 'THERE ARE ATTACHMENTS':
            insert_carrier_tracking_ref_odoo(order_id, so_name, carrier_tracking_ref)
            logging.info(f'El PICK: {pick_id} de la orden {so_name} YA tiene guia adjunta, no se consulta ML ni se agrega guia.')
        else:
            #Los logs del resto de casos están en la funcion search_pick_id
            pass

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

def insert_carrier_tracking_ref_odoo(order_id, so_name, carrier_tracking_ref):
    try:
        new_carrier_tracking_ref = carrier_tracking_ref + ' / ' + so_name

        models.execute_kw(ODOO_DB_NAME, uid, ODOO_PASSWORD,
                          'sale.order', 'write',
                          [[order_id], {'yuju_carrier_tracking_ref': new_carrier_tracking_ref}])

        return 'Número de guia actualizado'

    except Exception as e:
        return 'No se ha podido actualizar el número de guía'

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

            return f"Carrier asignado correctamente a la orden {so_name}"
        else:
            return f"No se ecncontró el carrier"

    except Exception as e:
        return f"No se pudo modificar el carrier para la orden {so_name}"

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

def save_log_db(order_id, so_name, marketplace_reference,seller_marketplace, carrier_tracking_ref, date_order_odoo, last_update_odoo, processed_successfully, pick_id=None, zpl=None, failure_reason=None, status=None, already_printed=None):
    """Guarda la información de una orden procesada o no procesada en ml_guide_insertion."""
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute('''
        INSERT INTO ml_guide_insertion (
            order_id, so_name, marketplace_reference, seller_marketplace, carrier_tracking_ref, date_order_odoo, last_update_odoo, processed_successfully, pick_id, zpl, failure_reason, status, already_printed
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (order_id, so_name, marketplace_reference,seller_marketplace, carrier_tracking_ref, date_order_odoo, last_update_odoo, processed_successfully, pick_id, zpl, failure_reason, status, already_printed))

    connection.commit()
    cursor.close()
    connection.close()

def update_log_db(record_id, processed_successfully, status=None, failure_reason=None, zpl=None, already_printed=None):
    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        UPDATE ml_guide_insertion
        SET processed_successfully = %s, status = %s, failure_reason = %s, zpl = %s, already_printed = %s, last_update_DB = NOW()
        WHERE id = %s;
        """
    values = (processed_successfully, status, failure_reason, zpl, already_printed, record_id)

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
            HAVING SUM(CASE WHEN status IN ('picked_up', 'shipped', 'delivered', 'guide_obtained') THEN 1 ELSE 0 END) = 0
        )
        SELECT id, order_id, so_name, marketplace_reference, seller_marketplace, carrier_tracking_ref, pick_id
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
            "order_id": row[1],
            "so_name": row[2],
            "marketplace_reference": row[3],
            "seller_marketplace": row[4],
            "carrier_tracking_ref": row[5],
            "pick_id": row[6],
        }
        for row in results
    ]

    cursor.close()
    connection.close()

    logging.info(f"{len(orders)} órdenes pendientes en DB")
    print(f"{len(orders)} órdenes pendientes en DB")

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

    query = f"""
            SELECT DISTINCT status_name, sub_status_name, txn_id_mp, inserted_at
            FROM ml_sr_orders_h
            WHERE inserted_at > '{start_date}'
            AND inserted_at < '{end_date}';
            """

    cursor.execute(query)
    results = cursor.fetchall()

    orders = [
        {
            "status_name": row[0],
            "sub_status_name": row[1],
            "txn_id_mp": row[2],
            "inserted_at": row[3],
        }
        for row in results
    ]

    cursor.close()
    connection.close()

    logging.info(f"{len(orders)} Órdenes en la DB ML")
    print(f"{len(orders)} Órdenes en la DB ML")

    return orders


#//////////////////// Funcion para hacer el INNER JOIN /////////////////////////

def filter_matching_orders(odoo_orders, db_orders):
    """ Filtra las órdenes de Odoo que también existen en la base de datos crawl. """


    # Crear un conjunto con los IDs de la base de datos para búsqueda rápida (hash lookup)
    db_order_ids = {order["txn_id_mp"] for order in db_orders}

    # Filtrar las órdenes de Odoo cuyo 'channel_order_reference' existe en la DB
    matching_orders = [
        order for order in odoo_orders
        if order["channel_order_reference"] in db_order_ids or order["yuju_pack_id"] in db_order_ids
    ]

    logging.info("//////////////////////////////////////////////////////////////////////////////////////////////////")
    logging.info(f"Órdenes encontradas en Odoo y en ML (crawl DB): {len(matching_orders)}")
    print(f"Órdenes encontradas en Odoo y en ML (crawl DB): {len(matching_orders)}")

    return matching_orders


if __name__ == "__main__":
    logging.info("///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////")


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

