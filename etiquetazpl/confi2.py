
import json
import sys
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
def ubicacion_impresoras():
	archivo_comfiguracion = dir_path + '/' + str(sys.argv[1])
	print (archivo_comfiguracion)
	with open(archivo_comfiguracion, 'r') as file:
		config = json.load(file)

	print (config)

	try:
		EMPACADO = config['EMPACADO']
		print('EMPACADO',EMPACADO)
		PICKING = config['PICKING']
		print ('PICKING',PICKING)
	except KeyError:
		print("Error en la clave ")


if __name__ == "__main__":
	ubicacion_impresoras()
