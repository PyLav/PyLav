from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import discord
from redbot.core.i18n import Translator

from pylav.core.context import PyLavContext
from pylav.extension.red.ui.buttons.generic import CloseButton, NavigateButton, RefreshButton
from pylav.extension.red.ui.buttons.player import DisconnectButton
from pylav.extension.red.ui.buttons.queue import (
    DecreaseVolumeButton,
    EmptyQueueButton,
    EnqueueButton,
    IncreaseVolumeButton,
    PauseTrackButton,
    PlayNowFromQueueButton,
    PreviousTrackButton,
    QueueHistoryButton,
    RemoveFromQueueButton,
    ResumeTrackButton,
    ShuffleButton,
    SkipTrackButton,
    StopTrackButton,
    ToggleRepeatButton,
    ToggleRepeatQueueButton,
)
from pylav.extension.red.ui.menus.generic import BaseMenu
from pylav.extension.red.ui.selectors.queue import QueueSelectTrack
from pylav.extension.red.ui.sources.queue import QueuePickerSource, QueueSource
from pylav.extension.red.utils.decorators import is_dj_logic
from pylav.type_hints.bot import DISCORD_BOT_TYPE, DISCORD_COG_TYPE, DISCORD_INTERACTION_TYPE

_ = Translator("PyLav", Path(__file__))

if TYPE_CHECKING:
    from pylav.players.player import Player


class QueueMenu(BaseMenu):
    _source: QueueSource

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        bot: DISCORD_BOT_TYPE,
        source: QueueSource,
        original_author: discord.abc.User,
        *,
        delete_after_timeout: bool = True,
        timeout: int = 600,
        message: discord.Message = None,
        starting_page: int = 0,
        history: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            cog=cog,
            bot=bot,
            source=source,
            delete_after_timeout=delete_after_timeout,
            timeout=timeout,
            message=message,
            starting_page=starting_page,
            **kwargs,
        )
        self.author = original_author
        self.is_history = history
        self.forward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=1,
            row=0,
            cog=cog,
        )
        self.backward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=-1,
            row=0,
            cog=cog,
        )
        self.first_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}",
            direction=0,
            row=0,
            cog=cog,
        )
        self.last_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}",
            direction=self.source.get_max_pages,
            row=0,
            cog=cog,
        )
        self.refresh_button = RefreshButton(
            style=discord.ButtonStyle.grey,
            row=0,
            cog=cog,
        )

        self.queue_disconnect = DisconnectButton(
            style=discord.ButtonStyle.red,
            row=1,
            cog=cog,
        )
        self.repeat_queue_button_on = ToggleRepeatQueueButton(
            style=discord.ButtonStyle.blurple,
            row=1,
            cog=cog,
        )
        self.repeat_button_on = ToggleRepeatButton(
            style=discord.ButtonStyle.blurple,
            row=1,
            cog=cog,
        )
        self.repeat_button_off = ToggleRepeatButton(
            style=discord.ButtonStyle.grey,
            row=1,
            cog=cog,
        )
        self.show_history_button = QueueHistoryButton(
            style=discord.ButtonStyle.grey,
            row=1,
            cog=cog,
        )

        self.close_button = CloseButton(
            style=discord.ButtonStyle.red,
            row=1,
            cog=cog,
        )
        self.clear_queue_button = EmptyQueueButton(style=discord.ButtonStyle.red, row=1, cog=cog)

        self.previous_track_button = PreviousTrackButton(
            style=discord.ButtonStyle.grey,
            row=2,
            cog=cog,
        )
        self.stop_button = StopTrackButton(
            style=discord.ButtonStyle.grey,
            row=2,
            cog=cog,
        )
        self.paused_button = PauseTrackButton(
            style=discord.ButtonStyle.blurple,
            row=2,
            cog=cog,
        )
        self.resume_button = ResumeTrackButton(
            style=discord.ButtonStyle.blurple,
            row=2,
            cog=cog,
        )
        self.skip_button = SkipTrackButton(
            style=discord.ButtonStyle.grey,
            row=2,
            cog=cog,
        )
        self.shuffle_button = ShuffleButton(
            style=discord.ButtonStyle.grey,
            row=2,
            cog=cog,
        )

        self.decrease_volume_button = DecreaseVolumeButton(
            style=discord.ButtonStyle.grey,
            row=3,
            cog=cog,
        )
        self.increase_volume_button = IncreaseVolumeButton(
            style=discord.ButtonStyle.grey,
            row=3,
            cog=cog,
        )

        self.enqueue_button = EnqueueButton(
            cog=cog,
            style=discord.ButtonStyle.green,
            row=3,
        )
        self.remove_from_queue_button = RemoveFromQueueButton(
            cog=cog,
            style=discord.ButtonStyle.red,
            row=3,
        )
        self.play_now_button = PlayNowFromQueueButton(
            cog=cog,
            style=discord.ButtonStyle.blurple,
            row=3,
        )

    async def prepare(self):
        self.clear_items()
        max_pages = self.source.get_max_pages()
        is_dj = await is_dj_logic(self.ctx)

        if (not self.is_history) and is_dj is True:
            self.add_item(self.close_button)
            self.add_item(self.queue_disconnect)
            self.add_item(self.clear_queue_button)

        self.add_item(self.first_button)
        self.add_item(self.backward_button)
        self.add_item(self.forward_button)
        self.add_item(self.last_button)
        self.add_item(self.refresh_button)

        if not self.is_history:
            self.repeat_button_on.disabled = False
            self.repeat_button_off.disabled = False
            self.repeat_queue_button_on.disabled = False
            self.clear_queue_button.disabled = False
            self.show_history_button.disabled = False

        self.forward_button.disabled = False
        self.backward_button.disabled = False
        self.first_button.disabled = False
        self.last_button.disabled = False
        self.refresh_button.disabled = False

        if max_pages == 1:
            self.forward_button.disabled = True
            self.backward_button.disabled = True
            self.first_button.disabled = True
            self.last_button.disabled = True
        elif max_pages == 2:
            self.first_button.disabled = True
            self.last_button.disabled = True
        if self.is_history or is_dj is False:
            return

        self.previous_track_button.disabled = False
        self.paused_button.disabled = False
        self.resume_button.disabled = False
        self.stop_button.disabled = False
        self.skip_button.disabled = False
        self.shuffle_button.disabled = False

        self.decrease_volume_button.disabled = False
        self.increase_volume_button.disabled = False
        self.enqueue_button.disabled = False
        self.remove_from_queue_button.disabled = False
        self.play_now_button.disabled = False

        self.add_item(self.previous_track_button)
        self.add_item(self.stop_button)

        if (player := self.cog.pylav.get_player(self.source.guild_id)) and is_dj is not False:
            await self._player_and_dj(player)
        else:
            await self._no_player_or_no_dj()
        self.add_item(self.skip_button)
        self.add_item(self.shuffle_button)
        self.add_item(self.decrease_volume_button)
        self.add_item(self.increase_volume_button)
        self.add_item(self.enqueue_button)
        self.add_item(self.remove_from_queue_button)
        self.add_item(self.play_now_button)

    async def _player_and_dj(self, player: Player):
        self.queue_disconnect.disabled = False
        if player.paused:
            self.add_item(self.resume_button)
        else:
            self.add_item(self.paused_button)
        if player.queue.empty():
            self.shuffle_button.disabled = True
            self.remove_from_queue_button.disabled = True
            self.play_now_button.disabled = True
            self.clear_queue_button.disabled = True
        if not player.current:
            self.stop_button.disabled = True
            self.shuffle_button.disabled = True
            self.previous_track_button.disabled = True
            self.decrease_volume_button.disabled = True
            self.increase_volume_button.disabled = True
        if player.history.empty():
            self.previous_track_button.disabled = True
            self.show_history_button.disabled = True
        else:
            self.add_item(self.show_history_button)
        if await player.config.fetch_repeat_current():
            self.add_item(self.repeat_button_on)
        elif await player.config.fetch_repeat_queue():
            self.add_item(self.repeat_queue_button_on)
        else:
            self.add_item(self.repeat_button_off)

    async def _no_player_or_no_dj(self):
        self.queue_disconnect.disabled = True
        self.forward_button.disabled = True
        self.backward_button.disabled = True
        self.first_button.disabled = True
        self.last_button.disabled = True
        self.stop_button.disabled = True
        self.skip_button.disabled = True
        self.previous_track_button.disabled = True
        self.repeat_button_off.disabled = True
        self.show_history_button.disabled = True
        self.shuffle_button.disabled = True
        self.decrease_volume_button.disabled = True
        self.increase_volume_button.disabled = True
        self.resume_button.disabled = True
        self.repeat_button_on.disabled = True
        self.enqueue_button.disabled = True
        self.remove_from_queue_button.disabled = True
        self.play_now_button.disabled = True
        self.repeat_queue_button_on.disabled = True
        self.clear_queue_button.disabled = True
        self.add_item(self.resume_button)
        self.add_item(self.repeat_button_off)

    @property
    def source(self) -> QueueSource:
        return self._source

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.cog.bot.get_context(ctx)
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer(ephemeral=True)

        self.ctx = ctx
        await self.send_initial_message(ctx)


class QueuePickerMenu(BaseMenu):
    _source: QueuePickerSource

    def __init__(
        self,
        cog: DISCORD_COG_TYPE,
        bot: DISCORD_BOT_TYPE,
        source: QueuePickerSource,
        original_author: discord.abc.User,
        *,
        delete_after_timeout: bool = True,
        timeout: int = 120,
        message: discord.Message = None,
        starting_page: int = 0,
        menu_type: Literal["remove", "play"],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            cog=cog,
            bot=bot,
            source=source,
            delete_after_timeout=delete_after_timeout,
            timeout=timeout,
            message=message,
            starting_page=starting_page,
            **kwargs,
        )
        self.author = original_author
        self.menu_type = menu_type
        self.forward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=1,
            row=4,
            cog=cog,
        )
        self.backward_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            direction=-1,
            row=4,
            cog=cog,
        )
        self.first_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}",
            direction=0,
            row=4,
            cog=cog,
        )
        self.last_button = NavigateButton(
            style=discord.ButtonStyle.grey,
            emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}",
            direction=self.source.get_max_pages,
            row=4,
            cog=cog,
        )
        self.close_button = CloseButton(
            style=discord.ButtonStyle.red,
            row=4,
            cog=cog,
        )
        self.refresh_button = RefreshButton(
            style=discord.ButtonStyle.grey,
            row=4,
            cog=cog,
        )
        self.select_view: QueueSelectTrack | None = None
        self.add_item(self.first_button)
        self.add_item(self.backward_button)
        self.add_item(self.forward_button)
        self.add_item(self.last_button)

    @property
    def source(self) -> QueuePickerSource:
        return self._source

    async def start(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.cog.bot.get_context(ctx)
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer(ephemeral=True)
        self.ctx = ctx
        await self.send_initial_message(ctx)

    async def send_initial_message(self, ctx: PyLavContext | DISCORD_INTERACTION_TYPE):
        await self._source.get_page(0)
        self.ctx = ctx
        kwargs = await self.source.format_page(self, [])
        await self.prepare()
        self.message = await ctx.send(view=self, ephemeral=True, **kwargs)
        return self.message

    async def show_page(self, page_number: int, interaction: DISCORD_INTERACTION_TYPE):
        await self._source.get_page(page_number)
        await self.prepare()
        self.current_page = page_number
        if self.message is not None:
            if not interaction.response.is_done():
                await interaction.response.pong()
            await self.message.edit(view=self)
        elif not interaction.response.is_done():
            await interaction.response.edit_message(view=self)

    async def prepare(self):
        self.clear_items()
        max_pages = self.source.get_max_pages()
        self.forward_button.disabled = False
        self.backward_button.disabled = False
        self.first_button.disabled = False
        self.last_button.disabled = False
        if max_pages == 1:
            self.forward_button.disabled = True
            self.backward_button.disabled = True
            self.first_button.disabled = True
            self.last_button.disabled = True
        elif max_pages == 2:
            self.first_button.disabled = True
            self.last_button.disabled = True
        self.add_item(self.close_button)
        self.add_item(self.first_button)
        self.add_item(self.backward_button)
        self.add_item(self.forward_button)
        self.add_item(self.last_button)
        if self.source.select_options:
            options = self.source.select_options
            if self.menu_type == "remove":
                title = _("Select a track to remove.")
            else:
                title = _("Select a track to play now.")
            self.remove_item(self.select_view)
            self.select_view = QueueSelectTrack(
                options=options,
                cog=self.cog,
                placeholder=title,
                interaction_type=self.menu_type,
                mapping=self.source.select_mapping,
            )
            self.add_item(self.select_view)
        if self.select_view and not self.source.select_options:
            self.remove_item(self.select_view)
            self.select_view = None
