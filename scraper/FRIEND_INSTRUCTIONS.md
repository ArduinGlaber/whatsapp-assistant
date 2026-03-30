# Facebook Marketplace Scraper

## Para tu amigo (instrucciones simples)

### Paso 1: Descargar el proyecto
1. Ve a: https://github.com/ArduinGlaber/whatsapp-assistant
2. Click en el botón verde **"Code"**
3. Click en **"Download ZIP"**
4. Descomprime el archivo

### Paso 2: Instalar Python
1. Descarga Python desde: https://www.python.org/downloads/
2. Durante la instalación, marca **"Add Python to PATH"**
3. Verifica que esté instalado: abre CMD y escribe `python --version`

### Paso 3: Instalar GitHub CLI (necesario para subir la DB)
1. Descarga de: https://cli.github.com/manual/installation
2. O sigue las instrucciones para Windows/Mac
3. después de instalar, abre CMD y escribe:
   ```
   gh auth login
   ```
4. Sigue las instrucciones para autenticarte con GitHub

### Paso 4: Configurar credenciales
1. Crea un archivo `.env` en la carpeta `scraper/` con este contenido:
   ```
   FACEBOOK_EMAIL=jevargas910127@gmail.com
   FACEBOOK_PASSWORD=V1rg1$64
   ```

### Paso 5: Ejecutar el scraper
1. Abre la carpeta `whatsapp-assistant-main`
2. Ve a la carpeta `scraper/`
3. **Windows**: Doble click en `run_scraper.bat`
4. **Mac/Linux**: Ejecuta `bash run_scraper.sh` en la terminal

### Paso 6: Esperar
- El scraper va a abrir Chrome, loguearse en Facebook y extraer listings
- Puede tardar 5-15 minutos dependiendo de la cantidad de posts
- Cuando termine, verás "Scraper completado!"

### Frecuencia recomendada
- Puedes correrlo cada 1-2 horas (sin límite)
- Facebook no va a bloquearte si no lo haces muy seguido
- Recomendado: cada 4-6 horas

---

## Solución de problemas

### Error: "Python no está instalado"
Descarga Python desde https://www.python.org/downloads/ y marca "Add to PATH"

### Error: "gh no está instalado"
Descarga GitHub CLI desde https://cli.github.com/

### Error: "Login failed"
Facebook puede pedir verificación. En ese caso:
1. En tu navegador, anda a m.facebook.com
2. Logueate manualmente
3. Completa cualquier verificación que pida
4. Intenta de nuevo

### El script se cierra muy rápido
Abre CMD, ve a la carpeta scraper y ejecuta:
```
python -m scraper.main --db-path data\listings.db
```
Así verás los errores en la pantalla

---

## ¿Qué hace el script?
1. Se loguea en Facebook con las credenciales
2. Entra al grupo de compra/venta
3. Extrae los posts con artículos y precios
4. Guarda todo en una base de datos
5. Sube la base de datos a GitHub (donde el bot la descarga)
