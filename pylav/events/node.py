import discord

from pylav.events.base import PyLavEvent


class NodeDisconnectedEvent(PyLavEvent):
    """This event is dispatched when a node disconnects and becomes unavailable.

    Attributes
    ----------
    node: :class:`Node`
        The node that was disconnected from.
    code: :class:`int`
        The status code of the event.
    reason: :class:`str`
        The reason of why the node was disconnected.

    Parameters
    ----------
    node: :class:`Node`
        The node that was disconnected from.
    code: :class:`int`
        The status code of the event.
    reason: :class:`str`
        The reason of why the node was disconnected.
    """

    __slots__ = ("node", "code", "reason")

    def __init__(self, node: Node, code: int, reason: str) -> None:
        self.node = node
        self.code = code
        self.reason = reason


class NodeConnectedEvent(PyLavEvent):
    """This event is dispatched when Lavalink.py successfully connects to a node.

    Attributes
    ----------
    node: :class:`Node`
        The node that was successfully connected to.

    Parameters
    ----------
    node: :class:`Node`
        The node that was successfully connected to.
    """

    __slots__ = ("node",)

    def __init__(self, node: Node) -> None:
        self.node = node


class NodeChangedEvent(PyLavEvent):
    """This event is dispatched when a player changes to another node.
    Keep in mind this event can be dispatched multiple times if a node
    disconnects and the load balancer moves players to a new node.


    Attributes
    ----------
    player: :class:`Player`
        The player whose node was changed.
    old_node: :class:`Node`
        The node the player was moved from.
    new_node: :class:`Node`
        The node the player was moved to.

    Parameters
    ----------
    player: :class:`Player`
        The player whose node was changed.
    old_node: :class:`Node`
        The node the player was moved from.
    new_node: :class:`Node`
        The node the player was moved to.
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

    Attributes
    ----------
    player: :class:`Player`
        The player whose audio websocket was closed.
    code: :class:`int`
        The node the player was moved from.
    reason: :class:`str`
        The node the player was moved to.
    by_remote: :class:`bool`
        If the websocket was closed remotely.
    channel: :class:`discord.channel.VocalGuildChannel`
        The voice channel the player was in.
    node: :class:`Node`
        The node the player was in.

    Parameters
    ----------
    player: :class:`Player`
        The player whose audio websocket was closed.
    channel: :class:`discord.channel.VocalGuildChannel`
        The voice channel the player was in.
    node: :class:`Node`
        The node the player was in.
    event_object: :class:`WebSocketClosedEventOpObject`
        The event object that was received from Lavalink.
    """

    __slots__ = ("player", "code", "reason", "by_remote", "node", "channel", "event")

    def __init__(
        self,
        player: Player,
        node: Node,
        channel: discord.channel.VocalGuildChannel,
        event_object: WebSocketClosedEventOpObject,
    ) -> None:
        self.player = player
        self.code = event_object.code
        self.reason = event_object.reason
        self.by_remote = event_object.byRemote
        self.node = node
        self.channel = channel
        self.event = event_object
