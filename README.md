# Telegram Marketplace Bot

Bot de Telegram con scraping de Facebook para marketplace en Cuba.

## Características

- 🤖 **Scraper automático** de grupos de Facebook
- 💬 **Bot de Telegram** que responde consultas
- 📦 **Base de datos local** SQLite
- 🔒 **Sin riesgo de ban** (API oficial de Telegram)
- 📱 **Funciona offline** (ideal para Cuba)

## Estructura

```
telegram-marketplace-bot/
├── scraper/              # Scraper de Facebook (Python)
├── bot/                  # Bot de Telegram (Go)
├── docs/                 # Documentación
└── data/                 # Base de datos
```

## Setup Rápido

### 1. Scraper

```bash
cd scraper
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python get_groups.py  # Obtener grupos
python main.py --all-groups  # Scrapear
```

### 2. Bot

```bash
go mod init bot
go get github.com/go-telegram-bot-api/telegram-bot-api/v5
go run bot/main.go
```

## Uso

```
/start - Iniciar
/busco iphone - Buscar ventas
/vendo iphone - Buscar compras
```

## Documentación

Ver [docs/README.md](docs/README.md)

## Estado

**Fase 1 completada:** Scraper de Facebook con parser, OCR y gestión de grupos.

**Fase 2 en progreso:** Bot de Telegram.

---

Hecho para Cuba 🇬🇺
