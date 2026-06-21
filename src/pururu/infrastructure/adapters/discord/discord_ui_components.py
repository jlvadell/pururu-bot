from datetime import datetime

import discord

from pururu.config import settings
from pururu.domain.entities.session import Session, Status, Type


class SessionStatusTitleTextDisplay(discord.ui.TextDisplay):
    def __init__(self, status: Status):
        status_mapping = {
            status.DRAFT: "## Nueva sesión iniciada! :new:",
            status.COMPLETED: "## Sesión concluida! :checkered_flag:",
            status.DISCARDED: "## Sesión descartada! :x:"
        }
        content = status_mapping.get(status, "## Sesión con estado desconocido :interrobang:")
        super().__init__(content=content)


class SessionDetailsTextDisplay(discord.ui.TextDisplay):
    def __init__(self, session: Session):
        content = self.build_concluded_content(
            session=session) if session.is_concluded() else self.build_ongoing_content(session=session)
        super().__init__(content=content)

    def build_concluded_content(self, session: Session) -> str:
        official_start_time = session.get_official_start_time(settings.general.min_attendance_members)
        official_end_time = session.get_official_end_time(settings.general.min_attendance_members)
        duration = official_end_time - official_start_time
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        return (f":video_game: **Type:** `{session.type.value}`\n\n"
                f":busts_in_silhouette: **Players:** {len(session.get_checked_in_players())} / 5\n\n"
                f":clock3: **Started:** <t:{int(official_start_time.timestamp())}:f>\n\n"
                f":stopwatch: **Ended:** <t:{int(official_end_time.timestamp())}:f>\n\n"
                f":hourglass: **Duration:** {duration_str}\n\n")

    def build_ongoing_content(self, session: Session) -> str:
        return (f":video_game: **Type:** `{session.type.value}`\n\n"
                f":busts_in_silhouette: **Players:** {len(session.get_checked_in_players())} / 5\n\n"
                f":clock3: **Started:** <t:{int(session.start_time.timestamp())}:f>\n\n"
                f":athletic_shoe: **Pole:** <@{session.get_first_joiner().player_id}>\n\n")


class EditAttendanceButton(discord.ui.Button):
    def __init__(self, modal: discord.ui.Modal):
        super().__init__(label="Gestión asistencias", style=discord.ButtonStyle.secondary,
                         custom_id="edit_attendance_btn", emoji="✏️")
        self.modal = modal

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(self.modal)


class ChangeSessionTypeButton(discord.ui.Button):
    def __init__(self, modal: discord.ui.Modal):
        super().__init__(label="Cambiar Tipo", style=discord.ButtonStyle.secondary, custom_id="change_session_type_btn",
                         emoji="🔄")
        self.modal = modal

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(self.modal)


class NotifyMissingUsersButton(discord.ui.Button):
    def __init__(self, missing_users: list[str], cooldown_secs: int = 30):
        super().__init__(label="Notificar ausentes", style=discord.ButtonStyle.secondary,
                         custom_id="notify_missing_users_btn", emoji="🔔")
        self.missing_users = missing_users
        self.last_usage = None
        self.cooldown_secs = cooldown_secs

    async def callback(self, interaction: discord.Interaction):
        if not self.missing_users:
            await interaction.response.send_message("Ya se han conectado todos :dumb:.", ephemeral=True)
            return
        if self.last_usage is not None:
            diff = (datetime.now() - self.last_usage).total_seconds()
            if diff < self.cooldown_secs:
                await interaction.response.send_message(
                    f":dumb: Chill bro, los acabo de llamar; Cooldown: {int(self.cooldown_secs - diff)}",
                    ephemeral=True)
                return
        self.last_usage = datetime.now()

        user_mentions = '\n'.join(f'- <@{user}>' for user in self.missing_users)
        text = f"{user_mentions}\nFaltais vosotros, se estan cocinando unas faltitas :eyes:."
        await interaction.response.send_message(text)


class SessionTypeSelectorLabel(discord.ui.Label):
    def __init__(self, current_type: Type):
        super().__init__(text="Tipo de sesión", description="Qué tipo de sesión es?",
                         component=SessionTypeSelector(current_type))


class SessionTypeSelector(discord.ui.Select):
    def __init__(self, current_type: Type):
        options = [
            discord.SelectOption(label=sess_type.value, value=sess_type.value, emoji=self.get_emoji_for_type(sess_type),
                                 default=sess_type == current_type) for sess_type in Type]
        super().__init__(min_values=1, max_values=1, options=options, required=True)

    def get_emoji_for_type(self, session_type: Type) -> str:
        emoji_mapping = {
            Type.OFFICIAL_GAME: "📅",
            Type.ADDITIONAL_GAME: "🎮",
            Type.OFFICIAL_MEETING: "🍻"
        }
        return emoji_mapping.get(session_type, "❓")


class UserSelectorLabel(discord.ui.Label):
    def __init__(self, text: str, description: str, user_ids: list[str]):
        ids = [discord.Object(id=int(user_id)) for user_id in user_ids]
        super().__init__(text=text, description=description,
                         component=discord.ui.UserSelect(default_values=ids, min_values=0, max_values=25))


class MotiveTextInput(discord.ui.TextInput):
    def __init__(self, user_name: str, user_id: str, motive: str):
        super().__init__(label=f"{user_name}: Motivo justificación", default=motive, style=discord.TextStyle.paragraph,
                         placeholder="Escribe el motivo aquí...", required=False, max_length=200,
                         custom_id=f"Motive-{user_id}")
