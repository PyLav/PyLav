from __future__ import annotations

from enum import Enum


class SegmentCategory(Enum):
    """
    Segment category
    """

    Sponsor = "sponsor"
    Selfpromo = "selfpromo"
    Interaction = "interaction"
    Intro = "intro"
    Outro = "outro"
    Preview = "preview"
    MusicOfftopic = "music_offtopic"
    Filler = "filler"

    @classmethod
    def get_category(cls, segment_type: str) -> SegmentCategory:
        """
        Get segment category
        """
        if segment_type == "intro":
            return SegmentCategory.Intro
        elif segment_type == "outro":
            return SegmentCategory.Outro
        elif segment_type == "preview":
            return SegmentCategory.Preview
        elif segment_type == "music_offtopic":
            return SegmentCategory.MusicOfftopic
        elif segment_type == "filler":
            return SegmentCategory.Filler
        elif segment_type == "sponsor":
            return SegmentCategory.Sponsor
        elif segment_type == "selfpromo":
            return SegmentCategory.Selfpromo
        elif segment_type == "interaction":
            return SegmentCategory.Interaction
        else:
            raise ValueError(f"Unknown segment type: {segment_type}")

    @classmethod
    def get_category_name(cls, segment_type: str) -> str:
        """
        Get segment category name
        """
        return cls.get_category(segment_type).name

    @classmethod
    def get_category_from_name(cls, category_name: str) -> SegmentCategory:
        """
        Get segment category from name
        """
        return SegmentCategory[category_name]

    @classmethod
    def get_category_list(cls) -> list[SegmentCategory]:
        """
        Get segment category list
        """
        return list(cls)

    @classmethod
    def get_category_list_name(cls) -> list[str]:
        """
        Get segment category list name
        """
        return [category.name for category in cls]

    @classmethod
    def get_category_list_value(cls) -> list[str]:
        """
        Get segment category list value
        """
        return [category.value for category in cls]  # type: ignore
