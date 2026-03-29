#!/bin/bash

# Script para detener el bot de Telegram
# Uso: ./detener_bot

echo "🛑 Deteniendo bot..."

# Buscar el proceso
PID=$(pgrep -f "telegram-marketplace-bot")

if [ -z "$PID" ]; then
    echo "⚠️  El bot no está corriendo"
    exit 1
fi

# Matar el proceso
kill $PID

sleep 1

# Verificar que se detuvo
if pgrep -f "telegram-marketplace-bot" > /dev/null; then
    echo "❌ No se pudo detener el bot. Forzando..."
    kill -9 $PID
    sleep 1
fi

if pgrep -f "telegram-marketplace-bot" > /dev/null; then
    echo "❌ Error al detener el bot"
else
    echo "✅ Bot detenido correctamente"
fi
