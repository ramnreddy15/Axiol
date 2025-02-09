import time
import random
import discord
import datetime
from typing import Union
from discord.ext import commands, tasks
import database as db
import variables as var
from functions import get_prefix
from ext.permissions import has_command_permission



class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot  = bot
        self.check_gw.start()
    
   #Simple check to see if this cog (plugin) is enabled
    async def cog_check(self, ctx):
        GuildDoc = await db.PLUGINS.find_one({"_id": ctx.guild.id})
        if GuildDoc.get("Giveaway"):
            return True
        else:
            await ctx.send(embed=discord.Embed(
                description=f"{var.E_DISABLE} The Giveaway plugin is disabled in this server",
                color=var.C_ORANGE
            ))


    async def end_gw(self, i):
        channel = self.bot.get_channel(i["channel_id"])
        message = await channel.fetch_message(i["message_id"])
        winner_amount = i["winner_amount"]
        embed_data = message.embeds[0].to_dict()
        hosted_by = embed_data["description"].split("\n")[-1]

        users = await message.reactions[0].users().flatten()
        users.remove(self.bot.user)
        if len(users) < winner_amount:
            winners = random.sample(users, len(users))
        else:
            winners = random.sample(users, winner_amount)

        await db.GIVEAWAY.delete_one(i)
        embed = discord.Embed(
            title="Giveaway over",
            description= f"🎁 {embed_data['title']}\n{hosted_by}\n📩 **{len(users)}** entries\n📋 **{len(winners)}** winners",
            timestamp = datetime.datetime.now(),
            color=var.C_BLUE
        ).set_footer(text="Ended")
        await message.edit(embed=embed)
        if len(users) > 0:
            annoucement = await channel.send(f"Congratulations, you have won **{embed_data['title']}**!" + ", ".join([w.mention for w in winners]))
        else:
            annoucement = await channel.send("Aw man, no one participated :(")
        return annoucement.id


    @commands.command()
    @has_command_permission()
    async def gstart(self, ctx, channel:discord.TextChannel=None):
        if channel is None:
            return await ctx.send(embed=discord.Embed(
                description="🚫 You need to define the channel too!",
                color=var.C_ORANGE
                ).add_field(name="Format", value=f"```{await get_prefix(ctx)}gstart <#channel>```", inline=False
                ).add_field(name="Don't worry, this won't send the giveaway right away!", value="** **")
                )

        data = {"Channel": channel.mention}
        questions = {
            "Prize": "🎁 Enter the giveaway prize, what are winners going to get?", 
            "Duration": "⏳ Enter the giveaway time duration, how long should the giveaway last?", 
            "Winners": "📝 Enter the winner amount, how many winners should there be?",
            "Host": "🔍 Enter the giveaway host, who is hosting the giveaway? It can be you, someone else, a discord server or any other kind person :D"
            }
        
        def messagecheck(message):
            return message.author == ctx.author and message.channel.id == ctx.channel.id

        def reactioncheck(reaction, user):
            if str(reaction.emoji) == var.E_ACCEPT:
                return user == ctx.author and reaction.message == botmsg

        def time_converter(string, type_):
            if type_ == "Duration":
                formats = ("s", "m", "h", "d")
                conversions = {"s":1, "m":60, "h":3600, "d":86400}

                if string[-1] in formats and len([l for l in string if l.isdigit()]) != 0:
                    return True, int(string[:-1]) * conversions[string[-1]]
                else:
                    return False, None

            elif type_ == "Winners":
                return string.isdigit(), None
            else:
                return True, None

        embed = discord.Embed(
            color=var.C_BLUE
            ).set_footer(text="To stop the proccess, enter cancel"
            ).set_thumbnail(url="https://cdn.discordapp.com/attachments/843519647055609856/845662999686414336/Logo1.png")

        for q in questions:
            embed.title = q
            embed.description = questions[q]
            embed.clear_fields()
            embed.add_field(name="Information", value="\n".join([f"{x}: **{y[0] if type(y) == tuple else y}**" for x,y in data.items()]))
            await ctx.send(embed=embed)
            usermsg = await self.bot.wait_for("message", check=messagecheck, timeout=60)
            check, value = time_converter(usermsg.content, q)
            if usermsg.content == "cancel":
                await ctx.send("Cancelled giveaway proccess.")
                return

            if check:
                data.update({q: usermsg.content}) if value == None else data.update({q: (usermsg.content, value)})
            else:
                tries = 3
                status = True
                while status:
                    tries -= 1
                    if tries == 0:
                        await ctx.send(f"The giveaway proccess has been cancelled because you failed to enter {q.lower()} field in correct format.")
                        return
                    else:
                        if q == "Duration":
                            await ctx.send(embed=discord.Embed(description="Invalid format for time duration, try again.\nExample:\n> 24h", color= var.C_ORANGE
                                    ).add_field(name="All formats", value="s: seconds\nm: minutes\nh: hours\nd: days\n", inline=False
                                    ).add_field(name="Tries left", value=tries
                                    ))
                        else:
                            await ctx.send(embed=discord.Embed(description="Winner amount can only be a positive number!", color= var.C_ORANGE
                                    ).add_field(name="Example", value="5", inline=False
                                    ).add_field(name="Tries left", value=tries
                                    ))
                        usermsg = await self.bot.wait_for("message", check=messagecheck, timeout=60)
                        if usermsg.content == "cancel":
                            await ctx.send("Cancelled giveaway proccess.")
                            return
                        check, value = time_converter(usermsg.content, q)
                        if check:
                            status = False
                else:
                    data.update({q: (usermsg.content, value)})

        embed = discord.Embed(
            title="Confirm giveaway",
            description=f"You are about to start the giveaway! Press {var.E_ACCEPT} to start it.",
            color=var.C_GREEN
        ).add_field(name="Channel", value=data["Channel"], inline=False
        ).add_field(name="Prize", value=data["Prize"], inline=False
        ).add_field(name="Duration", value=data["Duration"][0], inline=False
        ).add_field(name="Winner amount", value=data["Winners"][0], inline=False
        ).add_field(name="Hosted by", value=data["Host"], inline=False)

        botmsg = await ctx.send(embed=embed)
        await botmsg.add_reaction(var.E_ACCEPT)
        await self.bot.wait_for("reaction_add", check=reactioncheck, timeout=60)

        end_time = round(time.time() + int(data["Duration"][1]))
        readable = str(datetime.datetime.fromtimestamp(end_time) - datetime.datetime.fromtimestamp(time.time()))
        main_time = readable.split(":")[0] + " Hours" 
        secondary_time = readable.split(":")[1] + " Minutes"
        embed = discord.Embed(
            title=data["Prize"],
            description=f"React to the 🎉 emoji to participate!\n\n📝 Winner amount: **{data['Winners'][0]}**\n🔍 Hosted by: **{data['Host']}**",
            color=var.C_MAIN,
            timestamp= datetime.datetime.now()
        ).add_field(name="⏳ Ending time", value=main_time + " " + secondary_time
        ).set_thumbnail(url=ctx.guild.icon_url
        )
        gwmsg = await channel.send(content="New giveaway woohoo!", embed=embed)
        await gwmsg.add_reaction("🎉")

        guild_gw_cols  = [x async for x in db.GIVEAWAY.find({"_id": {"$regex": "^"+str(ctx.guild.id)}})]
        await db.GIVEAWAY.insert_one({"_id": str(ctx.guild.id + len(guild_gw_cols)), "channel_id":channel.id, "message_id": gwmsg.id, "end_time": end_time, "winner_amount": int(data["Winners"][0])})


    @commands.command()
    @has_command_permission()
    async def gshow(self, ctx):
        embed = discord.Embed(title="All active giveaways", color=var.C_MAIN)
        async for i in db.GIVEAWAY.find({"_id": {"$regex": "^" + str(ctx.guild.id)}}):
            
            readable = str(datetime.datetime.fromtimestamp(i["end_time"]) - datetime.datetime.fromtimestamp(time.time()))
            main_time = readable.split(":")[0] + " Hours" 
            secondary_time = readable.split(":")[1] + " Minutes"
            embed.add_field(name=f"Ends in {main_time} {secondary_time}", value=f"Winners: {i['winner_amount']} [Jump to the message!](https://discord.com/channels/{ctx.guild.id}/{i['channel_id']}/{i['message_id']})", inline=False)
        
        embed.description = f"There are **{len(embed.fields)}** active giveaways right now"
        await ctx.send(embed=embed)
    

    @commands.command()
    @has_command_permission()
    async def gend(self, ctx, msgid:Union[int, None]):
        if msgid is None:
            return await ctx.send(embed=discord.Embed(
            description="🚫 You need to define the message ID in order to end a giveaway!",
            color=var.C_RED
            ).add_field(name="Format", value=f"`{await get_prefix(ctx)}gend <message_id>`"
            )
            )
    
        all_msg_ids = [x["message_id"] async for x in db.GIVEAWAY.find({"_id": {"$regex": "^" + str(ctx.guild.id)}})]
        if not msgid in all_msg_ids:
            return await ctx.send(embed=discord.Embed(
                description = f"🚫 There are no active giveaways in this server with the message ID **{msgid}**",
                color=var.C_RED
                ))
        else:
            i = await db.GIVEAWAY.find_one({"message_id": msgid})
            annoucement_id = await self.end_gw(i)
            await ctx.send(f"The giveaway has been ended https://discord.com/channels/{ctx.guild.id}/{i['channel_id']}/{annoucement_id}")


    @tasks.loop(seconds=5)
    async def check_gw(self):
        await self.bot.wait_until_ready()
        try:
            async for i in db.GIVEAWAY.find({}):
                channel = self.bot.get_channel(i["channel_id"])
                message = await channel.fetch_message(i["message_id"])
                end_time = i["end_time"]
                embed_data = message.embeds[0].to_dict()
                readable = str(datetime.datetime.fromtimestamp(end_time) - datetime.datetime.fromtimestamp(time.time()))
                main_time = readable.split(":")[0] + " Hours" 
                secondary_time = readable.split(":")[1] + " Minutes"

                if time.time() > end_time:
                    await self.end_gw(i)
                else:
                    embed = discord.Embed(
                        title=embed_data["title"],
                        description=embed_data["description"],
                        color=var.C_MAIN,
                        timestamp = datetime.datetime.now()
                        ).add_field(name=embed_data["fields"][0]["name"], value=main_time + " " + secondary_time
                        ).set_thumbnail(url=embed_data["thumbnail"]["url"]
                        )
                    await message.edit(embed=embed)
        except Exception as e:
            print("Exception in giveaway task:", e)

def setup(bot):
    bot.add_cog(Giveaway(bot))
