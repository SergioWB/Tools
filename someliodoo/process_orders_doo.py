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
from odoo_utils import *
from meli_utils import *

date_time = datetime.now()
date_time_iso= date_time.isoformat() 
fecha=date_time_iso.split('T')[0]

#log_file='/home/ubuntu/meli/logs/orders_meli_'+str(fecha)+'.log'
log_file='/home/moi/meli/someliodoo/orders_meli_'+str(fecha)+'.log'
logging.basicConfig(filename=log_file,format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%Y-%d-%m %I:%M:%S %p',level=logging.INFO)


null='null'
false=False


def get_shipment_order_meli(seller_id, order_id, access_token):
	try:
		headers = {'Accept': 'application/json','content-type': 'application/json', 'x-format-new': 'true','Authorization': 'Bearer '+ access_token}
		url='https://api.mercadolibre.com/orders/search?seller='+str(seller_id)+'&q='+str(order_id)+'&access_token='+access_token
		print (url)
		r=requests.get(url, headers=headers)
		order = r.json()['results'][0]
		print (json.dumps(r.json()['results'], indent=4, sort_keys=True))#ok
		shipping_id = order.get('shipping').get('id')
		pack_id =  order.get('pack_id')
		return dict(shipping_id=shipping_id, pack_id=pack_id)
	except Exception as e:
		print (' Error get_shipment_order_meli: '+ str(e))
		return False


def get_order_ids_from_carrito(shipping_id, access_token):
	try:
		headers = {'Accept': 'application/json','content-type': 'application/json', 'x-format-new': 'true', 'Authorization': 'Bearer '+ access_token}
		url='https://api.mercadolibre.com/shipments/'+str(shipping_id)+'/items'+'?access_token='+access_token
		r=requests.get(url, headers=headers)
		results = r.json()
		#print (json.dumps(r.json(), indent=4, sort_keys=True))#ok
		orders_id=[]
		for item in r.json():
			#print (item.get('order_id'))
			orders_id.append(item.get('order_id'))
		return orders_id
	except Exception as e:
		print (' Error get_shipment_meli_new: '+ str(e))
		return False


def get_order_meli(seller_id, order_id, access_token):
	try:
		headers = {'Accept': 'application/json','content-type': 'application/json', 'x-format-new': 'true','Authorization': 'Bearer '+ access_token}
		url='https://api.mercadolibre.com/orders/search?seller='+str(seller_id)+'&q='+str(order_id)+'&access_token='+access_token
		#print url
		r=requests.get(url, headers=headers)
		order_exist = len(r.json()['results'])
		#print (json.dumps(r.json()['results'], indent=4, sort_keys=True))#ok
		#print shipping_id, feedback,shipment,id_order,order_status,date_created
		shipping_labels=''
		feedback = None

		if order_exist>0:
			order = r.json()['results'][0]
			id_order = order['id']
			order_status = order['status']
			date_created = order['date_created'][:-10]
			shipping_id = order['shipping']['id']
			#shipping_status = order['shipping']['status']
			shipping_status=''
			order_items = order['order_items']
			feedback = order.get('feedback').get('sale')
			#print ('SHIPPING_ID: ',shipping_id)
			#print ('FEEDBACK: ',id_order, feedback)
			
			shipment= {}

			if shipping_id:
				shipment = get_shipment_meli(shipping_id, access_token)
				print ('SHIPMENT', shipment)
				shipping_labels='https://api.mercadolibre.com/shipment_labels?shipment_ids='+str(shipping_id)+'&response_type=zpl2&access_token='
			else:
				shipment={'status': shipping_status, u'tracking_method': '', u'tracking_number':''}
				print ('SHIPMENT', shipment)
				shipping_labels=''

			fulfilled = False
			if feedback==None:
				fulfilled = False	
			else: 
				fulfilled = feedback['fulfilled']
				#fulfilled_id = feedback['fulfilled']['id']

			print ('FULFILLED: ', fulfilled)
			
			buyer_name = order['buyer']['nickname'] #+'/'+order['buyer']['first_name']+ ' '+order['buyer']['last_name']
			buyer_email ='' # order['buyer']['email']
			seller_nickname = order['seller']['nickname']

			#--- Pago
			payments = order['payments']
			for payment in payments:
				#payment_market_place_fee = payment['marketplace_fee']
				payment_market_place_fee = 17.5
				payment_shipping_cost = payment['shipping_cost']
				payment_total_paid_amount = payment['total_paid_amount']
				payment_transaction_amount = payment['transaction_amount']
				payment_status_detail = payment['status_detail']
				
				payment_method_id = payment['payment_method_id']
				payment_type = payment['payment_type']
				payment_method_id = get_payment_method_id(payment_type)
				#print ('payment_method_id', payment_method_id)
				

				#print ('PAGO: ',payment_method_id, payment_type, payment_total_paid_amount, payment_transaction_amount, payment_market_place_fee, payment_total_paid_amount, payment_status_detail )

			list_items=[]
			list_item_selled=[]
			item_selled = {}
			lineas_pedido=[]
			es_combo=False
			combo_detail=''
			autoconfirmar = False # autoconfirmar sera TRUE si todos los productos cumplen las validaciones
			for item in order_items:
				#print (item)
				mlm = item['item']['id']
				logistic_type  = get_logistic_type_item_meli(mlm, access_token)	
				seller_sku = item['item']['seller_sku']

				print ('SELLER SKU:', seller_sku,'MLM: ', mlm,'LOGISTICA MELI: ', logistic_type)

				if seller_sku==None: #  No todos los productos tienen este campo ... buscar en seller_custom_field
					print ('NO TIENE SELLER SKU')
					seller_custom_field = item['item']['seller_custom_field']
					print ('seller_custom_field: ', seller_custom_field)
					seller_sku=seller_custom_field

				#sale_fee = item['sale_fee']
				unit_price = item['unit_price']/1.16
				quantity = item['quantity']	
				#print ('seller_sku->', seller_sku, quantity)
				title =  item['item']['title']

				if 'COMBO' in seller_sku:
					combo = get_id_odoo_product_kit(seller_sku, title, id_order, logistic_type, unit_price)
					lineas_pedido = combo['lineas_pedido']
					list_items = combo['list_items']
					stock_neto_odoo=combo['stock_neto_odoo_combo']
					#porcentaje_descuento =combo['porcentaje_descuento_combo'] Nota: Se comenta el calculo de descuento 04/03/22
					if shipping_id:
						etiqueta_impresion = get_substatus_shipment_label_meli (id_order, access_token)
						print('ETIQUETA DE IMPRESION: ', etiqueta_impresion)
						print('COMBOS PEDIDOS',quantity, 'COMBOS EN EXISTENCIA:',stock_neto_odoo)
					else:
						etiqueta_impresion = ''

					if (quantity <= stock_neto_odoo) and (etiqueta_impresion==True): #Nota: Se comenta el calculo de descuento 04/03/22 (porcentaje_descuento < 40.00) and 
						print ('SI AUTOCONFIRMAR')
						autoconfirmar = True
					else:
						print ('NO AUTOCONFIRMAR')
						autoconfirmar = False
						if  logistic_type =='fulfillment':
							autoconfirmar = True

					es_combo=True
					combo_detail=str(seller_sku)+'|'+str(title)+'|'+str(quantity)+'|$'+str(item['unit_price'])

				else:	
					product = get_id_odoo_product(seller_sku, title, id_order)

					#======== Si encontramos el producto, validar para autoconfirmación productos unitarios=========				
					stock_neto_odoo = product['stock_neto']
					precio_venta_odoo = product['precio_venta']
					marca_producto_odoo = product['categ_id']
					precio_vendido_meli = item['unit_price']/1.16 #NOTA: Modificación 07/03/22 se le elimina el IVA
					product_id =  product['product_id']
					etiqueta_impresion = get_substatus_shipment_label_meli (id_order, access_token)
					print('ETIQUETA DE IMPRESION: ', etiqueta_impresion)
					
					#-- Obteniendo el Descuento 
					diferencia = round((precio_venta_odoo*1.16) - precio_vendido_meli,2)
					#porcentaje_descuento = round((diferencia * 100)/ (precio_venta_odoo*1.16),2) Nota: Se comenta el calculo de descuento 04/03/22
					print ('DIFERENCIA:', diferencia, 'DESCUENTO: Ya no incluye descuento', )
					print('PRODUCTO NORMAL->', 'STOCK NETO ODOO',stock_neto_odoo,'PRECIO VENTA ODOO:',precio_venta_odoo,'PRECIO VENDIDO MELI:',precio_vendido_meli, 'MARCA EN ODOO:',marca_producto_odoo )
					
					if (quantity <= stock_neto_odoo) and (etiqueta_impresion==True): #Nota: Se comenta el calculo de descuento 04/03/22 (porcentaje_descuento < 15.00) and 
						print ('SI AUTOCONFIRMAR')
						autoconfirmar = True
					else:
						print ('NO AUTOCONFIRMAR')
						autoconfirmar = False
						if  logistic_type =='fulfillment':
							autoconfirmar = True
					#======== Fin de la validación para autoconfirmar =============================================			

					if product:
						item_selled['seller_sku'] = seller_sku
						item_selled['product_id'] = product_id
						item_selled['quantity'] = quantity
						item_selled['unit_price'] = unit_price

						list_items.append(product_id)
						list_item_selled.append(item_selled)

						#lineas_pedido.append( (0,0,{'product_id': product_id,'product_uom':1, 'product_uom_qty':quantity, 'price_unit': unit_price, 'name': title}) )

						lineas_pedido.append( (0,0,{'product_id': product_id,'product_uom':1, 'product_uom_qty':quantity, 'price_unit': precio_vendido_meli, 'name': title}) ) #Nota: Se comenta el calculo de descuento 04/03/22 'discount': porcentaje_descuento,

					print ('SKU', seller_sku, 'Product id: ', product_id, item_selled)

			print ('Lineas de pedido: ', lineas_pedido)
	
			
			#print ('RECUPERANDDO EL ID DEL CLIENTE DE MERCADO LIBRE')
			name='Mercado Libre API' # Cliente de Mercado Libre
			partner_id = get_id_odoo_buyer_by_name(name)
			#print ('partner_id: ', partner_id)

			#print ('RECUPERANDDO EL ID DEL COMERCIAL')
			usuario='Karen Monroy' # Comercial
			comercial_id = consulta_users(usuario)
			#print ('comercial_id', comercial_id)

			tipo_orden ='NORMAL'

			return dict(id_order=id_order, fulfilled=fulfilled, order_status=order_status, date_created=date_created,seller_nickname=seller_nickname, buyer_name=buyer_name, buyer_email=buyer_email, partner_id=partner_id, shipping_id=shipping_id, shipment=shipment, list_items=list_items, lineas_pedido=lineas_pedido,quantity=quantity,comercial_id=comercial_id, total_paid_amount=payment_total_paid_amount, transaction_amount=payment_transaction_amount, market_place_fee=payment_market_place_fee, shipping_cost=payment_shipping_cost, status_detail=payment_status_detail, logistic_type=logistic_type, shipping_labels=shipping_labels, es_combo=es_combo, combo_detail=combo_detail,payment_method_id=payment_method_id, autoconfirmar=autoconfirmar, tipo_orden=tipo_orden
			)
		else:
			print ('La ordern : '+order_id+' No se encontro!')
			return False
	
	except Exception as e:
		print ('Error en get_order_meli(): '+ str(e) )
		return False

def get_order_meli_multi(seller_id, pedidos_de_carrito, access_token):
	try:

		lista_ids=''
		for order_id in pedidos_de_carrito:
			lista_ids+=str(order_id)+','

		ids = lista_ids[:-1]
		print ('IDS MULTI: ',ids )
		shipping_labels=''
		headers = {'Accept': 'application/json','content-type': 'application/json', 'x-format-new': 'true', 'Authorization': 'Bearer '+ access_token}
		url = 'https://api.mercadolibre.com/multiget?resource=orders&ids='+str(ids)+'&access_token='+str(access_token)
		#print (url)
		r=requests.get(url, headers=headers)
		#print (json.dumps(r.json(), indent=4, sort_keys=True))
		numero_pedidos= len(r.json()[0])
		lineas_pedido=[]
		list_items=[]
		list_item_selled=[]
		payment_shipping_cost = 0.0
		payment_total_paid_amount = 0.0
		payment_transaction_amount = 0.0
		ids_order=''
		feedback = None
		combo_detail =''
		pedidos_de_carrito= r.json()[0]
		for pedido in pedidos_de_carrito:
			order = pedido['body']
			pack_id_order = order['pack_id']

			id_order = order['id']
			order_status = order['status']
			date_created = order['date_created'][:-10]
			shipping_id = order['shipping']['id']
			
			id_order = order['id']
			order_status = order['status']
			date_created = order['date_created'][:-10]
			shipping_id = order['shipping']['id']
	
			order_items = order['order_items']
			feedback = order.get('feedback').get('sale')
			print ('SHIPPING_ID: ',shipping_id)
			print ('FEEDBACK: ',id_order, feedback)
			
			if shipping_id:
				shipment = get_shipment_meli(shipping_id, access_token)
				print ('SHIPMENT', shipment)
				shipping_labels = 'https://api.mercadolibre.com/shipment_labels?shipment_ids='+str(shipping_id)+'&response_type=zpl2&access_token='

			else:
				shipment = dict(status="null", tracking_number="0", tracking_method="null")
				shipping_labels = ''

			fulfilled = False
			if feedback==None:
				fulfilled = False	
			else: 
				fulfilled = feedback['fulfilled']
				#fulfilled_id = feedback['fulfilled']['id']

			print ('FULFILLED: ', fulfilled)
			
			buyer_name = order['buyer']['nickname'] #+'/'+order['buyer']['first_name']+ ' '+order['buyer']['last_name']
			buyer_email = ''#order['buyer']['email']
			seller_nickname = order['seller']['nickname']

			#--- Pago
			payments = order['payments']
			for payment in payments:
				#payment_market_place_fee = payment['marketplace_fee']

				payment_market_place_fee=0.0
				payment_shipping_cost += payment['shipping_cost']
				payment_total_paid_amount += payment['total_paid_amount']
				payment_transaction_amount += payment['transaction_amount']
				payment_status_detail = payment['status_detail']

				payment_method_id = payment['payment_method_id']
				payment_type = payment['payment_type']
				payment_method_id = get_payment_method_id(payment_type)

				#print ('PAGO: ', payment_total_paid_amount, payment_transaction_amount, payment_market_place_fee, payment_total_paid_amount, payment_status_detail, payment_method_id, payment_type )

			item_selled = {}
			#lineas_pedido=[]
			es_combo=False
			
			autoconfirmar=False # autoconfirmar sera TRUE si todos los productos cumplen las validaciones
			for item in order_items:
				#print( item)
				mlm = item['item']['id']
				logistic_type  = get_logistic_type_item_meli(mlm, access_token)	
				seller_sku = item['item']['seller_sku']
				print ('SELLER SKU: ', seller_sku, 'MLM: ', mlm, 'LOGISTICA MELI: ', logistic_type)

				if seller_sku==None: #  No todos los productos tienen este campo ... buscar en seller_custom_field
					print ('NO TIENE SELLER SKU')
					seller_custom_field = item['item']['seller_custom_field']
					print ('seller_custom_field: ', seller_custom_field)
					seller_sku=seller_custom_field

					

				title =  item['item']['title']
				#sale_fee = item['sale_fee']
				unit_price = item['unit_price']/1.16
				quantity = item['quantity']	
				print ('seller_sku->', seller_sku, quantity)

				if 'COMBO' in seller_sku:
					combo = get_id_odoo_product_kit(seller_sku, title, id_order,logistic_type, unit_price)
					#lineas_pedido = combo['lineas_pedido']
					lineas_pedido.append(combo['lineas_pedido']) # ****Atencion adición los combos pueden ser mas de 1 combo
					print('LINEA DE PEDIDO COMBO: ', lineas_pedido)
					list_items = combo['list_items']
					stock_neto_odoo = combo['stock_neto_odoo_combo']
					#porcentaje_descuento = combo['porcentaje_descuento_combo'] Nota: Se comenta el calculo de descuento 04/03/22
					etiqueta_impresion = get_substatus_shipment_label_meli (id_order, access_token)
					print('ETIQUETA DE IMPRESION: ', etiqueta_impresion)
					print('COMBOS PEDIDOS:', quantity, 'COMBOS EXISTENTES',stock_neto_odoo )

					if (quantity <= stock_neto_odoo) and (etiqueta_impresion==True): #Nota: Se comenta el calculo de descuento 04/03/22 (porcentaje_descuento < 15.00) and 
						print ('SI AUTOCONFIRMAR')
						autoconfirmar = True
					else:
						print ('NO AUTOCONFIRMAR')
						autoconfirmar = False
						if  logistic_type =='fulfillment':
							autoconfirmar = True

					es_combo=True
					combo_detail+=str(seller_sku)+'|'+str(title)+'|'+str(quantity)+'|$'+str(item['unit_price'])
				else:
					product= get_id_odoo_product(seller_sku, title, id_order)
					product_id = product['product_id']
					
					#======== Si encontramos el producto, validar para autoconfirmación productos Multi=========				
					stock_neto_odoo = product['stock_neto']
					precio_venta_odoo = product['precio_venta']
					marca_producto_odoo = product['categ_id']
					precio_vendido_meli = item['unit_price']/1.16 #NOTA: 07/03/22 se elimina el IVA
					product_id =  product['product_id']
					etiqueta_impresion = get_substatus_shipment_label_meli (id_order, access_token)

					print('ETIQUETA DE IMPRESION: ', etiqueta_impresion)
					#-- Obteniendo el Descuento 
					diferencia = round((precio_venta_odoo*1.16) - precio_vendido_meli,2)
					print('DIFERENCIA:', diferencia)
					#porcentaje_descuento = round((diferencia * 100)/ (precio_venta_odoo*1.16),2) #Nota: Se comenta el calculo de descuento 04/03/22
					#print ('DESCUENTO:', porcentaje_descuento)

					print('PRODUCTO CARRO->', 'STOCK NETO ODOO',stock_neto_odoo,'PRECIO VENTA ODOO:',precio_venta_odoo,'PRECIO VENDIDO MELI:',precio_vendido_meli, 'MARCA EN ODOO:',marca_producto_odoo )
					if (quantity <= stock_neto_odoo) and (etiqueta_impresion==True): #Nota: Se comenta el calculo de descuento 04/03/22 (porcentaje_descuento < 15.00) and 
						print ('SI AUTOCONFIRMAR')
						autoconfirmar = True
					else:
						print ('NO AUTOCONFIRMAR')
						autoconfirmar = False
						if  logistic_type =='fulfillment':
							autoconfirmar = True
					#======== Fin de la validación para autoconfirmar =============================================			
					
					
					if product:
						item_selled['seller_sku']=seller_sku
						item_selled['product_id']=product_id
						item_selled['quantity']=quantity
						item_selled['unit_price']=unit_price

						list_items.append(product_id)			
						list_item_selled.append(item_selled)

						#lineas_pedido.append( (0,0,{'product_id': product_id,'product_uom':1, 'product_uom_qty':quantity, 'price_unit': unit_price, 'name': title}) ) 
						lineas_pedido.append( (0,0,{'product_id': product_id,'product_uom':1, 'product_uom_qty':quantity, 'price_unit': precio_vendido_meli, 'name': title}) ) #Nota: Se comenta el calculo de descuento 04/03/22 'discount': porcentaje_descuento, 


					print ('SKU MULTI', seller_sku, 'Product id: ', product_id, item_selled)

			print ('Lineas de pedido: ', lineas_pedido)
	
			
			print ('RECUPERANDDO EL ID DEL CLIENTE DE MERCADO LIBRE')
			name='Mercado Libre API' # Cliente de Mercado Libre
			partner_id = get_id_odoo_buyer_by_name(name)
			print ('partner_id: ', partner_id)

			#print ('RECUPERANDO EL ID DEL COMERCIAL')
			usuario='Moises Santiago' # Comercial
			#comercial_id = consulta_users(usuario)
			comercial_id = 6
			#print ('comercial_id', comercial_id)
			ids_order=str(pack_id_order)+':'+str(ids)
			print ('IDS PASADOS: ', ids_order)

		tipo_orden='CARRITO'

		return dict(id_order=ids_order, fulfilled=fulfilled, order_status=order_status, date_created=date_created,seller_nickname=seller_nickname,	buyer_name=buyer_name, buyer_email=buyer_email, partner_id=partner_id, shipping_id=shipping_id, shipment=shipment, list_items=list_items, lineas_pedido=lineas_pedido,quantity=quantity,comercial_id=comercial_id, total_paid_amount=payment_total_paid_amount, transaction_amount=payment_transaction_amount, market_place_fee=payment_market_place_fee, shipping_cost=payment_shipping_cost, status_detail=payment_status_detail, logistic_type=logistic_type, shipping_labels=shipping_labels, es_combo=es_combo, combo_detail=combo_detail, payment_method_id=payment_method_id, autoconfirmar=autoconfirmar, tipo_orden=tipo_orden)
		
	except Exception as e:
		print ('Error en get_order_meli_multi() '+ str(e) )
		return False

#----MAPEO Y CREACION DE LA ORDEN DE VENTA EN ODOO SO--------------------------------------------------------------------------------------
def make_map_meli_odoo(meli_data):
	try:
		name_team = 'Mercado Libre' 
		team_id = consulta_team(name_team)
		order_status = meli_data['order_status']
		list_items = meli_data['list_items']
		lista_productos = meli_data['lineas_pedido']							
		marketplace_order_id = meli_data['id_order']
		status = meli_data['order_status']

		shipping_labels=''
		autoconfirmar_pedido=False
		existe_orden = verify_exist_order_in_odoo(marketplace_order_id)# True ya nola crea, False La crea
		#existe_orden=False #**************PRODUCCCION QUITAR****************
		print('ID DE LA ORDEN EN ODOO:',existe_orden)

		if existe_orden:
			if status=='cancelled':
				print ('La Orden esta Cancelada Meli')
			else:
				print ('La Orden ya Existe en Odoo, actualizar')
				tracking_number = meli_data['shipment']['tracking_number']
				tracking_method = meli_data['shipment']['tracking_method']
				if tracking_method==None or tracking_number==None:
					pass
				else:
					tracking_number = meli_data['shipment']['tracking_number']
					tracking_method = meli_data['shipment']['tracking_method']
					print (tracking_method+'/'+tracking_number)
					update_sale_order(existe_orden, marketplace_order_id, tracking_method,  tracking_number)
		else:#====== NO existe la Orden, procesamiento para crear el PAYLOAD

			fecha_orden_venta_string = meli_data['date_created']
			fecha_orden_venta_datetime = datetime.strptime(fecha_orden_venta_string, '%Y-%m-%dT%H:%M:%S')
			ahora = datetime.now()
			fecha_hora_actual_utc = str(ahora.utcnow())[:-7] #
			
			tracking_method = meli_data['shipment']['tracking_method']
			if tracking_method==None:
				tracking_method =''
			
			tracking_number = meli_data['shipment']['tracking_number']
			if tracking_number==None:
				tracking_number=''
			
			state_so = 'draft' # Inicializamos Orden como Presupuesto de Venta
			warehouse_id=None
			if meli_data['logistic_type']=='fulfillment':                        #'Meli Fulfilment'
				warehouse_name='Mercado Libre Full'                              # Tomamos el stock del almacen Mercado Libre Full de Odoo
				warehouse_id = get_meli_ful_warehouse_id_by_name(warehouse_name) # Si es de Fulfillment...
				state_so = 'sale'                                                # Creamos automáticamente el Pedido de Venta
				print ('PEDIDO DE VENTA DE FULLFILMENT')
			else:
				warehouse_id=1
				shipping_labels=meli_data['shipping_labels']				
				state_so = 'draft'
				print('tipo lista_productos[0]', type(lista_productos[0]) )#30/08
				
				#----------------------Para reservar--------------------------------------------------------------------------
				productos=[]
				print ('INICIA PROCESO DE RESERVADO======================>')
				print ('LISTA DE PRODUCTOS:',lista_productos )
				print ('TIPO PRIMER ELEMENTO DE LISTA:',type(lista_productos[0] ))
				print ('TIPO LOGISTICA:', meli_data['logistic_type'])
				
				if len(lista_productos)==1 and  str(type(lista_productos[0])) =="<class 'tuple'>":
					lista_productos=lista_productos	

					for productos in lista_productos:
						if meli_data['logistic_type']!='fulfillment':
							product_id = productos[2]['product_id']
							product_uom_qty = productos[2]['product_uom_qty']
							print('RESERVAR  DE PRODUCT_ID: ', product_id, 'CANTIDAD: ', product_uom_qty)

							resultado_reservado = update_stock_reservado(product_id, product_uom_qty, status)
							print ('RESERVADO:'+str(meli_data['date_created'])+'|'+str( meli_data['id_order'])+'|'+str(product_id)+'|'+str(resultado_reservado[0]['default_code'])+'|'+str(product_uom_qty)+'|'+status)
							logging.info('RESERVADO:'+str(meli_data['date_created'])+'|'+str( meli_data['id_order'])+'|'+str(product_id)+'|'+str(resultado_reservado[0]['default_code'])+'|'+str(product_uom_qty)+'|'+status)		
						else:
							print('LISTA DE PRODUCTOS TUPLA: ',lista_productos )
							product_id = productos[0][2]['product_id']
							print('PRODUCT_ID', product_id)
							print ('La orden no existe y se creara')
							product_uom_qty = productos[0][2]['product_uom_qty']
					print ('TERMINA PROCESO DE RESERVADO======================>')
				#-------------Fin Reserva---------------------------------------------------------------------------------------
		
			comercial_id = meli_data['comercial_id']
			quantity = meli_data['quantity']
			lineas_pedido = meli_data['lineas_pedido']

			print('LINEAS PEDIDO antes:',lineas_pedido)
			print('LINEAS PEDIDO type:',str(type(lineas_pedido[0])))
			
			if len(lineas_pedido)==1 and str(type(lineas_pedido[0]) )=="<class 'list'>":
				lineas_pedido=lista_productos[0]

			print('LINEAS PEDIDO despues:',lineas_pedido)

			es_combo = meli_data['es_combo']
			
			if es_combo == True:
				state_so = 'draft' #---- para que revisen los precios no permitir la confirmación. #20201109

			combo_detail = meli_data['combo_detail']
			payment_method_id = meli_data['payment_method_id']
			shipping_id = meli_data['shipping_id']
			print ('SHIPING_ID al crear la Orden:',shipping_id)
			tipo_orden=meli_data['tipo_orden']
			autoconfirmar_pedido= meli_data.get('autoconfirmar')
			print('TIPO DE ORDEN:',tipo_orden)
			print('AUTOCONFIRMAR:',autoconfirmar_pedido)
			comentario_autonfirmacion=''
			if autoconfirmar_pedido == True :
				comentario_autonfirmacion='AUTOCONFIRMADO'
				state_so = 'sale'
			else:
				comentario_autonfirmacion=''

			values = {
			'partner_id': meli_data['partner_id'],
			'state': state_so,
			'confirmation_date': fecha_hora_actual_utc, #fecha_hora_actual_utc,
			'payment_term_id': 1,
			'user_id':comercial_id, 
			'order_line':lineas_pedido,
			'commitment_date': fecha_orden_venta_string,
			'tracking_number': tracking_method+'/'+tracking_number,
			'etiqueta_meli':shipping_labels, 
			'marketplace':'MERCADO LIBRE',
			'marketplace_order_id':marketplace_order_id,
			'seller_marketplace': meli_data['seller_nickname'],
			'date_created': fecha_orden_venta_string,
			'correo_marketplace':meli_data['buyer_email'],
			'client_order_ref' : meli_data['buyer_name'],
			'order_status':meli_data['order_status'],
			'warehouse_id':warehouse_id, 
			'picking_policy':'one',
			'combo':es_combo,
			'combo_detail':combo_detail,
			'team_id':team_id, 
			'l10n_mx_edi_payment_method_id':payment_method_id,
			'shipping_id':shipping_id,
			'comments': comentario_autonfirmacion,  
			}
			print ('PAYLOAD: ', values)
			logging.info('PAYLOAD|'+ str(values) )
			data = {
				'model': "sale.order",
				'values': json.dumps(values),
			}
			#print (data)

			response = api.execute('/api/create', type="POST", data=data)
			#print ('Respuesta al intentar crear la Orden en Odoo: ',response)
			return response
			print ('===============================================================================================')
		
		#else:
		#	print 'No se encontraron los articulos'
		#	return False
	
	except Exception as e:
		print ('Error make_map_meli_odoo(): '+str(e))
		return False


def procesa_pedido_normal(orden, access_token):
	try:
		result=''
		if orden:
			order_id =orden['id_order']  	
			order_status = orden['order_status']
			shipment_status = orden['shipment']['status']
			tracking_method = orden['shipment']['tracking_method']
			tracking_number = orden['shipment']['tracking_number']
			market_place_fee = orden['market_place_fee']
			shipping_cost = orden['shipping_cost']
			total_paid_amount = orden['total_paid_amount']
			transaction_amount = orden['transaction_amount']
			status_detail = orden['status_detail']

			autoconfirmar = orden['autoconfirmar']
			print ('AUTOCONFIRMAR NORMAL: ',autoconfirmar )
			aviso_autoconfirmado=''
			if autoconfirmar==True:
				aviso_autoconfirmado = ' AUTOCONFIRMADO'
			else:
				aviso_autoconfirmado=''

			result  = make_map_meli_odoo(orden)
			print ('Resultado al intentar crear la Orden: ', result, ' Order Id: ', order_id)
			if result:
				#update_orders_saved(order_id, order_status,shipment_status,tracking_method,tracking_number, str(result), market_place_fee, shipping_cost, total_paid_amount, transaction_amount, status_detail)
				so_name = get_name_order_in_odoo(result[0])
				print ('La orden se ha generado en Odoo con nombre: ' + str(so_name) )
				
				colocar_nota_a_orden_meli(so_name+aviso_autoconfirmado, order_id, access_token)
				origin=so_name
				carrier_tracking_ref = tracking_number
				picking_ids = get_picking_ids_order_in_odoo(origin)
				update_pick_carrier_tracking_ref(picking_ids, carrier_tracking_ref)
			return so_name
		else:
			return result
		

		return so_name
	except Exception as e:
		return False
		print ('Error procesa_pedido_normal(): ' +str (e) )
		print ('========================================================================================')
		


def procesa_pedido_carrito(orden, access_token):
	try:
		result=''
		if orden:
			order_status = orden['order_status']
			shipment_status = orden['shipment']['status']
			tracking_method = orden['shipment']['tracking_method']
			tracking_number = orden['shipment']['tracking_number']

			market_place_fee = orden['market_place_fee']
			shipping_cost = orden['shipping_cost']
			total_paid_amount = orden['total_paid_amount']
			transaction_amount = orden['transaction_amount']
			status_detail = orden['status_detail']
			autoconfirmar = orden['autoconfirmar']
			
			print ('AUTOCONFIRMAR CARRO: ',autoconfirmar )
			aviso_autoconfirmado=''
			if autoconfirmar==True:
				aviso_autoconfirmado = ' AUTOCONFIRMADO'
			else:
				aviso_autoconfirmado=''

			order_ids=orden['id_order']
			pack_orders = order_ids.split(':')
			print (pack_orders)
			orders=pack_orders[1].split(',')
		
			result  = make_map_meli_odoo(orden)
			print ('Resultado al intentar crear la Orden: ', result, ' Order Id: ', order_ids)
			for order_id in orders:
				print (order_id)
				if result: #NOTA: Aclarar porque esto está comentado 
					#update_orders_saved(order_id, order_status,shipment_status,tracking_method,tracking_number, str(result), market_place_fee, shipping_cost, total_paid_amount, transaction_amount, status_detail)
					so_name = get_name_order_in_odoo(result[0])

					print (order_id, ' La orden se ha generado en Odoo con nombre: ' + str(so_name) )
					colocar_nota_a_orden_meli(so_name+aviso_autoconfirmado, order_id, access_token)	
					origin = so_name
					carrier_tracking_ref = tracking_number
					picking_ids = get_picking_ids_order_in_odoo(origin)
					update_pick_carrier_tracking_ref(picking_ids, carrier_tracking_ref)
			return so_name
		else:
			return result
			print (result)

	except Exception as e:
		return False
		print ('Error procesa_pedido_carrito(): ' +str (e) )


if __name__ == '__main__':
	date_time = datetime.now()
	date_time_iso= date_time.isoformat() 
	fecha=date_time_iso.split('T')[0]
	#0. Definimos si es de Ventas u Oficiales
	seller_id = 25523702
	#1. Extraemos su Token
	access_token=recupera_meli_token(seller_id)
	#2. Capturamos la Orden de Meli
	order_id = '4807684289'
	#3. Extraer el Shipment
	shipment_order = get_shipment_order_meli(seller_id, order_id, access_token)
	shipping_id = shipment_order.get('shipping_id')
	pack_id = shipment_order.get('pack_id')
	print(shipping_id, pack_id)
	
	ordenes=[]
	if pack_id:
		print('Buscando pedidos del carrito')
		ordenes_meli = get_order_ids_from_carrito(shipping_id, access_token)	
		#4. Crear el formato de creación
		for orden in ordenes_meli:
			#print(orden)
			la_orden=(str(seller_id),str(pack_id),orden)
			print(la_orden)
			ordenes.append(la_orden)

	else:
		print('No es carrito')
		orden=(str(seller_id), str(order_id), str(order_id) )
		ordenes.append(orden)
	
	ordenes.append( ('25523702', '1000000000', '1000000000') )
	print(ordenes)
