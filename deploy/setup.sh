#!/bin/bash
set -e

DOMAIN="timer-of-life.com"
EMAIL="$1"

if [ -z "$EMAIL" ]; then
  echo "Usage: ./deploy/setup.sh your@email.com"
  exit 1
fi

if [ ! -f .env ]; then
  echo "Create .env first: cp .env.example .env && nano .env"
  exit 1
fi

echo "==> Building and starting postgres + backend..."
docker compose -f docker-compose.prod.yml up -d --build postgres backend

echo "==> Starting nginx with HTTP-only config for certbot..."
docker compose -f docker-compose.prod.yml build nginx
docker run -d --name nginx-init \
  --network life-timer_default \
  -p 80:80 \
  -v life-timer_certbot-var:/var/www/certbot \
  -v "$(pwd)/deploy/nginx-init.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:alpine

echo "==> Requesting Let's Encrypt certificate..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d "$DOMAIN" -d "www.$DOMAIN" \
  --email "$EMAIL" --agree-tos --no-eff-email

echo "==> Stopping temp nginx..."
docker rm -f nginx-init

echo "==> Starting full stack with HTTPS..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "Done! https://$DOMAIN should be live."
echo ""
echo "To auto-renew certificates, add this cron:"
echo "0 3 * * * cd $(pwd) && docker compose -f docker-compose.prod.yml run --rm certbot renew && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload"
