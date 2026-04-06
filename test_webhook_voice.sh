#!/bin/bash

# Test webhook with voice note parameters (simulating Twilio)

echo "Testing WhatsApp webhook with voice note parameters..."
echo ""

curl -X POST 'http://localhost:8000/api/munim/whatsapp/webhook' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'From=whatsapp:+919425129512' \
  -d 'Body=' \
  -d 'MessageSid=SM1234567890' \
  -d 'MediaUrl0=https://api.twilio.com/2010-04-01/Accounts/ACxxx/Messages/MMxxx/Media/MExxx' \
  -d 'MediaContentType0=audio/ogg' \
  -d 'NumMedia=1'

echo ""
echo ""
echo "If you see a 200 OK response, the webhook is accepting voice note parameters correctly!"
