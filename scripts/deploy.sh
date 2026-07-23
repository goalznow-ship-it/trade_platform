#!/bin/bash
set -euo pipefail

# TradeAnalyst Pro - Production Deployment Script
# Usage: ./scripts/deploy.sh [--ssl] [--domain example.com] [--email admin@example.com]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "=== TradeAnalyst Pro Deployment ==="
echo ""

# Check dependencies
for cmd in docker docker-compose; do
    if ! command -v $cmd &>/dev/null; then
        echo "Error: $cmd not found. Please install Docker first."
        exit 1
    fi
done

# Parse arguments
SSL=false
DOMAIN="trading.example.com"
EMAIL="admin@example.com"

while [[ $# -gt 0 ]]; do
    case $1 in
        --ssl) SSL=true; shift ;;
        --domain) DOMAIN="$2"; shift 2 ;;
        --email) EMAIL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Create required directories
mkdir -p nginx/ssl nginx/letsencrypt

# Generate self-signed SSL cert if needed for initial setup
if [ ! -f nginx/ssl/cert.pem ]; then
    echo "Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/CN=$DOMAIN" 2>/dev/null
fi

# Update domain in nginx config
sed -i "s/server_name trading.example.com;/server_name $DOMAIN;/g" nginx/nginx.conf

# Copy env file
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "Created backend/.env. Replace placeholder secrets before deploying."
    exit 1
fi

# Generate secure secret key
if grep -q "ta-pro-secret-key-change-in-production" backend/.env 2>/dev/null; then
    echo "Generating secure SECRET_KEY..."
    NEW_SECRET=$(openssl rand -hex 32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/SECRET_KEY=ta-pro-secret-key-change-in-production/SECRET_KEY=$NEW_SECRET/" backend/.env
    else
        sed -i "s/SECRET_KEY=ta-pro-secret-key-change-in-production/SECRET_KEY=$NEW_SECRET/" backend/.env
    fi
fi

# Build and start
echo ""
echo "Building and starting services..."
docker-compose -f docker/docker-compose.yml up -d --build

echo ""
echo "=== Deployment Complete ==="
echo "Service will be available at: https://$DOMAIN"
echo ""
echo "To view logs: docker-compose -f docker/docker-compose.yml logs -f"
echo "To stop: docker-compose -f docker/docker-compose.yml down"
