#!/usr/bin/python
import requests
#from get_data_odoo import *
import pytz
import datetime

token_dir='/home/ubuntu/Documents/server-Tln/Tools/meli/tokens_meli_oficiales.txt'
# token_dir = r'C:\Users\Sergio Gil Guerrero\Documents\WonderBrands\Repos\Tools\Tools\tokens_meli_oficiales.txt'

def obtener_token_meli_oficiales(client_id, client_secret):
    try:
        archivo_tokens=open(token_dir, 'w')

        headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        }   
        
        url='https://api.mercadolibre.com/oauth/token?grant_type=client_credentials&client_id='+str(client_id)+'&client_secret='+str(client_secret)
        r=requests.post(url, headers=headers)
        archivo_tokens.write(str(r.text) )
        archivo_tokens.close()
        #print (r.json())
        return r.json()
    except Exception as e:
        print (str(e))
        return False

if __name__ == '__main__':
    try:
        client_id='5630132812404309'
        client_secret='mptf9EnLyuEIWcIoUbrj8dIBkgHGAZAI'

        access_tokens = obtener_token_meli_oficiales(client_id, client_secret)
        
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
    
