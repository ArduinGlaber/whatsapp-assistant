# Telegram Marketplace Bot - Documentación

Asistente de Telegram con scraping de Facebook para marketplace en Cuba.

## Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Arquitectura](#arquitectura)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Instalación](#instalación)
5. [Configuración](#configuración)
6. [Uso](#uso)
7. [Base de Datos](#base-de-datos)
8. [Parser de Listings](#parser-de-listings)
9. [Scraper de Facebook](#scraper-de-facebook)
10. [Bot de Telegram](#bot-de-telegram)
11. [Limitaciones](#limitaciones)
12. [Futuro](#futuro)

---

## Descripción General

Este proyecto automatiza la gestión de un marketplace en Telegram mediante:

- **Scraping automático** de grupos de Facebook de compra/venta
- **Extracción inteligente** de información de anuncios (artículo, precio, contacto)
- **Bot de Telegram** que responde consultas sobre productos disponibles
- **Base de datos local** para almacenamiento offline

### Por qué Telegram?

| Ventaja | Detalle |
|---------|---------|
| API oficial | Sin riesgo de ban |
| Solo token | No necesita teléfono online |
| Multi-device | Funciona en cualquier dispositivo |
| Simple | Desarrollo rápido |

### Contexto

Diseñado para usuarios en Cuba con limitaciones de conectividad (6GB/mes). Todas las operaciones son locales.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Marketplace Bot                      │
├──────────────────┬──────────────────┬───────────────────────┤
│   Facebook       │    Telegram      │      SQLite           │
│   Scraper       │      Bot         │      Database         │
│   (Python)      │     (Go)         │      (Local)         │
├──────────────────┴──────────────────┴───────────────────────┤
│                    Ollama (IA Local)                        │
│                    qwen2.5:1.5b                            │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de datos

```
Facebook → Scraper → Parser → SQLite DB ← Bot Telegram
                                       ↓
                                   Usuario
```

---

## Estructura del Proyecto

```
telegram-marketplace-bot/
├── scraper/              # Scraper de Facebook (Python)
│   ├── main.py           # Entrada principal
│   ├── get_groups.py     # Obtener grupos de Facebook
│   ├── facebook.py       # Login y scraping
│   ├── parser.py         # Extracción de listings
│   ├── ocr.py           # OCR con Tesseract
│   ├── storage.py        # Repositorio SQLite
│   └── requirements.txt  # Dependencias
├── bot/                  # Bot de Telegram (Go)
│   ├── main.go
│   └── handlers.go
├── internal/            # Código compartido
│   └── models/          # Entidades
├── migrations/           # Migraciones SQL
├── data/                 # Datos (DB, cookies)
├── .env                  # Credenciales
├── .gitignore
└── README.md
```

---

## Instalación

### Requisitos del Sistema

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-spa
```

### Python (Scraper)

```bash
cd scraper
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Go (Bot)

```bash
go mod init telegram-marketplace-bot
go get github.com/go-telegram-bot-api/telegram-bot-api/v5
```

---

## Configuración

### 1. Token de Telegram

Obtener token de [@BotFather](https://t.me/botfather):

1. Enviar `/newbot`
2. Dar nombre al bot
3. Obtener token tipo: `123456789:ABCdefGhIJKlmNoPQRsTUVwxYZ`

Crear archivo `.env`:

```env
TELEGRAM_BOT_TOKEN=tu-token-aqui
FACEBOOK_EMAIL=tu@email.com
FACEBOOK_PASSWORD=tu_password
```

### 2. Credenciales de Facebook

Igual que arriba. El bot usa las mismas credenciales para scraping.

---

## Uso

### Scraper de Facebook

#### 1. Obtener Grupos

```bash
source venv/bin/activate
python get_groups.py
```

#### 2. Scrapeear Grupos

```bash
# Un grupo específico
python main.py --group-id 774703760229907

# Grupos específicos
python main.py --groups 1,3,7

# Todos los grupos
python main.py --all-groups

# Ver grupos
python main.py --list-groups
```

### Bot de Telegram

```bash
go run bot/main.go
```

---

## Base de Datos

### Esquema

```sql
-- Grupos de Facebook
CREATE TABLE groups (
    id INTEGER PRIMARY KEY,
    name TEXT,
    url TEXT,
    group_id TEXT UNIQUE,
    is_active INTEGER DEFAULT 1,
    last_scraped_at TEXT,
    created_at TEXT
);

-- Listings (anuncios extraídos)
CREATE TABLE listings (
    id INTEGER PRIMARY KEY,
    group_id INTEGER REFERENCES groups(id),
    post_id TEXT,
    type TEXT CHECK(type IN ('V', 'C')),
    article TEXT,
    price REAL,
    currency TEXT,
    contact_phone TEXT,
    contact_fb_username TEXT,
    original_text TEXT,
    ocr_text TEXT,
    posted_at TEXT,
    is_available INTEGER DEFAULT 1,
    created_at TEXT,
    scraped_at TEXT
);

-- Conversaciones de Telegram
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER UNIQUE,
    username TEXT,
    first_name TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- Mensajes
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    sender TEXT CHECK(sender IN ('U', 'B')),
    content TEXT,
    created_at TEXT
);

-- Log de scraping
CREATE TABLE scraping_logs (
    id INTEGER PRIMARY KEY,
    group_id INTEGER REFERENCES groups(id),
    started_at TEXT,
    completed_at TEXT,
    posts_found INTEGER,
    posts_saved INTEGER,
    errors TEXT,
    status TEXT
);
```

---

## Parser de Listings

### Detección de Tipo

| Patrón | Tipo |
|--------|------|
| "Vendo X" | V |
| "Tengo X, interesados al privado" | V |
| "Compro X" | C |
| "Busco X" | C |
| Solo nombre: "iPhone 15" | V |

### Extracción de Datos

| Campo | Ejemplo |
|-------|---------|
| `type` | 'V' o 'C' |
| `article` | "iPhone 15 Pro Max" |
| `price` | 150.0 o null |
| `currency` | "CUC", "USD" |
| `contact_phone` | "+5351234567" |
| `contact_fb_username` | "vendedor123" |
| `posted_at` | "2026-03-24T10:30:00" |

---

## Bot de Telegram

### Comandos

| Comando | Descripción |
|---------|-------------|
| `/start` | Iniciar conversación |
| `/help` | Mostrar ayuda |
| `/busco <articulo>` | Buscar ventas |
| `/vendo <articulo>` | Buscar compras |
| `/grupos` | Ver grupos configurados |

### Ejemplo de Uso

```
Usuario: /busco iphone
Bot: 
📱 iPhone 13 Pro Max - 150 CUC
📞 +53 5XXXXXXXX - @vendedor123
Publicado: hace 2 horas

📱 iPhone 12 - 100 CUC  
📞 +53 5XXXXXXXX - @otrovendedor
Publicado: hace 5 horas
```

---

## Limitaciones

### Facebook
- ToS: Scraper viola términos de Facebook
- Detección: Facebook puede bloquear sesiones
- 2FA: No soportado

### Contextura Cuba
- Datos limitados (6GB/mes)
- Scraper debe ejecutarse con WiFi

---

## Futuro

### Fase 1 (Completado)
- [x] Parser de listings
- [x] Extracción de precio y contacto
- [x] OCR con Tesseract
- [x] Base de datos SQLite
- [x] Gestión de múltiples grupos
- [x] Detección de "precio privado"

### Fase 2 (En progreso)
- [ ] Bot de Telegram (Go)
- [ ] Integración con Ollama

### Fase 3 (Ideas)
- [ ] Migración a Termux/Android
- [ ] Sincronización entre dispositivos
- [ ] Notificaciones de nuevos listings
- [ ] Interfaz web para administración

---

## Licencia

Privado - Solo para uso personal.
