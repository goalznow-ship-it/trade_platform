#!/bin/bash
set -euo pipefail

# TradeAnalyst Pro - Let's Encrypt SSL Setup
# Usage: ./scripts/setup-ssl.sh --domain trading.example.com --email admin@example.com

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

DOMAIN=""
EMAIL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --domain) DOMAIN="$2"; shift 2 ;;
        --email) EMAIL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Usage: $0 --domain example.com --email admin@example.com"
    exit 1
fi

echo "=== Setting up SSL for $DOMAIN ==="

# Ensure directories exist
mkdir -p nginx/ssl nginx/letsencrypt/webroot

# Update domain in nginx config
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/server_name .*;/server_name $DOMAIN;/g" nginx/nginx.conf
else
    sed -i "s/server_name .*;/server_name $DOMAIN;/g" nginx/nginx.conf
fi

# Stop nginx if running to free port 80
docker compose -f docker/docker-compose.yml stop nginx 2>/dev/null || true

# Run certbot to get certificate
docker run --rm -v "$(pwd)/nginx/letsencrypt:/etc/letsencrypt" \
    -v "$(pwd)/nginx/ssl:/etc/nginx/ssl" \
    -p 80:80 \
    certbot/certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --domain "$DOMAIN" \
    --cert-name trading

# Copy certificates to ssl directory
cp "nginx/letsencrypt/live/$DOMAIN/fullchain.pem" nginx/ssl/cert.pem
cp "nginx/letsencrypt/live/$DOMAIN/privkey.pem" nginx/ssl/key.pem

echo ""
echo "=== SSL Certificate Installed Successfully ==="
echo "Certificate will auto-renew via certbot service"
echo ""
echo "Restarting services..."
docker compose -f docker/docker-compose.yml up -d --build

echo "Done! Your site is now available at https://$DOMAIN"
