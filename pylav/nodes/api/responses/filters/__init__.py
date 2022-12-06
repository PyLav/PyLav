import dataclasses
from typing import Union

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

from pylav.type_hints.dict_typing import JSON_DICT_TYPE
from pylav.type_hints.generics import ANY_GENERIC_TYPE


@dataclasses.dataclass(repr=True, frozen=True, kw_only=True, slots=True)
class Filters:
    volume: Union[float, None] = None
    equalizer: Union[Equalizer, None] = dataclasses.field(default_factory=list)  # type: ignore
    karaoke: Union[Karaoke, JSON_DICT_TYPE, None] = dataclasses.field(default_factory=dict)
    timescale: Union[Timescale, JSON_DICT_TYPE, None] = dataclasses.field(default_factory=dict)
    tremolo: Union[Tremolo, JSON_DICT_TYPE, None] = dataclasses.field(default_factory=dict)
    vibrato: Union[Vibrato, JSON_DICT_TYPE, None] = dataclasses.field(default_factory=dict)
    rotation: Union[Rotation, JSON_DICT_TYPE, None] = dataclasses.field(default_factory=dict)
    distortion: Union[Distortion, JSON_DICT_TYPE, None] = dataclasses.field(default_factory=dict)
    channelMix: Union[ChannelMix, JSON_DICT_TYPE, None] = dataclasses.field(default_factory=dict)
    lowPass: Union[LowPass, JSON_DICT_TYPE, None] = dataclasses.field(default_factory=dict)
    echo: Union[Echo, JSON_DICT_TYPE, None] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.karaoke, dict):
            object.__setattr__(self, "karaoke", Karaoke(**self.karaoke) if self.karaoke else None)
        if isinstance(self.timescale, dict):
            object.__setattr__(self, "timescale", Timescale(**self.timescale) if self.timescale else None)
        if isinstance(self.tremolo, dict):
            object.__setattr__(self, "tremolo", Tremolo(**self.tremolo) if self.tremolo else None)
        if isinstance(self.vibrato, dict):
            object.__setattr__(self, "vibrato", Vibrato(**self.vibrato) if self.vibrato else None)
        if isinstance(self.rotation, dict):
            object.__setattr__(self, "rotation", Rotation(**self.rotation) if self.rotation else None)
        if isinstance(self.distortion, dict):
            object.__setattr__(self, "distortion", Distortion(**self.distortion) if self.distortion else None)
        if isinstance(self.channelMix, dict):
            object.__setattr__(self, "channelMix", ChannelMix(**self.channelMix) if self.channelMix else None)
        if isinstance(self.lowPass, dict):
            object.__setattr__(self, "lowPass", LowPass(**self.lowPass) if self.lowPass else None)
        if isinstance(self.echo, dict):
            object.__setattr__(self, "echo", Echo(**self.echo) if self.echo else None)

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
            "echo",
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
            case "echo":
                return self._process_filter_object(name, self.echo, Echo, response)
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

    @staticmethod
    def _process_filter_object(
        name: str,
        filter_name: Union[
            Karaoke, Timescale, Tremolo, Vibrato, Rotation, Distortion, ChannelMix, LowPass, Echo | JSON_DICT_TYPE, None
        ],
        cls: type[Union[Karaoke, Timescale, Tremolo, Vibrato, Rotation, Distortion, ChannelMix, LowPass, Echo]],
        response: ANY_GENERIC_TYPE,
    ) -> ANY_GENERIC_TYPE:
        if isinstance(filter_name, cls):
            response[name] = filter_name.to_dict()  # type: ignore
        else:
            response[name] = None
        return response
