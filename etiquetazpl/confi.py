
import json
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
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


if __name__ == "__main__":
	ubicacion_impresoras()
