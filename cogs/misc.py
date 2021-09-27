import discord
from discord.ext import commands


class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_check(self, ctx: commands.Context):

       #Ignore blacklisted users unless they are mods or LonelyPenguin
        return ctx.author.id not in [each_row[1] for each_row in self.bot.blacklisted_users] or ctx.author.id == 305704400041803776 or ctx.author.id in self.bot.moderator_ids

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send(f'Pong! Bot latency: {round(self.bot.latency * 1000, 2)} milliseconds.')


def setup(bot: commands.Bot):
    bot.add_cog(Misc(bot))
