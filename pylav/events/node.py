from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from pylav.events.base import PyLavEvent

if TYPE_CHECKING:
    from pylav.nodes.api.responses.websocket import Closed
    from pylav.nodes.node import Node
    from pylav.players.player import Player


class NodeDisconnectedEvent(PyLavEvent):
    """This event is dispatched when a node disconnects and becomes unavailable.

    Event can be listened to by adding a listener with the name `pylav_node_disconnected_event`.

    Attributes
    ----------
    node: :class:`Node`
        The node that disconnected.
    code: :class:`int`
        The close code.
    reason: :class:`str`
        The close reason.

    """

    __slots__ = ("node", "code", "reason")

    def __init__(self, node: Node, code: int, reason: str) -> None:
        self.node = node
        self.code = code
        self.reason = reason


class NodeConnectedEvent(PyLavEvent):
    """This event is dispatched when PyLav successfully connects to a node.

    Event can be listened to by adding a listener with the name `pylav_node_connected_event`.

    Attributes
    ----------
    node: :class:`Node`
        The node that connected.
    """

    __slots__ = ("node",)

    def __init__(self, node: Node) -> None:
        self.node = node


class NodeChangedEvent(PyLavEvent):
    """This event is dispatched when a player changes to another node.
    Keep in mind this event can be dispatched multiple times if a node
    disconnects and the load balancer moves players to a new node.

    Event can be listened to by adding a listener with the name `pylav_node_changed_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player that changed nodes.
    old_node: :class:`Node`
        The node the player was on before the change.
    new_node: :class:`Node`
        The node the player is on after the change.
    """

    __slots__ = ("player", "old_node", "new_node")

    def __init__(self, player: Player, old_node: Node, new_node: Node) -> None:
        self.player = player
        self.old_node = old_node
        self.new_node = new_node


class WebSocketClosedEvent(PyLavEvent):
    """This event is dispatched when an audio websocket to Discord
    is closed. This can happen for various reasons like an
    expired voice server update.

    Event can be listened to by adding a listener with the name `pylav_websocket_closed_event`.

    Attributes
    ----------
    player: :class:`Player`
        The player whose websocket was closed.
    node: :class:`Node`
        The node the player is on.
    channel: :class:`discord.channel.VocalGuildChannel`
        The channel the player is in.
    code: :class:`int`
        The close code.
    reason: :class:`str`
        The close reason.
    by_remote: :class:`bool`
        Whether the close was initiated by Discord or not.
    event: :class:`Closed`
        The received event object.
    """

    __slots__ = ("player", "node", "channel", "code", "reason", "by_remote", "event")

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
