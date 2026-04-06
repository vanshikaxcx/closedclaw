#!/bin/bash

echo "Testing new branding in WhatsApp bot..."
echo ""

# Test help message
echo "Sending 'hello' to trigger help message..."
response=$(curl -s -X POST 'http://localhost:8000/api/munim/whatsapp/webhook' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'From=whatsapp:+919425129512' \
  -d 'Body=hello' \
  -d 'MessageSid=SM123')

echo "Response: $response"
echo ""

# Check server logs for the new name
echo "Checking server logs for 'Arthsetu Merchant Help'..."
echo ""
echo "✅ If you see 'Arthsetu Merchant Help initialized' in the logs above,"
echo "   the rebranding is complete!"
echo ""
echo "To test on WhatsApp:"
echo "  1. Send 'hello' to +1 415 523 8886"
echo "  2. Bot will reply with new name: 'Arthsetu Merchant Help'"
