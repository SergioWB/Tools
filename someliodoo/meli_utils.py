#!/usr/bin/python
import sys
import json
import requests
import datetime
from datetime import datetime, date, time, timedelta
import pprint 
import logging
#from connector_mariadb import *
from collections import OrderedDict


#connect=connect_to_orders()
#cursor=connect['cursor']
#connection_object=connect['connection_object']

def get_result_orders():
	try:
		#print 'Recuperando ordenes notificadas....'
		query='SELECT user_id, car_id, order_id FROM notify_meli WHERE status_order IS NULL or status_order="";'
		cursor.execute(query)
		result = cursor.fetchall()
		cursor.close()
		connection_object.close()
		return result
	except mysql.connector.Error as mysql_error:
		print ("Error executing query: %s" % (str(mysql_error)) )
		return False


def recupera_meli_token(user_id):
	try:
		#print 'USER ID:', user_id
		token_dir=''
		if user_id == 25523702:# Usuario de SOMOS REYES VENTAS
			token_dir='/home/serverubuntu/meli/tokens_meli.txt' 
		elif user_id == 160190870:# Usuario de SOMOS REYES OFICIALES
			token_dir='/home/serverubuntu/meli/tokens_meli_oficiales.txt'
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
	
def get_shipment_meli(shipping_id, access_token):
	try:
		headers = {'Accept': 'application/json','content-type': 'application/json', 'x-format-new': 'true', 'Authorization': 'Bearer '+ access_token}
		url='https://api.mercadolibre.com/shipments/'+str(shipping_id)+'?access_token='+access_token
		r=requests.get(url, headers=headers)
		results = r.json()
		#order_id=results['order_id']
		#order_cost=results['order_cost']
		status = results['status']
		tracking_number = results['tracking_number']
		tracking_method = results['tracking_method']
		return dict(status=status, tracking_number=tracking_number, tracking_method=tracking_method)
	except Exception as e:
		print (' Error get_shipment_meli: '+ str(e))
		return False

def get_logistic_type_item_meli(mlm, access_token ):
	try:
		headers = {'Accept': 'application/json','content-type': 'application/json', 'Authorization': 'Bearer '+ access_token}
		url='https://api.mercadolibre.com/items/'+mlm+'?access_token='+access_token
		r=requests.get(url, headers=headers)
		#print (json.dumps(r.json(), indent=4, sort_keys=True))
		existe_item = len( r.json()['shipping'])
		
		if existe_item:
			item = r.json()['shipping']
			#print(json.dumps(item, indent=4, sort_keys=True))
			shipping_logistic_type = item.get('logistic_type')
			print('LOGISTICA MELI:', shipping_logistic_type)
			return shipping_logistic_type
		else:
			return False	
			
	except Exception as e:
		print ('Error en get_logistic_type_item_meli() '+str(e) )
		return False

#def get_substatus_shipment_label_meli (order_id, access_token): 
#    try:
#        headers = {'Accept': 'application/json','content-type': 'application/json'}
#        url='https://api.mercadolibre.com/orders/'+str(order_id)+'/shipments?access_token='+access_token
#        r=requests.get(url, headers=headers)
        #print (json.dumps(r.json(), indent=4, sort_keys=True))
#        substatus = r.json()['substatus']
#        tracking_number = r.json()['tracking_number']
#        print ('SUBSTATUS: ',substatus, tracking_number)
        #print (results['receiver_address'])
        #print (json.dumps(results['receiver_address'], indent=4, sort_keys=True))
#        if tracking_number:
#        	return True
#        else:
#        	return False
#
#    except Exception as e:
#        print (' Error order_shipment_meli(): '+ str(e))
#        return False
#30/08/22
def get_substatus_shipment_label_meli (order_id, access_token):
	try:
		headers = {'Accept': 'application/json','content-type': 'application/json'}
		url='https://api.mercadolibre.com/orders/'+str(order_id)+'/shipments?access_token='+access_token
		r=requests.get(url, headers=headers)
		#print (json.dumps(r.json(), indent=4, sort_keys=True))
		shipment_id = r.json()['id']
		substatus = r.json()['substatus']
		tracking_number = r.json()['tracking_number']
		print ('SUBSTATUS: ',shipment_id,substatus, tracking_number)
		#print (results['receiver_address'])
		#print (json.dumps(results['receiver_address'], indent=4, sort_keys=True))
		if tracking_number:
			return True
		else:
			return False

	except Exception as e:
		print (' Error order_shipment_meli(): '+ str(e))
		return False
