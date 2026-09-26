#!/usr/bin/env bash

source .env

cd pagespeed || true

echo "Checking Desktop"
curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://omena0.dev/fr-docs/&strategy=desktop&key=$PAGESPEED_KEY" > desktop.json

echo "Waiting 2s"
sleep 2

echo "Checking Mobile"
curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://omena0.dev/fr-docs/&strategy=mobile&key=$PAGESPEED_KEY" > mobile.json
