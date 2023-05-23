from __future__ import annotations

import asyncio
import contextlib
import datetime
import pathlib
import platform
import re
import shlex
import shutil
import tempfile
from typing import TYPE_CHECKING, Any

import aiohttp
import aiopath
import dateutil
import dateutil.parser
import psutil
import rich.progress
import yaml
from packaging.version import Version

from pylav._internals.functions import get_true_path
from pylav.compat import json
from pylav.constants.config import JAVA_EXECUTABLE
from pylav.constants.misc import EPOCH_DT_TZ_AWARE
from pylav.constants.node import JAR_SERVER_RELEASES
from pylav.constants.regex import (
    JAVA_VERSION_LINE_223,
    JAVA_VERSION_LINE_PRE223,
    LAVALINK__READY_LINE,
    LAVALINK_BRANCH_LINE,
    LAVALINK_BUILD_LINE,
    LAVALINK_BUILD_TIME_LINE,
    LAVALINK_COMMIT_LINE,
    LAVALINK_FAILED_TO_START,
    LAVALINK_JAVA_LINE,
    LAVALINK_LAVAPLAYER_LINE,
    LAVALINK_VERSION_LINE,
    SEMANTIC_VERSION_LAZY,
)
from pylav.constants.versions import VERSION_4_0_0
from pylav.exceptions.node import (
    EarlyExitException,
    IncorrectProcessFoundException,
    InvalidArchitectureException,
    LavalinkDownloadFailedException,
    ManagedLavalinkNodeException,
    ManagedLavalinkStartFailureException,
    ManagedLinkStartAbortedUseExternal,
    NodeUnhealthyException,
    NoProcessFoundException,
    PortAlreadyInUseException,
    TooManyProcessFoundException,
    UnexpectedJavaResponseException,
    UnsupportedJavaException,
    WebsocketNotConnectedException,
)
from pylav.extension.bundled_node import LAVALINK_APP_YML, LAVALINK_DOWNLOAD_DIR, LAVALINK_JAR_FILE, USING_FORCED
from pylav.extension.bundled_node.utils import change_dict_naming_convention, get_jar_ram_actual
from pylav.helpers.misc import ExponentialBackoffWithReset
from pylav.logging import getLogger
from pylav.nodes.node import Node
from pylav.storage.migrations.high_level.always.update_plugins import update_plugins
from pylav.type_hints.dict_typing import JSON_DICT_TYPE

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLav", pathlib.Path(__file__))
except ImportError:
    Translator = None

    def _(string: str) -> str:
        return string


if TYPE_CHECKING:
    from pylav.core.client import Client


LOGGER = getLogger("PyLav.ManagedNode")


class LocalNodeManager:
    """A manager for a local Lavalink node."""

    __slots__ = (
        "ready",
        "_ci_info",
        "_client",
        "_proc",
        "_node_pid",
        "_shutdown",
        "start_monitor_task",
        "timeout",
        "_args",
        "_session",
        "_node_id",
        "_node",
        "_current_config",
        "abort_for_unmanaged",
        "_wait_for",
        "_java_path",
        "_java_exc",
        "_java_available",
        "_java_version",
        "_java_version",
        "_up_to_date",
        "_blacklisted_archs",
        "_lavaplayer",
        "_lavalink_build",
        "_jvm",
        "_lavalink_branch",
        "_buildtime",
        "_commit",
        "_version",
        "__buffer_task",
        "_disabled",
    )

    def __init__(self, client: Client, timeout: int | None = None) -> None:
        self._java_available: bool | None = None
        self._java_version: tuple[int, int] | None = None
        self._up_to_date: bool | None = None
        self._blacklisted_archs: list[str] = []

        self._lavaplayer: str | None = None
        self._lavalink_build: int | None = None
        self._jvm: str | None = None
        self._lavalink_branch: str | None = None
        self._buildtime: str | None = None
        self._commit: str | None = None
        self._version: str | None = None
        self._java_exc: str = JAVA_EXECUTABLE

        self.ready: asyncio.Event = asyncio.Event()
        self._ci_info: dict = {"number": 0, "branchName": "", "finishDate": "", "href": "", "jar_url": ""}
        self._client = client
        self._proc: asyncio.subprocess.Process | None = None  # pylint:disable=no-member
        self._node_pid: int | None = None
        self._shutdown: bool = False
        self.start_monitor_task = None
        self.timeout = timeout
        self._args = []
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120), json_serialize=json.dumps)
        self._node_id: int = self._client.bot.user.id
        self._node: Node | None = None
        self._current_config = {}
        self.abort_for_unmanaged: asyncio.Event = asyncio.Event()
        self._args = []
        self._wait_for = asyncio.Event()
        self._java_path = None
        self.__buffer_task = None
        self._disabled = True

    @property
    def disabled(self) -> bool:
        """Whether the node is disabled or not."""
        return self._disabled

    @property
    def node(self) -> Node | None:
        """The node object."""
        return self._node

    @property
    def path(self) -> str | None:
        """The path to the Lavalink jar file."""
        return self._java_exc

    @property
    def jvm(self) -> str | None:
        """The JVM version used by Lavalink."""
        return self._jvm

    @property
    def lavaplayer(self) -> str | None:
        """The Lavaplayer version used by Lavalink."""
        return self._lavaplayer

    @property
    def ll_build(self) -> int | None:
        """The Lavalink build number used by Lavalink."""
        return self._lavalink_build

    @property
    def ll_branch(self) -> str | None:
        """The Lavalink branch used by Lavalink."""
        return self._lavalink_branch

    @property
    def build_time(self) -> str | None:
        """The Lavalink build time used by Lavalink."""
        return self._buildtime

    @staticmethod
    def _get_release_publish_dt_or_epoch(release: dict) -> datetime.datetime:
        return (
            dateutil.parser.parse(release["published_at"])
            if Version(release["tag_name"]) >= VERSION_4_0_0
            else EPOCH_DT_TZ_AWARE
        )

    @staticmethod
    def _get_release_filter(release: dict) -> bool:
        return Version(release["tag_name"]) >= VERSION_4_0_0

    async def get_ci_latest_info(self) -> dict[str, int | str | None]:
        """Get the latest CI info from GitHub."""
        async with self._client.cached_session.get(
            f"{JAR_SERVER_RELEASES}", headers={"Accept": "application/json"}
        ) as response:
            if response.status != 200:
                LOGGER.warning("Failed to get latest CI info from GitHub: %s", response.status)
                self._ci_info["number"] = -1
                return self._ci_info
            data = await response.json(loads=json.loads)
            release = max(filter(self._get_release_filter, data), key=self._get_release_publish_dt_or_epoch)
            assets = release.get("assets", [])
            url = None
            for asset in iter(assets):
                if asset["name"] != "Lavalink.jar":
                    continue
                url = asset.get("browser_download_url")
            if url is None:
                LOGGER.warning("Failed to get a supported released from from GitHub")
                self._ci_info["number"] = -1
                return self._ci_info
            date = release.get("published_at")
            branch = release.get("target_commitish")
            return {"number": int(release.get("id")), "branchName": branch, "finishDate": date, "jar_url": url}

    async def _start(self, java_path: str) -> None:
        arch_name = platform.machine()
        self._java_exc = java_path
        if arch_name in self._blacklisted_archs:
            raise InvalidArchitectureException(
                _("You are attempting to run the managed Lavalink node on an unsupported machine architecture.")
            )
        await self.process_settings()
        possible_lavalink_processes = await self.get_lavalink_process(lazy_match=True)
        if possible_lavalink_processes:
            await self.process_existing_lavalink_processes(possible_lavalink_processes)

        await self.maybe_download_jar()
        args, msg = await self._get_jar_args()
        if msg is not None:
            LOGGER.warning(msg)
        command_string = shlex.join(args)
        LOGGER.info("Managed Lavalink node startup command: %s", command_string)
        if "-Xmx" not in command_string and msg is None:
            LOGGER.warning("Managed Lavalink node maximum allowed RAM not set or higher than available RAM")
        try:
            self._proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
                *args,
                cwd=str(LAVALINK_DOWNLOAD_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            self._node_pid = self._proc.pid
            LOGGER.info("Managed Lavalink node started. PID: %s", self._node_pid)
            try:
                await asyncio.wait_for(self._wait_for_launcher(), timeout=self.timeout)
            except asyncio.TimeoutError:
                LOGGER.warning("Timeout occurred whilst waiting for managed Lavalink node to be ready")
                raise
        except asyncio.TimeoutError:
            await self._partial_shutdown()
        except Exception:  # noqa
            await self._partial_shutdown()
            raise

    async def process_existing_lavalink_processes(self, possible_lavalink_processes: list[dict[str, Any]]) -> None:
        """Process existing Lavalink processes."""
        LOGGER.info(
            "Found %s processes that match potential unmanaged Lavalink nodes", len(possible_lavalink_processes)
        )
        valid_working_dirs = [
            cwd  # noqa
            for d in iter(possible_lavalink_processes)
            if d.get("name") in ["java", "java.exe"] and (cwd := d.get("cwd"))
        ]
        LOGGER.debug("Found %s java processed with a cwd set", len(valid_working_dirs))
        for cwd in iter(valid_working_dirs):
            config = aiopath.AsyncPath(cwd) / "application.yml"
            if await config.exists() and await config.is_file():
                LOGGER.debug(
                    "The following settings file exists for an unmanaged Lavalink node %s",
                    config,
                )
                try:
                    async with config.open(mode="r") as config_data:
                        data = yaml.safe_load(await config_data.read())
                        data["server"]["address"]  # noqa
                        data["server"]["port"]  # noqa
                        data["lavalink"]["server"]["password"]  # noqa
                        self._node_pid = 0
                        self._current_config = data
                        raise ManagedLinkStartAbortedUseExternal
                except ManagedLinkStartAbortedUseExternal:
                    raise
                except Exception:  # noqa
                    LOGGER.exception("Failed to read contents of %s", config)
                    continue

    async def process_settings(self) -> None:
        """Process settings."""
        data = await self._client.node_db_manager.bundled_node_config().fetch_yaml()
        data = change_dict_naming_convention(data)
        # The reason this is here is to completely remove these keys from the application.yml
        # if they are set to empty values
        await self.maybe_remove_youtube_config(data)
        await self.maybe_remove_ratelimit_config(data)
        await self.update_dns_config(data)
        await self.maybe_remove_proxy_config(data)
        await self.maybe_remove_apple_music_config(data)
        await self.maybe_remove_yandex_config(data)
        data["plugins"]["lavasrc"]["providers"] = list(dict.fromkeys(data["plugins"]["lavasrc"]["providers"]))

        await self.maybe_update_apple_music_country_code(data)
        await self.maybe_update_spotify_country_code(data)
        await self.maybe_update_tts_country_code(data)

        self._current_config = data
        async with LAVALINK_APP_YML.open("w") as f:
            await f.write(yaml.safe_dump(data))

    @staticmethod
    async def maybe_update_tts_country_code(data: JSON_DICT_TYPE) -> None:
        """Update TTS country code if it's invalid."""
        if len(data["plugins"]["dunctebot"]["ttsLanguage"]) != 5:
            data["plugins"]["dunctebot"]["ttsLanguage"] = "en-US"
            LOGGER.warning("Invalid TTS language code provided for dunctebot plugin, defaulting to en-US")

    @staticmethod
    async def maybe_update_spotify_country_code(data: JSON_DICT_TYPE) -> None:
        """Update Spotify country code if it's invalid."""
        if len(data["plugins"]["lavasrc"]["spotify"]["countryCode"]) != 2:
            data["plugins"]["lavasrc"]["spotify"]["countryCode"] = "US"
            LOGGER.warning(
                "Spotify country code is not set to a valid ISO 3166-1 alpha-2 code and has been defaulted to US"
            )

    @staticmethod
    async def maybe_update_apple_music_country_code(data: JSON_DICT_TYPE) -> None:
        """Update Apple Music country code if it's invalid."""
        if len(data["plugins"]["lavasrc"]["applemusic"]["countryCode"]) != 2:
            data["plugins"]["lavasrc"]["applemusic"]["countryCode"] = "US"
            LOGGER.warning(
                "Apple Music country code is not set to a valid ISO 3166-1 alpha-2 code and has been defaulted to US"
            )

    @staticmethod
    async def maybe_remove_yandex_config(data: JSON_DICT_TYPE) -> None:
        """Remove Yandex Music config if it's not set."""
        if (
            "accessToken" not in data["plugins"]["lavasrc"]["yandexmusic"]
            or not data["plugins"]["lavasrc"]["yandexmusic"]["accessToken"]
        ):
            del data["plugins"]["lavasrc"]["yandexmusic"]

    @staticmethod
    async def maybe_remove_apple_music_config(data: JSON_DICT_TYPE) -> None:
        """Remove Apple Music config if it's not set."""
        if (
            "mediaAPIToken" not in data["plugins"]["lavasrc"]["applemusic"]
            or not data["plugins"]["lavasrc"]["applemusic"]["mediaAPIToken"]
        ):
            del data["plugins"]["lavasrc"]["applemusic"]["mediaAPIToken"]

    @staticmethod
    async def maybe_remove_proxy_config(data: JSON_DICT_TYPE) -> None:
        """Remove proxy config if it's not set."""
        if not data["lavalink"]["server"]["httpConfig"].get("proxyHost"):
            del data["lavalink"]["server"]["httpConfig"]

    async def update_dns_config(self, data: JSON_DICT_TYPE) -> None:
        """Update DNS config if it's not set."""
        if data["sentry"]["dsn"]:
            data["sentry"]["tags"]["ID"] = self._client.bot.user.id
            data["sentry"]["tags"]["pylav_version"] = self._client.lib_version

    @staticmethod
    async def maybe_remove_ratelimit_config(data: JSON_DICT_TYPE) -> None:
        """Remove ratelimit config if it's not set."""
        if not (
            data["lavalink"]["server"]["ratelimit"].get("ipBlocks")
            and data["lavalink"]["server"]["ratelimit"].get("strategy")
        ):
            del data["lavalink"]["server"]["ratelimit"]

    @staticmethod
    async def maybe_remove_youtube_config(data: JSON_DICT_TYPE) -> None:
        """Remove YouTube config if it's not set."""
        if not all(
            (
                data["lavalink"]["server"]["youtubeConfig"].get("email"),
                data["lavalink"]["server"]["youtubeConfig"].get("password"),
            )
        ):
            del data["lavalink"]["server"]["youtubeConfig"]

    async def _get_jar_args(self) -> tuple[list[str], str | None]:
        java_available, java_version = await self._has_java()
        if not java_available:
            raise OSError(f"Pylav - Java executable not found, tried to use: '{self._java_exc}'")

        java_xms_default, java_xmx_default, __, java_max_allowed_ram = get_jar_ram_actual(self._java_exc)
        java_xms, java_xmx = (
            java_xms_default,
            (await self._client.node_db_manager.bundled_node_config().fetch_extras()).get("max_ram", java_xmx_default),
        )

        match = re.match(r"^(\d+)([MG])$", java_xmx, flags=re.IGNORECASE)
        command_args = [self._java_exc, f"-Xms{java_xms}"]
        if (11, 0) <= java_version < (12, 0):
            command_args.append("-Djdk.tls.client.protocols=TLSv1.2")
        meta = 0, None
        invalid = None
        if match and int(match[1]) * 1024 ** (2 if match[2].lower() == "m" else 3) <= java_max_allowed_ram:
            command_args.append(f"-Xmx{java_xmx}")
        elif meta[0] is not None:
            invalid = "Managed Lavalink node RAM allocation ignored due to system limitations, please fix this"

        command_args.extend(["-jar", str(LAVALINK_JAR_FILE)])
        self._args = command_args
        return command_args, invalid

    async def _has_java(self) -> tuple[bool, tuple[int, int] | None]:
        if self._java_available:
            # Return cached value if we've checked this before
            return self._java_available, self._java_version
        java_exec = get_true_path(self._java_exc)
        java_available = java_exec is not None
        if not java_available:
            self._java_available = False
            self._java_version = None
        else:
            self._java_version = await self._get_java_version()
            self._java_available = self._java_version >= (
                11,
                0,
            )  # https://github.com/lavalink-devs/Lavalink#requirements
            self._java_exc = java_exec
        return self._java_available, self._java_version

    async def _get_java_version(self) -> tuple[int, int]:
        """This assumes we've already checked that java exists"""
        _proc: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(  # pylint:disable=no-member
            self._java_exc,
            "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # java -version outputs to stderr
        __, err = await _proc.communicate()

        version_info: str = err.decode("utf-8")
        lines = version_info.splitlines()

        for line in iter(lines):
            match = JAVA_VERSION_LINE_PRE223.search(line)
            if match is None:
                match = JAVA_VERSION_LINE_223.search(line)
            if match is None:
                match = SEMANTIC_VERSION_LAZY.search(line)
            if match is None:
                continue
            major = int(match["major"])
            minor = 0
            if minor_str := match["minor"]:
                minor = int(minor_str)

            return major, minor

        raise UnexpectedJavaResponseException(
            _(
                "The output of `{command_name_variable_do_not_translate}` was unexpected\n{command_output_variable_do_not_translate}"
            ).format(
                command_name_variable_do_not_translate=f"{self._java_exc} -version",
                command_output_variable_do_not_translate=version_info,
            )
        )

    async def __consume_buffer(self) -> None:
        async for __ in self._proc.stdout:
            pass

    async def _wait_for_launcher(self) -> None:
        LOGGER.info("Waiting for Managed Lavalink node to be ready")
        async for line in self._proc.stdout:
            if LAVALINK__READY_LINE.search(line):
                self.ready.set()
                LOGGER.info("Managed Lavalink node is ready to receive requests")
                self.__buffer_task = asyncio.create_task(self.__consume_buffer())
                break
            if LAVALINK_FAILED_TO_START.search(line):
                if f"Port {self._current_config['server']['port']} was already in use".encode() in line:
                    raise PortAlreadyInUseException(
                        _(
                            "The port {port_variable_do_not_translate} is already in use. Managed Lavalink startup has been aborted."
                        ).format(port_variable_do_not_translate=self._current_config["server"]["port"])
                    )
                raise ManagedLavalinkStartFailureException(
                    _("Lavalink failed to start: {error_variable_do_not_translate}").format(
                        error_variable_do_not_translate=line.decode("utf-8")
                    )
                )
            if self._proc.returncode is not None:
                # Avoid Console spam only print once every 2 seconds
                raise EarlyExitException("Managed Lavalink node server exited early")

    async def shutdown(self) -> None:
        """Shuts down the managed Lavalink node server and removes it from the node manager."""
        self._disabled = True
        if self.start_monitor_task is not None:
            self.start_monitor_task.cancel()
        if self.node:
            await self._client.node_manager.remove_node(self.node)
            self._node = None
        await self._partial_shutdown()
        await self._session.close()

    async def _partial_shutdown(self) -> None:
        self.ready.clear()
        self._wait_for.clear()
        self.abort_for_unmanaged.clear()
        # In certain situations to await self._proc.wait() is invalid so waiting on it waits forever.
        if self._shutdown is True:
            # For convenience, calling this method more than once or calling it before starting it
            # does nothing.
            return
        if self.__buffer_task is not None:
            self.__buffer_task.cancel()
            self.__buffer_task = None
        await self.maybe_kill_existing_process()
        await self.maybe_kill_alive_process()
        self._proc = None
        self._shutdown = True
        self._node_pid = None
        if self._node is not None:
            await self._client.remove_node(self._node_id)
            self._node = None

    async def maybe_kill_alive_process(self) -> None:
        """Kills the process if it is still alive"""
        if self._proc is not None and self._proc.returncode is None:
            self._proc.terminate()
            self._proc.kill()
            await self._proc.wait()

    async def maybe_kill_existing_process(self) -> None:
        """Kills the process if it is still alive"""
        if self._node_pid:
            with contextlib.suppress(psutil.Error):
                p = psutil.Process(self._node_pid)
                p.terminate()
                p.kill()

    async def should_auto_update(self) -> bool:
        """Returns whether or not the managed node should auto update"""
        # noinspection PyProtectedMember
        return (
            False
            if USING_FORCED
            else await self._client._lib_config_manager.get_config().fetch_auto_update_managed_nodes()
        )

    async def _download_jar(self, forced: bool = False) -> None:
        if not await self.should_auto_update() and not forced:
            return
        LOGGER.info("Downloading Lavalink.jar")
        jar_url = (
            self._ci_info["jar_url"] or "https://github.com/lavalink-devs/Lavalink/releases/download/4.0.0/Lavalink.jar"
        )

        async with self._session.get(jar_url, timeout=3600) as response:
            if response.status == 404:
                raise LavalinkDownloadFailedException(response=response, should_retry=False)
            elif 400 <= response.status < 600:
                raise LavalinkDownloadFailedException(response=response, should_retry=True)
            fd, path = tempfile.mkstemp()
            file = open(fd, "wb")
            nbytes = 0
            with rich.progress.Progress(
                rich.progress.SpinnerColumn(),
                rich.progress.TextColumn("[progress.description]{task.description}"),
                rich.progress.BarColumn(),
                rich.progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                rich.progress.TimeRemainingColumn(),
                rich.progress.TimeElapsedColumn(),
            ) as progress:
                progress_task_id = progress.add_task("[red]Downloading Lavalink.jar", total=response.content_length)
                try:
                    chunk = await response.content.read(1024)
                    while chunk:
                        chunk_size = file.write(chunk)
                        nbytes += chunk_size
                        progress.update(progress_task_id, advance=chunk_size)
                        chunk = await response.content.read(1024)
                    file.flush()
                finally:
                    file.close()

            shutil.move(path, str(LAVALINK_JAR_FILE), copy_function=shutil.copyfile)

        LOGGER.info("Successfully downloaded Lavalink.jar (%s bytes written)", format(nbytes, ","))
        await self._is_up_to_date(forced=forced)
        # noinspection PyProtectedMember
        await self._client._config.update_download_id(self._ci_info["number"])

    async def _is_up_to_date(self, forced: bool = False) -> bool:
        if self._up_to_date is True and not forced:
            # Return cached value if we've checked this before
            return True
        # noinspection PyProtectedMember
        last_download_id = await self._client._config.fetch_download_id()
        args, _ = await self._get_jar_args()
        args.append("--version")
        _proc = await asyncio.subprocess.create_subprocess_exec(  # pylint:disable=no-member
            *args,
            cwd=str(LAVALINK_DOWNLOAD_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout = (await _proc.communicate())[0]
        build = LAVALINK_BUILD_LINE.search(stdout) or {"build": b"Unknown"}
        branch = LAVALINK_BRANCH_LINE.search(stdout) or {"branch": b"Unknown"}
        java = LAVALINK_JAVA_LINE.search(stdout) or {"jvm": b"Unknown"}
        lavaplayer = LAVALINK_LAVAPLAYER_LINE.search(stdout) or {"lavaplayer": b"Unknown"}
        buildtime = LAVALINK_BUILD_TIME_LINE.search(stdout) or {"build_time": b"Unknown"}
        commit = LAVALINK_COMMIT_LINE.search(stdout) or {"commit": b"Unknown"}
        version = LAVALINK_VERSION_LINE.search(stdout) or {"version": b"Unknown"}
        LOGGER.info(
            "Current Lavalink meta: Lavalink build: %s, branch: %s, "
            "java: %s, lavaplayer: %s, build_time: %s commit: %s version: %s",
            build["build"],
            branch["branch"],
            java["jvm"],
            lavaplayer["lavaplayer"],
            buildtime["build_time"],
            commit["commit"],
            version["version"],
        )
        if build["build"] == b"Unknown":
            build = int(last_download_id)
        else:
            build = int(build["build"])
        date = buildtime["build_time"].decode()
        date = date.replace(".", "/")
        self._lavalink_build = build
        self._lavalink_branch = branch["branch"].decode()
        self._jvm = java["jvm"].decode()
        self._lavaplayer = lavaplayer["lavaplayer"].decode()
        self._commit = commit["commit"].decode()
        self._version = version["version"].decode()
        self._buildtime = date
        if await self.should_auto_update() or forced:
            self._up_to_date = last_download_id == self._ci_info.get("number", -1)
        else:
            self._ci_info["number"] = build
            self._up_to_date = True
        return self._up_to_date

    async def maybe_download_jar(self) -> None:
        """Download the Lavalink.jar if it doesn't exist or is out of date."""
        if USING_FORCED is False:
            self._ci_info = await self.get_ci_latest_info()
        LOGGER.info("CI info: %s", self._ci_info)
        if not (await LAVALINK_JAR_FILE.exists() and await self._is_up_to_date()):
            await self._download_jar()

    async def wait_until_ready(self, timeout: float | None = None) -> None:
        """Wait until Lavalink is ready to accept connections."""
        tasks = [asyncio.create_task(c) for c in [self.ready.wait(), self.abort_for_unmanaged.wait()]]
        done, pending = await asyncio.wait(tasks, timeout=timeout or self.timeout, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        if done:
            done.pop().result()
        if self.abort_for_unmanaged.is_set():
            raise asyncio.TimeoutError
        if not self.ready.is_set():
            raise asyncio.TimeoutError

    async def wait_until_connected(self, timeout: float | None = None) -> None:
        """Wait until Lavalink is connected."""
        tasks = [asyncio.create_task(c) for c in [self._wait_for.wait(), self.wait_until_ready()]]
        done, pending = await asyncio.wait(tasks, timeout=timeout or self.timeout, return_when=asyncio.ALL_COMPLETED)
        for task in pending:
            task.cancel()

    async def start_monitor(self, java_path: str) -> None:
        """Start the monitor task for this node."""
        retry_count = 0
        backoff = ExponentialBackoffWithReset(base=3)
        while True:
            try:
                await self._monitor_primary_healthy_flow(backoff, java_path, retry_count)
            except (TooManyProcessFoundException, IncorrectProcessFoundException, NoProcessFoundException):
                await self._partial_shutdown()
            except asyncio.TimeoutError:
                delay = backoff.delay()
                await self._partial_shutdown()
                LOGGER.warning(
                    "Lavalink Managed node health check timeout, restarting in %s seconds",
                    delay,
                )
                await asyncio.sleep(delay)
            except ManagedLavalinkStartFailureException:
                await self._monitor_managed_start_failure()
            except NodeUnhealthyException:
                await self._monitor_handle_unhealthy(backoff)
            except LavalinkDownloadFailedException as exc:
                delay = backoff.delay()
                if exc.should_retry:
                    LOGGER.warning(
                        "Lavalink Managed node download failed retrying in %s seconds\n%s",
                        delay,
                        exc.response,
                    )
                    retry_count += 1
                    await self._partial_shutdown()
                    await asyncio.sleep(delay)
                else:
                    LOGGER.error(
                        "Fatal exception whilst starting managed Lavalink node, aborting...\n%s",
                        exc.response,
                    )
                    # lavalink_connection_aborted
                    return await self.shutdown()
            except InvalidArchitectureException:
                LOGGER.error("Invalid machine architecture, cannot run a managed Lavalink node")
                # lavalink_connection_aborted
                return await self.shutdown()
            except (UnsupportedJavaException, UnexpectedJavaResponseException) as exc:
                LOGGER.error(exc)
                # lavalink_connection_aborted
                return await self.shutdown()
            except ManagedLinkStartAbortedUseExternal:
                LOGGER.warning("Lavalink Managed node start aborted, using the detected external Lavalink node")
                return await self.connect_node(reconnect=False, wait_for=0, external_fallback=True)
            except ManagedLavalinkNodeException as exc:
                await self._monitor_managed_node_error(backoff, exc)
            except asyncio.CancelledError:
                LOGGER.warning("Lavalink Managed monitor task cancelled")
                return
            except Exception as exc:
                delay = backoff.delay()
                LOGGER.warning("Lavalink Managed node startup failed retrying in %s seconds", delay, exc_info=exc)
                await self._partial_shutdown()
                await asyncio.sleep(delay)

    async def _monitor_primary_healthy_flow(
        self, backoff: ExponentialBackoffWithReset, java_path: str, retry_count: int
    ) -> None:
        self._shutdown = False
        if self._node_pid is None or not psutil.pid_exists(self._node_pid):
            self.ready.clear()
            await self._start(java_path=java_path)
        while True:
            await self._monitor_primary_node_iteration(backoff, retry_count)

    async def _monitor_primary_node_iteration(self, backoff: ExponentialBackoffWithReset, retry_count: int) -> None:
        await self.wait_until_ready(timeout=self.timeout)
        if not psutil.pid_exists(self._node_pid):
            raise NoProcessFoundException
        if self._node is None or not self._node.websocket.connected and not self._node.websocket.connecting:
            await self.connect_node(reconnect=retry_count != 0, wait_for=3)
        try:
            await self._monitor_connect_to_node(backoff)
        except AttributeError as e:
            await self._monitor_wait_for_connection(e)
        except Exception as exc:
            LOGGER.debug(exc, exc_info=exc)
            raise NodeUnhealthyException(str(exc)) from exc

    async def _monitor_managed_node_error(self, backoff: ExponentialBackoffWithReset, exc: Exception) -> None:
        delay = backoff.delay()
        LOGGER.error(
            exc,
        )
        await self._partial_shutdown()
        LOGGER.warning("Lavalink Managed node startup failed retrying in %s seconds", delay, exc_info=exc)
        await asyncio.sleep(delay)

    async def _monitor_handle_unhealthy(self, backoff: ExponentialBackoffWithReset) -> None:
        delay = backoff.delay()
        await self._partial_shutdown()
        LOGGER.warning(
            "Lavalink Managed node health check failed, restarting in %s seconds",
            delay,
        )
        await asyncio.sleep(delay)

    async def _monitor_managed_start_failure(self) -> None:
        LOGGER.warning("Lavalink Managed node failed to start, restarting")
        await self._partial_shutdown()
        for process in iter(
            await self.get_lavalink_process(
                "-Djdk.tls.client.protocols=TLSv1.2", "-Xms64M", "-jar", cwd=str(LAVALINK_DOWNLOAD_DIR)
            )
        ):
            with contextlib.suppress(psutil.Error):
                pid = process["pid"]
                p = psutil.Process(pid)
                p.terminate()
                p.kill()

    async def _monitor_wait_for_connection(self, e: Exception) -> None:
        try:
            LOGGER.debug("Managed node monitor detected PyLav is not connected to any nodes -%s", exc_info=e)
            while True:
                node = self._client.node_manager.get_node_by_id(self._node_id)
                if node is not None:
                    await node.wait_until_ready(timeout=30)
                if node and node.websocket.connected:
                    break
                await asyncio.sleep(1)
        except asyncio.TimeoutError:
            raise

    async def _monitor_connect_to_node(self, backoff: ExponentialBackoffWithReset) -> None:
        node = self._client.node_manager.get_node_by_id(self._node_id)
        if node is not None:
            await node.wait_until_ready(timeout=30)
        if node.websocket.connected:
            try:
                # Hoping this throws an exception which will then trigger a restart
                await node.websocket.ping()
                backoff.reset()
                await asyncio.sleep(1)
            except WebsocketNotConnectedException:
                await asyncio.sleep(5)
            except ConnectionResetError as e:
                raise AttributeError from e
        elif node.websocket.connecting:
            await node.websocket.wait_until_ready(timeout=30)
        else:
            raise AttributeError

    async def start(self, java_path: str) -> None:
        """Start the managed node."""
        self._disabled = False
        self._java_path = java_path
        if self.start_monitor_task is not None:
            await self.shutdown()
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120), json_serialize=json.dumps)
        if self.__buffer_task is not None:
            self.__buffer_task.cancel()
            self.__buffer_task = None
        self._wait_for.clear()

        await update_plugins(self._client)
        self.start_monitor_task = asyncio.create_task(self.start_monitor(java_path))
        self.start_monitor_task.set_name("LavalinkManagedNode.health_monitor")

    async def connect_node(self, reconnect: bool, wait_for: float = 0.0, external_fallback: bool = False) -> None:
        """Connect to the managed node."""
        # sourcery no-metrics
        await asyncio.sleep(wait_for)
        self._wait_for.clear()
        if not self.ready.is_set():
            if external_fallback:
                self.ready.set()
            else:
                raise ManagedLavalinkStartFailureException()
        if reconnect:
            node = self._client.node_manager.get_node_by_id(self._node_id)
            if node is not None:
                self._node = node
                if node.websocket.connecting:
                    await node.wait_until_ready(timeout=30)
                elif node.websocket.connected:
                    LOGGER.info("Managed Lavalink node is connected")
                else:
                    LOGGER.info("Managed Lavalink node is not connected, reconnecting")
                    await self.restart()
                    return
                self._wait_for.set()
                return
        if (node := self._client.node_manager.get_node_by_id(self._node_id)) is None:
            node = await self.connect_to_node(external_fallback)
        else:
            self._node = node
        if node.websocket.connecting:
            await node.wait_until_ready()
        elif node.websocket.connected:
            LOGGER.info("Managed Lavalink node is connected")
        else:
            LOGGER.info("Managed Lavalink node is not connected, reconnecting")
            await node.websocket.close()
            # noinspection PyProtectedMember
            await node.websocket._websocket_closed(reason="Managed Node restart")
            await node.wait_until_ready(timeout=60)
        self._wait_for.set()

    async def connect_to_node(self, external_fallback: bool) -> Node:
        """Connect to the managed node."""
        data = await self._client.node_db_manager.bundled_node_config().fetch_all()
        name = (
            f"PyLavPortConflictRecovery: {self._node_pid}"
            if external_fallback
            else f"PyLavManagedNode: {self._node_pid}"
        )
        data["yaml"]["sentry"]["tags"]["pylav_version"] = self._client.lib_version
        node = self._node = await self._client.add_node(
            host=self._current_config["server"]["address"],
            port=self._current_config["server"]["port"],
            password=self._current_config["lavalink"]["server"]["password"],
            resume_timeout=data["resume_timeout"],
            name=name,
            managed=True,
            ssl=False,
            search_only=False,
            unique_identifier=self._client.node_db_manager.bundled_node_config().id,
            temporary=True,
        )
        await node.config.update_name(name)
        return node

    @staticmethod
    async def get_lavalink_process(
        *matches: str, cwd: str | None = None, lazy_match: bool = False
    ) -> list[dict[str, Any]]:
        """Get a list of Lavalink processes."""
        process_list = []
        filter_ = [cwd] if cwd else []
        for proc in psutil.process_iter():
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                if cwd and await asyncio.to_thread(proc.cwd) not in filter_:
                    continue
                cmdline = await asyncio.to_thread(proc.cmdline)
                if (
                    matches
                    and all(a in cmdline for a in iter(matches))
                    or lazy_match
                    and any("lavalink" in arg.lower() for arg in iter(cmdline))
                ):
                    proc_as_dict = await asyncio.to_thread(
                        proc.as_dict, attrs=["pid", "name", "create_time", "status", "cmdline", "cwd"]
                    )

                    process_list.append(proc_as_dict)
        return process_list

    async def restart(self, java_path: str = None) -> None:
        """Restart the managed node."""
        LOGGER.info("Restarting managed Lavalink node")
        if node := self._client.get_my_node():
            if self.start_monitor_task is not None:
                self.start_monitor_task.cancel()
                self.start_monitor_task = None
            if self.__buffer_task is not None:
                self.__buffer_task.cancel()
                self.__buffer_task = None

            # noinspection PyProtectedMember
            if not node.websocket._manual_shutdown:
                await node.websocket.manual_closure(managed_node=True)
            with contextlib.suppress(Exception):
                await node.close()
        await self.shutdown()
        await self.start(java_path=java_path or self._java_path)
