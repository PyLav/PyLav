from __future__ import annotations

from pylav.players.filters import plugins
from pylav.players.filters.channel_mix import ChannelMix as ChannelMix
from pylav.players.filters.distortion import Distortion as Distortion
from pylav.players.filters.equalizer import Equalizer as Equalizer
from pylav.players.filters.karaoke import Karaoke as Karaoke
from pylav.players.filters.low_pass import LowPass as LowPass
from pylav.players.filters.plugins import *
from pylav.players.filters.rotation import Rotation as Rotation
from pylav.players.filters.timescale import Timescale as Timescale
from pylav.players.filters.tremolo import Tremolo as Tremolo
from pylav.players.filters.vibrato import Vibrato as Vibrato
from pylav.players.filters.volume import Volume as Volume

__all__ = (
    "ChannelMix",
    "Distortion",
    "Echo",
    "Equalizer",
    "Karaoke",
    "LowPass",
    "Rotation",
    "Timescale",
    "Tremolo",
    "Vibrato",
    "Volume",
    *plugins.__all__,
)
