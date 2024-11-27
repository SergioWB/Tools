import requests
import json


def get_api_key():
    with open(r'C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\Tools\etiquetazpl\credentials.json') as f:
        data = json.load(f)
        return data.get("API_KEY")


# Coloca tu API Key de PrintNode aquí
API_KEY = get_api_key()
BASE_URL = 'https://api.printnode.com'

# Autenticación con PrintNode
auth = (API_KEY, '')

def obtener_jobs():
    # Solicita la lista de trabajos de impresión
    response = requests.get(f'{BASE_URL}/printjobs', auth=auth)
    if response.status_code == 200:
        jobs_data = response.json()
        # Extrae solo los id y state de cada trabajo
        job_info = [{"id": job["id"], "state": job["state"]} for job in jobs_data]
        return job_info
    else:
        print(f'Error al obtener trabajos: {response.status_code}')
        return []

def cancelar_job(job_id):
    # Cancela un trabajo de impresión
    response = requests.delete(f'{BASE_URL}/printjobs/{job_id}', auth=auth)
    print(response)
    if response.status_code == 200:
        print(f'Trabajo {job_id} cancelado con éxito.')
    else:
        print(f'Error al cancelar trabajo {job_id}: {response.status_code}')


def cancelar_jobs_masivos():
    # Obtiene todos los trabajos de impresión
    jobs = obtener_jobs()

    # Itera sobre los trabajos y cancela solo los que están en estado "sent_to_client"
    for job in jobs:
        job_id = job['id']
        job_state = job.get('state')

        # Cancela solo si el estado es "sent_to_client"
        if job_state: # == "sent_to_client":
            response = requests.delete(f'{BASE_URL}/printjobs/{job_id}', auth=auth)
            if response.status_code == 200:
                print(f'Trabajo {job_id} cancelado con éxito.')
            else:
                print(f'Error al cancelar trabajo {job_id}: {response.status_code}')

def obtener_info_job(job_id):
    # Solicita la información de un solo trabajo de impresión
    response = requests.get(f'{BASE_URL}/printjobs/{job_id}', auth=auth)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error al obtener información del trabajo {job_id}: {response.status_code}')
        return None


# Ejecuta la cancelación masiva
# cancelar_jobs_masivos()
print(obtener_jobs())
cancelar_jobs_masivos()

print(obtener_info_job(5535708418))
# cancelar_job(5535741766)