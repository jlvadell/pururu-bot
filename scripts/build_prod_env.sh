#!/bin/sh
# create google creds file
echo $SPREADSHEET_CREDS | base64 -d > "google_creds.json"
# create .env.production file
echo "DISCORD_TOKEN="$DISCORD_TOKEN > "production.properties"
echo "GS_ATTENDANCE_PLAYER_MAPPING="$GS_ATTENDANCE_PLAYER_MAPPING >> "production.properties"
echo "GUILD_ID="$GUILD_ID >> "production.properties"
echo "PLAYERS="$PLAYERS >> "production.properties"
echo "GOOGLE_SHEETS_CREDENTIALS='./pururu/google_creds.json'" >> "production.properties"
