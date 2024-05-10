#!/usr/bin/python
import sys
import json
import requests
from time import sleep
import datetime
from datetime import datetime, date, time, timedelta
import pprint 
import logging
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
#from connector_mariadb import *
from collections import OrderedDict


date_time = datetime.now()
date_time_iso= date_time.isoformat() 
fecha=date_time_iso.split('T')[0]

log_file='/home/serverubuntu/someliodoo/orders_meli_'+str(fecha)+'.log'
logging.basicConfig(filename=log_file,format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%Y-%d-%m %I:%M:%S %p',level=logging.INFO)

url_sr ='https://somosreyes.odoo.com'
client_id_sr ='B38ULenQ5Wo9YHVpCNPwLYU06o0dif'
client_secret_sr ='PDzW1J08BJB0JB3UXh0TlQkiPOm3pU'

#url_sr =''
#client_id_sr ='KNw8rzxEoaV9G2iKy5xMLSGcQgW2fQ'
#client_secret_sr ='1XohxIhvNFKUjdd3TEkU6OKb9dRcZr'

def update_orders_saved(order_id,status_order,shipment_status,carrier,tracking_id, respuesta_odoo,market_place_fee, shipping_cost, total_paid_amount, transaction_amount, status_detail):
	try:
		connect=connect_to_orders()
		cursor=connect['cursor']
		connection_object=connect['connection_object']

		sql_update_query = "UPDATE notify_meli SET status_order=%s, shipment_status=%s, carrier=%s, tracking_id=%s, respuesta_odoo =%s,market_place_fee= '%s', shipping_cost='%s', total_paid_amount='%s', transaction_amount='%s', status_detail=%s WHERE order_id = %s;"
		#print sql_update_query
		input = (status_order, shipment_status, carrier, tracking_id, str(respuesta_odoo), market_place_fee, shipping_cost, total_paid_amount, transaction_amount, status_detail, order_id)
		dato = cursor.execute(sql_update_query, input)
		connection_object.commit()
		print("MariaSQL|order_id:", order_id," Odoo Id:",respuesta_odoo)
	except mysql.connector.Error as error :
		print("Failed to update record to database: {}".format(error))

def colocar_nota_a_orden_meli(so_name, order_id, access_token):
    headers = {
        'content-type': 'application/json', 'Authorization': 'Bearer '+ access_token
        } 

    data={"note":so_name}

    url='https://api.mercadolibre.com/orders/'+str(order_id)+'/notes?access_token='+access_token
    try:
        r=requests.post(url, data=json.dumps(data), headers=headers)
        mi_json= r.json()
        print (json.dumps(mi_json, sort_keys=True, indent=4, separators=(',', ': ')) )
        return True
    except Exception as e:
        print ('Error en colocar_nota_a_orden_meli(): '+str(e) )
        return False

def get_id_odoo_product(seller_sku, title, id_order):
	try:
		data = {
		'model': "product.product",
		'domain': json.dumps([['default_code', '=', seller_sku]]),
		'fields': json.dumps(['id','default_code','name','list_price','stock_real', 'stock_reservado','stock_urrea', 'categ_id']),
		}
		response = api.execute('/api/search_read', data=data)
		print ('RESPONSE PRODUCT:', response )
		if len(response)==0:
			print (seller_sku,'No encontrado en odoo')
		cantidad_productos=len(response)
		 
		if cantidad_productos>0:
			id_product=response[0]['id']

			product_id = response[0]['id']
			stock_real = response[0]['stock_real']
			stock_reservado = response[0]['stock_reservado']
			stock_urrea = response[0]['stock_urrea']
			precio_venta = response[0]['list_price']
			categ_id = (response[0]['categ_id'][1]).lower()

			#--- Productos de Urrea, Surtek o Lock se comparan con el Stock de Urrea
			stock_neto=0
			if 'urrea' in categ_id or 'lock' in categ_id or 'surtek' in categ_id :
				stock_neto = stock_real+stock_urrea - stock_reservado
			else:
				stock_neto = stock_real - (stock_reservado+1)

			print('STOCK_NETO_PRODUCTO:', stock_neto)


			return dict(product_id=product_id, stock_neto=stock_neto, precio_venta=precio_venta, categ_id=categ_id)
		else:
			logging.info('Orden Id: '+ str(id_order)+' No se encontro el Id del Producto en Odoo. SKU: '+ str(seller_sku)+' '+title )
			return False

	except Exception as e:
		print('Error en get_id_odoo_product() : '+str(e))
		return False


def get_odoo_sub_product(product_id):
	try:
		data = {
		'model': "product.product",
		'domain': json.dumps([['id', '=', product_id]]),
		'fields': json.dumps(['id','default_code','name','list_price','precio_con_iva']),
		}
		response = api.execute('/api/search_read', data=data)
		print ('RESPONSE SUB PRODUCT:', response )
		cantidad_productos=len(response)

		if cantidad_productos>0:
			return response[0]
		else:
			logging.info('Orden Id: '+ str(id_order)+' No se encontro el Id del Producto en Odoo. SKU: '+ str(seller_sku)+' '+title )
			return False
	except Exception as e:
		print('Error en get_odoo_sub_product() datos del producto del combo: '+str(e))
		return False


def get_id_odoo_product_kit(seller_sku, title, id_order, logistic_type, unit_price_combo):
	try:
		data = {
		'model': "product.product",
		'domain': json.dumps([['default_code', '=', seller_sku]]),
		'fields': json.dumps(['id','default_code','name','list_price','is_kit','categ_id', 'sub_product_line_ids','stock_real','stock_reservado', 'stock_urrea','precio_con_iva']),
		}
		response = api.execute('/api/search_read', data=data)
		print ('RESPONSE KIT PRODUCT:', response)
		sub_product_line_ids = response[0]['sub_product_line_ids']

		stock_real_combo = response[0]['stock_real']
		stock_reservado_combo = response[0]['stock_reservado']
		stock_neto_odoo_combo = stock_real_combo - stock_reservado_combo
		precio_con_iva_combo_odoo = response[0]['precio_con_iva']
		print ('COMBO sub_product_line_ids:',sub_product_line_ids )
		precio_vendido_meli_combo = round(unit_price_combo*1.16,0)
		print('PRECIO VENDIDO EN MELI DEL COMBO:',precio_vendido_meli_combo )


		total_precios_productos_no_combo=0.00
		for sub_product in sub_product_line_ids:
			data = {
			'model': "sub.product.lines",
			'domain': json.dumps([['id', '=', sub_product ]]),
			'fields': json.dumps(['id','product_id','quantity']),
			}
			response = api.execute('/api/search_read', data=data)
			print('Producto en el combo:', response)
			product_id = response[0]['product_id'][0]
			quantity_combo = response[0]['quantity']
			item_selled_precio = get_odoo_sub_product(product_id)
			precio_con_iva_no_combo = item_selled_precio['precio_con_iva'] * quantity_combo
			total_precios_productos_no_combo += precio_con_iva_no_combo
		
		print('TOTAL DE PRECIOS DE PRODUCTOS NO COMBO:',total_precios_productos_no_combo )
		diferencia_combo = round(total_precios_productos_no_combo - precio_vendido_meli_combo, 2)
		print('DIFERENCIA COMBO:', diferencia_combo)
		#porcentaje_descuento_combo = round((diferencia_combo * 100)/ (total_precios_productos_no_combo),2) #Nota: Se comenta el calculo de descuento 05/03/22
		#print ('DESCUENTO COMBO:', porcentaje_descuento_combo)
		print('PRODUCTO COMBO->', 'STOCK NETO ODOO',stock_neto_odoo_combo,'PRECIO VENTA ODOO:',precio_con_iva_combo_odoo,'PRECIO VENDIDO MELI:',precio_vendido_meli_combo)

		autoconfirmar=False
		lineas_pedido=[]
		list_items = []

		for sub_product in sub_product_line_ids:
			data = {
			'model': "sub.product.lines",
			'domain': json.dumps([['id', '=', sub_product ]]),
			'fields': json.dumps(['id','product_id', 'quantity']),
			}
			response = api.execute('/api/search_read', data=data)
			product_id = response[0]['product_id'][0]
			item_selled = get_odoo_sub_product(product_id)
			
			print ('item_selled COMBO : ',item_selled)
			product_id = item_selled['id']
			quantity =  response[0]['quantity']
			unit_price = item_selled['list_price']
			title = item_selled['name']						

			list_items.append(product_id)
			lineas_pedido.append( (0,0,{'product_id': product_id,'product_uom':1, 'product_uom_qty':quantity, 'price_unit': unit_price, 'name': title}) ) #Nota: Se comenta el calculo de descuento 05/03/22 'discount': porcentaje_descuento_combo,
		return dict(lineas_pedido=lineas_pedido, list_items=list_items, stock_neto_odoo_combo=stock_neto_odoo_combo)  #Nota: Se comenta el calculo de descuento 05/03/22 , porcentaje_descuento_combo=porcentaje_descuento_combo)
			
	except Exception as e:
		print('Error en get_id_odoo_product_kit() : '+str(e))
		return False

def consulta_team(name_team):
		try:
			lista_urrea=[]
			data = {
			"model":"crm.team",
			"domain":json.dumps([["name","=", name_team]]),
			"fields":json.dumps(["id", "name"]),
			}
			response =api.execute("/api/search_read", data=data)
			id_equipo = response[0]['id']
			#print response
			return id_equipo
		except Exception as e:
			print('Error en consulta_equipo() : '+str(e))
			return False

def consulta_users(usuario):
		try:
			lista_urrea=[]
			print ('Este es el usuario: ',usuario)
			data = {
			"model":"res.users",
			"domain":json.dumps([["name","=", usuario]]),
			"fields":json.dumps(["name"]),
			}
			response =api.execute("/api/search_read", data=data)
			id_usuario = response[0]['id']
			return id_usuario

		except Exception as e:
			api.authenticate()
			print('Error en consulta_users() : '+str(e))
			return 1

def verify_exist_order_in_odoo(marketplace_order_id):
	try:
		data = {
			'model': "sale.order",
			'domain': json.dumps([['marketplace_order_id', '=', str(marketplace_order_id) ]]),
			'fields': json.dumps(['id','name', 'marketplace_order_id']),
			'limit': 1
		}
		response = api.execute('/api/search_read', data=data)
		existe=len(response)
		if existe==0: #No existe
			return False 
		else:
			ids=response[0]['id']
			return ids
	except Exception as e:
		print('Error en verify_exist_order_in_odoo() : '+str(e))
		return False

def get_name_order_in_odoo(order_id):
	try:
		data = {
			'model': "sale.order",
			'domain': json.dumps([['id', '=', order_id ]]),
			'fields': json.dumps(['id','name', 'marketplace_order_id']),
			'limit': 1
		}
		response = api.execute('/api/search_read', data=data)
		existe=len(response)
		if existe==0: #No existe
			print('No se ha encontrado el Nombre de la orden ')
			return False 
		else:
			print('Se ha encontrado el Nombre de la orden ')
			name=response[0]['name']
			return name
	except Exception as e:
		print('Error en get_name_order_in_odoo() : '+str(e))
		return False

def get_name_order_in_odoo_by_order_meli(order_id_meli):
	try:
		data = {
			'model': "sale.order",
			'domain': json.dumps([['marketplace_order_id', 'like', order_id_meli ]]),
			'fields': json.dumps(['id','name', 'marketplace_order_id']),
			'limit': 1
		}
		response = api.execute('/api/search_read', data=data)
		existe=len(response)
		if existe==0: #No existe
			print('No se ha encontrado el Nombre de la orden ')
			return False 
		else:
			print('Se ha encontrado el Nombre de la orden ')
			name=response[0]['name']
			return name
	except Exception as e:
		print('Error en get_name_order_in_odoo() : '+str(e))
		return False
	
def update_sale_order(ids, marketplace_order_id, tracking_method,  tracking_number):
		try:		
			values = {'tracking_number': tracking_method+'/'+tracking_number,}

			data = {
				"model": "sale.order",
				'ids':ids,
				"values": json.dumps(values),
			}
			response = api.execute('/api/write', type="PUT", data=data)
			print('UPDATE SALE ORDER|',marketplace_order_id, response)
		except Exception as e:
			print ('Error en update_sale_order: '+str(e) )


def get_id_odoo_buyer_by_name(name):
	try:
		data = {
		'model': "res.partner",
		'domain': json.dumps([['name', '=', name]]),
		'fields': json.dumps(['id','name']),
		}
		response = api.execute('/api/search_read', data=data)
		#print (response)
		id_partner=None
		for partner in response:
			#print (partner['id'])
			id_partner = partner['id']
		return id_partner
	except Exception as e:
		return False
		print('Error en get_id_odoo_buyer_by_name() : '+str(e))

def get_meli_ful_warehouse_id_by_name(warehouse_name):
	try:
		data = {
		'model': "stock.warehouse",
		'domain': json.dumps([['name', '=', warehouse_name]]),
		'fields': json.dumps(['id','name']),
		}
		response = api.execute('/api/search_read', data=data)
		#print (response)
		warehouse_id = response[0]['id']
		return warehouse_id
	except Exception as e:
		return False
		print('Error en get_meli_ful_warehouse_id_by_name() : '+str(e))

def update_stock_reservado(product_id, quantity, status):
		try:
			data = {
			'model': "product.product",
			'domain': json.dumps([['id', '=', product_id]]),
			'fields': json.dumps(['id','default_code','stock_reservado']),
			'limit':1,
			}
			response = api.execute('/api/search_read', data=data)
			print ('BUSQUEDA =>',response)
			stock_reservado_actual = response[0]['stock_reservado']
			default_code = response[0]['default_code']
			stock_reservado_nueva=0
			if status=='cancelled':
				pass
				#stock_reservado_nueva = stock_reservado_actual - quantity
			else:
				stock_reservado_nueva = stock_reservado_actual  + quantity

			values = {'stock_reservado': stock_reservado_nueva}

			data = {
				"model": "product.product",
				'ids':product_id,
				"values": json.dumps(values),
			}
			print ('ACTUALIZACION=>',data)
			response_update = api.execute('/api/write', type="PUT", data=data)
			print('UPDATE PRODUCT |',product_id, default_code, response_update )

			if response_update:
				return response
			else:
				return False


		except Exception as e:
			print ('Error en update_stock_reservado: '+str(e) )
	


def get_picking_ids_order_in_odoo(origin):
	try:
		data = {
			'model': "sale.order",
			'domain': json.dumps([['name', '=', origin ]]),
			'fields': json.dumps(['id','name', 'marketplace_order_id', 'picking_ids']),
			'limit': 1
		}
		response = api.execute('/api/search_read', data=data)
		existe=len(response)
		print('BUSCANDO PICK Y OUT: ',response)
		if existe==0: #No existe
			print('No se ha encontrado el PICK y OUT de la orden ')
			return False 
		else:
			print('Se ha encontrado el PICK y OUT de la orden ')

			picking_ids=response[0]['picking_ids']
			return picking_ids
	except Exception as e:
		print('Error en get_picking_ids_order_in_odoo() : '+str(e))
		return False


def update_pick_carrier_tracking_ref(picking_ids, carrier_tracking_ref):
	try:
			
		values = {'carrier_tracking_ref': carrier_tracking_ref}

		for picking_id in picking_ids:
			data = {
				"model": "stock.picking",
				'ids':picking_id,
				"values": json.dumps(values),
			}
			print ('ACTUALIZACION=>',data)
			response_update = api.execute('/api/write', type="PUT", data=data)
			print('UPDATE MOVIMIENTO |',picking_id,response_update )	
	
	except Exception as e:
		print ('Error en update_pick_carrier_tracking_ref(): '+str(e) )



class RestAPI:
	def __init__(self):
		self.url = url_sr
		self.client_id = client_id_sr
		self.client_secret = client_secret_sr
		self.client = BackendApplicationClient(client_id=self.client_id)
		self.oauth = OAuth2Session(client=self.client)

	def route(self, url):
		if url.startswith('/'):
			url = "%s%s" % (self.url, url)
		return url

	def authenticate(self):
		try:
			self.oauth.fetch_token(
			token_url=self.route('/api/authentication/oauth2/token'),
			client_id=self.client_id, client_secret=self.client_secret
			)
			#print(self.oauth.fetch_token(token_url=self.route('/api/authentication/oauth2/token'),client_id=self.client_id, client_secret=self.client_secret) )
		except Exception as e:
			raise e
		

	def execute(self, enpoint, type="GET", data={}):
		try:
			if type == "POST":
				response = self.oauth.post(self.route(enpoint), data=data)
			elif type == "PUT":
				response = self.oauth.put(self.route(enpoint), data=data)
			else:
				response = self.oauth.get(self.route(enpoint), data=data)
				#print 'RESPONSE', response
			if response.status_code != 200:
				api.authenticate()# OJO COLOCAR PARA RECUPERAR EL ACCES TOKEN DE ODOO, SE PIERDE EN 1 HORA
				raise Exception(pprint(response.json()))
			else:
				#print response.json()
				return response.json()

		except Exception as e:
			api.authenticate()
			print ('Error al realizar el request en: Execute()'+str(e) )
			return False

def get_payment_method_id(payment_type):
	try:
		formas_pago_odoo = {'01':1, #Efectivo
							'02':2, #Cheque nominativo
							'03':3, #Transferencia electronica de fondos
							'04':4, #Tarjeta de Credito
							'05':5, #Monedero Electronico
							'06':6, #Dinero Electronico
							'08':7, #Vales de despensa
							'12':8,#Dacion en pago
							'13':9, #Pago por subrogacion 
							'14':10,#Pago por consignacion
							'15':11,#Condonacion
							'17':12,#Compensacion
							'23':13,#Novacion
							'24':14,#Confusion
							'25':15,#Remision de deuda
							'26':16,#Prescripcion o caducidad
							'27':17,#A satisfaccion del acreedor
							'28':18,#Tarjeta de Debito
							'29':19,#Tarjeta de Servicio
							'30':20,#Aplicacion de anticipos
							'99':21,#Por definir
							'31':22,#Intermediario pagos
							}
				
		formas_de_pago_meli_sat = { "credit_card":"04", 
									"debit_card":"28",
									"prepaid_card":"06",
									"atm":"03",
									"ticket":"01",
									"account_money":"06",
									"digital_currency":"06"}

		if payment_type == 'credit_card':
			forma_pago_SAT = formas_de_pago_meli_sat[payment_type]
			formas_pago_odoo_id=formas_pago_odoo[forma_pago_SAT]
		elif payment_type == 'debit_card':
			forma_pago_SAT =formas_de_pago_meli_sat[payment_type]
			formas_pago_odoo_id=formas_pago_odoo[forma_pago_SAT]
		elif payment_type == 'prepaid_card':
			forma_pago_SAT = formas_de_pago_meli_sat[payment_type]
			formas_pago_odoo_id=formas_pago_odoo[forma_pago_SAT]
		elif payment_type == 'atm':
			forma_pago_SAT = formas_de_pago_meli_sat[payment_type]
			formas_pago_odoo_id=formas_pago_odoo[forma_pago_SAT]
		elif payment_type == 'ticket':
			forma_pago_SAT = formas_de_pago_meli_sat[payment_type]
			formas_pago_odoo_id=formas_pago_odoo[forma_pago_SAT]
		elif payment_type == 'account_money':
			forma_pago_SAT = formas_de_pago_meli_sat[payment_type]
			formas_pago_odoo_id=formas_pago_odoo[forma_pago_SAT]
		elif payment_type == 'digital_currency':
			forma_pago_SAT = formas_de_pago_meli_sat[payment_type]
			formas_pago_odoo_id=formas_pago_odoo[forma_pago_SAT]
		else :
			forma_pago_SAT = '99'
			formas_pago_odoo_id=formas_pago_odoo[forma_pago_SAT]

		#print ('Forma de Pago SAT: ', forma_pago_SAT,formas_pago_odoo_id )
		return formas_pago_odoo_id

	except Exception as e:
		print('Error|get_payment_method_id(): '+str(e) )
		return False


api = RestAPI()
api.authenticate()

if __name__ == '__main__':
	seller_sku='300076-MOD'
	title =''
	id_order =''
	get_id_odoo_product(seller_sku, title, id_order)