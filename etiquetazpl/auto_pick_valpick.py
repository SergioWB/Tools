import json
import time
import xmlrpc.client
import requests

config_file = 'config_dev2.json'
config_file_name = rf'C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\wb_odoo_external_api\config\{config_file}'

print(config_file_name)

def get_odoo_access():
    with open(config_file_name, 'r') as config_file:
        config = json.load(config_file)
    return config['odoo']


# Obtener credenciales
odoo_keys = get_odoo_access()

# odoo
server_url = odoo_keys['odoourl']
db_name = odoo_keys['odoodb']
username = odoo_keys['odoouser']
password = odoo_keys['odoopassword']

json_endpoint = "%s/jsonrpc" % server_url
headers = {"Content-Type": "application/json"}
user_id = 2

print('----------------------------------------------------------------')
print('Conectando API Odoo')
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(server_url))
uid = common.authenticate(db_name, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(server_url))
print('Conexión con Odoo establecida')
print('----------------------------------------------------------------')

def get_json_payload(service, method, *args):
	return json.dumps({
	"jsonrpc": "2.0",
	"method": 'call',
	"params": {
	"service": service,
	"method": method,
	"args": args
	},
	"id": 162,
	})
def search_valpick_id(so_name, type='VALPICK'): #/VALPICK/  /PICK/
    try:
        payload = get_json_payload("common", "version")
        response = requests.post(json_endpoint, data=payload, headers=headers)

        if so_name:
            search_domain = [['origin', '=', so_name], ['name', 'like', type]]
            payload = json.dumps({"jsonrpc": "2.0", "method": "call",
                                  "params": {"service": "object", "method": "execute",
                                             "args": [db_name, user_id, password, "stock.picking", "search_read",
                                                      search_domain, ['id', 'name', 'state']]}})

            res = requests.post(json_endpoint, data=payload, headers=headers).json()
            id_valpick = res['result'][0]['id']
            return id_valpick
        else:
            print("Error: No se encontro orden de venta")
            return False
    except Exception as e:
        print('Error:' + str(e))
        return False


def set_pick_done(so_name, type="/VALPICK/", tried_pick=False):
    try:
        # Buscar el ID del picking (VALPICK o PICK dependiendo del tipo pasado)
        transfer_id = search_valpick_id(so_name, type)

        # Si no se encuentra el picking, retorna False
        if not transfer_id:
            print(f"No se encontró un picking para el tipo: {type}")
            return False
        else:
            payload_check_state = json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute",
                    "args": [db_name, user_id, password, "stock.picking", "read", [transfer_id], ["id", "state"]]
                }
            })
            response_check_state = requests.post(json_endpoint, data=payload_check_state, headers=headers).json()
            picking_state = response_check_state.get('result', [{}])[0].get('state', '')


        # Definir los payloads para las acciones
        payload_set_quantities = json.dumps({
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute",
                "args": [db_name, user_id, password, "stock.picking", "action_set_quantities_to_reservation",
                         [transfer_id]]
            }
        })

        payload_validate = json.dumps({
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute",
                "args": [db_name, user_id, password, "stock.picking", "button_validate", [transfer_id]]
            }
        })

        # Primero se setean las cantidades si es que aún no se ha hecho.
        requests.post(json_endpoint, data=payload_set_quantities, headers=headers).json()
        # Si hay respuesta
        if picking_state != 'done':
            # Intentar validar el transfer (Pick o Valpick)
            response_validate = requests.post(json_endpoint, data=payload_validate, headers=headers).json()
            if response_validate.get('result'):
                print(f"{type}: {transfer_id} ha sido validado y ahora está en estado 'done'.")
                return True
            else:
                print(f"{type}: {transfer_id}: aun no está validado")
                # Si no se ha intentado aún con "/PICK/", hacerlo ahora
                if not tried_pick:
                    print("Intentando validar el PICK en lugar del VALPICK.")
                    pick_validated = set_pick_done(so_name, "/PICK/", tried_pick=True)

                    # Si el PICK se valida correctamente, intentamos nuevamente validar el VALPICK
                    if pick_validated:
                        print("PICK validado correctamente. Reintentando validar el VALPICK.")
                        return set_pick_done(so_name, "/VALPICK/", tried_pick=True)  # Intentar nuevamente con VALPICK
                else:
                    print("Ya se intentó con /PICK/, deteniendo recursión.")
                    return False
        else:
            print(f"{type}: {transfer_id} ya está hecho")
            return False

    except Exception as e:
        print(f"Error al cambiar el estado a done: {str(e)}")
        return False


# # Uso del método para cambiar el estado a 'done'
# id_valpick = search_valpick_id("SO3212523") #SO3212503  #ML SO3212505
# print(id_valpick)
# #id_pick = 2498068 ; id_valpick = 2498069
# set_pick_done(id_valpick)

# Uso del método para cambiar el estado a 'done'

#id_pick = 2498068 ; id_valpick = 2498069
set_pick_done("SO3212529")

