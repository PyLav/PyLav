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
  - PYLAV__POSTGRES_PORT - Defaults to 5432
  - PYLAV__POSTGRES_PASSWORD - Defaults to ""
  - PYLAV__POSTGRES_USER - Defaults to "postgres"
  - PYLAV__POSTGRES_DB - Defaults to "pylav"
  - PYLAV__POSTGRES_HOST - Defaults to "localhost"
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
$ sudo apt install libaio1 libaio-dev
```
---------------------------

Getting Started
-------------------------------------

Credits
---------------------------
- [Devoxin- Lavalink.py](https://github.com/Devoxin/Lavalink.py) for ideas for implementation.
- [globocom/m3u8](https://github.com/globocom/m3u8) for the M3U8 parser which I made asynchronous found in [m3u8_parser](./pylav/m3u8_parser).
- [andreztz/pyradios](https://github.com/andreztz/pyradios) for the radio parser which I made asynchronous found in [radio](./pylav/radio).
