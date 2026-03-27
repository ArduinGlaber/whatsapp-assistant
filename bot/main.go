package main

import (
	"log"
	"os"
	"strings"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
	// Get token from environment
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		log.Fatal("TELEGRAM_BOT_TOKEN not set")
	}

	// Create bot
	bot, err := tgbotapi.NewBotAPI(token)
	if err != nil {
		log.Fatalf("Error creating bot: %v", err)
	}

	log.Printf("Bot started: @%s", bot.Self.UserName)

	// Get updates channel
	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60

	updates := bot.GetUpdatesChan(u)

	// Handle messages
	for update := range updates {
		if update.Message == nil {
			continue
		}

		// Log message
		log.Printf("[%s] %s", update.Message.From.UserName, update.Message.Text)

		// Process command
		text := strings.TrimSpace(update.Message.Text)

		var response string

		switch {
		case text == "/start":
			response = welcomeMessage()
		case text == "/help":
			response = helpMessage()
		case strings.HasPrefix(text, "/busco"):
			response = handleSearch(strings.TrimPrefix(text, "/busco"), "V")
		case strings.HasPrefix(text, "/vendo"):
			response = handleSearch(strings.TrimPrefix(text, "/vendo"), "C")
		case strings.HasPrefix(text, "/search"):
			response = handleSearch(strings.TrimPrefix(text, "/search"), "")
		default:
			response = "Usa /help para ver los comandos disponibles."
		}

		// Send response
		msg := tgbotapi.NewMessage(update.Message.Chat.ID, response)
		msg.ReplyToMessageID = update.Message.MessageID
		bot.Send(msg)
	}
}

func welcomeMessage() string {
	return `👋 ¡Bienvenido al Asistente de Marketplace!

Este bot busca en anuncios de compra y venta de Facebook.

📋 Comandos disponibles:

/busco <articulo> - Buscar lo que alguien vende
/vendo <articulo> - Buscar quién quiere comprar
/search <articulo> - Buscar en ambos
/help - Ver esta ayuda

Ejemplo: /busco iphone`
}

func helpMessage() string {
	return `📋 Ayuda - Comandos disponibles:

• /start - Iniciar el bot
• /help - Ver esta ayuda
• /busco <articulo> - Buscar ventas
• /vendo <articulo> - Buscar compras
• /search <articulo> - Buscar en ambos

📝 Ejemplos:
/busco iphone
/vendo laptop
/search playstation`
}

func handleSearch(query string, listingType string) string {
	// TODO: Query database
	if query == "" {
		return "❌ Indica qué buscas. Ejemplo: /busco iphone"
	}

	query = strings.TrimSpace(query)
	if query == "" {
		return "❌ Indica qué buscas. Ejemplo: /busco iphone"
	}

	// Placeholder - will connect to DB later
	return `🔍 Buscando: "` + query + `"

⏳ Esta función aún está en desarrollo.
El bot buscará en la base de datos de Facebook.
Consultar más tarde.`
}
