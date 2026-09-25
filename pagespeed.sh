#!/usr/bin/env bash

source .env

echo "Checking Desktop"
curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://omena0.dev/fr-docs/&strategy=desktop&key=$PAGESPEED_KEY" > pagespeed/desktop.json

echo "Waiting 5s"
sleep 5

echo "Checking Mobile"
curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://omena0.dev/fr-docs/&strategy=mobile&key=$PAGESPEED_KEY" > pagespeed/mobile.json
