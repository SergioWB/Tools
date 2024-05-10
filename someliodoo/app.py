from flask import Flask, render_template, request, make_response, url_for, session 
import json
import requests
from pprint import pprint
import logging
import zipfile
import socket
import os 
from datetime import datetime
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

from process_orders_doo import *
from odoo_utils import *


logging.basicConfig(format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%Y-%d-%m %I:%M:%S %p',level=logging.INFO)

dir_path = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)
app.secret_key = 'esto-es-una-clave-muy-secreta'

@app.route('/')
def index():
	# Permite insertar el nombre de la localización de la impreslora dentro de SOMOS REYES
	return render_template("index.html" )

@app.route('/inicio', methods =['POST'])
def inicio():
	cuenta = request.form.get("cuenta").upper()
	session['cuenta'] = cuenta
	cuenta = session['cuenta']
	return render_template("formulario.html", cuenta=cuenta )

@app.route('/procesar', methods=['POST'])
def procesar():
	e=None
	try:
		so_oder_odoo=''
		cuenta = session['cuenta']
		id_meli_order = request.form.get("id_meli_order")
		print(id_meli_order)
		if cuenta == 'VENTAS':
			seller_id = 25523702
		elif cuenta == 'OFICIALES':
			seller_id = 160190870
		else:
			seller_id = None
		print(seller_id)

		access_token=recupera_meli_token(seller_id)
		print(access_token)

		shipment_order = get_shipment_order_meli(seller_id, id_meli_order, access_token)
		shipping_id = shipment_order.get('shipping_id')
		pack_id = shipment_order.get('pack_id')
		print(shipping_id, pack_id)
		ordenes=[]

		if pack_id:
			print('Buscando pedidos del carrito')
			ordenes_meli = get_order_ids_from_carrito(shipping_id, access_token)	
			#4. Crear el formato de creación
			for orden in ordenes_meli:
				la_orden=(str(seller_id),str(pack_id),orden)
				print(la_orden)
				ordenes.append(la_orden)
		else:
			print('No es carrito')
			orden=(str(seller_id), str(id_meli_order), str(id_meli_order) )
			ordenes.append(orden)

		ordenes.append( ('25523702', '1000000000', '1000000000') )
		ordenes.append(orden)
		print(ordenes)

		carro_anterior=None
		orden_anterior=None
		seller_anterior=None
		lista_pedidos=[]
		datos={}
		carro={}
		lista_carros=[]
		print('lista_carros', lista_carros)
		
		for orden in ordenes:
			seller={}
			carro={}
			seller_actual =orden[0] 
			carro_actual=orden[1]
			orden_actual=orden[2]

			if carro_actual==carro_anterior and seller_actual == seller_anterior:
				lista_pedidos.append(orden_anterior)

				print('CARRO ACTUAL ESIGUAL AL ANTERIOR',carro_actual, carro_anterior)
				print('LISTA PEDIDOS:', lista_pedidos)			
			else:
				#print('CARRO ACTUAL NO ESIGUAL AL ANTERIOR',carro_actual, carro_anterior)
				lista_pedidos.append(orden_anterior)

				seller['seller_id']=seller_anterior
				lista_pedidos.append(seller)

				carro['car_id']=carro_anterior
				lista_pedidos.append(carro)

				print ('Lista Pedidos: ',lista_pedidos)
				lista_carros.append(lista_pedidos)	
				lista_pedidos=[]

			carro_anterior=carro_actual
			orden_anterior=orden_actual
			seller_anterior=seller_actual

		#print ('Lista carros: ', lista_carros)
		print ('-'*110)


		for carro in lista_carros[1:]:
			carrito = carro[-1]['car_id']
			if carrito:
				carrito = carro[-1]['car_id']
				seller_id =  int(carro[-2]['seller_id'])
				pedidos= carro[:-2]
				print ('PROCESANDO ===> ',carrito, seller_id, pedidos)
				
				if len(carrito)>10: # Es Carrito de Compras
					print ('****SI ES CARRO: ',carro)
					#-----------------------------INICIO Nuevo 2019-12-02
					if len(pedidos)>10:
						access_token=recupera_meli_token(seller_id)
						pedidos1 = pedidos[:10] 
						print ('CARRO1:', carrito, pedidos1, seller_id)
						orden=get_order_meli_multi(seller_id, pedidos1, access_token)
						#print  ('CARRRO ORDEN1: ', orden )
						so_oder_odoo = procesa_pedido_carrito(orden, access_token)
						print ('============================================================================================================')

						otros =  len(pedidos) - 10
						pedidos2 =  pedidos[:otros] 
						#procesar el segundo grupo 
						#print ('CARRO2:', carrito, pedidos2, seller_id)
						orden=get_order_meli_multi(seller_id, pedidos2, access_token)
						#print  ('CARRRO ORDEN2: ', orden )
						so_oder_odoo = procesa_pedido_carrito(orden, access_token)
						print ('============================================================================================================')
					else:# Si tenemos un carrito hasta con 10 pedidos.
						#------------------------------FIN Nuevo 2019-12-02
						access_token=recupera_meli_token(seller_id)
						#print ('CARRO:', carrito, pedidos, seller_id )
						orden=get_order_meli_multi(seller_id, pedidos, access_token)

						#print  ('CARRRO ORDEN: ', orden )
						so_oder_odoo = procesa_pedido_carrito(orden, access_token)
						print ('============================================================================================================')

				else:
					access_token=recupera_meli_token(seller_id)
					print ('NORMAL', carrito, pedidos, seller_id )
					orden=get_order_meli(seller_id, pedidos[0], access_token)
					#print ('NORMAL ORDEN: ', orden)
					so_oder_odoo = procesa_pedido_normal(orden, access_token)
					print ('============================================================================================================' )


		so_oder_odoo = get_name_order_in_odoo_by_order_meli(id_meli_order)
		print ('RETORNANDO:',so_oder_odoo )

		respuesta='Orden Creada en odoo: '+str(so_oder_odoo)
		print('respuesta:', respuesta, id_meli_order, so_oder_odoo)

		formulario = 'mostrar.html'
	except Exception as e:
		order_id = ''
		respuesta = str(e)
		formulario = 'error.html'
		

	return render_template(formulario, id_meli_order=id_meli_order, so_oder_odoo = so_oder_odoo, respuesta = respuesta)


if __name__ == "__main__":

	app.run(host='0.0.0.0', port=8001, debug=True)