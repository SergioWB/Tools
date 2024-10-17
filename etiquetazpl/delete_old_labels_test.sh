#!/bin/bash

# Directorio donde están las subcarpetas
DIRECTORIO="/home/ubuntu/Documents/server-Tln/Tools/etiquetazpl/Etiquetas"

# Elimina las carpetas modificadas hace más de 1 hora
find "$DIRECTORIO" -type d -mmin +60 -exec rm -rf {} \;

# Mensaje de confirmación
echo "Carpetas modificadas hace más de 1 hora han sido eliminadas."
