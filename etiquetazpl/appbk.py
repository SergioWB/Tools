from flask import Flask, render_template, request, make_response, url_for, session 
import json
import requests
from pprint import pprint
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import zipfile
import socket
import os 

dir_path = os.path.dirname(os.path.realpath(__file__))
#url ='https://somosreyes-test-973378.dev.odoo.com'
url ='https://somosreyes.odoo.com'
client_id ='B38ULenQ5Wo9YHVpCNPwLYU06o0dif'
client_secret ='PDzW1J08BJB0JB3UXh0TlQkiPOm3pU'

limite =100000
class RestAPI:
	def __init__(self):
		self.url = url
		self.client_id = client_id
		self.client_secret = client_secret

		self.client = BackendApplicationClient(client_id=self.client_id)
		self.oauth = OAuth2Session(client=self.client)

	def route(self, url):
		if url.startswith('/'):
			url = "%s%s" % (self.url, url)
			#print (url)
		return url

	def authenticate(self):
		self.oauth.fetch_token(
			token_url=self.route('/api/authentication/oauth2/token'),
			client_id=self.client_id, client_secret=self.client_secret
		)
		#print( self.oauth.fetch_token(token_url=self.route('/api/authentication/oauth2/token'),client_id=self.client_id, client_secret=self.client_secret) )


	def execute(self, enpoint, type="GET", data={}):
		if type == "POST":
			response = self.oauth.post(self.route(enpoint), data=data)
		elif type == "PUT":
			response = self.oauth.put(self.route(enpoint), data=data)
		elif type == "DELETE":
			response = self.oauth.delete(self.route(enpoint), data=data)
		else:
			response = self.oauth.get(self.route(enpoint), data=data)
		if response.status_code != 200:
			api.authenticate()
			raise Exception(pprint(response.json()))
		else:
			#print (response.json() )
			return response.json()

	def get_order_id(self, name):
		try:
			data = {
			'model': "sale.order",
			'domain': json.dumps([['name', '=', name]]),
			'fields': json.dumps(['marketplace_order_id', 'name', 'seller_marketplace']),
			}
			response = api.execute('/api/search_read', data=data)
			print (json.dumps(response, indent=4, sort_keys=True))
			marketplace_order_id = str(response[0]['marketplace_order_id'])
			seller_marketplace = str(response[0]['seller_marketplace'])

			return dict(marketplace_order_id = marketplace_order_id,seller_marketplace =seller_marketplace )
		except Exception as e:
			return False

	def update_imprimio_etiqueta_meli(self, so_name):
		try:
			data = {
			'model': "sale.order",
			'domain': json.dumps([['name', '=',so_name]]),
			'fields': json.dumps(['id','name','imprimio_etiqueta_meli']),
			#'fields': json.dumps([]),
			}

			response =api.execute("/api/search_read", data=data)
			ids=response[0]["id"]
			
			# update product
			values = {
				'imprimio_etiqueta_meli': True,
			}

			data = {
				"model": "sale.order",
				'ids':[ids],
				"values": json.dumps(values),
			}

			response = api.execute('/api/write', type="PUT", data=data)
			print (response)
			return  True

		except Exception as e:
			print ('Error No marco la impresión en ODOO: '+str(e) + '| '+str(so_name))
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


def imprime_zpl(so_name, ubicacion):
	etiqueta_imprimir = dir_path + '/Etiquetas/Etiqueta_'+so_name+'/Etiqueta de envio.txt'
	#print (etiqueta_imprimir)
	zpl_meli = open (etiqueta_imprimir) 
	zpl = zpl_meli.read()
	#print (zpl)
	mysocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)         
	#host = "10.99.0.14" 
	print ('Ubicacion de la impresora: ', ubicacion)

	ubicaciones = ubicacion_impresoras()

	#ubicaciones = {"EMPACADO":"192.168.0.54", "PICKING":"192.168.0.55", }
	
	host = ubicaciones.get(ubicacion)

	print ('IP de la Impresora:', host)
	port = 9100   
	
	try:

		datos=bytes(zpl, 'utf-8')
		print (datos)
		mysocket.connect((host, port)) #connecting to host
		mysocket.send(datos)#using bytes
		mysocket.close () #closing connection
		print ('Etiqueta para la orden ' +so_name+'se ha impreso con exito')
		resultado = api.update_imprimio_etiqueta_meli(so_name)
		if resultado:
			return '|Etiqueta para la orden ' +so_name+'se ha impreso con exito'
		else:
			return '|No se marco la impresión de la Guía para ' +so_name

	except:
		print(" Error en la conexión con la impresora ZPL ")
		return "|Error en la conexión con la impresora ZPL"
		

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

def get_zpl_meli(shipment_ids,so_name, access_token, ubicacion):
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
				resultado = imprime_zpl(so_name, ubicacion)
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
		order_odoo = api.get_order_id(name_so)
		order_id = order_odoo.get('marketplace_order_id')
		seller_marketplace = order_odoo.get('seller_marketplace')

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

		respuesta = get_zpl_meli(shipment_ids,name_so, access_token, ubicacion )
		formulario = 'mostrar.html'
	except Exception as e:
		order_id = ''
		respuesta = str(e)
		formulario = 'error.html'
		

	return render_template(formulario, name_so=name_so, order_id = order_id, respuesta = respuesta)


if __name__ == "__main__":
	api = RestAPI()
	api.authenticate()

	app.run(host='0.0.0.0', port=8000, debug=True)