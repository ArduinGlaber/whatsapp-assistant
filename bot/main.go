package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
	_ "github.com/mattn/go-sqlite3"
)

const (
	dbOwner   = "ArduinGlaber"
	dbRepo    = "whatsapp-assistant"
	dbName    = "listings.db"
	localPath = "data/" + dbName
)

var db *sql.DB

type Listing struct {
	ID          int
	Title       string
	Description string
	Price       sql.NullString
	Currency    sql.NullString
	Type        string
	Contact     string
	PostedDate  string
}

func main() {
	token := os.Getenv("TELEGRAM_BOT_TOKEN")
	if token == "" {
		log.Fatal("TELEGRAM_BOT_TOKEN not set")
	}

	bot, err := tgbotapi.NewBotAPI(token)
	if err != nil {
		log.Fatalf("Error creating bot: %v", err)
	}

	log.Printf("Bot started: @%s", bot.Self.UserName)

	if err := os.MkdirAll("data", 0755); err != nil {
		log.Printf("Warning: Could not create data directory: %v", err)
	}

	go downloadDatabase()

	if err := initDatabase(); err != nil {
		log.Printf("Warning: Could not initialize database: %v", err)
	}

	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60
	updates := bot.GetUpdatesChan(u)

	for update := range updates {
		if update.Message == nil {
			continue
		}

		log.Printf("[%s] %s", update.Message.From.UserName, update.Message.Text)

		text := strings.TrimSpace(update.Message.Text)
		var response string

		switch {
		case text == "/start":
			response = welcomeMessage()
		case text == "/help":
			response = helpMessage()
		case text == "/actualizar" || text == "/update":
			response = handleUpdate(bot, update.Message.Chat.ID)
		case strings.HasPrefix(text, "/busco"):
			response = handleSearch(strings.TrimPrefix(text, "/busco"), "V")
		case strings.HasPrefix(text, "/vendo"):
			response = handleSearch(strings.TrimPrefix(text, "/vendo"), "C")
		case strings.HasPrefix(text, "/search"):
			response = handleSearch(strings.TrimPrefix(text, "/search"), "")
		default:
			response = "Usa /help para ver los comandos disponibles."
		}

		msg := tgbotapi.NewMessage(update.Message.Chat.ID, response)
		msg.ReplyToMessageID = update.Message.MessageID
		bot.Send(msg)
	}
}

func initDatabase() error {
	var err error
	db, err = sql.Open("sqlite3", localPath)
	if err != nil {
		return err
	}

	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS listings (
			id INTEGER PRIMARY KEY,
			title TEXT,
			description TEXT,
			price TEXT,
			currency TEXT,
			type TEXT,
			contact TEXT,
			posted_date TEXT
		)
	`)
	return err
}

func downloadDatabase() {
	githubToken := os.Getenv("GITHUB_TOKEN")
	if githubToken == "" {
		githubToken = os.Getenv("GH_TOKEN")
	}

	needsDownload := false

	info, err := os.Stat(localPath)
	if err != nil {
		if os.IsNotExist(err) {
			needsDownload = true
			log.Println("Local DB does not exist, will download...")
		}
	} else {
		releaseTime, err := getLatestReleaseTime(githubToken)
		if err != nil {
			log.Printf("Could not check release time: %v", err)
			return
		}
		if releaseTime.After(info.ModTime()) {
			needsDownload = true
			log.Println("Remote DB is newer, will download...")
		}
	}

	if !needsDownload {
		log.Println("Database is up to date")
		return
	}

	if err := downloadLatestDB(githubToken); err != nil {
		log.Printf("Failed to download database: %v", err)
		return
	}

	log.Println("Database downloaded successfully")

	if db != nil {
		db.Close()
	}
	initDatabase()
}

func getLatestReleaseTime(token string) (time.Time, error) {
	url := fmt.Sprintf("https://api.github.com/repos/%s/%s/releases/latest", dbOwner, dbRepo)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return time.Time{}, err
	}

	req.Header.Set("Accept", "application/vnd.github+json")
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return time.Time{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return time.Time{}, fmt.Errorf("GitHub API returned status %d", resp.StatusCode)
	}

	var release struct {
		PublishedAt string `json:"published_at"`
	}

	if err := decodeJSON(resp.Body, &release); err != nil {
		return time.Time{}, err
	}

	publishedAt, err := time.Parse("2006-01-02T15:04:05Z", release.PublishedAt)
	if err != nil {
		return time.Time{}, err
	}

	return publishedAt, nil
}

func downloadLatestDB(token string) error {
	url := fmt.Sprintf("https://api.github.com/repos/%s/%s/releases/latest", dbOwner, dbRepo)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("Accept", "application/vnd.github+json")
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("GitHub API returned status %d", resp.StatusCode)
	}

	var release struct {
		Assets []struct {
			Name               string `json:"name"`
			BrowserDownloadURL string `json:"browser_download_url"`
		} `json:"assets"`
	}

	if err := decodeJSON(resp.Body, &release); err != nil {
		return err
	}

	var downloadURL string
	for _, asset := range release.Assets {
		if strings.HasSuffix(asset.Name, ".db") || strings.HasSuffix(asset.Name, ".sqlite") || strings.HasSuffix(asset.Name, ".sqlite3") {
			downloadURL = asset.BrowserDownloadURL
			break
		}
	}

	if downloadURL == "" {
		return fmt.Errorf("no database asset found in release")
	}

	req, err = http.NewRequest("GET", downloadURL, nil)
	if err != nil {
		return err
	}

	req.Header.Set("Accept", "application/octet-stream")
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}

	resp, err = client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("download returned status %d", resp.StatusCode)
	}

	tmpPath := localPath + ".tmp"
	out, err := os.Create(tmpPath)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return err
	}

	if err := out.Close(); err != nil {
		return err
	}

	if err := os.Rename(tmpPath, localPath); err != nil {
		return err
	}

	return nil
}

func decodeJSON(body io.Reader, v interface{}) error {
	return json.NewDecoder(body).Decode(v)
}

func handleUpdate(bot *tgbotapi.BotAPI, chatID int64) string {
	msg := tgbotapi.NewMessage(chatID, "🔄 Actualizando base de datos...")
	sent, err := bot.Send(msg)
	if err != nil {
		return "❌ Error al actualizar: " + err.Error()
	}

	go func() {
		downloadDatabase()

		editMsg := tgbotapi.NewEditMessageText(chatID, sent.MessageID, "✅ Base de datos actualizada correctamente.")
		bot.Send(editMsg)
	}()

	return "🔄 Actualizando base de datos..."
}

func handleSearch(query string, listingType string) string {
	if query == "" {
		return "❌ Indica qué buscas. Ejemplo: /busco iphone"
	}

	query = strings.TrimSpace(query)
	if query == "" {
		return "❌ Indica qué buscas. Ejemplo: /busco iphone"
	}

	if db == nil {
		return "❌ Base de datos no disponible. Intenta más tarde o usa /actualizar."
	}

	results, err := searchListings(query, listingType, 10)
	if err != nil {
		log.Printf("Search error: %v", err)
		return "❌ Error al buscar. Intenta más tarde."
	}

	if len(results) == 0 {
		return fmt.Sprintf("🔍 No se encontraron resultados para \"%s\"\n\nPrueba con otros términos.", query)
	}

	return formatSearchResults(results, query)
}

func searchListings(query string, listingType string, limit int) ([]Listing, error) {
	searchPattern := "%" + query + "%"

	var rows *sql.Rows
	var err error

	if listingType == "" {
		rows, err = db.Query(`
			SELECT id, title, description, price, currency, type, contact, posted_date
			FROM listings
			WHERE title LIKE ? OR description LIKE ?
			LIMIT ?
		`, searchPattern, searchPattern, limit)
	} else {
		rows, err = db.Query(`
			SELECT id, title, description, price, currency, type, contact, posted_date
			FROM listings
			WHERE (title LIKE ? OR description LIKE ?) AND type = ?
			LIMIT ?
		`, searchPattern, searchPattern, listingType, limit)
	}

	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []Listing
	for rows.Next() {
		var l Listing
		err := rows.Scan(&l.ID, &l.Title, &l.Description, &l.Price, &l.Currency, &l.Type, &l.Contact, &l.PostedDate)
		if err != nil {
			continue
		}
		results = append(results, l)
	}

	return results, rows.Err()
}

func formatSearchResults(results []Listing, query string) string {
	var b strings.Builder

	b.WriteString(fmt.Sprintf("🔍 Resultados para \"%s\":\n\n", query))

	for i, l := range results {
		b.WriteString(formatListing(l))
		if i < len(results)-1 {
			b.WriteString("\n─────────────────────\n")
		}
	}

	b.WriteString(fmt.Sprintf("\n\n📊 Total: %d resultado(s)", len(results)))

	return b.String()
}

func formatListing(l Listing) string {
	var b strings.Builder

	typeStr := "Compra"
	if l.Type == "V" {
		typeStr = "Venta"
	}
	b.WriteString(fmt.Sprintf("📦 Tipo: %s\n", typeStr))

	b.WriteString(fmt.Sprintf("📝 Artículo: %s\n", l.Title))

	if l.Price.Valid && l.Price.String != "" {
		currency := "ARS"
		if l.Currency.Valid && l.Currency.String != "" {
			currency = l.Currency.String
		}
		b.WriteString(fmt.Sprintf("💰 Precio: %s %s\n", l.Price.String, currency))
	} else {
		b.WriteString("💰 Precio: Precio privado\n")
	}

	b.WriteString(fmt.Sprintf("📞 Contacto: %s\n", l.Contact))

	if l.PostedDate != "" {
		b.WriteString(fmt.Sprintf("🕐 Posted: %s", l.PostedDate))
	}

	return b.String()
}

func welcomeMessage() string {
	return `👋 ¡Bienvenido al Asistente de Marketplace!

Este bot busca en anuncios de compra y venta de Facebook.

📋 Comandos disponibles:

/busco <articulo> - Buscar lo que alguien vende
/vendo <articulo> - Buscar quién quiere comprar
/search <articulo> - Buscar en ambos
/actualizar - Actualizar la base de datos
/help - Ver esta ayuda

💾 La base de datos se sincroniza automáticamente desde GitHub.

Ejemplo: /busco iphone`
}

func helpMessage() string {
	return `📋 Ayuda - Comandos disponibles:

• /start - Iniciar el bot
• /help - Ver esta ayuda
• /busco <articulo> - Buscar ventas
• /vendo <articulo> - Buscar compras
• /search <articulo> - Buscar en ambos
• /actualizar - Actualizar DB desde GitHub

📝 Ejemplos:
/busco iphone
/vendo laptop
/search playstation`
}
