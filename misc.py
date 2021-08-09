import discord
from discord.ext import commands


class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send(f'Pong! Bot latency: {round(self.bot.latency * 1000, 2)} milliseconds.')


def setup(bot: commands.Bot):
    bot.add_cog(Misc(bot))
