import discord
from discord.ext import commands
import database as db
import variables as var
from functions import get_prefix


def has_command_permission():
    async def predicate(ctx: commands.Context):
        plugin_name = ctx.cog.__cog_name__
        cmd_name = ctx.command.name
        GuildDoc = await db.PERMISSIONS.find_one({"_id": ctx.guild.id})
        try:
            permitted_roles = [i for i in GuildDoc[plugin_name][cmd_name]]
            author_roles = [i.id for i in ctx.author.roles]
            if permitted_roles == []:
                return True
            else:
                permission = any(item in permitted_roles for item in author_roles)
                if permission:
                    return True
        except KeyError:
            return True

    return commands.check(predicate)


class Permissions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def allperms(self, ctx):
        embed = discord.Embed(title=f"Command role permissions", color=var.C_MAIN)
        GuildDoc = await db.PERMISSIONS.find_one({"_id":ctx.guild.id}, {"_id":0})
        for i in GuildDoc:
            perms = GuildDoc[i]
            cmds = [x for x in perms]
            roles = [x for x in perms.values()]
            value = ""
            for c in cmds:
                roleids = roles[cmds.index(c)]
                mentioned = [f"<@&{x}>" for x in roleids]
                stringed = ", ".join(mentioned)
                value += f"{c}: {stringed}\n"
            if GuildDoc[i] == {}:
                value = None
            embed.add_field(name=i, value=value, inline=False)
        await ctx.send(embed=embed)


    @commands.command(aliases=["setpermission", "addperm", "addpermission"])
    @commands.has_permissions(administrator=True)
    async def setperm(self, ctx, plugin=None):
        cogs = ['Leveling', 'Moderation', 'ReactionRoles', 'Welcome' , 'Verification', 'Chatbot', 'AutoMod', "Karma", "Fun", "Giveaway"]

        if plugin is not None and plugin.lower() in [i.lower() for i in cogs]:
            embed = discord.Embed(
                title=f"All commands for {plugin}",
                color=var.C_GREEN
            ).add_field(name="Note", value="Make sure to not enter the command name with the prefix, that would trigger the command. Just enter the command name followed by a space and then role (ID or Mention can be used)")

            if plugin.lower() == "reactionroles":
                plugin_name = "ReactionRoles"

            elif plugin.lower() == "automod":
                plugin_name = "AutoMod"
                
            else:
                plugin_name = plugin.capitalize()

            desc = "Type the name of the command (without prefix) and the role with a space to let members with that role be able to use the command\n Type `cancel` to stop the process\n\n"
            for i in self.bot.cogs[plugin_name].walk_commands():
                desc += f"`{i}`\n"
            embed.description = desc
            await ctx.send(embed=embed)

            def messagecheck(message):
                return message.author == ctx.author and message.channel.id == ctx.channel.id

            while True:
                usermsg = await self.bot.wait_for("message", check=messagecheck)
                if usermsg.content in ["cancel", "`cancel`", "```cancel```"]:
                    await ctx.send(f"Cancelled permissions change for {plugin} plugin")
                    break
                else:
                    GuildDoc = await db.PERMISSIONS.find_one({"_id": ctx.guild.id})
                    data = usermsg.content.split(" ")
                    if len(data) != 2:
                        await ctx.send(embed=discord.Embed(
                            title="Invalid format",
                            description="You don't need to start over again, just send the message in correct format as shown below",
                            color=var.C_ORANGE
                        ).add_field(name="Format", value="`command_name role`"
                        ).set_footer(text="Don't enter the command name with prefix, that would trigger the command, just write the command name")
                        )
                    elif data[0].lower() not in [str(i).lower() for i in self.bot.cogs[plugin_name].walk_commands()]:
                        await ctx.send(embed=discord.Embed(
                            title="Command not found",
                            description=f"There is no command named `{data[0].lower()}`` in **{plugin_name}**. Try again with correct command in {plugin_name} plugin",
                            color=var.C_ORANGE
                        ))
                    elif data[1].strip("<>@&").isnumeric() == False or ctx.guild.get_role(int(data[1].strip("<>@&"))) == None:
                        await ctx.send(embed=discord.Embed(
                            title="Role not found",
                            description=f"There is no role with the ID `{data[1]}`. Try again with correct role mention or ID",
                            color=var.C_ORANGE
                        ))
                    elif data[0].lower() in GuildDoc[plugin_name].keys() and int(data[1].strip("<>@&")) in GuildDoc[plugin_name][data[0].lower()]:
                        await ctx.send(embed=discord.Embed(description=f"{ctx.guild.get_role(int(data[1].strip('<>@&'))).mention} role already has permissions for **{data[0].lower()}**", color=var.C_RED))
                    else:
                        GuildDoc = await db.PERMISSIONS.find_one({"_id": ctx.guild.id})
                        role = ctx.guild.get_role(int(data[1].strip("<>@&")))
                        plugin_dict = GuildDoc[plugin_name]
                        newdict = plugin_dict.copy()
                        try:
                            currentlist = plugin_dict[data[0].lower()]
                        except KeyError:
                            currentlist = []
                        newlist = currentlist.copy()
                        newlist.append(role.id)
                        newdict.update({data[0].lower(): newlist})

                        newdata = {"$set":{
                            plugin_name: newdict
                        }}
                        await db.PERMISSIONS.update_one(GuildDoc, newdata)
                        await ctx.send(embed=discord.Embed(
                                    title="Successfully updated permissions",
                                    description=f"{var.E_ACCEPT} Users with {role.mention} can now use the command {data[0].lower()}",
                                    color=var.C_GREEN
                        ).add_field(name="To view all permissions", value=f"```{await get_prefix(ctx)}allperms```")
                        )
                        break
        else:
            await ctx.send(embed=discord.Embed(
            description="🚫 You need to define a valid plugin!",
            color=var.C_RED
            ).add_field(name="Format", value=f"`{await get_prefix(ctx)}setperm <plugin>`"
            ).set_footer(text=f"You can view all plugins by using the command {await get_prefix(ctx)}plugins")
            )

    @commands.command(aliases=["removepermission", "disablepermission"])
    @commands.has_permissions(administrator=True)
    async def removeperm(self, ctx, cmd=None, role:discord.Role=None):
        if cmd and role is not None:
            GuildDoc = await db.PERMISSIONS.find_one({"_id": ctx.guild.id}, {"_id":0})
            all_perm_commmands = [x for i in GuildDoc.values() for x in i]

            if cmd not in all_perm_commmands:
                await ctx.send(embed=discord.Embed(
                            title="Invalid command",
                            description="This command has no permissions setted up",
                            color=var.C_RED
                ))
            else:
                plugin_name = [x for x in GuildDoc if cmd in GuildDoc[x].keys()][0]
                plugin_dict = GuildDoc[plugin_name]
                newdict = plugin_dict.copy()
                rolelist = plugin_dict[cmd]
                newlist = rolelist.copy()

                try:
                    newlist.remove(role.id)
                    newdict.update({cmd:newlist})

                    newdata = {"$set":{
                        plugin_name: newdict
                    }}
                    await db.PERMISSIONS.update_one(GuildDoc, newdata)

                    await ctx.send(embed=discord.Embed(
                        title="Successfully removed permission",
                        description=f"{var.E_ACCEPT} Members with {role.mention} role can't use **{cmd}** command anymore",
                        color=var.C_GREEN
                    ).add_field(name="To add new command permission", value=f"```{await get_prefix(ctx)}addperm <plugin>```")
                    )
                except ValueError:
                    await ctx.send(embed=discord.Embed(
                        title="Invalid combination",
                        description=f"The command {cmd} has no permissions setted up with role {ctx.guild.get_role(role.id).mention}",
                        color=var.C_RED
                    ))

        else:
            await ctx.send(embed=discord.Embed(
            description="🚫 You need to define the command name and the role",
            color=var.C_RED
            ).add_field(name="Format", value=f"`{await get_prefix(ctx)}removeperm <command> <role>`"
            ).set_footer(text=f"You can view all plugins by using the permissions setted up using {await get_prefix(ctx)}allperms")
            )


def setup(bot):
    bot.add_cog(Permissions(bot))
