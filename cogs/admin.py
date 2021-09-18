import discord
from discord.ext import commands
import aiosqlite
from sys import stderr
from traceback import print_exception


class Admin(commands.Cog):
    """Commands to manage the administration of the bot itself, which aren't as sensitive as the development commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_check(self, ctx: commands.Context):
        return ctx.author.id in self.bot.moderator_ids or ctx.author.id == 305704400041803776

    def simple_embed(self, desc: str):
        """Shortcut for creating an embed with only a description."""

        my_embed = discord.Embed(description=desc)
        return my_embed

    @commands.command(name='manualmodmailadd', aliases=['manualmodmail', 'syncmodmail', 'registermodmail'])
    async def manual_modmail_add(self, ctx: commands.Context, modmail_user: discord.User, modmail_channel: discord.TextChannel, *, modmail_reason: str = 'no reason specified'):
        """Re-registers a modmail that already exists on the server, but which the bot has forgotten about for whatever reason."""

        c = await self.bot.conn.cursor()
        await c.execute('SELECT * FROM activemodmails WHERE userid=?', (modmail_user.id,))
        my_row = await c.fetchone()
        if my_row is not None:
            await ctx.send(embed=self.simple_embed(f'Error: There is already a known modmail attached to that user: <#{my_row[1]}>.'))
            return

        await c.execute('INSERT INTO activemodmails VALUES (?,?,?)', (modmail_user.id, modmail_channel.id, modmail_reason))
        await self.bot.conn.commit()

        await ctx.send(embed=self.simple_embed(f'Successfully re-registered a modmail: {modmail_user.mention} in the channel {modmail_channel.mention}.'))

    @manual_modmail_add.error
    async def manual_modmail_add_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=self.simple_embed(f'Error: Missing a required argument. Proper syntax: `;manualmodmailadd <user> <channel> [reason]`. ({error})'))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=self.simple_embed(f'Error: member not found. ({error})'))
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(embed=self.simple_embed(f'Error: channel not found. ({error})'))
        else:
            # All other errors not returned come here. And we can just print the default Traceback.
            await ctx.send(embed=self.simple_embed(f'Something went wrong: {error}'))
        print('Ignoring exception in command {}:'.format(
            ctx.command), file=stderr)
        print_exception(
            type(error), error, error.__traceback__, file=stderr)


def setup(bot: commands.Bot):
    bot.add_cog(Admin(bot))
