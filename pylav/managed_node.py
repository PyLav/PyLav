from __future__ import annotations

import asyncio
import asyncio.subprocess  # disables for # https://github.com/PyCQA/pylint/issues/1469
import contextlib
import pathlib
import platform
import re
import shlex
import shutil
import tempfile
from re import Pattern
from typing import TYPE_CHECKING, Final

import aiohttp
import asyncstdlib
import dateutil.parser
import psutil
import rich.progress
import ujson
import yaml

from pylav._config import CONFIG_DIR
from pylav._logging import getLogger
from pylav.envvars import JAVA_EXECUTABLE
from pylav.exceptions import (
    EarlyExitError,
    IncorrectProcessFound,
    InvalidArchitectureError,
    LavalinkDownloadFailed,
    ManagedLavalinkNodeError,
    ManagedLavalinkStartFailure,
    ManagedLinkStartAbortedUseExternal,
    NodeUnhealthy,
    NoProcessFound,
    PortAlreadyInUseError,
    TooManyProcessFound,
    UnexpectedJavaResponseError,
    UnsupportedJavaError,
    WebsocketNotConnectedError,
)
from pylav.node import Node
from pylav.utils import AsyncIter, ExponentialBackoffWithReset, get_jar_ram_actual, get_true_path
from pylav.vendored import aiopath

if TYPE_CHECKING:
    from pylav.client import Client

try:
    from redbot.core.i18n import Translator

    _ = Translator("PyLavPlayer", pathlib.Path(__file__))
except ImportError:
    _ = lambda x: x

LOGGER = getLogger("PyLav.ManagedNode")

LAVALINK_DOWNLOAD_DIR = CONFIG_DIR / "lavalink"
LAVALINK_DOWNLOAD_DIR = pathlib.Path(LAVALINK_DOWNLOAD_DIR)  # type: ignore
LAVALINK_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
LOGGER.info("Lavalink folder: %s", LAVALINK_DOWNLOAD_DIR)
_LAVALINK_JAR_FILE_FORCED_SYNC = LAVALINK_DOWNLOAD_DIR / "forced.jar"
LAVALINK_DOWNLOAD_DIR: aiopath.AsyncPath = aiopath.AsyncPath(LAVALINK_DOWNLOAD_DIR)
LAVALINK_JAR_FILE: aiopath.AsyncPath = LAVALINK_DOWNLOAD_DIR / "Lavalink.jar"
LAVALINK_JAR_FILE_FORCED: Final[aiopath.AsyncPath] = LAVALINK_DOWNLOAD_DIR / "forced.jar"
if USING_FORCED := _LAVALINK_JAR_FILE_FORCED_SYNC.exists():
    LOGGER.warning("%s found, disabling any JAR automated downloads", LAVALINK_JAR_FILE_FORCED)
    LAVALINK_JAR_FILE: aiopath.AsyncPath = LAVALINK_JAR_FILE_FORCED


LAVALINK_APP_YML: Final[aiopath.AsyncPath] = LAVALINK_DOWNLOAD_DIR / "application.yml"

_RE_READY_LINE: Final[Pattern] = re.compile(rb"Lavalink is ready to accept connections")
_FAILED_TO_START: Final[Pattern] = re.compile(rb"Web server failed to start\. (.*)")

# Version regexes
#
# We expect the output to look something like:
#     $ java -version
#     ...
#     ... version "VERSION STRING HERE" ...
#     ...
#
# There are two version formats that we might get here:
#
# - Version scheme pre JEP 223 - used by Java 8 and older
#
# examples:
# 1.8.0
# 1.8.0_275
# 1.8.0_272-b10
# 1.8.0_202-internal-201903130451-b08
# 1.8.0_272-ea-202010231715-b10
# 1.8.0_272-ea-b10
#
# Implementation based on J2SE SDK/JRE Version String Naming Convention document:
# https://www.oracle.com/java/technologies/javase/versioning-naming.html
_RE_JAVA_VERSION_LINE_PRE223 = re.compile(r'version "1\.(?P<major>[0-8])\.(?P<minor>0)(?:_\d+)?(?:-.*)?"')
# - Version scheme introduced by JEP 223 - used by Java 9 and newer
#
# examples:
# 11
# 11.0.9
# 11.0.9.1
# 11.0.9-ea
# 11.0.9-202011050024
#
# Implementation based on JEP 223 document:
# https://openjdk.java.net/jeps/223
_RE_JAVA_VERSION_LINE_223 = re.compile(r'version "(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.\d+)*(-[a-zA-Z\d]+)?"')
_RE_SEMANTIC_VERSION_LAZY = re.compile(
    r"(?P<major>[0-9]|[1-9][0-9]*)\."
    r"(?P<minor>[0-9]|[1-9][0-9]*)\."
    r"(?P<micro>[0-9]|[1-9][0-9]*)"
    r"(?:-(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+)?"
)

LAVALINK_BUILD_LINE: Final[Pattern] = re.compile(rb"Build:\s+(?P<build>\d+|Unknown)")
LAVALINK_BRANCH_LINE: Final[Pattern] = re.compile(rb"Branch\s+(?P<branch>.+?)\n")
LAVALINK_JAVA_LINE: Final[Pattern] = re.compile(rb"JVM:\s+(?P<jvm>.+?)\n")
LAVALINK_LAVAPLAYER_LINE: Final[Pattern] = re.compile(rb"Lavaplayer\s+(?P<lavaplayer>.+?)\n")
LAVALINK_BUILD_TIME_LINE: Final[Pattern] = re.compile(rb"Build time:\s+(?P<build_time>.+?)\n")
LAVALINK_COMMIT_LINE: Final[Pattern] = re.compile(rb"Commit:\s+(?P<commit>.+?)\n")
LAVALINK_VERSION_LINE: Final[Pattern] = re.compile(rb"Version:\s+(?P<version>.+?)\n")
JAR_SERVER_RELEASES = "https://api.github.com/repos/freyacodes/Lavalink/releases"


def convert_function(key: str) -> str:
    return key.replace("_", "-")


def change_dict_naming_convention(data: dict) -> dict:
    new = {}
    for k, v in data.items():
        new_v = v
        if isinstance(v, dict):
            new_v = change_dict_naming_convention(v)
        elif isinstance(v, list):
            new_v = []
            for x in v:
                if isinstance(x, dict):
                    new_v.append(change_dict_naming_convention(x))
                else:
                    new_v.append(x)
        new[convert_function(k)] = new_v
    return new


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
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), json_serialize=ujson.dumps)
        self._node_id: int = self._client.bot.user.id
        self._node: Node | None = None
        self._current_config = {}
        self.abort_for_unmanaged: asyncio.Event = asyncio.Event()
        self._args = []
        self._wait_for = asyncio.Event()
        self._java_path = None

    @property
    def node(self) -> Node | None:
        return self._node

    @property
    def path(self) -> str | None:
        return self._java_exc

    @property
    def jvm(self) -> str | None:
        return self._jvm

    @property
    def lavaplayer(self) -> str | None:
        return self._lavaplayer

    @property
    def ll_build(self) -> int | None:
        return self._lavalink_build

    @property
    def ll_branch(self) -> str | None:
        return self._lavalink_branch

    @property
    def build_time(self) -> str | None:
        return self._buildtime

    async def get_ci_latest_info(self) -> dict:
        async with self._client.cached_session.get(
            f"{JAR_SERVER_RELEASES}", headers={"Accept": "application/json"}
        ) as response:
            if response.status != 200:
                LOGGER.warning("Failed to get latest CI info from GitHub: %s", response.status)
                self._ci_info["number"] = -1
                return self._ci_info
            data = await response.json(loads=ujson.loads)
            release = await asyncstdlib.max(data, key=lambda x: dateutil.parser.parse(x["published_at"]))
            assets = release.get("assets", [])
            url = None
            async for asset in asyncstdlib.iter(assets):
                if asset["name"] != "Lavalink.jar":
                    continue
                url = asset.get("browser_download_url")
            date = release.get("published_at")
            branch = release.get("target_commitish")
            return {"number": int(release.get("id")), "branchName": branch, "finishDate": date, "jar_url": url}

    async def _start(self, java_path: str) -> None:
        arch_name = platform.machine()
        self._java_exc = java_path
        if arch_name in self._blacklisted_archs:
            raise InvalidArchitectureError(
                _("You are attempting to run the managed Lavalink node on an unsupported machine architecture")
            )
        await self.process_settings()
        possible_lavalink_processes = await self.get_lavalink_process(lazy_match=True)
        if possible_lavalink_processes:
            LOGGER.info(
                "Found %s processes that match potential unmanaged Lavalink nodes",
                len(possible_lavalink_processes),
            )
            valid_working_dirs = [
                cwd
                async for d in asyncstdlib.iter(possible_lavalink_processes)
                if d.get("name") == "java" and (cwd := d.get("cwd"))
            ]
            LOGGER.debug("Found %s java processed with a cwd set", len(valid_working_dirs))
            async for cwd in asyncstdlib.iter(valid_working_dirs):
                config = aiopath.AsyncPath(cwd) / "application.yml"
                if await config.exists() and await config.is_file():
                    LOGGER.debug(
                        "The following config file exists for an unmanaged Lavalink node %s",
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
                    except Exception:
                        LOGGER.exception("Failed to read contents of %s", config)
                        continue

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
                stderr=asyncio.subprocess.STDOUT,
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
        except Exception:
            await self._partial_shutdown()
            raise

    async def process_settings(self):
        data = await self._client.node_db_manager.bundled_node_config().fetch_yaml()
        data = change_dict_naming_convention(data)
        # The reason this is here is to completely remove these keys from the application.yml
        # if they are set to empty values
        if not await asyncstdlib.all(
            (
                data["lavalink"]["server"]["youtubeConfig"].get("email"),
                data["lavalink"]["server"]["youtubeConfig"].get("password"),
            )
        ):
            del data["lavalink"]["server"]["youtubeConfig"]
        if not (
            data["lavalink"]["server"]["ratelimit"].get("ipBlocks")
            and data["lavalink"]["server"]["ratelimit"].get("strategy")
        ):
            del data["lavalink"]["server"]["ratelimit"]
        if data["sentry"]["dsn"]:
            data["sentry"]["tags"]["ID"] = self._client.bot.user.id
            data["sentry"]["tags"]["pylav_version"] = self._client.lib_version
        if not data["lavalink"]["server"]["httpConfig"].get("proxyHost"):
            del data["lavalink"]["server"]["httpConfig"]
        self._current_config = data
        async with LAVALINK_APP_YML.open("w") as f:
            await f.write(yaml.safe_dump(data))

    async def _get_jar_args(self) -> tuple[list[str], str | None]:
        java_available, java_version = await self._has_java()
        if not java_available:
            raise Exception(f"Pylav - Java executable not found, tried to use: '{self._java_exc}'")

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
            self._java_available = self._java_version >= (11, 0)  # https://github.com/freyacodes/Lavalink#requirements
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

        async for line in asyncstdlib.iter(lines):
            match = _RE_JAVA_VERSION_LINE_PRE223.search(line)
            if match is None:
                match = _RE_JAVA_VERSION_LINE_223.search(line)
            if match is None:
                match = _RE_SEMANTIC_VERSION_LAZY.search(line)
            if match is None:
                continue
            major = int(match["major"])
            minor = 0
            if minor_str := match["minor"]:
                minor = int(minor_str)

            return major, minor

        raise UnexpectedJavaResponseError(
            _("The output of `{java_exc} -version` was unexpected\n{version_info}").format(
                java_exc=self._java_exc, version_info=version_info
            )
        )

    async def _wait_for_launcher(self) -> None:
        LOGGER.info("Waiting for Managed Lavalink node to be ready")
        async for __ in asyncstdlib.cycle("."):
            line = await self._proc.stdout.readline()
            if _RE_READY_LINE.search(line):
                self.ready.set()
                LOGGER.info("Managed Lavalink node is ready to receive requests")
                break
            if _FAILED_TO_START.search(line):
                if f"Port {self._current_config['server']['port']} was already in use".encode() in line:
                    raise PortAlreadyInUseError(
                        _("Port {port} already in use. Managed Lavalink startup aborted").format(
                            port=self._current_config["server"]["port"]
                        )
                    )
                raise ManagedLavalinkStartFailure(
                    _("Lavalink failed to start: {line}").format(line=line.decode("utf-8"))
                )
            if self._proc.returncode is not None:
                # Avoid Console spam only print once every 2 seconds
                raise EarlyExitError("Managed Lavalink node server exited early")

    async def shutdown(self) -> None:
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
        if self._node_pid:
            with contextlib.suppress(psutil.Error):
                p = psutil.Process(self._node_pid)
                p.terminate()
                p.kill()
        if self._proc is not None and self._proc.returncode is None:
            self._proc.terminate()
            self._proc.kill()
            await self._proc.wait()
        self._proc = None
        self._shutdown = True
        self._node_pid = None
        if self._node is not None:
            await self._client.remove_node(self._node_id)
            self._node = None

    async def should_auto_update(self) -> bool:
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
            self._ci_info["jar_url"] or "https://github.com/freyacodes/Lavalink/releases/download/3.5.1/Lavalink.jar"
        )

        async with self._session.get(jar_url, timeout=3600) as response:
            if 400 <= response.status < 600:
                raise LavalinkDownloadFailed(response=response, should_retry=True)
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
        await self._client._config.update_download_id(self._ci_info["number"])

    async def _is_up_to_date(self, forced: bool = False) -> bool:
        if self._up_to_date is True and not forced:
            # Return cached value if we've checked this before
            return True
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

    async def maybe_download_jar(self):
        self._ci_info = await self.get_ci_latest_info()
        LOGGER.info("CI info: %s", self._ci_info)
        if not (await LAVALINK_JAR_FILE.exists() and await self._is_up_to_date()):
            await self._download_jar()

    async def wait_until_ready(self, timeout: float | None = None):
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

    async def wait_until_connected(self, timeout: float | None = None):
        tasks = [asyncio.create_task(c) for c in [self._wait_for.wait(), self.wait_until_ready()]]
        done, pending = await asyncio.wait(tasks, timeout=timeout or self.timeout, return_when=asyncio.ALL_COMPLETED)
        for task in pending:
            task.cancel()

    async def start_monitor(self, java_path: str):  # sourcery no-metrics
        retry_count = 0
        backoff = ExponentialBackoffWithReset(base=3)
        while True:
            try:
                self._shutdown = False
                if self._node_pid is None or not psutil.pid_exists(self._node_pid):
                    self.ready.clear()
                    await self._start(java_path=java_path)
                while True:
                    await self.wait_until_ready(timeout=self.timeout)
                    if not psutil.pid_exists(self._node_pid):
                        raise NoProcessFound
                    if self._node is None or not self._node.websocket.connected and not self._node.websocket.connecting:
                        await self.connect_node(reconnect=retry_count != 0, wait_for=3)
                    try:
                        node = self._client.node_manager.get_node_by_id(self._node_id)
                        if node is not None:
                            await node.wait_until_ready(timeout=30)
                        if node.websocket.connected:
                            try:
                                # Hoping this throws an exception which will then trigger a restart
                                await node.websocket.ping()
                                backoff.reset()
                                await asyncio.sleep(1)
                            except WebsocketNotConnectedError:
                                await asyncio.sleep(5)
                            except ConnectionResetError:
                                raise AttributeError
                        elif node.websocket.connecting:
                            await node.websocket.wait_until_ready(timeout=30)
                        else:
                            raise AttributeError
                    except AttributeError as e:
                        try:
                            LOGGER.debug(
                                "Managed node monitor detected RLL is not connected to any nodes -%s", exc_info=e
                            )
                            while True:
                                node = self._client.node_manager.get_node_by_id(self._node_id)
                                if node is not None:
                                    await node.wait_until_ready(timeout=30)
                                if node and node.websocket.connected:
                                    break
                                await asyncio.sleep(1)
                        except asyncio.TimeoutError:
                            raise
                    except Exception as exc:
                        LOGGER.debug(exc, exc_info=exc)
                        raise NodeUnhealthy(str(exc)) from exc
            except (TooManyProcessFound, IncorrectProcessFound, NoProcessFound):
                await self._partial_shutdown()
            except asyncio.TimeoutError:
                delay = backoff.delay()
                await self._partial_shutdown()
                LOGGER.warning(
                    "Lavalink Managed node health check timeout, restarting in %s seconds",
                    delay,
                )
                await asyncio.sleep(delay)
            except ManagedLavalinkStartFailure:
                LOGGER.warning("Lavalink Managed node failed to start, restarting")
                await self._partial_shutdown()
                async for process in asyncstdlib.iter(
                    await self.get_lavalink_process(
                        "-Djdk.tls.client.protocols=TLSv1.2", "-Xms64M", "-jar", cwd=str(LAVALINK_DOWNLOAD_DIR)
                    )
                ):
                    with contextlib.suppress(psutil.Error):
                        pid = process["pid"]
                        p = psutil.Process(pid)
                        p.terminate()
                        p.kill()
            except NodeUnhealthy:
                delay = backoff.delay()
                await self._partial_shutdown()
                LOGGER.warning(
                    "Lavalink Managed node health check failed, restarting in %s seconds",
                    delay,
                )
                await asyncio.sleep(delay)
            except LavalinkDownloadFailed as exc:
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
                    LOGGER.critical(
                        "Fatal exception whilst starting managed Lavalink node, aborting...\n%s",
                        exc.response,
                    )
                    # lavalink_connection_aborted
                    return await self.shutdown()
            except InvalidArchitectureError:
                LOGGER.critical("Invalid machine architecture, cannot run a managed Lavalink node")
                # lavalink_connection_aborted
                return await self.shutdown()
            except (UnsupportedJavaError, UnexpectedJavaResponseError) as exc:
                LOGGER.critical(exc)
                # lavalink_connection_aborted
                return await self.shutdown()
            except ManagedLinkStartAbortedUseExternal:
                LOGGER.warning("Lavalink Managed node start aborted, using the detected external Lavalink node")
                await self.connect_node(reconnect=False, wait_for=0, external_fallback=True)
                return
            except ManagedLavalinkNodeError as exc:
                delay = backoff.delay()
                LOGGER.critical(
                    exc,
                )
                await self._partial_shutdown()
                LOGGER.warning("Lavalink Managed node startup failed retrying in %s seconds", delay, exc_info=exc)
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                LOGGER.warning("Lavalink Managed monitor task cancelled")
                return
            except Exception as exc:
                delay = backoff.delay()
                LOGGER.warning("Lavalink Managed node startup failed retrying in %s seconds", delay, exc_info=exc)
                await self._partial_shutdown()
                await asyncio.sleep(delay)

    async def start(self, java_path: str):
        self._java_path = java_path
        if self.start_monitor_task is not None:
            await self.shutdown()
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), json_serialize=ujson.dumps)
        self._wait_for.clear()
        self.start_monitor_task = asyncio.create_task(self.start_monitor(java_path))
        self.start_monitor_task.set_name("LavalinkManagedNode.health_monitor")

    async def connect_node(self, reconnect: bool, wait_for: float = 0.0, external_fallback: bool = False):
        # sourcery no-metrics
        await asyncio.sleep(wait_for)
        self._wait_for.clear()
        if not self.ready.is_set():
            if external_fallback:
                self.ready.set()
            else:
                raise ManagedLavalinkStartFailure()
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
            data = await self._client.node_db_manager.bundled_node_config().fetch_all()
            resume_key = (
                f"PyLav/{self._client.lib_version}/PyLavPortConflictRecovery-{self._client.bot.user.id}-{self._node_pid}"
                if external_fallback
                else f"PyLav/{self._client.lib_version}/PyLavManagedNode-{self._client.bot.user.id}-{self._node_pid}"
            )
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
                resume_key=resume_key,
                resume_timeout=data["resume_timeout"],
                name=name,
                managed=True,
                ssl=False,
                search_only=False,
                unique_identifier=self._client.node_db_manager.bundled_node_config().id,
                temporary=True,
            )
            await node.config.update_name(name)
            await node.config.update_resume_key(resume_key)
        else:
            self._node = node
        if node.websocket.connecting:
            await node.wait_until_ready()
        elif node.websocket.connected:
            LOGGER.info("Managed Lavalink node is connected")
        else:
            LOGGER.info("Managed Lavalink node is not connected, reconnecting")
            await node.websocket.close()
            await node.websocket._websocket_closed(reason="Managed Node restart")
            await node.wait_until_ready(timeout=60)
        self._wait_for.set()

    @staticmethod
    async def get_lavalink_process(*matches: str, cwd: str | None = None, lazy_match: bool = False):
        process_list = []
        filter_ = [cwd] if cwd else []
        async for proc in AsyncIter(psutil.process_iter()):
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                if cwd and await asyncio.to_thread(proc.cwd) not in filter_:
                    continue
                cmdline = await asyncio.to_thread(proc.cmdline)
                if (
                    matches
                    and await asyncstdlib.all(a in cmdline async for a in asyncstdlib.iter(matches))
                    or lazy_match
                    and await asyncstdlib.any("lavalink" in arg.lower() async for arg in asyncstdlib.iter(cmdline))
                ):
                    proc_as_dict = await asyncio.to_thread(
                        proc.as_dict, attrs=["pid", "name", "create_time", "status", "cmdline", "cwd"]
                    )

                    process_list.append(proc_as_dict)
        return process_list

    async def restart(self, java_path: str = None):
        LOGGER.info("Restarting managed Lavalink node")
        node = await self._client.get_my_node()
        if node:
            if self.start_monitor_task is not None:
                self.start_monitor_task.cancel()
                self.start_monitor_task = None
            if not node.websocket._manual_shutdown:
                await node.websocket.manual_closure(managed_node=True)
            with contextlib.suppress(Exception):
                await node.close()
        await self.shutdown()
        await self.start(java_path=java_path or self._java_path)
