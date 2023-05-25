import dataclasses
from typing import NotRequired

from pylav.nodes.api.responses.filters import plugins
from pylav.nodes.api.responses.filters.channel_mix import ChannelMix as ChannelMix
from pylav.nodes.api.responses.filters.distortion import Distortion as Distortion
from pylav.nodes.api.responses.filters.equalizer import Equalizer as Equalizer
from pylav.nodes.api.responses.filters.equalizer import EqualizerBand as EqualizerBand
from pylav.nodes.api.responses.filters.karaoke import Karaoke as Karaoke
from pylav.nodes.api.responses.filters.low_pass import LowPass as LowPass
from pylav.nodes.api.responses.filters.plugins import *
from pylav.nodes.api.responses.filters.rotation import Rotation as Rotation
from pylav.nodes.api.responses.filters.timescale import Timescale as Timescale
from pylav.nodes.api.responses.filters.tremolo import Tremolo as Tremolo
from pylav.nodes.api.responses.filters.vibrato import Vibrato as Vibrato

__all__ = (
    "Filters",
    "ChannelMix",
    "Distortion",
    "Echo",
    "Equalizer",
    "EqualizerBand",
    "Karaoke",
    "LowPass",
    "Rotation",
    "Timescale",
    "Tremolo",
    "Vibrato",
    *plugins.__all__,
)

from pylav.nodes.api.responses.shared import PluginInfo
from pylav.type_hints.dict_typing import JSON_DICT_TYPE
from pylav.type_hints.generics import ANY_GENERIC_TYPE


@dataclasses.dataclass(kw_only=True)
class PluginFilters(PluginInfo):
    echo: NotRequired[Echo] | None = dataclasses.field(init=False)


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Filters:
    volume: float | None = None
    equalizer: Equalizer | None = dataclasses.field(default_factory=list)
    karaoke: Karaoke | None = dataclasses.field(default_factory=dict)
    timescale: Timescale | None = dataclasses.field(default_factory=dict)
    tremolo: Tremolo | None = dataclasses.field(default_factory=dict)
    vibrato: Vibrato | None = dataclasses.field(default_factory=dict)
    rotation: Rotation | None = dataclasses.field(default_factory=dict)
    distortion: Distortion | None = dataclasses.field(default_factory=dict)
    channelMix: ChannelMix | None = dataclasses.field(default_factory=dict)
    lowPass: LowPass | None = dataclasses.field(default_factory=dict)
    pluginFilters: PluginFilters | None = dataclasses.field(default_factory=dict)

    def to_dict(self) -> JSON_DICT_TYPE:
        response: JSON_DICT_TYPE = {"volume": self.volume}
        for filter_name in [
            "equalizer",
            "karaoke",
            "timescale",
            "tremolo",
            "vibrato",
            "rotation",
            "distortion",
            "channelMix",
            "lowPass",
            "pluginFilters",
        ]:
            response = self._process_filter(filter_name, response)
        return response

    def _process_filter(self, name: str, response: ANY_GENERIC_TYPE) -> ANY_GENERIC_TYPE:
        match name:
            case "equalizer":
                return self._process_equalizer(response)
            case "karaoke":
                return self._process_filter_object(name, self.karaoke, Karaoke, response)
            case "timescale":
                return self._process_filter_object(name, self.timescale, Timescale, response)
            case "tremolo":
                return self._process_filter_object(name, self.tremolo, Tremolo, response)
            case "vibrato":
                return self._process_filter_object(name, self.vibrato, Vibrato, response)
            case "rotation":
                return self._process_filter_object(name, self.rotation, Rotation, response)
            case "distortion":
                return self._process_filter_object(name, self.distortion, Distortion, response)
            case "channelMix":
                return self._process_filter_object(name, self.channelMix, ChannelMix, response)
            case "lowPass":
                return self._process_filter_object(name, self.lowPass, LowPass, response)
            case "pluginFilters":
                return self._process_plugin_filters(response)
            case __:
                return response

    def _process_equalizer(self, response: ANY_GENERIC_TYPE) -> ANY_GENERIC_TYPE:
        if isinstance(self.equalizer, list):
            response["equalizer"] = [
                band.to_dict() if isinstance(band, EqualizerBand) else band for band in self.equalizer
            ]
        else:
            response["equalizer"] = None
        return response

    def _process_plugin_filters(self, response: ANY_GENERIC_TYPE) -> ANY_GENERIC_TYPE:
        if isinstance(self.pluginFilters, PluginFilters):
            response["pluginFilters"] = self.pluginFilters.to_dict()
        else:
            response["pluginFilters"] = None
        return response

    @staticmethod
    def _process_filter_object(
        name: str,
        filter_name: Karaoke
        | Timescale
        | Tremolo
        | Vibrato
        | Rotation
        | Distortion
        | ChannelMix
        | LowPass
        | Echo
        | None,
        cls: type[Karaoke | Timescale | Tremolo | Vibrato | Rotation | Distortion | ChannelMix | LowPass | Echo],
        response: ANY_GENERIC_TYPE,
    ) -> ANY_GENERIC_TYPE:
        if isinstance(filter_name, cls):
            response[name] = filter_name.to_dict()
        else:
            response[name] = None
        return response
