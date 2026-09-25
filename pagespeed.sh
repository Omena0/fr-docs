#!/usr/bin/env bash

source .env

curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://omena0.dev/&strategy=desktop&key=$PAGESPEED_KEY" > pagespeed/desktop.json
curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://omena0.dev/&strategy=mobile&key=$PAGESPEED_KEY" > pagespeed/mobile.json
