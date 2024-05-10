from flask import Flask, render_template, request, make_response, url_for, session 
import json
import requests
from pprint import pprint
import logging
import zipfile
import socket
import os 
from datetime import datetime
logging.basicConfig(format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%Y-%d-%m %I:%M:%S %p',level=logging.INFO)

dir_path = os.path.dirname(os.path.realpath(__file__))

server_url  ='https://somosreyes.odoo.com'
db_name = 'xmarts-somosreyes-somosreyes-250093'
#server_url = 'https://somosreyes-test-862115.dev.odoo.com'
#db_name = 'somosreyes-test-862115'
username = 'moises.santiago@somos-reyes.com'
password = 'ttgo702'
json_endpoint = "%s/jsonrpc" % server_url

headers = {"Content-Type": "application/json"}


def get_json_payload(service, method, *args):
	return json.dumps({
	"jsonrpc": "2.0",
	"method": 'call',
	"params": {
	"service": service,
	"method": method,
	"args": args
	},
	"id": 6,
	})


def get_user_id():
	try:
		payload = get_json_payload("common", "login", db_name, username, password)
		response = requests.post(json_endpoint, data=payload, headers=headers)

		user_id = response.json()['result']
		if user_id:
			logging.info("Success: User id is: "+str(user_id))
			return user_id
		else:
			logging.error("Failed: wrong credentials")
			return False
	except Exception as e:
		logging.error("Error: get_user_id()| "+str(e))
		return False


user_id = 6
def get_order_id(name):
	try:
		payload = get_json_payload("common", "version")
		response = requests.post(json_endpoint, data=payload, headers=headers)

		if user_id:
			search_domain = [['name', '=', name]]
			payload = get_json_payload("object", "execute_kw",db_name, user_id, password,'sale.order', 'search_read', [search_domain, ['marketplace_order_id', 'name', 'seller_marketplace']],
			{'limit': 1})
			res = requests.post(json_endpoint, data=payload, headers=headers).json()
			#logging.info(default_code+str(res))
			#print (res)
			marketplace_order_id = res['result'][0]['marketplace_order_id']
			seller_marketplace = res['result'][0]['seller_marketplace']
			order_odoo_id = res['result'][0]['id']

			return dict(marketplace_order_id = marketplace_order_id, seller_marketplace =seller_marketplace, order_odoo_id = order_odoo_id )
		else:
			logging.error("Failed: wrong credentials")	
			return False
	except Exception as e:
		logging.error ('Error:'+str(e))
		return False

def update_imprimio_etiqueta_meli(order_odoo_id):
	try:
		write_data = {'imprimio_etiqueta_meli': True}
		payload = get_json_payload("object", "execute_kw", db_name, user_id, password, 'sale.order', 'write', [order_odoo_id, write_data])
		res = requests.post(json_endpoint, data=payload, headers=headers).json()
		return True
	except Exception as e:
		print("Error: update_imprimio_etiqueta_meli()| "+str(e))
		return False

def get_picking_id(so_name):
	try:
		payload = get_json_payload("common", "version")
		response = requests.post(json_endpoint, data=payload, headers=headers)

		if user_id:
			search_domain = [['origin', '=', so_name], ['name', 'like', 'WH/PICK']]
			payload = get_json_payload("object", "execute_kw",db_name, user_id, password,'stock.picking', 'search_read', [search_domain, ['name','origin','imprimio_etiqueta_meli']],
			{'limit': 1})
			res = requests.post(json_endpoint, data=payload, headers=headers).json()
			#logging.info(default_code+str(res))
			print (res)
			
			name_picking = res['result'][0]['name']
			picking_id = res['result'][0]['id']
			return dict( name_picking = name_picking, picking_id = picking_id)
		else:
			logging.error("Failed: wrong credentials")	
			return False
	except Exception as e:
		logging.error ('Error:'+str(e))
		return False

def update_imprimio_etiqueta_meli_picking(picking_id):
	try:
		write_data = {'imprimio_etiqueta_meli': True}
		payload = get_json_payload("object", "execute_kw", db_name, user_id, password, 'stock.picking', 'write', [picking_id, write_data])
		res = requests.post(json_endpoint, data=payload, headers=headers).json()
		return True

	except Exception as e:
		print("Error: update_imprimio_etiqueta_meli()| "+str(e))
		return False

def ubicacion_impresoras():
	archivo_comfiguracion = dir_path + '/config.json'
	print (archivo_comfiguracion)
	with open(archivo_comfiguracion, 'r') as file:
		config = json.load(file)

	print (config)

	EMPACADO = config['EMPACADO']
	print('EMPACADO',EMPACADO)
	PICKING = config['PICKING']
	print ('PICKING',PICKING)

	return config


def imprime_zpl(so_name, ubicacion, order_odoo_id):
	etiqueta_imprimir = dir_path + '/Etiquetas/Etiqueta_'+so_name+'/Etiqueta de envio.txt'
	zpl_meli = open (etiqueta_imprimir) 
	zpl = zpl_meli.read()

	mysocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)         

	print ('Ubicacion de la impresora: ', ubicacion)

	ubicaciones = ubicacion_impresoras()
	
	host = ubicaciones.get(ubicacion)

	print ('IP de la Impresora:', host)
	port = 9100   
	respuesta_imprime_zpl = ''

	try:

		datos=bytes(zpl, 'utf-8')
		print (datos)

		mysocket.connect((host, port)) #connecting to host
		mysocket.send(datos)#using bytes

		mysocket.close () #closing connection
		print ('Etiqueta para la orden ' +so_name+' se ha impreso con exito')
		resultado = update_imprimio_etiqueta_meli(order_odoo_id)
		picking = get_picking_id(so_name)
		picking_id = picking.get('picking_id')
		resultado_pick = update_imprimio_etiqueta_meli_picking(picking_id)
		
		if resultado:
			respuesta_imprime_zpl += '|Etiqueta para la orden ' +so_name+' se ha impreso con exito'
		else:
			respuesta_imprime_zpl +=  '|No se marco la impresión de la Guía para ' +so_name

		if resultado_pick:
			respuesta_imprime_zpl +=  '|Se marco impresión de Etiqueta para el Picking de la orden: ' +so_name+' con exito'
		else:
			respuesta_imprime_zpl += '|No Se marco impresión de Etiqueta para el Picking de la orden:: ' +so_name

		return respuesta_imprime_zpl
	except Exception as e:
		print(" Error en la conexión con la impresora ZPL "+str(e))
		return "|Error en la conexión con la impresora ZPL: "+str(e)
		

def recupera_meli_token(user_id):
	try:
		#print 'USER ID:', user_id
		token_dir=''
		if user_id == 25523702:# Usuario de SOMOS REYES VENTAS
			token_dir='/home/leon/meli/tokens_meli.txt' 
		elif user_id == 160190870:# Usuario de SOMOS REYES OFICIALES
			token_dir='/home/leon/meli/tokens_meli_oficiales.txt'
		#print token_dir

		archivo_tokens=open(token_dir, 'r')
		#print 'archivo_tokens', archivo_tokens
		tokens=archivo_tokens.read()
		#print 'tokens',tokens
		tokens_meli = json.loads(tokens)
		#print (tokens_meli)
		archivo_tokens.close()
		access_token=tokens_meli['access_token']
		#print access_token
		return access_token	
	except Exception as e:
		print ('Error recupera_meli_token() : '+str(e) )
		return False

def get_zpl_meli(shipment_ids,so_name, access_token, ubicacion, order_odoo_id):
	try:

		#headers = {'Accept': 'application/json','content-type': 'application/json'}
		url='https://api.mercadolibre.com/shipment_labels?shipment_ids='+str(shipment_ids)+'&response_type=zpl2&access_token='+access_token
		print (url)
		r=requests.get(url)
		#print (r.text)
		open('Etiqueta.zip', 'wb').write(r.content)
		respuesta =''
		resultado = ''
		if shipment_ids:
			try:
				with zipfile.ZipFile("Etiqueta.zip","r") as zip_ref:
					zip_ref.extractall("Etiquetas/Etiqueta_"+so_name)
					respuesta += 'Se proceso el archivo ZPL de la Orden: '+so_name+' con éxito'
				resultado = imprime_zpl(so_name, ubicacion, order_odoo_id)
			except Exception as e:
				respuesta += '|Error al extraer el archivo zpl: '+str(e) 
			finally:
				respuesta +='|Finalizó el intento de extraccion'+resultado
		#print (json.dumps(r.json(), indent=4, sort_keys=True))
		return respuesta
	except Exception as e:
		respuesta += '|Error get_zpl_meli: '+ str(e)
		return respuesta


def get_order_meli(order_id, access_token):
	try:
		headers = {'Accept': 'application/json','content-type': 'application/json'}
		url='https://api.mercadolibre.com/orders/'+order_id+'?access_token='+access_token
		print (url)
		r=requests.get(url)
		shipping_id = r.json()['shipping']['id']
		seller_id =  r.json()['seller']['id'] 
		#print (json.dumps(r.json(), indent=4, sort_keys=True))
		#----RECUPERA TAMBIEN EL ID DEL SELLER
		print(shipping_id, seller_id)
		return dict(shipping_id = shipping_id, seller_id =seller_id)
	except Exception as e:
		print (' Error get_order_meli: '+ str(e))
		return False


app = Flask(__name__)
app.secret_key = 'esto-es-una-clave-muy-secreta'

@app.route('/')
def index():
	# Permite insertar el nombre de la localización de la impreslora dentro de SOMOS REYES
	return render_template("index.html" )

@app.route('/inicio', methods =['POST'])
def inicio():
	localizacion = request.form.get("localizacion")
	session['ubicacion'] = localizacion
	ubicacion = session['ubicacion']
	return render_template("formulario.html", ubicacion=ubicacion )

@app.route('/procesar', methods=['POST'])
def procesar():
	ubicacion = session['ubicacion']
	e=None
	try:

		name_so = request.form.get("name_so")
		#SO192732
		order_odoo =get_order_id(name_so)
		order_id = order_odoo.get('marketplace_order_id')
		seller_marketplace = order_odoo.get('seller_marketplace')
		order_odoo_id = order_odoo.get('order_odoo_id')

		print ('ODOO:', order_id, seller_marketplace)
		if ':' in order_id:
			solo_orden = order_id.split(':')
			order_id=solo_orden[1]
		
		if  seller_marketplace == 'SOMOS-REYES OFICIALES':
			user_id = 160190870
		else:
			user_id = 25523702
		
		access_token = recupera_meli_token(user_id)

		order_meli = get_order_meli(order_id, access_token)
		
		shipment_ids = order_meli.get('shipping_id')
		seller_id = order_meli.get('seller_id')

		respuesta = get_zpl_meli(shipment_ids,name_so, access_token, ubicacion, order_odoo_id)
		formulario = 'mostrar.html'
	except Exception as e:
		order_id = ''
		respuesta = str(e)
		formulario = 'error.html'
		

	return render_template(formulario, name_so=name_so, order_id = order_id, respuesta = respuesta)


if __name__ == "__main__":

	app.run(host='0.0.0.0', port=8000, debug=True)