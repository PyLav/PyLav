# Setup
**NOTICE**:
  - **These instructions are only applicable until Red 3.5 release.**
  - If you are a Red user, PyLav does not require your Red instance to be running a Postgres Config, however PyLav will still need its own Postgres server.

**NOTICE**:
  - PyLav assumes you are using PostgresSQL server running version 14  and it also requires Python3.11 any other version for these will not work/be supported.
  - If you have docker; Setting up a postgres container for it would likely be the simplest option to setup the necessary server.

# Linux (Ubuntu 20.04) <a name="Linux"></a>
If you are not on Ubuntu 20.04 you just have to follow the instructions below to install the dependencies and set them up for your Linux distro (Google is your friend).
- #### [libaio](https://pagure.io/libaio)
  - `sudo apt install libaio1 libaio-dev`
- #### [Python 3.11](https://www.python.org/downloads/release/python-3110/)
  - ##### Ubuntu
    - `sudo apt update -y && sudo apt upgrade -y`
    - `sudo apt install software-properties-common -y`
    - `sudo add-apt-repository ppa:deadsnakes/ppa -y`
    - `sudo apt update -y`
    - `sudo apt install python3.11 -y`
    - `sudo apt install python3.11-dev python3.11-venv python3.11-distutils -y`

- #### [Python VENV](https://docs.python.org/3/tutorial/venv.html#introduction)
  - A VENV is a self-contained directory tree that contains a Python installation for a particular version of Python, plus a number of additional packages.
  - `python3.11 -m venv ~/p311`
- #### Python Packages
  - First activate the previous created VENV by running `source ~/p311/bin/activate`
  - Install the package download dependencies - `python -m pip install -U pip setuptools wheel`
  - ##### For non Red users
    - Install PyLav -`python -m pip install Py-Lav`
  - ##### For Red users
    - Complete the "Installing the pre-requirements" section of the [Red Docs](https://docs.discord.red/en/stable/install_guides/index.html)
    - Install a custom build of Red - `python -m pip install --force-reinstall git+https://github.com/Drapersniper/Red-DiscordBot@hybrid#egg=Red-DiscordBot`
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
- #### [Install Java Azul Zulu 18](https://docs.azul.com/core/)
  - Follow the instructions [here](https://docs.azul.com/core/zulu-openjdk/install/debian)
    - When prompted to run `sudo apt-get install zulu11-jdk` make sure to run `sudo apt-get install zulu18-ca-jdk-headless` instead.

## Mac <a name="Mac"></a>
- #### [Python 3.11](https://www.python.org/downloads/release/python-3110/)
  - Download and run the [MacOS Installer](https://www.python.org/ftp/python/3.11.0/python-3.11.0-macos11.pkg)
- #### [Python VENV](https://docs.python.org/3/tutorial/venv.html#introduction)
  - A VENV is a self-contained directory tree that contains a Python installation for a particular version of Python, plus a number of additional packages.
  - `python3.11 -m venv ~/p311`
- #### Python Packages
  - First activate the previous created VENV by running `source ~/p311/bin/activate`
  - Install the package download dependencies - `python -m pip install -U pip setuptools wheel`
  - ##### For non Red users
    - Install PyLav -`python -m pip install Py-Lav`
  - ##### For Red users
    - Complete the "Installing the pre-requirements" section of the [Red Docs](https://docs.discord.red/en/stable/install_guides/index.html)
    - Install a custom build of Red - `python -m pip install --force-reinstall git+https://github.com/Drapersniper/Red-DiscordBot@hybrid#egg=Red-DiscordBot`
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
- #### [Install Java Azul Zulu 18](https://docs.azul.com/core/)
  - Download and run the dmg executable [here](https://cdn.azul.com/zulu/bin/zulu18.32.13-ca-jdk18.0.2.1-macosx_x64.dmg)

## Windows <a name="Windows"></a>
- #### [Python 3.11](https://www.python.org/downloads/release/python-3110/)
  - Download the [Windows installer (64-bit)](https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe)
  - Once you're given the option to run the installer, select both the checkboxes – "Install launcher for all users" and "Add Python Python 3.11 to PATH" – at the bottom of the dialog box. Then click on "Install Now."

- #### [Python VENV](https://docs.python.org/3/tutorial/venv.html#introduction)
  - A VENV is a self-contained directory tree that contains a Python installation for a particular version of Python, plus a number of additional packages.
  - `py -3.11 -m venv "%userprofile%\p311"`
- #### Python Packages
  - First activate the previous created VENV by running `source "%userprofile%\p311\Scripts\activate.bat"`
  - Install the package download dependencies - `python -m pip install -U pip setuptools wheel`
  - ##### For non Red users
    - Install PyLav -`python -m pip install Py-Lav`
  - ##### For Red users
    - Complete the "Installing the pre-requirements" section of the [Red Docs](https://docs.discord.red/en/stable/install_guides/index.html)
    - Install a custom build of Red - `python -m pip install --force-reinstall git+https://github.com/Drapersniper/Red-DiscordBot@hybrid#egg=Red-DiscordBot`
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
- #### [Install Java Azul Zulu 18](https://docs.azul.com/core/)
  - Download and run the msi executable [here](https://cdn.azul.com/zulu/bin/zulu18.32.13-ca-jdk18.0.2.1-win_x64.msi)
    - Make sure to select the following when prompted `Add to PATH`, `set JAVA_HOME variable` and `JavaSoft (Oracle) registry keys`


## pylav.yaml Setup
 - Go to your home directory for the user which will run the bot.
   - Windows
     - Run `cd %userprofile%`
   - Mac/Linux
     - Run `cd ~`
- Make a copy of [`pylav.example.yaml`](https://github.com/Drapersniper/PyLav/blob/master/pylav.example.yaml) to your home directory and name it `pylav.yaml`
- Change the values inside the `pylav.yaml` to the desired values
  - Change `PYLAV__POSTGRES_PASSWORD` from `changeme` to to the password of the Postgres user you created above.
  - Change `PYLAV__POSTGRES_USER` from `postgres` to the user you created above.
  - Change `PYLAV__POSTGRES_DB` from `py_lav` to the name of the database you created above (if you followed the commands above it should be `pylav_db`).
  - Change `PYLAV__POSTGRES_PORT` and `PYLAV__POSTGRES_HOST` to the connection host and port for the Postgres server.
  - `PYLAV__JAVA_EXECUTABLE` can be changed from java to the full path of the Azul Zulu 18 Java executable installed above.
    - By default it will use `java` to ensure you have the correct version under `java` run `java --version` if it says "OpenJDK Runtime Environment Zulu18..." then this is not needed to be changed.
  - PyLav bundled an external unmanaged public lavalink Node - The node used is a public node (lava.link) unaffiliated with PyLav or Draper, this will expose you IP to the server hosting the node for communication purposes.
    - To disable this set `PYLAV__USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE` to `false`
    - To enable this set `PYLAV__USE_BUNDLED_EXTERNAL_LAVA_LINK_NODE` to `true`
  - PyLav bundled an external unmanaged public lavalink Node - The node used is a public node (ll.draper.wtf) hosted by Draper, this will expose you IP to the server hosting the node for communication purposes.
    - To disable this set `PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE` to `false`
    - To enable this set `PYLAV__USE_BUNDLED_EXTERNAL_PYLAV_NODE` to `true`
  - If you don't want PyLav to manage a node (not recommended) you can specify the connection args from an external node instead.
    - Note: PyLav supports multiple bots running on the same machine, this should not be the reason why you set these.
      - Set `PYLAV__EXTERNAL_UNMANAGED_HOST` to the Lavalink node connection host
      - Set `PYLAV__EXTERNAL_UNMANAGED_PASSWORD` to the Lavalink node connection auth password.
      - Set `PYLAV__EXTERNAL_UNMANAGED_PORT` to the Lavalink node connection port - If this is not specified the node will use port `80` if `PYLAV__EXTERNAL_UNMANAGED_SSL` is set to `false` or `443` if `PYLAV__EXTERNAL_UNMANAGED_SSL` is set to `true`.
      - Set `PYLAV__EXTERNAL_UNMANAGED_SSL` to `true` or `false` depending on weather or not the external node is using SSL
- If you already have a Redis server and want to make use of it for the request cache you can set `PYLAV__REDIS_FULL_ADDRESS_RESPONSE_CACHE` to the full connection url of your existing server.
  - e.g. `redis://[[username]:[password]]@localhost:6379/0`
  - e.g. `unix://[[username]:[password]]@/path/to/socket.sock?db=0`
- If you want to decrease the frequency of Playlist update tasks you can change the values of the following, note it will only get applied for the next cycle.
  - `PYLAV__TASK_TIMER_UPDATE_BUNDLED_PLAYLISTS_DAYS`: Defaults to  1  # How many days to wait between updates - Minimum 1 Day.
  - `PYLAV__TASK_TIMER_UPDATE_BUNDLED_EXTERNAL_PLAYLISTS_DAYS`: Defaults to  7 # How many days to wait between updates - Minimum 7 Days.
  - `PYLAV__TASK_TIMER_UPDATE_EXTERNAL_PLAYLISTS_DAYS`: Defaults to  7 # How many days to wait between updates - Minimum 7 Days.
- If you want PyLav to cache most of the queries from the Postgres server you can use `PYLAV__CACHING_ENABLED`
  ### **DO NOTE**: If this is set to true multiple bots should not share the same database, as reads and writes will be out of sync.
  - If this is turned off every read from the database will be a direct query to the database, if this is turned on PyLav will cache the results in memory after the first query.
    - If you have a remote server, this will likely be a good idea to turn on, however you loose the ability to manually or otherwise edit the db and changes to be reflected in PyLav. - I would recommend enabling this **ONLY** if you notice slow operation with a remove Postgres server.
- Optional configuration values
  - PYLAV__DEFAULT_SEARCH_SOURCE: Defaults to dzsearch - Possible values are dzsearch (Deezer), spsearch (Spotify), amsearch (Apple Music), ytmsearch (YouTube Music), ytsearch (YouTube)
  - PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_ID: Defaults to None - Required if you want to use Spotify with the managed node
  - PYLAV__MANAGED_NODE_SPOTIFY_CLIENT_SECRET: Defaults to None - Required if you want to use Spotify with the managed node
  - PYLAV__MANAGED_NODE_SPOTIFY_COUNTRY_CODE: Defaults to US
  - PYLAV__MANAGED_NODE_APPLE_MUSIC_API_KEY - Defaults to None
  - PYLAV__MANAGED_NODE_APPLE_MUSIC_COUNTRY_CODE : Defaults to US
  - PYLAV__MANAGED_NODE_YANDEX_MUSIC_ACCESS_TOKEN - Defaults to None - Required if you want to use Yandex with the managed node
  - PYLAV__MANAGED_NODE_DEEZER_KEY - Required if you want to use Deezer
-------------
## Red Users (PyLav Cogs) Setup
### Starting up your bot
  - Activate your VENV created above
  - Run `python -O -m redbot <instance name> -vv`
### Install [PyLav Cogs](https://github.com/Drapersniper/PyLav-Cogs)
- Now that you have your env fully setup you can process to installing the desired cogs.
  - `[p]load downloader`
  - `[p]repo add PyLav https://github.com/Drapersniper/PyLav-Cogs`
  - `[p]cog install PyLav audio`
  - `[p]load audio`
