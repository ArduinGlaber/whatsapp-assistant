#!/bin/bash
# ===============================================
# Facebook Marketplace Scraper
# ===============================================
# Uso: bash run_scraper.sh
# ===============================================

set -e

echo "============================================"
echo "Facebook Marketplace Scraper"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado${NC}"
    echo "Instala Python desde: https://www.python.org/downloads/"
    exit 1
fi

# Check if in scraper directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ No estás en el directorio del scraper${NC}"
    echo "Ejecuta este script desde la carpeta scraper/"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Instalando dependencias...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Activate venv
source venv/bin/activate

# Run scraper
echo -e "${GREEN}🚀 Corriendo scraper...${NC}"
python3 -m scraper.main --db-path data/listings.db

echo ""
echo -e "${GREEN}✅ Scraper completado!${NC}"
echo ""
