from __future__ import annotations

from typing import TYPE_CHECKING

from pylav.nodes.api.responses.rest_api import EmptyResponse
from pylav.nodes.api.responses.websocket import Stats as StatsMessage

if TYPE_CHECKING:
    from pylav.nodes.node import Node


async def sort_key_nodes(node: Node, region: str = None) -> float:
    """The sort key for nodes."""
    return await node.penalty_with_region(region)


class Penalty:
    """Represents the penalty of the stats of a Node"""

    __slots__ = ("_stats",)

    def __init__(self, stats: Stats) -> None:
        self._stats = stats

    @property
    def player_penalty(self) -> int:
        """The penalty of the players playing on the node.

        This is the number of players playing in the node.
        """
        return self._stats.playing_players

    @property
    def cpu_penalty(self) -> float:
        """The penalty of the cpu load of the node"""
        return 1.05 ** (100 * self._stats.system_load) * 10 - 10

    @property
    def null_frame_penalty(self) -> float | int:
        """The penalty of the nulled frames of the node"""
        null_frame_penalty = 0
        if self._stats.frames_nulled != -1:
            null_frame_penalty = (1.03 ** (500 * (self._stats.frames_nulled / 3000))) * 300 - 300
            null_frame_penalty *= 2
        return null_frame_penalty

    @property
    def deficit_frame_penalty(self) -> float | int:
        """The penalty of the deficit frames of the node"""
        return (
            1.03 ** (500 * (self._stats.frames_deficit / 3000)) * 600 - 600 if self._stats.frames_deficit != -1 else 0
        )

    # noinspection PyProtectedMember
    @property
    def special_handling(self) -> float:
        """The special handling penalty of the node."""
        # Node connection isn't ready yet
        if not self._stats._node.is_ready:
            return 1000000
        # Ws connection isn't available yet
        if not self._stats._node.available:
            return 1000000
        match self._stats._node.identifier:
            # PyLav external are feature full nodes and will usually be better than the other external nodes
            case 1 | 2:
                return -50
            # If the node is a lava.link node then lets penalise it heavily
            case 1001:
                return 2000
            # EnvVar nodes are always the second best nodes as they are explicitly set
            case 31415:
                return -1500
        # Bundled nodes are always the best nodes
        if self._stats._node.managed:
            # These are nodes already in the same machine using the config port - they are considered good but since they aren't fully managed they are not the best
            if self._stats._node.name.startswith("PyLavPortConflictRecovery"):
                return -500
            # This is a fully managed bundled node - it is the best
            return -2000
        # Reduce the penalty of the node based on how many features it has
        return -1 * len(self._stats._node._capabilities)

    @property
    def total(self) -> float:
        """The total penalty of the node.

        This is the sum of the penalties of the node.
        """
        # noinspection PyProtectedMember
        return (
            self.player_penalty
            + self.cpu_penalty
            + self.null_frame_penalty
            + self.deficit_frame_penalty
            + self._stats._node.down_votes * 100
            + self.special_handling
        )

    def __repr__(self) -> str:
        # noinspection PyProtectedMember
        return (
            f"<Penalty player={self.player_penalty} "
            f"cpu={self.cpu_penalty} "
            f"null_frame={self.null_frame_penalty} "
            f"deficit_frame={self.deficit_frame_penalty} "
            f"votes={self._stats._node.down_votes * 100} "
            f"feature_weighting={self.special_handling} "
            f"total={self.total}>"
        )


class Stats:
    """Represents the stats of Lavalink node"""

    __slots__ = (
        "_node",
        "_data",
        "_penalty",
        "_memory",
        "_cpu",
        "_frame_stats",
    )

    def __init__(self, node: Node, data: StatsMessage) -> None:
        self._node = node
        self._data = data
        self._memory = data.memory
        self._cpu = data.cpu
        self._frame_stats = data.frameStats
        self._penalty = Penalty(self)

    @property
    def uptime(self) -> int:
        """How long the node has been running for in milliseconds"""
        return self._data.uptime

    @property
    def uptime_seconds(self) -> float:
        """How long the node has been running for in seconds"""
        return self.uptime / 1000

    @property
    def players(self) -> int:
        """The amount of players connected to the node"""
        return self._data.players or self._node.connected_count

    @property
    def playing_players(self) -> int:
        """The amount of players that are playing in the node"""
        return self._data.playingPlayers or self._node.playing_count

    @property
    def memory_free(self) -> int:
        """The amount of memory free to the node"""
        return self._memory.free

    @property
    def memory_used(self) -> int:
        """The amount of memory that is used by the node"""
        return self._memory.used

    @property
    def memory_allocated(self) -> int:
        """The amount of memory allocated to the node"""
        return self._memory.allocated

    @property
    def memory_reservable(self) -> int:
        """The amount of memory reservable to the node"""
        return self._memory.reservable

    @property
    def cpu_cores(self) -> int:
        """The amount of cpu cores the system of the node has"""
        return self._cpu.cores

    @property
    def system_load(self) -> float:
        """The overall CPU load of the system"""
        return self._cpu.systemLoad

    @property
    def lavalink_load(self) -> float:
        """The CPU load generated by Lavalink"""
        return self._cpu.lavalinkLoad

    @property
    def frames_sent(self) -> int:
        """The number of frames sent to Discord.
        Warning
        -------
        Given that audio packets are sent via UDP, this number may not be 100% accurate due to dropped packets.
        """
        return self._frame_stats.sent if self._frame_stats else -1

    @property
    def frames_nulled(self) -> int:
        """The number of frames that yielded null, rather than actual data"""
        return self._frame_stats.nulled if self._frame_stats else -1

    @property
    def frames_deficit(self) -> int:
        """The number of missing frames. Lavalink generates this figure by calculating how many packets to expect
        per minute, and deducting ``frames_sent``. Deficit frames could mean the CPU is overloaded, and isn't
        generating frames as quickly as it should be.
        """
        return self._frame_stats.deficit if self._frame_stats else -1

    @property
    def penalty(self) -> Penalty:
        """The penalty for the node"""
        return self._penalty

    def __repr__(self) -> str:
        return (
            f"<Stats node_id={self._node.identifier} "
            f"uptime={self.uptime} "
            f"players={self.players} "
            f"playing_players={self.playing_players} "
            f"memory_free={self.memory_free} "
            f"memory_used={self.memory_used} "
            f"memory_allocated={self.memory_allocated} "
            f"memory_reservable={self.memory_reservable} "
            f"cpu_cores={self.cpu_cores} "
            f"system_load={self.system_load} "
            f"lavalink_load={self.lavalink_load} "
            f"frames_sent={self.frames_sent} "
            f"frames_nulled={self.frames_nulled} "
            f"frames_deficit={self.frames_deficit}> "
            f"penalty={self.penalty}>"
        )


EMPTY_RESPONSE = EmptyResponse(loadType="empty", data=None)
