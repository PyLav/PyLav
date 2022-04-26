[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Drapersniper/Py-Lav/master.svg)](https://results.pre-commit.ci/latest/github/Drapersniper/Py-Lav/master)

Documentation
---------------------------
### Requirements
- PostgresSQL 14 server
  - MacOS: [PostgresSQL](https://www.postgresql.org/download/macosx/)
  - Windows: [PostgresSQL](https://www.postgresql.org/download/windows/)
  - Linux: [PostgresSQL](https://www.postgresql.org/download/linux/)
- Python 3.10+
- Env Vars to connect the lib to the PostgresSQL server
  - PYLAV__POSTGRES_POST - Defaults to 5432
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
  - lgetyarn
  - lclypit
  - ltts
  - lpornhub
  - lreddit
  - locremix
  - ltiktok
  - lmixcloud
### With [Google Cloud TTS](https://github.com/DuncteBot/tts-plugin):
  - lgcloud-tts
### With [Sponsorblock-Plugin](https://github.com/Topis-Lavalink-Plugins/Sponsorblock-Plugin):
  - lsponsorblock

## Supported Lavalink features
  - Supports all features of [Lavalink](https://github.com/freyacodes/Lavalink)
    - Filters
    - IP Rotation

Features
---------------------------
- Multiple node support
- Local track cache
- Managed local node with auto-restart and auto update
- Many helper methods and functions
- Support for multiple cogs to access the library at once
- Playlists and EQ saved at a library level to be shared with cogs
- Player state persistence
    - Upon library state being shutdown all player states are saved and restored on library startup
- History of played tracks available for players


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
