[![GitHub license](https://img.shields.io/github/license/PyLav/PyLav.svg)](https://github.com/PyLav/PyLav/blob/develop/LICENSE)
[![Support Server](https://img.shields.io/discord/970987707834720266)](https://discord.com/invite/vnmcXqtgeY)
[![PyPi](https://img.shields.io/pypi/v/Py-Lav?style=plastic)](https://pypi.org/project/Py-Lav/)
[![Crowdin](https://badges.crowdin.net/pylav/localized.svg)](https://crowdin.com/project/pylav)
[![Documentation Status](https://readthedocs.org/projects/pylav/badge/?version=stable)](https://pylav.readthedocs.io/en/stable/?badge=stable)


# Documentation
### Installation
 - [Click Here](SETUP.md)
---------------------------
### Requirements
- PostgresSQL 14 server
  - MacOS: [PostgresSQL](https://www.postgresql.org/download/macosx/)
  - Windows: [PostgresSQL](https://www.postgresql.org/download/windows/)
  - Linux: [PostgresSQL](https://www.postgresql.org/download/linux/)
- Python 3.11
- [Discord.py](https://github.com/Rapptz/discord.py) 2.1.0+ bot
- [Lavalink](https://github.com/lavalink-devs/Lavalink) v4.0.0+ server
---------------------------
## Supported sources
### [Built-in](https://github.com/lavalink-devs/Lavalink):
  - youtube
  - soundcloud
  - bandcamp
  - twitch
  - vimeo
  - http
  - local
### With [LavaSrc](https://github.com/TopiSenpai/LavaSrc)
  - spotify
  - applemusic
  - deezer
### With [DuncteBot-plugin](https://github.com/DuncteBot/skybot-lavalink-plugin):
  - getyarn.io
  - clypit
  - tts
  - pornhub
  - reddit
  - ocremix
  - tiktok
  - mixcloud
  - soundgasm
### With [Google Cloud TTS](https://github.com/DuncteBot/tts-plugin):
  - gcloud-tts
### With [Sponsorblock-Plugin](https://github.com/Topis-Lavalink-Plugins/Sponsorblock-Plugin):
  - sponsorblock

## Supported Lavalink features
  - Supports all features of [Lavalink](https://github.com/lavalink-devs/Lavalink)
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
- Lyrics API to retrieve lyrics for tracks provided by [Flowery](https://flowery.pw)
- M3U, PLS and PYLAV text file parser to convert contents into a playlist (p.s. Lavalink must support the format/coded of files still)

System Requirements
------------------------------------
With a locally hosted Postgres server and locally hosted/managed lavalink node (**recommended - Best performance**):
- CPU: 3 cores or more
- RAM: 4GB or more
- Disk Space: 10GB or more (NVME Ideally, SSD OK)

With a locally hosted Postgres server and externally hosted lavalink node (Okay performance):
- CPU: 2 cores or more
- RAM: 3GB or more
- Disk Space: 10GB or more (NVME Ideally, SSD OK)

With an externally hosted Postgres server and locally hosted/managed lavalink node (Poor performance):
- CPU: 2 cores or more
- RAM: 2GB or more
- Disk Space: 10GB or more (SSD)

With an externally hosted Postgres server and externally hosted lavalink node (Worst performance):
- CPU: 1 cores or more
- RAM: 1GB or more
- Disk Space: 10GB or more (SSD)

Credits
---------------------------
- [Topi](https://github.com/TopiSenpai) for all the work done to Lavalink and implementing direct requests to make PyLav even better.
- [Devoxin - Lavalink.py](https://github.com/Devoxin/Lavalink.py) for the original ideas for implementation.
- [Ryan](https://github.com/ryan5453) for the amazing [Lyrics API](https://flowery.pw) used for lyrics.
- [globocom/m3u8](https://github.com/globocom/m3u8) for the M3U8 parser which I made asynchronous found in [m3u8_parser](pylav/extension/m3u).
- [andreztz/pyradios](https://github.com/andreztz/pyradios) for the radio parser which I made asynchronous found in [radio](pylav/extension/radio).
- [Lifeismana](https://github.com/Lifeismana) for the custom Red-DiscordBot docker image which added Python3.11 support until Phasecore's image is updated.
