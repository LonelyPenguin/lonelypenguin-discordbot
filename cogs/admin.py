import json
from sys import stderr
from traceback import print_exception

import discord
from discord.ext import commands


class Admin(commands.Cog):
    """Commands to manage the administration of the bot itself, which aren't as sensitive as the development commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_check(self, ctx: commands.Context):

       # Ignore blacklisted users unless they are mods or LonelyPenguin
        return ctx.author.id not in self.bot.blacklisted_users or ctx.author.id in self.bot.moderator_ids or ctx.author.id == 305704400041803776

    def mod_only():
        """Commands with this check will only execute for moderators."""

        def predicate(ctx: commands.Context):
            return ctx.author.id in ctx.bot.moderator_ids
        return commands.check(predicate)

# region admin commands and errors
    @commands.group(name='admin')
    @mod_only()
    @commands.guild_only()
    async def admin(self, ctx: commands.Context):
        await ctx.send(embed=self.bot.simple_embed('Run `;help admin` for details.'))

    @admin.command(name='manualmodmailadd', aliases=['manualmodmail', 'syncmodmail', 'registermodmail'])
    async def manual_modmail_add(self, ctx: commands.Context, modmail_user: discord.Member, modmail_channel: discord.TextChannel, *, modmail_reason: str = 'no reason specified'):
        """Re-registers a modmail that already exists on the server, but which the bot has forgotten about for whatever reason."""

        c = await self.bot.conn.cursor()
        await c.execute('SELECT * FROM activemodmails WHERE userid=?', (modmail_user.id,))
        my_row = await c.fetchone()
        if my_row is not None:
            await ctx.send(embed=self.bot.simple_embed(f'Error: There is already a known modmail attached to that user: <#{my_row[1]}>.'))
            return

        await c.execute('INSERT INTO activemodmails VALUES (?,?,?)', (modmail_user.id, modmail_channel.id, modmail_reason))
        await self.bot.conn.commit()

        await ctx.send(embed=self.bot.simple_embed(f'Successfully re-registered a modmail: {modmail_user.mention} in the channel {modmail_channel.mention}.'))

    @admin.command(name='addmoderator', aliases=['addmod', 'moderatoradd', 'newmod', 'modadd', 'modnew', 'addmoderators'])
    async def add_moderators(self, ctx: commands.Context, *, new_moderators: str):
        """Add users to the bot's list of moderators."""

        new_moderators = new_moderators.split()

        with open('config/server_vars.json', 'r') as server_vars_file:
            data = json.load(server_vars_file)

        for mod in new_moderators:
            mod = int(mod)
            if mod not in data['moderator_ids']:
                data['moderator_ids'].append(mod)

        with open('config/server_vars.json', 'w') as server_vars_file:
            json.dump(data, server_vars_file)

        self.bot.moderator_ids = data['moderator_ids'].copy()

        await ctx.send(embed=self.bot.simple_embed('That/those user(s) are now on the list of moderators.'))

    @admin.command(name='removemoderator', aliases=['removemod', 'moderatorremove', 'delmod', 'rmmod', 'modrm', 'moddel', 'removemoderators'])
    async def remove_moderators(self, ctx: commands.Context, *, del_moderators: str):
        """Remove users from the bot's list of moderators."""

        del_moderators = del_moderators.split()

        with open('config/server_vars.json', 'r') as server_vars_file:
            data = json.load(server_vars_file)

        for mod in del_moderators:
            mod = int(mod)
            if mod in data['moderator_ids']:
                data['moderator_ids'].remove(mod)

        with open('config/server_vars.json', 'w') as server_vars_file:
            json.dump(data, server_vars_file)

        self.bot.moderator_ids = data['moderator_ids'].copy()

        await ctx.send(embed=self.bot.simple_embed('That/those user(s) are no longer on the list of moderators.'))

    @admin.command()
    async def moderators(self, ctx: commands.Context):
        """Shows a list of the current moderators in the bot."""

        with open('config/server_vars.json') as server_vars_file:
            data = json.load(server_vars_file)

        await ctx.send(embed=self.bot.simple_embed(f'IDs of moderators registered in the bot: {data["moderator_ids"]}'))

    @admin.error
    async def admin_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(embed=self.bot.simple_embed('Error: command cannot be used in DMs.'))
        elif isinstance(error, commands.CheckFailure):
            if ctx.author.id in self.bot.blacklisted_users:
                return
            await ctx.send(embed=self.bot.simple_embed("You may not use this command."))

    @manual_modmail_add.error
    async def manual_modmail_add_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=self.bot.simple_embed(f'Error: Missing a required argument. Proper syntax: `;manualmodmailadd <user> <channel> [reason]`. ({error})'))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=self.bot.simple_embed(f'Error: member not found. ({error})'))
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(embed=self.bot.simple_embed(f'Error: channel not found. ({error})'))
        else:
            # All other errors not returned come here. And we can just print the default Traceback.
            await ctx.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in command {}:'.format(
                ctx.command), file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)

    @add_moderators.error
    async def add_moderators_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=self.bot.simple_embed(f'Error: Missing a required argument. Proper syntax: `;addmoderators <moderator_id(s)>` (separate IDs with spaces). ({error})'))
        else:
            # All other errors not returned come here. And we can just print the default Traceback.
            await ctx.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in command {}:'.format(
                ctx.command), file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)

    @remove_moderators.error
    async def remove_moderators_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=self.bot.simple_embed(f'Error: Missing a required argument. Proper syntax: `;removemoderators <moderator_id(s)>` (separate IDs with spaces). ({error})'))
        else:
            # All other errors not returned come here. And we can just print the default Traceback.
            await ctx.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
            print('Ignoring exception in command {}:'.format(
                ctx.command), file=stderr)
            print_exception(
                type(error), error, error.__traceback__, file=stderr)

    @moderators.error
    async def moderators_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        # All other errors not returned come here. And we can just print the default Traceback.
        await ctx.send(embed=self.bot.simple_embed(f'Something went wrong: {error}'))
        print('Ignoring exception in command {}:'.format(
            ctx.command), file=stderr)
        print_exception(type(error), error, error.__traceback__, file=stderr)
# endregion


def setup(bot: commands.Bot):
    bot.add_cog(Admin(bot))
