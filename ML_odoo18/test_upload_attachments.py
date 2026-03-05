import os
import base64
import time as tm
import logging

import upload_ml_attachments_DB_day_orders as uploader


# =============================================================================
# FUNCIONES "DUMMY"
# =============================================================================

def mock_recupera_meli_token(user_id, local):
    """ Finge recuperar un token exitosamente """
    print(f"👉 [TEST ML API] Simulando recuperación de token para user: {user_id}")
    return "TEST_DUMMY_TOKEN_123456"


def mock_get_order_meli(order_id, access_token):
    """ Finge consultar la orden en Mercado Libre """
    print(f"👉 [TEST ML API] Simulando info de orden ML para ID: {order_id}")
    return {
        'shipping_id': f"SHIP_{order_id}",
        'seller_id': 123456789,
        'status': 'paid'  # Ponemos 'paid' para que no caiga en la validación de 'cancelled' o 'delivered'
    }


def mock_get_zpl_meli(shipment_ids, so_name, access_token):
    """
    Finge descargar el ZPL. En lugar de descargar el zip, crea el archivo
    de texto con un contenido ZPL básico en la ruta donde tu código lo va a buscar.
    """
    print(f"👉 [TEST ML API] Simulando descarga de ZPL para SO: {so_name}")

    #Creamos las carpetas tal como las espera tu script original
    folder_path = f"{uploader.labels_path}/Etiqueta_{so_name}"
    os.makedirs(folder_path, exist_ok=True)
    file_path = f"{folder_path}/Etiqueta de envio.txt"

    #Creamos un ZPL de prueba muy simple
    dummy_zpl_content = f"^XA^FO50,50^ADN,36,20^FDGuia DUMMY de prueba para {so_name}^FS^XZ"

    #Escribimos el archivo físicamente para que upload_attachment lo encuentre
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(dummy_zpl_content)

    # Lo codificamos a base64 tal como lo devolvería tu script original
    dummy_base64 = base64.b64encode(dummy_zpl_content.encode('utf-8')).decode('utf-8')

    # Retornamos el diccionario simulando un éxito.
    return {
        'ml_api_message': 'éxito (ZPL Generado en modo de pruebas)',
        'zpl_response': dummy_base64
    }


# =============================================================================
# INTERCEPTAMOS (MONKEY PATCH) LAS FUNCIONES EN TU MÓDULO
# =============================================================================
uploader.recupera_meli_token = mock_recupera_meli_token
uploader.get_order_meli = mock_get_order_meli
uploader.get_zpl_meli = mock_get_zpl_meli

# =============================================================================
# EJECUCIÓN DEL FLUJO PRINCIPAL
# =============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("INICIANDO MODO TEST (Sin conexión real a Mercado Libre API)")
    print("=" * 70)

    start = tm.time()

    # Cargar variables de entorno
    from dotenv import load_dotenv

    load_dotenv()

    # ---------------------------------------------------------
    # CONFIGURACIÓN SEGURA PARA PRUEBAS
    # ---------------------------------------------------------
    # Aseguramos usar base de datos de test de Odoo 18
    enviroment = 'test_18'
    uploader.get_odoo_model(enviroment)

    # Cambiamos la ruta de las etiquetas a una carpeta temporal
    current_dir = os.path.dirname(os.path.abspath(__file__))
    uploader.labels_path = os.path.join(current_dir, "Etiquetas_Test")
    # ---------------------------------------------------------

    try:
        #Ejecutar el flujo completo:
        #Odoo y la DB se actualizarán REALMENTE, pero el ZPL será el dummy.
        uploader.process_orders(local=True)
    except Exception as e:
        logging.error(f"Error durante el test: {e}")
        print(f"❌ Error: {e}")

    end = tm.time()
    print("\n" + "=" * 70)
    print(f"TEST FINALIZADO CON ÉXITO. Tiempo: {round(end - start, 2)} [s]")
    print(f"Revisa la carpeta local '{uploader.labels_path}' para ver los TXTs creados.")
    print("=" * 70)
