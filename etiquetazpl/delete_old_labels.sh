#!/bin/bash

# Directorio donde están las subcarpetas
DIRECTORIO="/home/ubuntu/Documents/server-Tln/Tools/etiquetazpl/Etiquetas"

# Elimina las carpetas modificadas hace más de 30 días
find "$DIRECTORIO" -type d -mtime +30 -exec rm -rf {} \;

