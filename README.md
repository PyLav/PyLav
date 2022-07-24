[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Drapersniper/Py-Lav/master.svg)](https://results.pre-commit.ci/latest/github/Drapersniper/Py-Lav/master)
[![GitHub license](https://img.shields.io/github/license/Drapersniper/Py-Lav.svg)](https://github.com/Drapersniper/Py-Lav/blob/master/LICENSE)
[![Support Server](https://img.shields.io/discord/970987707834720266)](https://discord.com/invite/Sjh2TSCYQB)
[![PyPi](https://img.shields.io/pypi/v/Py-Lav?style=plastic)](https://pypi.org/project/Py-Lav/)

Documentation
---------------------------
### Requirements
- PostgresSQL 14 server
  - MacOS: [PostgresSQL](https://www.postgresql.org/download/macosx/)
  - Windows: [PostgresSQL](https://www.postgresql.org/download/windows/)
  - Linux: [PostgresSQL](https://www.postgresql.org/download/linux/)
- Python 3.10+ (On initial release - during pre-alpha phase 3.9+)
- Env Vars to connect the lib to the PostgresSQL server
  All Envvars default to AsyncPG [defaults](https://magicstack.github.io/asyncpg/current/api/index.html#connection)
  - PYLAV__POSTGRES_PORT
  - PYLAV__POSTGRES_PASSWORD
  - PYLAV__POSTGRES_USER
  - PYLAV__POSTGRES_DB
  - PYLAV__POSTGRES_HOST
- Env Vars to connect the lib cache to Redis, note if these are missing the library will default to PostgresSQL, therefore they are not necessary.
    - This will be used by the aiohttp cached client session for storing cached responses for 1 day, this reduces stress on some of the requests the lib makes such as to RadioBrowser.
      - REDIS_FULLADDRESS_RESPONSE_CACHE
        - e.g. redis://[[username]:[password]]@localhost:6379/0
        - e.g. unix://[[username]:[password]]@/path/to/socket.sock?db=0
- Optional Env vars
  - PYLAV__LOGGER_PREFIX - Sets the logger prefix, defaults to None, or "red." if [redbot](https://github.com/Cog-Creators/Red-DiscordBot) is installed.

- [Discord.py](https://github.com/Rapptz/discord.py) 2.0.0+ bot

---------------------------
## Supported sources
### [Built-in](https://github.com/freyacodes/Lavalink):
  - youtube
  - soundcloud
  - twitch
  - bandcamp
  - vimeo
  - http
  - local
### With [Topis-Source-Managers-Plugin](https://github.com/Topis-Lavalink-Plugins/Topis-Source-Managers-Plugin):
  - spotify
  - applemusic
### With [DuncteBot-plugin](https://github.com/DuncteBot/skybot-lavalink-plugin):
  - getyarn
  - clypit
  - tts
  - pornhub
  - reddit
  - ocremix
  - tiktok
  - mixcloud
### With [Google Cloud TTS](https://github.com/DuncteBot/tts-plugin):
  - gcloud-tts
### With [Sponsorblock-Plugin](https://github.com/Topis-Lavalink-Plugins/Sponsorblock-Plugin):
  - sponsorblock

## Supported Lavalink features
  - Supports all features of [Lavalink](https://github.com/freyacodes/Lavalink)
    - Filters
    - IP Rotation
    - Plug-ins

Features
---------------------------
- Multiple node support
  - Node region assignment based on IP
- Track cache for the last 30 days to reduce the number of duplicated queries
- Managed local node with auto-restart and auto update
- Many helper methods and functions
- Support for multiple cogs to access the library at once
- Playlists and EQ saved at a library level to be shared with cogs
- Player state persistence
    - Upon library state being shutdown all player states are saved and restored on library startup
- History of played tracks available for players
- RadioBrowser.org API to retrieve radio stations available for players
- M3U, PLS and PYLAV text file parser to convert contents into a playlist (p.s. Lavalink must support the format/coded of files still)


Installation
---------------------------

### Dependencies
 - A POSIX compliant OS, or Windows

If you're using a 4.18 or newer kernel and have [`libaio`](https://pagure.io/libaio) installed, `aiopath` will use it via `aiofile`. You can install `libaio` on Debian/Ubuntu like so:
```bash
sudo apt install libaio1 libaio-dev
```

#### Install Python 3.10
  - [Windows & Mac](https://www.python.org/downloads/release/python-3105/)
  - [Ubuntu 22.04](https://www.linuxcapable.com/how-to-install-python-3-10-on-ubuntu-22-04-lts/)
    - Followed by:
```bash
sudo apt install python3.10-dev python3.10-venv python3.10-distutils -y
```

#### Create a Python3.10 Venv
```bash
python3.10 -m venv ~/p310
```
#### Activated Python3.10 Venv
```bash
source ~/p310/bin/activate
```

#### Pre-setup Python 3.10 Venv (After activating it)
```bash
python -m pip install -U pip setuptools wheel
```

#### Install Postgres14
**I will not be providing any further support on how to setup/use Postgres other than the instructions below**

**Postgres is widely used so if you have any issue with the instructions below, or something is missing you can use Google to figure out the missing steps for you case**

- PostgresSQL 14 server
  - MacOS: [PostgresSQL 14 using Postgres.app](https://postgresapp.com/)
  - Windows: [PostgresSQL 14](https://www.postgresql.org/download/windows/)
  - Linux: [PostgresSQL 14](https://www.postgresql.org/download/linux/) - Note you will want to use `postgresql-14` instead of `postgresql` i.e `sudo apt-get -y install postgresql-14`

### Create a new Postgres User and Password
**I will not be providing any further support on how to setup/use Postgres other than the instructions below**

**Postgres is widely used so if you have any issue with the instructions below, or something is missing you can use Google to figure out the missing steps for you case**

- Linux (Credits: [Predeactor](https://github.com/Predeactor)):
```bash
sudo -u postgres createuser -s -i -d -r -l -w <username>
sudo -u postgres psql -c "ALTER ROLE <username> WITH PASSWORD '<password>';"
```
Make sure to replace `<username>` and `<password>` with the new values for example:
```bash
sudo -u postgres createuser -s -i -d -r -l -w Draper
sudo -u postgres psql -c "ALTER ROLE Draper WITH PASSWORD 'MyNewPassword';"
```

#### Setting Environment variables:
- MacOS: [Set Permanent Environment Variable](https://phoenixnap.com/kb/set-environment-variable-mac#ftoc-heading-5)
- Windows: [Set Permanent System Environment Variable](https://www.forbeslindesay.co.uk/post/42833119552/permanently-set-environment-variables-on-windows)
- Linux: [Set Permanent Environment Variable](https://phoenixnap.com/kb/linux-set-environment-variable#ftoc-heading-9)
  - Not if you start your bot wil a service file you will need to set the environment variables there - [more info here](https://flatcar-linux.org/docs/latest/setup/systemd/environment-variables/).

```bash
PYLAV__POSTGRES_PORT=5432
PYLAV__POSTGRES_PASSWORD=<password>
PYLAV__POSTGRES_USER=<username>
PYLAV__POSTGRES_DB=postgres
PYLAV__POSTGRES_HOST=localhost
```
Make sure to replace `<username>` and `<password>` with the new values for example:
```bash
PYLAV__POSTGRES_PASSWORD=MyNewPassword
PYLAV__POSTGRES_USER=Draper
```

#### Install Java 11 or Java 13 (Only these 2 are known to have no issues with Lavalink)
- Debian based OS - [Azure 13](https://docs.azul.com/core/zulu-openjdk/install/debian)
- After installation run `which java` on Linux/Mac or `where java` on Windows, it should point to your install of Java 11/13 if it doesn't you will have to manually set the path the `PYLAV__JAVA_EXECUTABLE` environment variable
---------------------------

Getting Started
-------------------------------------
Once Postgres-14 is installed and you set the environment variables to the correct values for your instance you are all setup to start using PyLav.

Credits
---------------------------
- [Devoxin- Lavalink.py](https://github.com/Devoxin/Lavalink.py) for ideas for implementation.
- [globocom/m3u8](https://github.com/globocom/m3u8) for the M3U8 parser which I made asynchronous found in [m3u8_parser](./pylav/m3u8_parser).
- [andreztz/pyradios](https://github.com/andreztz/pyradios) for the radio parser which I made asynchronous found in [radio](./pylav/radio).
