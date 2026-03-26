# WhatsApp Assistant

Asistente de WhatsApp con scraping de Facebook para marketplace.

## Estructura del Proyecto

```
whatsapp-assistant/
├── cmd/
│   └── bot/              # Bot WhatsApp (Go)
├── scraper/               # Scraper de Facebook (Python)
│   ├── main.py
│   ├── facebook.py
│   ├── parser.py
│   ├── ocr.py
│   ├── storage.py
│   └── requirements.txt
├── internal/
│   ├── whatsapp/
│   ├── ai/
│   ├── storage/
│   └── models/
├── migrations/
├── data/                  # Datos (DB, cookies)
├── .env                   # Credenciales (NO committing)
├── .gitignore
└── go.mod
```

## Setup

### 1. Dependencias del Sistema

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-spa

# Install Playwright browsers
playwright install chromium
```

### 2. Python Environment

```bash
cd scraper
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 3. Credenciales

El scraper usa credenciales de Facebook desde `.env`:

```
FACEBOOK_EMAIL=tu@email.com
FACEBOOK_PASSWORD=tu_password
```

## Uso del Scraper

### Primera ejecución

```bash
cd scraper
source venv/bin/activate
python -m scraper.main --group-id 774703760229907 --max-posts 50
```

### Flags disponibles

| Flag | Descripción | Default |
|------|-------------|---------|
| `--group-id` | ID del grupo de Facebook | 774703760229907 |
| `--max-posts` | Número máximo de posts | 50 |
| `--headless` | Ejecutar navegador sin UI | true |

## Base de Datos

La base de datos SQLite se crea automáticamente en `data/listings.db`.

### Tablas principales:

- `groups` - Grupos de Facebook configurados
- `listings` - Anuncios extraídos
- `conversations` - Conversaciones de WhatsApp
- `messages` - Mensajes individuales
- `scraping_logs` - Log de operaciones de scraping

## Desarrollo Futuro

- [ ] Bot WhatsApp (Go + whasmeow)
- [ ] Integración con Ollama
- [ ] Migración a Termux/Android
