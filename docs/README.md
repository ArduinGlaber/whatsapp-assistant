# WhatsApp Assistant - Documentación

Asistente de WhatsApp con scraping de Facebook para marketplace.

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
10. [Limitaciones](#limitaciones)
11. [Futuro](#futuro)

---

## Descripción General

Este proyecto automatiza la gestión de un marketplace en WhatsApp mediante:

- **Scraping automático** de grupos de Facebook de compra/venta
- **Extracción inteligente** de información de anuncios (artículo, precio, contacto)
- **Bot de WhatsApp** que responde consultas sobre productos disponibles
- **Base de datos local** para almacenamiento offline

### Contexto

Diseñado para usuarios en Cuba con limitaciones de conectividad (6GB/mes). Todas las operaciones son locales.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    WhatsApp Assistant                         │
├──────────────────┬──────────────────┬───────────────────────┤
│   Facebook       │    WhatsApp      │      SQLite           │
│   Scraper       │      Bot         │      Database         │
│   (Python)      │     (Go)         │      (Local)         │
├──────────────────┴──────────────────┴───────────────────────┤
│                    Ollama (IA Local)                        │
│                    qwen2.5:1.5b                            │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de datos

```
Facebook → Scraper → Parser → SQLite DB ← Bot WhatsApp
                                       ↓
                                   Usuario
```

---

## Estructura del Proyecto

```
whatsapp-assistant/
├── scraper/
│   ├── main.py           # Entrada principal del scraper
│   ├── get_groups.py     # Obtener grupos de Facebook
│   ├── facebook.py       # Login y scraping con Selenium
│   ├── parser.py         # Extracción de listings
│   ├── ocr.py           # OCR con Tesseract
│   ├── storage.py        # Repositorio SQLite
│   ├── test_parser.py    # Tests del parser
│   ├── requirements.txt   # Dependencias Python
│   └── data/             # Base de datos y cookies
├── internal/             # Código Go (futuro)
│   ├── whatsapp/         # Bot WhatsApp
│   ├── ai/              # Cliente Ollama
│   └── models/          # Entidades
├── migrations/           # Migraciones SQL
├── .env                 # Credenciales (NO commitear)
├── .gitignore
├── go.mod               # Módulo Go
└── README.md            # Este archivo
```

---

## Instalación

### Requisitos del Sistema

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-spa
```

### Python

```bash
cd scraper
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Dependencias Python

```
selenium>=4.0
undetected-chromedriver>=3.5
python-dotenv>=1.0
pytesseract>=0.3
beautifulsoup4>=4.9
requests>=2.28
Pillow>=9.0
```

---

## Configuración

### 1. Credenciales de Facebook

Crear archivo `.env` en la carpeta scraper:

```env
FACEBOOK_EMAIL=tu@email.com
FACEBOOK_PASSWORD=tu_password
```

**Importante:** 
- Agregar `.env` a `.gitignore`
- Cambiar la contraseña después del MVP
- Considerar usar autenticación de dos factores

### 2. Base de Datos

La base de datos SQLite se crea automáticamente en `data/listings.db`.

---

## Uso

### 1. Obtener Grupos de Facebook

```bash
source venv/bin/activate
python get_groups.py
```

Este comando:
- Inicia sesión en Facebook
- Lista todos los grupos del usuario
- Permite seleccionar cuáles guardar
- Los guarda en la base de datos

### 2. Scrapeear Grupos

```bash
# Un grupo específico
python main.py --group-id 774703760229907

# Grupos específicos (por ID de base de datos)
python main.py --groups 1,3,7

# Rango de grupos
python main.py --groups 1-5

# Todos los grupos activos
python main.py --all-groups

# Ver grupos disponibles
python main.py --list-groups

# Mostrar navegador (para debugging)
python main.py --group-id 774703760229907 --show-browser
```

### 3. Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--group-id` | ID del grupo de Facebook | - |
| `--groups` | IDs separados por coma (1,3,5) | - |
| `--all-groups` | Scrapear todos los grupos activos | False |
| `--list-groups` | Mostrar grupos en DB | False |
| `--max-posts` | Posts máximos por grupo | 50 |
| `--headless` | Sin navegador visible | True |
| `--show-browser` | Mostrar navegador | False |
| `--db-path` | Ruta a la base de datos | data/listings.db |

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
    type TEXT CHECK(type IN ('V', 'C')),  -- Venta o Compra
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

-- Conversaciones de WhatsApp
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    contact_jid TEXT UNIQUE,
    contact_name TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- Mensajes
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    sender TEXT CHECK(sender IN ('U', 'B')),  -- User o Bot
    content TEXT,
    created_at TEXT
);

-- Log de operaciones de scraping
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

### Índices

```sql
CREATE INDEX idx_listings_article ON listings(article COLLATE NOCASE);
CREATE INDEX idx_listings_type ON listings(type);
CREATE INDEX idx_listings_available ON listings(is_available);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
```

---

## Parser de Listings

### Detección de Tipo

El parser determina si un post es **Venta** o **Compra**:

| Patrón | Tipo |
|--------|------|
| "Vendo X" | V |
| "Tengo X, interesados al privado" | V |
| "Compro X" | C |
| "Busco X" | C |
| Solo nombre: "iPhone 15" | V (asume venta) |

### Extracción de Datos

| Campo | Ejemplo | Notas |
|-------|---------|-------|
| `type` | 'V' o 'C' | Venta o Compra |
| `article` | "iPhone 15 Pro Max 256GB" | Limpiado de keywords |
| `price` | 150.0 | Float o null |
| `currency` | "CUC" | CUC, USD, CUP, EUR |
| `contact_phone` | "+5351234567" | Con código de país |
| `contact_fb_username` | "vendedor123" | Del autor |
| `posted_at` | "2026-03-24T10:30:00" | ISO format |

### Casos Especiales

#### Precio en privado

```
"Tengo PS5, consultar precio al privado"
→ price = null, currency = null
```

#### Solo nombre de producto

```
"iPhone 15 Pro"
→ type = 'V', price = null
```

### Patrones Detectados

**Venta:**
- vendo, venta
- tengo X, interesados al privado
- ofrezco

**Compra:**
- compro, compramos
- busco, necesito
- busco X, privado

---

## Scraper de Facebook

### Login

1. Intenta cargar sesión guardada (`data/facebook_cookies.json`)
2. Si falla, hace login con credenciales
3. Guarda cookies para siguientes ejecuciones

### Extracción de Posts

1. Navega al grupo
2. Hace scroll para cargar más posts
3. Extrae para cada post:
   - Autor
   - Texto del post
   - URL de imágenes
   - Timestamp

### Rate Limiting

- Pausas de 2 segundos entre scrolls
- Máximo 20 scrolls por grupo
- Sesión guardada para reutilizar

---

## Limitaciones

### Actuales

| Limitación | Descripción |
|------------|-------------|
| Facebook ToS | Scraper viola términos de servicio |
| Detección | Facebook puede detectar y bloquear |
| 2FA | No maneja autenticación de dos factores |
| Imágenes | Solo OCR, no descarga imágenes |

### Contexto Cuba

- Datos limitados (6GB/mes)
- Scraper debe ejecutarse con WiFi disponible
- Todo corre localmente

---

## Futuro

### Fase 1 (Completado)
- [x] Parser de listings
- [x] Extracción de precio y contacto
- [x] OCR con Tesseract
- [x] Base de datos SQLite
- [x] Gestión de múltiples grupos
- [x] Detección de "precio privado"

### Fase 2 (Pendiente)
- [ ] Bot de WhatsApp (Go + whasmeow)
- [ ] Integración con Ollama
- [ ] Búsqueda por similitud
- [ ] Historial de conversaciones

### Fase 3 (Ideas)
- [ ] Migración a Termux/Android
- [ ] Sincronización entre dispositivos
- [ ] Notificaciones de nuevos listings
- [ ] Interfaz web para administración

---

## Troubleshooting

### Error: "Login failed"

1. Verificar credenciales en `.env`
2. Si hay 2FA, desactivarlo temporalmente
3. Verificar que Facebook permita el acceso

### Error: "No groups found"

1. Asegurarse de estar logueado
2. Verificar cookies en `data/facebook_cookies.json`
3. Eliminar cookies y hacer login de nuevo

### Error: "Tesseract not found"

```bash
sudo apt install tesseract-ocr tesseract-ocr-spa
```

---

## Licencia

Privado - Solo para uso personal.

---

## Autores

- Proyecto para uso personal en Cuba
- Contexto: asistente de marketplace vía WhatsApp
