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
def search_valpick_id(so_name, type): #/VALPICK/  /PICK/
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
            print(res['result'])
            return id_valpick
        else:
            print("Error: No se encontro orden de venta")
            return False
    except Exception as e:
        print('Error:' + str(e))
        return False

def set_pick_done(valpick_id):
    try:
        payload_set_quantities = json.dumps({
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute",
                "args": [db_name, user_id, password, "stock.picking", "action_set_quantities_to_reservation", [valpick_id]]
            }
        })

        payload_validate = json.dumps({
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute",
                "args": [db_name, user_id, password, "stock.picking", "button_validate", [valpick_id]]
            }
        })

        # Primero se setea las cantidades si es que un no se ha hecho.
        response_set_quantities = requests.post(json_endpoint, data=payload_set_quantities, headers=headers).json()
        print(response_set_quantities, '***********')
        if response_set_quantities:
            # Se valida el valpick
            response_validate = requests.post(json_endpoint, data=payload_validate, headers=headers).json()
            if response_validate.get('result'):
                print(f"Picking {valpick_id} ha sido validado (Valpick) y ahora está en estado 'done'.")
            else:
                print(f"Error al validar el picking {valpick_id}: {response_validate.get('error')}")
        else:
            print(f"Error al setear las cantidades en {valpick_id}: {response_set_quantities.get('error')}")
    except Exception as e:
        print(f"Error al cambiar el estado a done: {str(e)}")

# Uso del método para cambiar el estado a 'done'
id_valpick = search_valpick_id("SO3212512") #SO3212503  #ML SO3212505
print(id_valpick)
#id_pick = 2498068 ; id_valpick = 2498069
set_pick_done(id_valpick)


