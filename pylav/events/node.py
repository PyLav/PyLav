from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from pylav.events.base import PyLavEvent

if TYPE_CHECKING:
    from pylav.nodes.api.responses.websocket import Closed
    from pylav.nodes.node import Node
    from pylav.players.player import Player


class NodeDisconnectedEvent(PyLavEvent):
    """This event is dispatched when a node disconnects and becomes unavailable."""

    __slots__ = ()

    def __init__(self, node: Node, code: int, reason: str) -> None:
        self.node = node
        self.code = code
        self.reason = reason


class NodeConnectedEvent(PyLavEvent):
    """This event is dispatched when PyLav successfully connects to a node."""

    __slots__ = ()

    def __init__(self, node: Node) -> None:
        self.node = node


class NodeChangedEvent(PyLavEvent):
    """This event is dispatched when a player changes to another node.
    Keep in mind this event can be dispatched multiple times if a node
    disconnects and the load balancer moves players to a new node.
    """

    __slots__ = ()

    def __init__(self, player: Player, old_node: Node, new_node: Node) -> None:
        self.player = player
        self.old_node = old_node
        self.new_node = new_node


class WebSocketClosedEvent(PyLavEvent):
    """This event is dispatched when an audio websocket to Discord
    is closed. This can happen for various reasons like an
    expired voice server update.
    """

    __slots__ = ()

    def __init__(
        self,
        player: Player,
        node: Node,
        channel: discord.channel.VocalGuildChannel,
        event_object: Closed,
    ) -> None:
        self.player = player
        self.code = event_object.code
        self.reason = event_object.reason
        self.by_remote = event_object.byRemote
        self.node = node
        self.channel = channel
        self.event = event_object
