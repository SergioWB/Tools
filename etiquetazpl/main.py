#!/usr/bin/python3

import sys
sys.path.append('/home/server-tnp')

from meli import get_access_token_meli
from meli import get_access_token_meli_oficiales
from etiquetazpl import app as ap
import pytz
import datetime
import time

time.sleep(5)

if __name__ == '__main__':
	try:
		client_id='5703097592380294'
		client_secret='Fn5yHq1e1DBgy2EiRk7rLhsyRexcZYAQ'
		access_tokens = get_access_token_meli.obtener_token_meli(client_id, client_secret)
		if access_tokens:
			access_token = access_tokens['access_token']
			refresh_token = access_tokens['refresh_token']
			token_type = access_tokens['token_type']
			expires = access_tokens['expires_in']
			time_zone= pytz.timezone('America/Mexico_City')
			Mexico_City_time = datetime.datetime.now(tz=time_zone)
			fecha = Mexico_City_time.isoformat(' ')[:-13]
			last_date_retrieve = fecha


		client_id='5630132812404309'
		client_secret='mptf9EnLyuEIWcIoUbrj8dIBkgHGAZAI'
		access_tokens = get_access_token_meli_oficiales.obtener_token_meli_oficiales(client_id, client_secret)
		if access_tokens:
			access_token = access_tokens['access_token']
			refresh_token = access_tokens['refresh_token']
			token_type = access_tokens['token_type']
			expires = access_tokens['expires_in']
			time_zone= pytz.timezone('America/Mexico_City')
			Mexico_City_time = datetime.datetime.now(tz=time_zone)
			fecha = Mexico_City_time.isoformat(' ')[:-13]
			last_date_retrieve = fecha
            #api.update_tokens_in_odoo(client_id, access_token, refresh_token, token_type, expires, last_date_retrieve)      
	except Exception as e:
		raise e

	ap.app.run(host='0.0.0.0', port=8000, debug=True)
