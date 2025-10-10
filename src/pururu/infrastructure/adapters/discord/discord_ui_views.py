from typing import Callable

import discord

import pururu.infrastructure.adapters.discord.discord_ui_components as discord_components
from pururu.domain.entities.session import Session, Status
from pururu.config import settings


class SessionInfoLayoutView(discord.ui.LayoutView):
    def __init__(self, session: Session, on_session_type_change: Callable[[str, str], None], on_attendance_edit: Callable[[str, dict[str,bool], dict[str,str]], None], thumbnail_url: str):
        super().__init__(timeout=None)
        self.session = session
        self.thumbnail_url = thumbnail_url
        self.on_session_type_change = on_session_type_change
        self.on_attendance_edit = on_attendance_edit
        self._build()

    def _build(self):
        accessory = discord.ui.Thumbnail(media=self.thumbnail_url) if not self.session.is_concluded() else discord_components.EditAttendanceButton(modal=EditAttendanceModal(session=self.session, callback=self.on_attendance_edit))
        self.add_item(discord.ui.Container(
            discord_components.SessionStatusTitleTextDisplay(status=self.session.status),
            discord.ui.Section(
                discord_components.SessionDetailsTextDisplay(session=self.session),
                accessory=accessory
            ),
            accent_color=self.get_accent_color_from_status()
        ))
        self.add_item(discord.ui.Separator(visible=False))

        action_row = discord.ui.ActionRow()
        action_row.add_item(discord_components.ChangeSessionTypeButton(modal=EditSessionTypeModal(session=self.session, callback=self.on_session_type_change)))
        offline_users = [player.player_id for player in self.session.get_offline_players()]
        if not self.session.is_concluded() and offline_users:
            action_row.add_item(discord_components.NotifyMissingUsersButton(missing_users=offline_users))

        self.add_item(action_row)

        self.add_item(discord.ui.Separator(visible=True))
        self.add_item(discord.ui.TextDisplay(content=f"-# Session ID: `{self.session.id}`"))

    def get_accent_color_from_status(self) -> discord.Color:
        if self.session.status == Status.DRAFT:
            return discord.Color.blue()
        elif self.session.status == Status.COMPLETED:
            return discord.Color.green()
        elif self.session.status == Status.DISCARDED:
            return discord.Color.red()
        else:
            return discord.Color.yellow()

class EditSessionTypeModal(discord.ui.Modal, title="Cambiar Tipo de Sesión"):
    def __init__(self, session: Session, callback: Callable[[str, str], None]):
        super().__init__()
        self.session = session
        self.callback = callback
        self._build()

    def _build(self):
        self.selector = discord_components.SessionTypeSelectorLabel(self.session.type)
        self.add_item(self.selector)

    async def on_submit(self, interaction: discord.Interaction):
        new_type = self.selector.component.values[0]
        self.callback(self.session.id, new_type)
        await interaction.response.send_message(f"El tipo de sesión ha sido cambiado a `{new_type}`.", ephemeral=True)

class EditAttendanceModal(discord.ui.Modal, title="Editar Asistencias"):
    def __init__(self, session: Session, callback: Callable[[str, dict[str,bool], dict[str,str]], None]):
        super().__init__()
        self.session = session
        self.callback = callback
        self._build()

    def _build(self):
        absent_players = self.session.get_absent_players()
        absent_players_ids = [player.player_id for player in absent_players]
        self.add_item(discord_components.UserSelectorLabel("Usuarios Ausentes", "no editable, solo para tener una referencia", absent_players_ids))
        players_with_justified_absence = [player.player_id for player in absent_players if player.justified_absence]
        self.justify_user_selector = discord_components.UserSelectorLabel("Justificar para:", "a que usuario de los anteriores se le va a justificar la ausencia",
                                                 players_with_justified_absence)
        self.add_item(self.justify_user_selector)
        self.user_motive_dict = {}
        for i in range(min(len(absent_players),3)):
            absent_player = absent_players[i]
            player_name = settings.general.players[absent_player.player_id].name
            self.user_motive_dict[absent_player.player_id] = discord_components.MotiveTextInput(player_name, absent_player.player_id, absent_player.motive)
            self.add_item(self.user_motive_dict[absent_player.player_id])

    async def on_submit(self, interaction: discord.Interaction):
        justification_dict = {}
        motives_dict = {}
        justified_ids = [member for member in self.justify_user_selector.component.values]
        for player in self.session.players:
            justification_dict[player.player_id] = player.player_id in justified_ids
            motives_dict[player.player_id] = self.user_motive_dict[player.player_id].value if player.player_id in self.user_motive_dict else ""
        self.callback(self.session.id, justification_dict, motives_dict)
        await interaction.response.send_message("Asistencias actualizadas.", ephemeral=True)