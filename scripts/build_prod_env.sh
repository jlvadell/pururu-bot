#!/bin/bash
# create google creds file
echo $SPREADSHEET_CREDS > "google_creds.json"
# create .env.production file
echo $DISCORD_TOKEN > ".env.production"
echo $GS_ATTENDANCE_PLAYER_MAPPING >> ".env.production"
echo $GUILD_ID >> ".env.production"
echo $PLAYERS >> ".env.production"
