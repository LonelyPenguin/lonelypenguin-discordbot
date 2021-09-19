import discord
from discord.ext import commands
import aiosqlite
from traceback import print_exception
from io import StringIO
from sys import stderr


class Blacklist(commands.Cog):
    """Commands to manage the blacklist."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.embed_details = {'author name': 'Servername Modmail',
                              'author icon': 'https://cdn.discordapp.com/attachments/743536411369799804/854865953083228181/mail_icon.png',
                              'footer': 'Use ;modmail close to close this modmail, and ;modmail reason to change its reason.'}

    def cog_check(self, ctx: commands.Context):

        return ctx.author.id not in [each_row[1] for each_row in self.bot.blacklisted_users] or ctx.author.id == 305704400041803776 or ctx.author.id in self.bot.moderator_ids

    def simple_embed(self, desc: str):
        """Shortcut for creating an embed with only a description."""

        my_embed = discord.Embed(description=desc)
        return my_embed

# region blacklist commands and errors
    @commands.group()
    async def blacklist(self, ctx: commands.Context):
        "Commands to prevent certain users from using the modmail bot (e.g. if they're spamming)."
        if not ctx.invoked_subcommand:
            await ctx.send(embed=self.simple_embed('Run `;help blacklist` for details, or `;blacklist show` to view the current blacklist.'))

    @blacklist.command(name='add')
    async def blacklist_add(self, ctx: commands.Context, user_to_blacklist: discord.Member):
        """Adds a user to the blacklist (prevents them from using the bot).

        Remove someone from the blacklist with ;blacklist remove.
        Only moderators can use this command.
        Users will be notified that they are blacklisted."""

        c = await self.bot.conn.cursor()
        await c.execute('SELECT * FROM blacklist WHERE userid=?', (user_to_blacklist.id,))

        if await c.fetchone() is not None:
            await ctx.send(embed=self.simple_embed('User is already blacklisted.'))
            return

        await c.execute('INSERT INTO blacklist VALUES (?,?,?)', (str(ctx.message.created_at)[:19], user_to_blacklist.id, user_to_blacklist.name))
        await self.bot.conn.commit()

        c = await self.bot.conn.execute('SELECT * FROM blacklist')
        self.bot.blacklisted_users = await c.fetchall()

        mod_confirmed_blacklist_embed = discord.Embed(description=f'Blacklisted {user_to_blacklist.mention} from interacting with the modmail system.').set_author(
            name=self.embed_details['author name'], icon_url=self.embed_details['author icon'])
        user_inform_blacklist_embed = discord.Embed(description='You have been blacklisted from the modmail system– this bot will no longer respond to any of your messages. If you believe this was in error, please DM a moderator directly.').set_author(
            name=self.embed_details['author name'], icon_url=self.embed_details['author icon'])

        await ctx.send(embed=mod_confirmed_blacklist_embed)
        await user_to_blacklist.send(embed=user_inform_blacklist_embed)

    @blacklist_add.error
    async def blacklist_add_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, discord.Forbidden):
            await ctx.send(embed=self.simple_embed(f"Note: Blacklisted user, but couldn't notify them– they have probably blocked the bot. ({error})"))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=self.simple_embed(f'Error: member not found. ({error})'))
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(embed=self.simple_embed('You may not use this command.'))
        else:
            # All other errors not returned come here. And we can just print the default Traceback.
            await ctx.send(embed=self.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in command {}:'.format(
                ctx.command), file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)

    @blacklist.command(name='show', aliases=['view'])
    async def blacklist_show(self, ctx: commands.Context):
        """Shows the current state of the blacklist (who's on it and when they were blacklisted).

        Blacklist someone with ;blacklist add and unblacklist them with ;blacklist remove.
        Only moderators can use this command."""
        c = await self.bot.conn.execute('SELECT * FROM blacklist')
        full_blacklist_table = await c.fetchall()
        await self.bot.conn.commit()

        blacklist_entries = StringIO()
        blacklist_entries.write('timestamp (UTC), userid, username\n\n')
        for myrow in full_blacklist_table:
            blacklist_entries.write(f'{myrow}\n')

        blacklist_entries.seek(0)
        blacklist_filename = f'{str(ctx.message.created_at)[:19]}-currently-blacklisted-users.txt'

        dpy_compatible_showtable_file = discord.File(fp=blacklist_entries, filename=blacklist_filename)
        blacklist_entries.close()

        await ctx.send(content=f'Users who are currently blacklisted (username accurate at time of initial blacklist):', file=dpy_compatible_showtable_file)

    @blacklist_show.error
    async def blacklist_show_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.CheckFailure):
            await ctx.send(embed=self.simple_embed('You may not use this command.'))
        else:
            await ctx.send(embed=self.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in command {}:'.format(
                ctx.command), file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)

    @blacklist.command(name='remove')
    async def blacklist_remove(self, ctx: commands.Context, user_to_unblacklist: discord.Member):
        """Unblacklists a user, allowing them to make use of the bot again.

        Only moderators can use this command.
        Users will be notified that they are unblacklisted.
        Add someone to the blacklist with ;blacklist add."""
        c = await self.bot.conn.cursor()
        await c.execute('SELECT * FROM blacklist WHERE userid=?', (user_to_unblacklist.id,))

        if await c.fetchone() is None:
            await ctx.send(embed=self.simple_embed('User is not blacklisted.'))
            return

        await c.execute('DELETE FROM blacklist WHERE userid=?', (user_to_unblacklist.id,))
        await self.bot.conn.commit()

        c = await self.bot.conn.execute('SELECT * FROM blacklist')
        self.bot.blacklisted_users = await c.fetchall()

        mod_confirmed_unblacklist_embed = discord.Embed(description=f'Removed {user_to_unblacklist.mention} from the blacklist. They can once again interact with the modmail system.').set_author(
            name=self.embed_details['author name'], icon_url=self. embed_details['author icon'])
        user_inform_unblacklist_embed = discord.Embed(description='You have been removed from the modmail blacklist– you can once again use the modmail system.').set_author(
            name=self.embed_details['author name'], icon_url=self.embed_details['author icon'])

        await ctx.send(embed=mod_confirmed_unblacklist_embed)
        await user_to_unblacklist.send(embed=user_inform_unblacklist_embed)

    @blacklist_remove.error
    async def blacklist_remove_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, discord.Forbidden):
            await ctx.send(embed=self.simple_embed(f"Note: Unblacklisted user, but but couldn't notify them– they have probably blocked the bot. ({error})"))
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(embed=self.simple_embed('You may not use this command.'))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=self.simple_embed(f'Error: member not found. ({error})'))
        else:
            # All other errors not returned come here. And we can just print the default Traceback.
            await ctx.send(embed=self.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in command {}:'.format(
                ctx.command), file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)
    # endregion


def setup(bot: commands.Bot):
    bot.add_cog(Blacklist(bot))
