import discord

# Define a simple View that gives us a confirmation menu
class Confirm(discord.ui.View):
    def __init__(self, confirm_user=None):
        super().__init__(timeout=30.0)
        self.value = None
        self.confirm_user = confirm_user

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = True
        button.disabled = True
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = False
        button.disabled = True
        self.stop()

    async def interaction_check(self, interaction):
        # If confirm_user is not None, only the specified user may confirm the action.
        if self.confirm_user:
            if interaction.user.id != self.confirm_user.id:
                await interaction.response.send_message(f'Only {self.confirm_user.mention} may confirm this action.', ephemeral=True)
                return False
        return True