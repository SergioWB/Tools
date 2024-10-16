import base64
import requests
from requests.auth import HTTPBasicAuth
import json

def get_api_key():
    with open('credentials.json') as f:
        data = json.load(f)
        return data.get("API_KEY")

def printnode_whoami(api_key):
    response = requests.get(
        "https://api.printnode.com/whoami",
        auth=(api_key, '')  # Autenticación básica (API Key como usuario)
    )

    # Verificar la respuesta y mostrar la información de la cuenta
    if response.status_code == 200:
        print("Autenticación exitosa. Datos de la cuenta:")
        print(response.json())  # Mostrar los datos de la cuenta
    else:
        print(f"Error en la autenticación: {response.status_code} - {response.text}")


def get_printers(api_url, api_key):
    # URL del endpoint para obtener las impresoras
    url = f"{api_url}/printers"

    # Realizamos la solicitud GET al endpoint usando HTTPBasicAuth
    try:
        response = requests.get(url, auth=HTTPBasicAuth(api_key, ''))

        # Verificamos si la solicitud fue exitosa
        if response.status_code == 200:
            printers = response.json()
            return printers
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error al realizar la solicitud: {e}")
        return None


dict_printers_id = {
    'Termica 1 Honeywell' : 73334068,
    'Termica 2 Honeywell' : 73334069,
    'Termica 3 Honeywell' : 73313368,
    'Termica 4 Honeywell' : 73313369,
    'Termica 5 Honeywell' : 73312424
}

def print_zpl(api_key, printer_id, zpl_file_path, title="Test Print Job"):
    try:
        # Leer el archivo ZPL y codificarlo en base64
        with open(zpl_file_path, 'rb') as zpl_file:
            zpl_content = zpl_file.read()

        zpl_base64 = base64.b64encode(zpl_content).decode('utf-8')  # Codificar en base64

        # Crear el payload con la información del trabajo de impresión
        payload = {
            "printerId": printer_id,
            "title": title,
            "contentType": "raw_base64",  # Usar raw_base64 para enviar contenido codificado
            "content": zpl_base64,  # El contenido codificado en base64
            "source": "Local File Example"  # Descripción del origen
        }

        # Realizar la solicitud POST para enviar el trabajo de impresión
        url = "https://api.printnode.com/printjobs"
        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, auth=HTTPBasicAuth(api_key, ''), headers=headers)

        # Imprimir detalles del estado de la respuesta
        print(f"Estado HTTP: {response.status_code}")
        print(f"Contenido de la respuesta: {response.text}")

        # Verificar si la respuesta es exitosa y procesar los datos
        if response.status_code == 201:
            response_data = response.json()
            print(f"Trabajo de impresión enviado correctamente. ID del trabajo: {response_data}")
        else:
            print(f"Error al enviar el trabajo de impresión: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Error: {e}")



if __name__ == '__main__':

    # printnode_whoami(api_key)

    # printers = get_printers(base_api_url, api_key)
    # if printers:
    #     print("Impresoras disponibles:")
    #     for printer in printers:
    #         print(f"- {printer['name']} (ID: {printer['id']})")

    api_key = get_api_key()
    base_api_url = 'https://api.printnode.com'
    file_print = r'C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\Tools\etiquetazpl\Etiquetas\test.txt'
    printer_id = dict_printers_id.get('Termica 3 Honeywell')

    print(printer_id)
    print_zpl(api_key,printer_id, file_print)