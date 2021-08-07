import discord
from discord.ext import commands
import aiohttp

class SpaghettiSlashCommands(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.id != 873001414094377050:
            return
        async with aiohttp.ClientSession() as session:
            url = f'https://discord.com/api/v8/interactions/{interaction.id}/{interaction.token}/callback'
            json = {
                'type': 4,
                'data': {
                    'content': f'Hello {interaction.user.mention}!',
                    'flags': 64
                }
            }
            await session.post(url, json=json)
        print('interaction recieved')

def setup(bot: commands.Bot):
    bot.add_cog(SpaghettiSlashCommands(bot))