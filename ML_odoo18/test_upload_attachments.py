import os
import sys
import base64
import time as tm
import logging

import upload_ml_attachments_DB_day_orders as uploader


# =============================================================================
# FUNCIONES "DUMMY" DE MERCADO LIBRE
# =============================================================================
def mock_recupera_meli_token(user_id, local):
    print(f"👉 [TEST ML API] Simulando recuperación de token para user: {user_id}")
    return "TEST_DUMMY_TOKEN_123456"


def mock_get_order_meli(order_id, access_token):
    print(f"👉 [TEST ML API] Simulando info de orden ML para ID: {order_id}")
    return {
        'shipping_id': f"SHIP_{order_id}",
        'seller_id': 123456789,
        'status': 'paid'
    }


def mock_get_zpl_meli(shipment_ids, so_name, access_token):
    print(f"👉 [TEST ML API] Simulando descarga de ZPL para SO: {so_name}")

    folder_path = f"{uploader.labels_path}/Etiqueta_{so_name}"
    os.makedirs(folder_path, exist_ok=True)
    file_path = f"{folder_path}/Etiqueta de envio.txt"

    dummy_zpl_content = f"^XA^FO50,50^ADN,36,20^FDGuia DUMMY de prueba para {so_name}^FS^XZ"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(dummy_zpl_content)

    dummy_base64 = base64.b64encode(dummy_zpl_content.encode('utf-8')).decode('utf-8')

    return {
        'ml_api_message': 'éxito (ZPL Generado en modo de pruebas)',
        'zpl_response': dummy_base64
    }


# =============================================================================
# FUNCIONES "DUMMY" DE BASE DE DATOS (Para no ensuciar tu MySQL)
# =============================================================================
def mock_save_log_db(*args, **kwargs):
    status = kwargs.get('status', 'unknown')
    print(f"👉 [TEST MYSQL] Simulando guardado en DB (ml_guide_insertion). Status: {status}")


def mock_update_latest_date_json(new_date_str):
    print(f"👉 [TEST JSON] Simulando actualización de fecha: {new_date_str}")
    return new_date_str


# =============================================================================
# INTERCEPTAMOS (MONKEY PATCH) LAS FUNCIONES EN TU MÓDULO
# =============================================================================
uploader.recupera_meli_token = mock_recupera_meli_token
uploader.get_order_meli = mock_get_order_meli
uploader.get_zpl_meli = mock_get_zpl_meli
uploader.save_log_db = mock_save_log_db
uploader.update_latest_date_json = mock_update_latest_date_json

# =============================================================================
# EJECUCIÓN DEL FLUJO PRINCIPAL
# =============================================================================
if __name__ == "__main__":

    # ---------------------------------------------------------
    # VALIDACIÓN DE ARGUMENTOS POR CONSOLA
    # ---------------------------------------------------------
    if len(sys.argv) < 2:
        print("\n❌ ERROR: Falta el nombre de la orden.")
        print("💡 Uso correcto: python3 test_upload_attachments.py <NOMBRE_DE_LA_ORDEN>")
        print("📝 Ejemplo:      python3 test_upload_attachments.py SO123456\n")
        sys.exit(1)

    NOMBRE_SO_PRUEBA = sys.argv[1].strip()

    print("\n" + "=" * 70)
    print("INICIANDO MODO TEST (Odoo Real, ML Simulado, MySQL Simulado)")
    print("=" * 70)

    start = tm.time()

    from dotenv import load_dotenv

    load_dotenv()

    # ---------------------------------------------------------
    # CONFIGURACIÓN SEGURA PARA PRUEBAS
    # ---------------------------------------------------------
    enviroment = 'test_18'
    uploader.get_odoo_model(enviroment)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    uploader.labels_path = os.path.join(current_dir, "Etiquetas_Test")

    try:
        print(f"\nBuscando la orden '{NOMBRE_SO_PRUEBA}' directamente en Odoo...")
        # Le pedimos a Odoo explícitamente solo esta orden
        test_orders = uploader.models.execute_kw(
            uploader.ODOO_DB_NAME, uploader.uid, uploader.ODOO_PASSWORD,
            'sale.order', 'search_read',
            [[['name', '=', NOMBRE_SO_PRUEBA]]],
            {'fields': ['channel_order_reference', 'yuju_pack_id', 'id', 'name', 'yuju_seller_id', 'create_date',
                        'date_order', 'yuju_carrier_tracking_ref', 'write_date']}
        )

        if test_orders:
            orden_odoo = test_orders[0]
            print(f"✅ Orden encontrada en Odoo con ID: {orden_odoo['id']}")

            # "Inyectamos" los datos que normalmente pondría el Inner Join con las tablas de MySQL
            orden_odoo['status_name'] = 'Envíos de hoy'
            orden_odoo['card_name'] = 'Hoy'

            # Completamos datos para que no truene el código si la orden de test está medio vacía
            if not orden_odoo.get('channel_order_reference'):
                orden_odoo['channel_order_reference'] = 'TEST_CHANNEL_REF_123'
            if not orden_odoo.get('yuju_seller_id'):
                orden_odoo['yuju_seller_id'] = '160190870'  # Un seller válido para el diccionario de tokens
            if not orden_odoo.get('yuju_carrier_tracking_ref'):
                orden_odoo['yuju_carrier_tracking_ref'] = 'Colecta'  # Forzamos que entre a la lógica de Colecta

            print("\nIniciando proceso de insersión de Guía y Mensaje en la Orden...")
            # Invocamos DIRECTAMENTE la función de nuevas órdenes pasando nuestra lista de 1 elemento
            uploader.procces_new_orders([orden_odoo], local=True)

        else:
            print(f"❌ No se encontró la orden '{NOMBRE_SO_PRUEBA}'. Revisa que el nombre sea exacto.")

    except Exception as e:
        logging.error(f"Error durante el test: {e}")
        print(f"❌ Error: {e}")

    end = tm.time()
    print("\n" + "=" * 70)
    print(f"TEST FINALIZADO CON ÉXITO. Tiempo: {round(end - start, 2)} [s]")
    print(f"Revisa Odoo para ver si el adjunto y el chatter están bien en la orden '{NOMBRE_SO_PRUEBA}'.")
    print("=" * 70)