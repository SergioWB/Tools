from flask import Flask, render_template, request, make_response, url_for, session 
import json
import jsonrpc
import jsonrpclib
import random
import urllib.request
import getpass
import http
import requests
from pprint import pprint
import logging
import zipfile
import socket
import os 
from datetime import datetime, timedelta
import time
import tokens_meli as tk_meli


logging.basicConfig(format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%Y-%d-%m %I:%M:%S %p',level=logging.INFO)

logging.info('\n')

dir_path = os.path.dirname(os.path.realpath(__file__))

server_url  = 'http://ec2-184-72-194-239.compute-1.amazonaws.com'
db_name = 'somosreyes15'
#server_url  ='https://wonderbrands.odoo.com'
#db_name = 'wonderbrands-main-4539884'
#username = 'will@wonderbrands.co'
#password = 'admin123'
json_endpoint = "%s/jsonrpc" % server_url

logging.warning("TEST DATABSE")

headers = {"Content-Type": "application/json"}

######### TIME DECORATOR #############
def measure_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()  # Tiempo inicial
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time  # Tiempo final
        logging.info(f"\nFUNCIÓN '{func.__name__}' TOMÓ {elapsed_time:.4f} [seg].\n")
        return result
    return wrapper

########## NEW FUNCTIONS #############
def get_password_user(usuario):
    with open('credentials.json') as f:
        data = json.load(f)
        for usuario_data in data:
            if usuario_data["USUARIO"] == usuario:
                return usuario_data["ID_ODOO"], usuario_data["USUARIO"], usuario_data["CONTRASEÑA"]
    return None

def search_valpick_id(so_name):
	try:
		payload = get_json_payload("common", "version")
		response = requests.post(json_endpoint, data=payload, headers=headers)

		if so_name:
			search_domain = [['origin', '=', so_name], ['name', 'like', '/VALPICK/']]
			payload = json.dumps({"jsonrpc": "2.0", "method": "call", "params": {"service": "object", "method": "execute", "args": [db_name, user_id, password, "stock.picking", "search_read",
									search_domain, ['id', 'name']]}})

			res = requests.post(json_endpoint, data=payload, headers=headers).json()
			#logging.info(default_code+str(res))
			#print (res)
			
			id_valpick = res['result'][0]['id']

			return id_valpick
		else:
			logging.error("Error: No se encontro orden de venta")
			return False
	except Exception as e:
		logging.error ('Error:'+str(e))
		return False

def ejecute_fedex_label(valpick_id):
	try:
		payload = get_json_payload("common", "version")
		response = requests.post(json_endpoint, data=payload, headers=headers)

		if valpick_id:

			search_domain = [['id', '=', valpick_id]]
			shipping_label_status = json.dumps({"jsonrpc": "2.0", "method": "call", "params": {"service": "object", "method": "execute", "args": [db_name, user_id, password, "stock.picking", "search_read",
									search_domain, ['shplbl_printed', 'shplbl_print_date']]}})

			res = requests.post(json_endpoint, data=shipping_label_status, headers=headers).json()

			state = res['result'][0]['shplbl_printed']
			shplbl_print_date = res['result'][0]['shplbl_print_date']

			if state == False: # Se coloca el status False debido a que aun se puede imprimir, si es True, es porque ya no se debe olver a imprimir.
				print_shipping_label = json.dumps({"jsonrpc": "2.0", "method": "call", "params": {"service": "object", "method": "execute", "args": [db_name, user_id, password, "stock.picking", 'print_last_shipping_label', [valpick_id]]}})

				res = requests.post(json_endpoint, data=print_shipping_label, headers=headers).json()
				return res
				#logging.info(f'RESPONSE DE EJEUTE {res}')
			else:
				logging.error("Error: La etiqueta ya fue impresa")
				return dict(state=True, shplbl_print_date=shplbl_print_date)
		else:
			logging.error("Error: No se encontro el id del valpick")
			return False
	except Exception as e:
		logging.error ('Error:'+str(e))
		return False

def get_label_case(filename, marketplace, carrier):
	# Cargar los datos del archivo JSON
    with open(filename, 'r') as file:
        data = json.load(file)
    
    # Buscar el valor en los datos
    if marketplace in data and carrier in data[marketplace]:
        return data[marketplace][carrier]
    else:
        return None

######################################

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

# HARDCODE 
#user_id = 162


def get_order_id(name):
	try:
		payload = get_json_payload("common", "version")
		response = requests.post(json_endpoint, data=payload, headers=headers)

		if user_id:
			search_domain = [['name', '=', name]]
			payload = json.dumps({"jsonrpc": "2.0", "method": "call", "params": {"service": "object", "method": "execute", "args": [db_name, user_id, password, "sale.order", "search_read",
									search_domain, ['channel_order_reference', 'name', 'yuju_seller_id', 'yuju_carrier_tracking_ref', 'team_id']]}})
			res = requests.post(json_endpoint, data=payload, headers=headers).json()
			#logging.info(default_code+str(res))
			#print (res)
			marketplace_order_id = res['result'][0]['channel_order_reference']
			print('channel_order_reference', marketplace_order_id)
			seller_marketplace = res['result'][0]['yuju_seller_id']
			order_odoo_id = res['result'][0]['id']
			guide_number = res['result'][0]['yuju_carrier_tracking_ref']
			team_id = res['result'][0]['team_id'][1] # La repuesta es [id, team]

			return dict(marketplace_order_id = marketplace_order_id, seller_marketplace =seller_marketplace, order_odoo_id = order_odoo_id, guide_number=guide_number, team_id=team_id)
		else:
			logging.error("Error: No se tiene un id de usuario, revisa el listado de usuarios")
			return False
	except Exception as e:
		logging.error ('Error:'+str(e))
		return False

@measure_time
def update_imprimio_etiqueta_meli(order_odoo_id):
	try:
		write_data = {'imprimio_etiqueta_meli': True}
		payload = get_json_payload("object", "execute_kw", db_name, user_id, password, 'sale.order', 'write', [order_odoo_id, write_data])
		res = requests.post(json_endpoint, data=payload, headers=headers).json()
		return True
	except Exception as e:
		print("Error: update_imprimio_etiqueta_meli()| "+str(e))
		return False

@measure_time
def get_picking_id(so_name):
	try:
		payload = get_json_payload("common", "version")
		response = requests.post(json_endpoint, data=payload, headers=headers)

		if user_id:
			search_domain = [['origin', '=', so_name], ['name', 'like', 'AG/PICK']]
			payload = get_json_payload("object", "execute_kw",db_name, user_id, password,'stock.picking', 'search_read', [search_domain, ['name','origin','imprimio_etiqueta_meli']],
			{'limit': 1})
			res = requests.post(json_endpoint, data=payload, headers=headers).json()
			#logging.info(default_code+str(res))
			logging.info(f'Respuesta en get_picking_id: {res}')
			
			name_picking = res['result'][0]['name']
			picking_id = res['result'][0]['id']
			return dict( name_picking = name_picking, picking_id = picking_id)
		else:
			logging.error("Failed: wrong credentials")	
			return False
	except Exception as e:
		logging.error ('Error en get_picking_id:'+str(e))
		return False

@measure_time
def update_imprimio_etiqueta_meli_picking(picking_id):
	try:
		write_data = {'imprimio_etiqueta_meli': True}
		payload = get_json_payload("object", "execute_kw", db_name, user_id, password, 'stock.picking', 'write', [picking_id, write_data])
		res = requests.post(json_endpoint, data=payload, headers=headers).json()
		return True

	except Exception as e:
		logging.error(f'Error: update_imprimio_etiqueta_meli()| {str(e)}')
		return False

def ubicacion_impresoras():
	archivo_comfiguracion = dir_path + '/config_dev.json'
	#print (archivo_comfiguracion)
	with open(archivo_comfiguracion, 'r') as file:
		config = json.load(file)
	#print (config)
	IMPRESORA1 = config['IMPRESORA1']
	#print ('IMPRESORA1',IMPRESORA1)
	IMPRESORA2 = config['IMPRESORA2']
	#print ('IMPRESORA2',IMPRESORA2)
	return config

@measure_time
def imprime_zpl(so_name, ubicacion, order_odoo_id):
	
	start_time = time.time()

	etiqueta_imprimir = dir_path + '/Etiquetas/Etiqueta_'+so_name+'/Etiqueta de envio.txt'
	zpl_meli = open (etiqueta_imprimir) 
	elapsed_time1 = time.time() - start_time
	zpl = zpl_meli.read()
	elapsed_time2 = time.time() - start_time

	zpl_hack = (zpl.replace(' 54030', ' 54030 - '+so_name ))
	elapsed_time3 = time.time() - start_time
	#print ('ZPL :  \n',zpl_hack)

	mysocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)   
	elapsed_time4 = time.time() - start_time      

	#print ('Ubicacion de la impresora: ', ubicacion)

	ubicaciones = ubicacion_impresoras()
	
	host = ubicaciones.get(ubicacion)
	logging.info(f'EL IP DE LA IMPRESORA  {ubicacion} ES: {host}')

	#print ('IP de la Impresora:', host)
	port = 9100
	#port = 5432
	respuesta_imprime_zpl = ''

	try:

		datos=bytes(zpl_hack, 'utf-8')
		#print (datos)
		
		elapsed_time5 = time.time() - start_time
		mysocket.connect((host, port)) #connecting to host
		elapsed_time6 = time.time() - start_time
		mysocket.send(datos)#using bytes
		elapsed_time7 = time.time() - start_time

		mysocket.close () #closing connection
		elapsed_time8 = time.time() - start_time

		logging.info('Etiqueta para la orden ' +so_name+' se ha impreso con exito')
		resultado = update_imprimio_etiqueta_meli(order_odoo_id)
		elapsed_time9 = time.time() - start_time
		picking = get_picking_id(so_name)
		elapsed_time10 = time.time() - start_time
		logging.info(f'Picking es :  {picking}')
		picking_id = picking.get('picking_id')

		elapsed_time11 = time.time() - start_time
		
		resultado_pick = update_imprimio_etiqueta_meli_picking(picking_id)
		elapsed_time12 = time.time() - start_time
		

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
		logging.error(f'Error en la conexión con la impresora ZPL: {str(e)}')
		return "|Error en la conexión con la impresora ZPL: "+str(e)
	finally:
		logging.info(f"\nTIEMPO EN {elapsed_time1:.4f}, {elapsed_time2:.4f}, {elapsed_time3:.4f}, {elapsed_time4:.4f}, {elapsed_time5:.4f}, {elapsed_time6:.4f}, {elapsed_time7:.4f}, {elapsed_time8:.4f}, {elapsed_time9:.4f}, {elapsed_time10:.4f}, {elapsed_time11:.4f}, {elapsed_time12:.4f}[seg].\n")
		
@measure_time
def recupera_meli_token(user_id):
	try:
		#print 'USER ID:', user_id
		token_dir=''
		if user_id == 25523702:# Usuario de SOMOS REYES VENTAS
			token_dir='/home/server-tnp/meli/tokens_meli.txt' 
		elif user_id == 160190870:# Usuario de SOMOS REYES OFICIALES
			token_dir='/home/server-tnp/meli/tokens_meli_oficiales.txt'
		elif user_id == 1029905409:# Usuario de SKYBRANDS
			token_dir='/home/server-tnp/meli/tokens_meli_skyBrands.txt'
		
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
		logging.error(f'Error recupera_meli_token() {str(e)}: ')
		return False

@measure_time
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

@measure_time
def get_order_meli(order_id, access_token):
	try:
		headers = {'Accept': 'application/json','content-type': 'application/json'}
		url='https://api.mercadolibre.com/orders/'+order_id+'?access_token='+access_token
		print (url)
		r=requests.get(url)
		shipping_id = r.json()['shipping']['id']
		seller_id =  r.json()['seller']['id']
		status =  r.json()['status']
		#print (json.dumps(r.json(), indent=4, sort_keys=True))
		#----RECUPERA TAMBIEN EL ID DEL SELLER
		logging.info(f'shipping_id: {shipping_id}, seller_id: {seller_id}, status: {status}')
		return dict(shipping_id = shipping_id, seller_id =seller_id, status=status)
	except Exception as e:
		logging.error(f' Error get_order_meli: {str(e)}')
		return False

@measure_time
def get_shipment_meli(shipping_id, access_token):
    try:
        headers = {'Accept': 'application/json','content-type': 'application/json'}
        url='https://api.mercadolibre.com/shipments/'+str(shipping_id)+'?access_token='+access_token

        r=requests.get(url, headers=headers)
        #print (json.dumps(r.json(), indent=4, sort_keys=True))
        results = r.json()#['results'][0]
        #print (results['receiver_address'])
        #print (json.dumps(results['receiver_address'], indent=4, sort_keys=True))

        order_id=results['order_id']
        status = results['status']
        tracking_number = results['tracking_number']
        tracking_method = results['tracking_method']
        date_delivered = results['status_history']['date_delivered']
        print ('status: ', status)
        print ('date_delivered: ', date_delivered)
        print('tracking_method: ', tracking_method)
        print ('tracking_number: ', tracking_number)

        return dict(status=status, date_delivered=date_delivered)
    except Exception as e:
        logging.error(f' Error get_shipment_meli: {str(e)}')
        return False

app = Flask(__name__)
app.secret_key = 'esto-es-una-clave-muy-secreta'

@app.route('/')
def index():
	# Permite insertar el nombre de la localización de la impreslora dentro de SOMOS REYES
	return render_template("index.html" )

@app.route('/inicio', methods =['POST'])
def inicio():
	global user_id, password, user_name

	#usuario_odoo = request.form.get("usuario_odoo")
	#session['usuario'] = usuario_odoo
	#user_name = session['usuario']
	#user_id, user_name, password = get_password_user(user_name)

	try:
		localizacion = request.form.get("localizacion")
		session['ubicacion'] = localizacion
		ubicacion = session['ubicacion']

		usuario_odoo = request.form.get("usuario_odoo")
		session['usuario'] = usuario_odoo
		user_name = session['usuario']

		user_id, user_name, password = get_password_user(user_name)

		logging.info('La ubicacion es: ' + str(ubicacion))
		logging.info('El usuario es: ' + str(user_name))
		return render_template("formulario.html", ubicacion=ubicacion, usuario=user_name)

	except Exception as e:
		time.sleep(2)
		logging.info('El error es: ' + str(e))
		return render_template("index.html" )


@app.route('/procesar', methods=['POST'])
def procesar():
	ubicacion = session['ubicacion']
	e=None
	try:
		name_so = request.form.get("name_so")
		order_odoo =get_order_id(name_so)
		order_id = order_odoo.get('marketplace_order_id')
		seller_marketplace = order_odoo.get('seller_marketplace')
		order_odoo_id = order_odoo.get('order_odoo_id')
		guide_number = order_odoo.get('guide_number')
		team_id = order_odoo.get('team_id')

		try:
			carrier = guide_number.lower().split("::")[0]
			marketplace = team_id.lower().split("_")[1]
			if carrier == 'walmart':
				carrier = guide_number.lower().split("::")[1][0]
				if carrier == 'y':
					carrier = 'yaltec'
				else:
					carrier = 'colecta'
			elif carrier == 'amazon':
				carrier = 'colecta'
			elif carrier == 'coppel':
				carrier = 'colecta'
		except Exception as e:
			carrier = "None"
			marketplace = "None"

		logging.info(f'ODOO: {order_id}, {name_so}, {seller_marketplace}, {guide_number}, {team_id}, {ubicacion}, {carrier}, {marketplace}')
		orders_id = []

		# REVISAR
		if ':' in order_id:
			solo_orden = order_id.split(':')
			orders_id=solo_orden[1].split(',')
		else:
			orders_id.append(order_id)


		for order_id in orders_id:

			try:

				# Revisar el caso de etiqueta que es:
				label_case = get_label_case('labels_types.json', marketplace, carrier)

				if not guide_number:
					order_id = ''
					respuesta = 'Esta orden de venta aun no tiene numero de guia'
					formulario = 'error.html'

					break

				# SE INCLUYEN LOS CASOS DE MARKETPLACES CON ETIQUETAS VALIDAS (a parte de Fedex)
				if 'fedex' in guide_number.lower() or label_case in [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]: # FeDex::2,7,15,16    LISTA DE CASOS PERMITIDOS DEL JSON labels_types.json   
					if team_id.lower() == 'team_elektra' or team_id.lower() == 'team_mercadolibre': #team_id.lower() == 'team_liverpool' or
						respuesta = f'¡ESTA  ORDEN  ES  DE  "{team_id.upper()}"  CON  GUIA  DE  FeDex,  FAVOR  DE  IMPRIMIR  EN  ODOO!'
						break
						
					# Coidgo para imprimir etiqueta Fedex
					order_id_valpick = search_valpick_id(name_so)
					response_fedex = ejecute_fedex_label(order_id_valpick)
					#logging.info(response_fedex)
					if response_fedex.get('state') == True:
						# Get fecha actual CDMX
						gap_utc_hours = -6
						gap_timedelta = timedelta(hours=gap_utc_hours)
						print_label_date = datetime.strptime(response_fedex.get('shplbl_print_date'), "%Y-%m-%d %H:%M:%S")
						print_label_date = print_label_date + gap_timedelta
						respuesta = 'La orden '+name_so+f' es de {marketplace.upper()} con carrier {carrier.upper()} pero ya fue impresa el dia: ' + str(print_label_date)
						order_id = order_id
					else:
						respuesta = 'La orden '+name_so+f' es de {marketplace.upper()} con el carrier {carrier.upper()} y se imprimió de manera correcta'
						order_id = order_id

				else:
					if  seller_marketplace == '160190870':
						#SOMOS-REYES OFICIALES
						user_id_ = 160190870
						market_ml = 'SOMOS-REYES OFICIALES'
					elif seller_marketplace == '25523702' :
						#SOMOS-REYES VENTAS
						user_id_ = 25523702
						market_ml = 'SOMOS-REYES VENTAS'
					elif seller_marketplace == '1029905409':
						#SOMOS-REYES SKYBRANDS
						user_id_ = 1029905409
						market_ml = 'SKYBRANDS'
					#elif seller_marketplace == '156001758': #SO3245440
					#	user_id_ = 156001758
					#	market_ml = 'TEST'
					else:
						respuesta = f'Esta orden NO es procesable en el sitio web. SM: {seller_marketplace}'
						break
					
					logging.info(f'El marketplace es: {market_ml}')
					access_token = recupera_meli_token(user_id_)

					order_meli = get_order_meli(order_id, access_token)
					logging.info(f' \n Orden {order_id}, Usuario id {user_id_}, Orden MELI {order_meli} \n')

					if order_meli == False:
						#respuesta = 'Esta orden de venta aun no se le adjunta etiqueta de envio en Mercado Libre (o tokens incorrectos) \n ESPERAR MAXIMO 30 MINUTOS'
						tk_meli.get_all_tokens()
						#respuesta = 'Tokens incorrectos ¡ESPERAR MAXIMO 30 MINUTOS E INTENTAR DE NUEVO!'
						respuesta = 'Recuperando Tokens... ¡VUELVE A INTENTAR!'
						formulario = 'error.html'
						break
					
					shipment_ids = order_meli.get('shipping_id')
					seller_id = order_meli.get('seller_id')
					status =  order_meli.get('status')

					if status == 'cancelled':
						respuesta = 'La orden '+name_so+' ha sido cancelada, no se imprimirá la etiqueta.'
					elif status == 'delivered':
						respuesta = 'La orden '+name_so+' ya ha sido entregada, no se imprimirá la etiqueta.'
					else:
						respuesta_ship =  get_shipment_meli(shipment_ids, access_token)
						status_shipping = respuesta_ship.get('status')
						date_delivered = respuesta_ship.get('date_delivered')
						if status_shipping == 'delivered':
							respuesta = 'La orden '+name_so+' ya ha sido entregada el dia: '+ date_delivered+',  no se imprimirá la etiqueta.'
						else:
							respuesta = get_zpl_meli(shipment_ids,name_so, access_token, ubicacion, order_odoo_id)
			except Exception as e:
				logging.error(f'ERROR: {e}')
				respuesta = f'Error de conexión, {e}'

		print('respuesta:', respuesta)
		formulario = 'mostrar.html'
	except Exception as e:
		order_id = ''
		logging.info(f'ERROR de try en PROCESAR {str(e)}')
		respuesta = str(e)
		formulario = 'error.html'
		

	return render_template(formulario, name_so=name_so, order_id = order_id, respuesta = respuesta)


if __name__ == "__main__":

	app.run(host='0.0.0.0', port=8000, debug=True)
