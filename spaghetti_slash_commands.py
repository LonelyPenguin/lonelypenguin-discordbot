import discord
from discord.ext import commands
import aiohttp

class SpaghettiSlashCommands(commands.Cog):
    """Slash commands before they're fully implemented by discord.py. Playing around, proof-of-concept."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handles this bot's one and only slash command."""

        if interaction.type != discord.InteractionType.application_command:
            return
        if interaction.data['id'] != '873001414094377050':
            return
        command_content = interaction.data['options'][0]['value']
        async with aiohttp.ClientSession() as session:
            url = f'https://discord.com/api/v9/interactions/{interaction.id}/{interaction.token}/callback'
            json = {
                'type': 4,
                'data': {
                    'content': f'Hello {interaction.user.mention}! You said:\n```{command_content}```',
                    'flags': 64
                }
            }
            await session.post(url, json=json)

def setup(bot: commands.Bot):
    bot.add_cog(SpaghettiSlashCommands(bot))