import socket
import os 

def imprime_zpl(so_name):
	
	dir_path = os.path.dirname(os.path.realpath(__file__))
	print (dir_path)
	etiqueta_imprimir = dir_path + '/Etiquetas/Etiqueta_'+so_name+'/Etiqueta de envio.txt'
	print (etiqueta_imprimir)
	zpl_meli = open (etiqueta_imprimir) 
	zpl = zpl_meli.read()
	print (zpl)

	mysocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)         
	host = "10.99.0.14" 
	port = 9100   
	
	try:

		datos=bytes(zpl, 'utf-8')
		print (datos)
		mysocket.connect((host, port)) #connecting to host
		mysocket.send(datos)#using bytes
		mysocket.close () #closing connection
		print ('Etiqueta para la orden ' +so_name+'se ha impreso con exito')
	except:
		print("Error with the connection")

if __name__ == "__main__":

	so_name = 'SO199054'
	imprime_zpl(so_name)
	Moisantgar2018@