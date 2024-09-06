# Pururu Bot

<div>
<img src="https://sonarcloud.io/api/project_badges/measure?project=jlvadell_pururu-bot&metric=alert_status">
<img src="https://sonarcloud.io/api/project_badges/measure?project=jlvadell_pururu-bot&metric=coverage">
<img src="https://img.shields.io/github/languages/top/jlvadell/pururu-bot">
<img src="https://img.shields.io/github/license/jlvadell/pururu-bot">
<img src="https://img.shields.io/github/v/tag/jlvadell/pururu-bot">
</div>

This is the repository for the Discord bot Pururu.

![Pururu App](docs/img/dc_user_app.png)

This bot is a private project for a Discord server, and it is not intended to be used by other servers.

## Purpose

The purpose of this bot is to provide a set of tools to the users of the server, such as:

- Automatic Attendance Control
- Clock in and out
- Absences control

## Dependencies

### Discord API

The app is fully-dependent on the Discord API, hence, it
uses [Discord.py](https://discordpy.readthedocs.io/en/latest/index.html) to interact with the API.

### Google Sheets API

The app is designed to use a Google Sheet as the main database service, for this, it uses
the [Google Sheets API](https://developers.google.com/sheets/api).

The why of this is because originally everything was made by hand using a Google Sheet, so when I was planning this bot
I wanted to preserve the easy way of visualizing and editing the data a Google Sheet provides.

## How it works?

Here is a flow diagram of how the bot works:

![Flow diagram](docs/img/pururu_flow.png)

It only uses the `on_voice_state_update` event to track the users' attendance. After meting the conditions to start a
new Game (attendance check) it will start recording every event locally so when the game finishes it will be inserted to
the google sheet.

### Attendance

Here is an example of how the attendance sheet would look like:
![Attendance Sheet](docs/img/attendance_sheet.png)

### Clocking

Here is an example of how the clocking sheet would look like:
![Attendance Sheet](docs/img/clocking_sheet.png)

### Event Logging

Here is an example of how the event logging sheet would look like:
![Attendance Sheet](docs/img/event_logging_sheet.png)

## Bot Commands

### Ping command (`/ping`)

Send a ping to the bot, if the bot is online and responding the bot answers with a pong and his current version.

### Stats command (`/stats`)

When you call the stats command the bot will query your attendance data and will return a resume of your attendance.
In this resume you will see:
- Total events
- Total attendances and absences
- Total justifications / injustifications

## Deployment

The app is configured to be deployed in an EC2 instance from AWS, to do so, it uses the deployment workflow from GitHub
Actions.

![Deployment Workflow](docs/img/pururu_deployment.png)

## Installation

To be able to run this app you will need:

- Python, this app is designed in Python 3.12
- Setup of the [basic configurations](#basic-configurations)
- Discord bot, see [Setting up a bot](#setting-up-a-discord-bot)
- Access to a google sheet, see [Enabling access to a Google Sheet](#enabling-access-to-a-google-sheet)

### Basic Configurations

To load the necessary configurations you can create a file called `.env.development` in the root of the project (use
`.env.base` as reference).

#### Required Configurations

The required configurations to run the app are:

- `DISCORD_TOKEN`: The token of the discord bot. See [Setting up a bot](#setting-up-a-discord-bot)
- `PLAYERS`: the name of the players that will be tracked by the bot, separated by a comma. The names should be
  the [discord member.name](https://discordpy.readthedocs.io/en/latest/api.html#discord.Member.name) that refers to the
  unique username (`username#1234`) without the `#XXXX` part
- `GUILD_ID`: The id of the guild where the bot will be used. You can get this id by right-clicking the server icon and
  selecting `Copy ID` (you will need to have the developer mode enabled in the discord settings)
- `GOOGLE_SHEET_CREDENTIALS`: Refers to the location of the `google_credentials.json` file. This file is the credentials
  to access the Google APIs as a service account.
  See [Enabling access to a Google Sheet](#enabling-access-to-a-google-sheet)
- `SPREADSHEET_ID`: The id of the Google sheet where the data will be stored. You can get this id from the URL of the
  Google sheet. It is the part between the `/d/` and the `/edit` part of the URL.
- `GS_ATTENDANCE_PLAYER_MAPPING`: a hash map that maps the discord member name to the column in the attendance sheet.
  The
  key should be the discord member name and the value should be the column in the attendance sheet. The column should be
  the letter of the column in the sheet (e.g. `A`, `B`, `C`, etc.). As an example this config
  `GS_ATTENDANCE_PLAYER_MAPPING='{"member1":"C","member2":"F",...}'`will work for the [attendance example](#attendance)

#### Customizations

Some configurations can be customized to fit your needs:

- `LOG_LEVEL`: The level of the logs that will be printed. The default is `INFO`, but you can change it to `DEBUG` to
  see more detailed logs; [Available logging levels](https://docs.python.org/3/library/logging.html#logging-levels).
- `ATTENDANCE_CHECK_DELAY`: Refers to time the app will wait to start a new attendance check after the conditions for
  starting a new one are met. The default is 1800 seconds (30 minutes).
- `MIN_ATTENDANCE_TIME`: Refers to the time a member should be in the voice channel to be considered as present. The
  default is 1800 seconds (30 minutes).
- `MIN_ATTENDANCE_MEMBERS`: Refers to the minimum number of members that should be in the voice channel to trigger the
  creation of a new attendance check. The default is 3 members.

### Setting up a discord bot

To be able to create a discord bot first you will need to go to
the [developer portal of discord](https://discord.com/developers/applications) and create a new Application.
Once you got the application, you will need 2 things:

- Adding the bot to your desired server, remember that this app is designed to be used in only 1 server.
- The bot token from the bot section of the application (`DISCORD_TOKEN`).

Note: this app does not require any special permissions, just the basic ones.

### Enabling access to a Google Sheet

First thing you will need to do is going to the [Google Cloud Console](https://console.cloud.google.com/welcome), and
create a new project. After that you will need to enable:

- The [Drive API](https://console.cloud.google.com/apis/api/drive.googleapis.com/metrics).
- The [Sheets API](https://console.cloud.google.com/apis/api/sheets.googleapis.com/metrics).

Once both APIs are enabled you will need to create a service account and download the `google_credentials.json`, to do
so, go to the credentials section.

After having created the Google service account you will need to share the Google sheet with the email of the service
account.

## Contributing

Even that this a private project for an specific needs, feel free to submit a pull request, every suggestion is welcome.

## Versioning

We use [Semantic Versioning](http://semver.org/) for versioning. For the versions
available, see the [tags on this
repository](https://github.com/jlvadell/pururu-bot/tags).

## Authors

- **José Vadell** - [jlvadell](https://github.com/jlvadell)

## License

This project is licensed under the [Apache License 2.0](LICENSE).