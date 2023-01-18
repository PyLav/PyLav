# Setup
**NOTICE**:
  - PyLav assumes you are using PostgresSQL server running version 14  and it also requires Python3.11 any other version for these will not work/be supported.
  - If you have docker; Setting up a postgres container for it would likely be the simplest option to setup the necessary server.
  - If you have docker you can use the Lavalink v4 image instead of installing Java for more info [see discord](https://discord.com/channels/970987707834720266/970987936063561738/1054069164148539422)
# Linux (Ubuntu 22.04) <a name="Linux"></a>
If you are not on Ubuntu 20.04 you just have to follow the instructions below to install the dependencies and set them up for your Linux distro (Google is your friend).
- #### [libaio](https://pagure.io/libaio)
  - `sudo apt install libaio1 libaio-dev`
- #### [Postgres14](https://www.postgresql.org/)
  - Follow the install instruction [here](https://www.postgresql.org/download/linux/#generic)
    - Note: When prompted to run `sudo apt-get -y install postgresql` make sure to run `sudo apt-get -y install postgresql-14` instead.
    - ##### Create a new Postgres user
      - `sudo -u postgres createuser -s -i -d -r -l -w <username>`
      - `sudo -u postgres psql -c "ALTER ROLE <username> WITH PASSWORD '<password>';"`
        - Make sure to replace <username> and <password> with the new values
    - ##### Create a new Database for the new user
      - Run `sudo -u postgres psql -c "CREATE DATABASE pylav_db;"`
        - This will crete a new database called `pylav_db`.
      - Run `sudo -u postgres psql -c "ALTER DATABASE pylav_db OWNER TO <username>;"`
- #### [Install Java Azul Zulu 19](https://docs.azul.com/core/)
  - Follow the instructions [here](https://docs.azul.com/core/zulu-openjdk/install/debian)
    - When prompted to run `sudo apt-get install zulu11-jdk` make sure to run `sudo apt-get install zulu19-ca-jdk-headless` instead.
-------------
## Mac <a name="Mac"></a>
- #### [Postgres14](https://www.postgresql.org/)
  - Follow the install instruction [here](https://postgresapp.com/)
  - ##### Create a new Postgres user
    - Open the `psql` command-line tool and login when prompted
    - Run `psql -u postgres` to login as the user `postgres`
    - When logged in run `CREATE ROLE <username> LOGIN PASSWORD '<password>';`
      - Make sure to replace <username> and <password> with the new values
  - ##### Create a new Database for the new user
    - Run `CREATE DATABASE pylav_db;`
      - This will crete a new database called `pylav_db`.
    - Run `ALTER DATABASE pylav_db OWNER TO <username>;`
- #### [Install Java Azul Zulu 19](https://docs.azul.com/core/)
  - Download and run the dmg executable [here](https://cdn.azul.com/zulu/bin/zulu19.30.11-ca-jdk19.0.1-macosx_x64.dmg)
-------------
## Windows <a name="Windows"></a>
- #### [Postgres14](https://www.postgresql.org/)
  - Follow the install instruction [here](https://www.postgresql.org/download/windows/)
  - ##### Create a new Postgres user
    - Open the `psql` command-line tool and login when prompted
    - Run `psql -u postgres` to login as the user `postgres`
    - When logged in run `CREATE ROLE <username> LOGIN PASSWORD '<password>';`
      - Make sure to replace <username> and <password> with the new values
  - ##### Create a new Database for the new user
    - Run `CREATE DATABASE pylav_db;`
      - This will crete a new database called `pylav_db`.
    - Run `ALTER DATABASE pylav_db OWNER TO <username>;`
- #### [Install Java Azul Zulu 19](https://docs.azul.com/core/)
  - Download and run the msi executable [here](https://cdn.azul.com/zulu/bin/zulu19.30.11-ca-jdk19.0.1-win_x64.msi)
    - Make sure to select the following when prompted `Add to PATH`, `set JAVA_HOME variable` and `JavaSoft (Oracle) registry keys`
-------------
##  Environment Variables
Note - All environment variables except `PYLAV__LOGGER_PREFIX` and `PYLAV__YAML_CONFIG` can be configured from the `pylav.yaml` file which should reside in the home directory of the user running the bot.
An example of the file can be found at [pylav.example.yaml](./pylav.example.yaml), if you don't create the file yourself pylav will do so on the first run.
 - `PYLAV__YAML_CONFIG`:
   - If you are in an environment where the home directory is not available you can specify a path to the config file using the `PYLAV__YAML_CONFIG` environment variable.
   - This should be the absolute path to the `pylav.yaml` file i.e `/config/pylav.yaml`.
 - `PYLAV__LOGGER_PREFIX`:
   - The prefix to use for the logger, defaults nothing, if provided all loggers used by PyLav will be prefixed with this value.
-------------
## pylav.yaml Setup (Non-Docker)
 - Go to your home directory for the user which will run the bot.
   - Windows
     - Run `cd %userprofile%`
   - Mac/Linux
     - Run `cd ~`
- Make a copy of [`pylav.example.yaml`](./pylav.example.yaml) to your home directory and name it `pylav.yaml`
- Change the values inside the `pylav.yaml` to the desired values
  - Change `PYLAV__POSTGRES_PASSWORD` from `changeme` to to the password of the Postgres user you created above.
  - Change `PYLAV__POSTGRES_USER` from `changeme` to the user you created above.
  - Change `PYLAV__POSTGRES_DB` from `pylav_db` to the name of the database you created above (if you followed the commands above it should be `pylav_db`).
  - Change `PYLAV__POSTGRES_PORT` and `PYLAV__POSTGRES_HOST` to the connection host and port for the Postgres server.
  -  To use a Unix socket instead of TCP
    - Provide the `PYLAV__POSTGRES_SOCKET` variable. If this is provided `PYLAV__POSTGRES_HOST` and `PYLAV__POSTGRES_PORT` will be ignored.
  - `PYLAV__JAVA_EXECUTABLE` can be changed from java to the full path of the Azul Zulu 18 Java executable installed above.
    - By default it will use `java` to ensure you have the correct version under `java` run `java --version` if it says "OpenJDK Runtime Environment Zulu18..." then this is not needed to be changed.
  - PyLav bundled an external unmanaged public lavalink Node - The node used is a public node (ll.draper.wtf) hosted by Draper, this will expose you IP to the server hosting the node for communication purposes.
    - To disable this set `PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE` to `false`
    - To enable this set `PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE` to `true`
  - If you don't want PyLav to manage a node (not recommended) you can specify the connection args from an external node instead.
    - Note: PyLav supports multiple bots running on the same machine, this should not be the reason why you set these.
      - Set `PYLAV__EXTERNAL_UNMANAGED_HOST` to the Lavalink node connection host
      - Set `PYLAV__EXTERNAL_UNMANAGED_PASSWORD` to the Lavalink node connection auth password.
      - Set `PYLAV__EXTERNAL_UNMANAGED_PORT` to the Lavalink node connection port - If this is not specified the node will use port `80` if `PYLAV__EXTERNAL_UNMANAGED_SSL` is set to `false` or `443` if `PYLAV__EXTERNAL_UNMANAGED_SSL` is set to `true`.
      - Set `PYLAV__EXTERNAL_UNMANAGED_SSL` to `true` or `false` depending on weather or not the external node is using SSL
      - Set `PYLAV__EXTERNAL_UNMANAGED_NAME` to the name of the external node (this is used for logging and event references)

- If you already have a Redis server and want to make use of it for the request cache you can set `PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE` to the full connection url of your existing server.
  - e.g. `redis://[[username]:[password]]@localhost:6379/0`
  - e.g. `unix://[[username]:[password]]@/path/to/socket.sock?db=0`
- If you want to change the frequency of Playlist update tasks you can change the values of the following, note it will only get applied for the next cycle.
  - `PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS`: Defaults to  1  # How many days to wait between updates - Minimum 1 Day.
  - `PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS`: Defaults to  7 # How many days to wait between updates - Minimum 7 Days.
  - `PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS`: Defaults to  7 # How many days to wait between updates - Minimum 7 Days.
- If you want PyLav to cache most of the queries from the Postgres server you can use `PYLAV__READ_CACHING_ENABLED`
  ### **DO NOTE**: If this is set to true multiple bots should not share the same database (The can still share the same Postgres server, just not the same database), as reads and writes will be out of sync.
  - If this is turned off every read from the database will be a direct query to the database, if this is turned on PyLav will cache the results in memory after the first query.
    - If you have a remote server, this will likely be a good idea to turn on, however you loose the ability to manually or otherwise edit the db and changes to be reflected in PyLav. - I would recommend enabling this **ONLY** if you notice slow operation with a remove Postgres server.
- Optional configuration values
  - `PYLAV__DEFAULT_SEARCH_SOURCE`: Defaults to dzsearch - Possible values are dzsearch (Deezer), spsearch (Spotify), amsearch (Apple Music), ytmsearch (YouTube Music), ytsearch (YouTube)
  - `PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_ID`: Defaults to None - Required if you want to use Spotify with the managed node
  - `PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_SECRET`: Defaults to None - Required if you want to use Spotify with the managed node
  - `PYLAV__MANAGED_NODE_SPOTIFY_COUNTRY_CODE`: Defaults to US
  - `PYLAV__MANAGED_NODE_APPLE_MUSIC_API_KEY` - Defaults to None
  - `PYLAV__MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE` : Defaults to US
  - `PYLAV__MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN` - Defaults to None - Required if you want to use Yandex with the managed node
  - `PYLAV__MANAGED_NODE_DEEZER_KEY` - Required if you want to use Deezer, leave empty unless you know what you are doing
## pylav.yaml Setup (Docker)
- Make a copy of [`pylav.docker.yaml`](./pylav.docker.yaml) and mount it to any chosen path i.e `./pylav.docker.yaml:/data/pylav.yaml`
- On your container set the following environment variables:
  - `PYLAV__YAML_CONFIG=/data/pylav.yaml`
- Change the values inside the `pylav.yaml` to the desired values
  - `PYLAV__JAVA_EXECUTABLE` Not applicable leave it as `java`, in a docket setup set the following environment variable instead:
  - Set `PYLAV__EXTERNAL_UNMANAGED_HOST` to the Lavalink node connection host
  - Set `PYLAV__EXTERNAL_UNMANAGED_PASSWORD` to the Lavalink node connection auth password.
  - Set `PYLAV__EXTERNAL_UNMANAGED_PORT` to the Lavalink node connection port - If this is not specified the node will use port `80` if `PYLAV__EXTERNAL_UNMANAGED_SSL` is set to `false` or `443` if `PYLAV__EXTERNAL_UNMANAGED_SSL` is set to `true`.
  - Set `PYLAV__EXTERNAL_UNMANAGED_SSL` to `false` depending on weather or not the external node is using SSL
  - PyLav bundled an external unmanaged public lavalink Node - The node used is a public node (ll.draper.wtf) hosted by Draper, this will expose you IP to the server hosting the node for communication purposes.
    - To disable this set `PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE` to `false`
    - To enable this set `PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE` to `true`
- If you already have a Redis server and want to make use of it for the request cache you can set `PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE` to the full connection url of your existing server.
  - e.g. `redis://[[username]:[password]]@localhost:6379/0`
  - e.g. `unix://[[username]:[password]]@/path/to/socket.sock?db=0`
- If you want to change the frequency of Playlist update tasks you can change the values of the following, note it will only get applied for the next cycle.
  - `PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS`: Defaults to  1  # How many days to wait between updates - Minimum 1 Day.
  - `PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS`: Defaults to  7 # How many days to wait between updates - Minimum 7 Days.
  - `PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS`: Defaults to  7 # How many days to wait between updates - Minimum 7 Days.
- If you want PyLav to cache most of the queries from the Postgres server you can use `PYLAV__READ_CACHING_ENABLED`
  ### **DO NOTE**: If this is set to true multiple bots should not share the same database (The can still share the same Postgres server, just not the same database), as reads and writes will be out of sync.
  - If this is turned off every read from the database will be a direct query to the database, if this is turned on PyLav will cache the results in memory after the first query.
    - If you have a remote server, this will likely be a good idea to turn on, however you loose the ability to manually or otherwise edit the db and changes to be reflected in PyLav. - I would recommend enabling this **ONLY** if you notice slow operation with a remove Postgres server.
- Optional configuration values
  - `PYLAV__DEFAULT_SEARCH_SOURCE`: Defaults to dzsearch - Possible values are dzsearch (Deezer), spsearch (Spotify), amsearch (Apple Music), ytmsearch (YouTube Music), ytsearch (YouTube)
  - `PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_ID`: Defaults to None - Required if you want to use Spotify
  - `PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_SECRET`: Defaults to None - Required if you want to use Spotify
  - `PYLAV__MANAGED_NODE_SPOTIFY_COUNTRY_CODE`: Defaults to US
  - `PYLAV__MANAGED_NODE_APPLE_MUSIC_API_KEY` - Defaults to None
  - `PYLAV__MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE` : Defaults to US
  - `PYLAV__MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN` - Defaults to None - Required if you want to use Yandex
  - `PYLAV__MANAGED_NODE_DEEZER_KEY` - Required if you want to use Deezer, leave empty unless you know what you are doing


## Red Users (PyLav Cogs) Setup
### Install [PyLav Cogs](https://github.com/Drapersniper/PyLav-Cogs)
- Now that you have your env fully setup you can process to installing the desired cogs.
  - `[p]load downloader`
  - `[p]repo add PyLav https://github.com/Drapersniper/PyLav-Cogs`
 - For a list of all available cogs visit the [PyLav Cogs](https://github.com/Drapersniper/PyLav-Cogs) repo
-------------
# Note for 1.0.0 release until Lavalink 4.0.0 is released
- This major release requires Lavalink 4.0.0 which has not yet been released.
## With Docker
  - A custom docker-compose file can be found [here](./docker-compose.yml)
    - This uses a custom fork of Phasecore's redbot image to add support for python3.11 i.e [docker-red-discordbot-fork](https://github.com/Lifeismana/docker-red-discordbot-fork)
    - This uses a custom lavalink image to allow you use Lavalink v4.0.0 early
  - If using this setup make sure to use this [pylav.yaml](./pylav.docker.yaml) file for the PyLav config.
## Without Docker
- You will need will need to complete the following steps before you can successfully use this version, these will only be necessary until Lavalink 4.0.0 is released.
  - Download the latest Lavalink.jar from this [GitHub action](https://github.com/TopiSenpai/Lavalink/suites/10212244117/artifacts/500230420)
  - Place these a directory of your choice.
  - Edit the custom  `application.yml` (If you don't have it join the support server and ask about it) to your liking changing the `CHANGE_ME` values, if you need help with this please join the [Discord support server](https://discord.com/invite/Sjh2TSCYQB)
    - You will need a specify version of the application.yml ping draper#6666 in the support server for it (not needed if you use docker to run Lavalink)
  - Start an unmanaged Lavalink node using the `application.yml` you just edited and the `Lavalink.jar` you just downloaded.
- Make the following changes to your `pylav.yaml` config file
  - Set `PYLAV__EXTERNAL_UNMANAGED_HOST` to `localhost`
  - Set `PYLAV__EXTERNAL_UNMANAGED_PASSWORD` to the `password` in the `lavalink.server` section of the `application.yml` file
  - Set `PYLAV__EXTERNAL_UNMANAGED_PORT` to the `port` in the `server` section of thee `application.yml` file (Default is `2155`)
  - Set `PYLAV__EXTERNAL_UNMANAGED_SSL` to `false`
  - Set `PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_ID` to the `clientId` in the `plugins.lavasrc.potify` section of the `application.yml` file
  - Set `PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_SECRET` to the `clientSecret` in the `plugins.lavasrc.spotify` section of the `application.yml` file
  - Set `PYLAV__MANAGED_NODE_SPOTIFY_COUNTRY_CODE` to the `countryCode` in the `plugins.lavasrc.spotify` section of the `application.yml` file
  - Set `PYLAV__MANAGED_NODE_APPLE_MUSIC_API_KEY` to the `mediaAPIToken` in the `plugins.lavasrc.applemusic` section of the `application.yml` file or if none leave it empty
  - Set `PYLAV__MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE` to the `countryCode` in the `plugins.lavasrc.applemusic` section of the `application.yml` file
  - Set `PYLAV__MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN` to the `accessToken` in the `plugins.lavasrc.yandexmusic` section of the `application.yml` file or if none leave it empty
