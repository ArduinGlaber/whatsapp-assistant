# Telegram Marketplace Bot

Este proyecto automatiza la búsqueda en Facebook Marketplace para alguien en Cuba.

Un bot de Telegram que:
- Escrapea publicaciones de grupos de Facebook
- Responde a comandos como `/busco iphone` con resultados
- Almacena todo en SQLite para búsqueda offline

**Nota**: Este es el hermano "WC" (WiFi/Costo) del proyecto. Usa la PC para scrapear, consume más datos pero es más rápido. Para una alternativa que usa el celular como terminal, ver [Proyecto Manolo](https://github.com/ArduinGlaber/proyecto-manolo).

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
