#!/bin/bash

# Script para iniciar el bot de Telegram
# Uso: ./iniciar_bot

cd ~/bot

# Verificar que el binario existe
if [ ! -f "./telegram-marketplace-bot" ]; then
    echo "❌ Error: Binario no encontrado. Compila primero con: go build -o bot ."
    exit 1
fi

# Verificar que el token está configurado
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    if [ -f ".env" ]; then
        echo "📦 Cargando token desde .env..."
        export $(cat .env | xargs)
    fi
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN no está configurado"
    echo "   Configura la variable o crea archivo .env"
    exit 1
fi

# Verificar si ya está corriendo
if pgrep -f "telegram-marketplace-bot" > /dev/null; then
    echo "⚠️  El bot ya está corriendo"
    echo "   Usa ./detener_bot para pararlo"
    exit 1
fi

echo "🚀 Iniciando bot..."
nohup ./telegram-marketplace-bot > bot.log 2>&1 &
sleep 1

# Verificar que inició
if pgrep -f "telegram-marketplace-bot" > /dev/null; then
    echo "✅ Bot iniciado correctamente"
    echo "📝 Logs: bot.log"
    echo "   Usa ./detener_bot para pararlo"
else
    echo "❌ Error al iniciar el bot"
    echo "   Revisa bot.log para más detalles"
    cat bot.log
fi
