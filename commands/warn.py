from logging import warn
from commands.mute import mute
from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from datetime import datetime, timedelta
from utils import find, fmt, std_embed
from utils.errors import ReportableError
from main import bot_prefix

import discord
import random
import db


class Warn_Command(Bot_Command):
    name = "warn"

    short_help = "Warn a member in the server."

    long_help = f"""Warns a member in the server or gets the count of warns on a user.
    Command Syntax:
    **{bot_prefix}warn [member] [Optional reason]**
    **{bot_prefix}warn count [member]**
    
    `member`: *@User, User ID, Nickname* (Not Case Sensitive)
    `Optional reason`: *Text* (Can have spaces)

    ~Example: (Assume this is the same user)
    **{bot_prefix}warn TheLegend47** or **{bot_prefix}warn 1234567891012345678** or **{bot_prefix}warn Legend** """

    category = Bot_Command_Category.MODERATION

    def __init__(self):
        db.execute("""CREATE TABLE IF NOT EXISTS warn (
                Server bigint,
                Member bigint,
                Count int,
                DT datetime,
                Moderator text,
                Reason text,
                MsgLog text,
                PRIMARY KEY (Server, Member, Count)
            );"""
        )


    # TODO command name "count"
    async def run(self, msg: discord.Message, args: str):
        if args.casefold().startswith("count ") and args[len("count "):]:
            split_args = args.split(" ", 1)
            print(split_args)
            """ split_args[0] = count
                split_args[1:] = user_id """
            user_name = split_args[1]
            member = await find.member(msg.channel, user_name, msg.author)
            if member is None:
                raise ReportableError(
                    fmt.format_maxlen(
                        "**{}** not found. If you are having trouble typing in a user's name, you can also use their User ID! Example: **$warn count {}** ",
                        user_name,
                        random.randint(100000000000000000, 999999999999999999),
                    )
                )
            #get the member's most recent warn
            operation = "SELECT Count, DT, Moderator FROM warn WHERE Count = (SELECT MAX(Count) FROM warn WHERE Server = %s AND Member = %s);"
            params = (msg.guild.id, member.id)
            result = db.read_execute(operation, params)
            if not result:
                await std_embed.send_info(
                    msg.channel,
                    title="This user has not been warned yet on this server.",
                    author=msg.author,
                )
            else:
                await std_embed.send_info(
                    msg.channel,
                    description=fmt.format_maxlen(
                        "**{}** has been warned {} "
                        f"{'time' if result[0][0] == 1 else 'times'}."
                        "\nLast warned: **<t:{}>** by **{}**",
                        member,
                        result[0][0],
                        int(result[0][1].timestamp()),
                        result[0][2],
                    ),
                    author=member
                )

        elif msg.author.guild_permissions.administrator:
            #if a member is not provided to warn
            if not args:
                raise ReportableError("No user entered")
            split_args = args.split(",", 1)

            #check if a reason for the warn is provided
            if len(split_args) < 2:
                user_name = args
                #TODO check if an attachment was provided as the reason
                #if msg.attachments:
                #    pass
                #else:
                #    pass
                reason = "No reason given"
            else:
                user_name = split_args[0]
                reason = split_args[1]
            """ split_args[0] = user_id
                split_args[1] = reason   """

            member = await find.member(msg.channel, user_name, msg.author)
            #if the member specified cannot be found
            if member is None:
                raise ReportableError(
                    fmt.format_maxlen(
                        "**{}** not found. If you are having trouble typing in a user's name, you can also use their User ID! Example: **$warn count {}** ",
                        user_name,
                        random.randint(100000000000000000, 999999999999999999),
                    )
                )
            elif member.bot:
                raise ReportableError("You cannot warn bots.")

            red = 0xFF0000  # red
            # run this 5 times
            check_counter = 0
            message_logs = []
            async for m in msg.channel.history(limit=200):
                if check_counter == 5:
                    break
                if m.author == member:
                    check_counter += 1
                    message_logs.insert(0, m.content)

            punishments = """~These are the punishments for a warning beyond the first one:
                Two Warnings: Server Muted for **6 Hours**
                Three Warnings: Server Muted for **3 Days**
                Four+ Warnings: Server Muted for **7 days** + A moderator will deal with you manually. This can result in a **permanent ban** or **permanent mute**.
                """

            #try to get the members previous warnings
            operation = "SELECT * FROM warn WHERE Server = %s AND Member = %s ORDER BY Count;"
            params = (msg.guild.id, member.id)
            warnings = db.read_execute(operation, params)

            #the user's first warning
            if not warnings:
                #log the warn in the table
                operation = "INSERT INTO warn VALUES (%s, %s, %s, %s, %s, %s, %s);"
                params = (msg.guild.id, member.id, 1, datetime.now().replace(microsecond=0), str(msg.author), reason, "\\n".join(message_logs))
                db.execute(operation, params)
                #send the user a private message explaining the warn
                warning_message = discord.Embed(
                    title="You have been warned!",
                    description=f"""
                        ~You have been warned by **{msg.author}** from the server: **{msg.guild.name}**\n
                        ~The reason you were warned: **{reason}**\n
                        ~Since this is your first warning, nothing will happen to you. However, future warnings may result in a mute or possible ban.\n
                        {punishments}\n
                        ~Be sure to not spam chats, say anything that would offend someone else, or post NSFW pictures in chats unless they are labeled NSFW.\n
                        ~If you believe you have been accidentally or wrongfully warned, don't hesitate to ping or PM a mod so that they can look into it.
                        """,
                    color=red,
                )
                await member.send(embed=warning_message)
                await std_embed.send_info(msg.channel,
                    title = f"{member} has been warned. This is their first warning.",
                    author = msg.author
                )

            #the user's successive warning
            else:
                #get how many times this member has been muted
                operation = "SELECT MAX(Count) FROM  warn WHERE Server = %s AND Member = %s;"
                warning_count = db.read_execute(operation, params)[0][0] + 1

                #log the warning
                operation = "INSERT INTO warn VALUES (%s, %s, %s, %s, %s, %s, %s);"
                params = (msg.guild.id, member.id, warning_count, datetime.now().replace(microsecond=0), str(msg.author), reason, "\\n".join(message_logs))
                db.execute(operation, params)

                operation = "SELECT Reason FROM warn WHERE Server = %s AND Member = %s ORDER BY Count;"
                params = (msg.guild.id, member.id)
                previous_reasons = db.read_execute(operation, params)
                previous_reasons = "\n".join(reason[0] for reason in previous_reasons)

                # https://stackoverflow.com/questions/9647202/ordinal-numbers-replacement
                ordinal = lambda n: "%d%s" % (
                    n,
                    "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
                )

                warning_message = discord.Embed(
                    title="You have been warned!",
                    description=f"""
                        ~You have been warned by **{msg.author}** from the server: **{msg.guild.name}**\n
                        ~The reason you were warned: **{reason}**\n
                        ~This is your **{ordinal(warning_count)}** warning.\n
                        ~Previous Reason(s): \n**{previous_reasons}**\n
                        {punishments}
                        ~Be sure to not spam chats, say anything that would offend someone else, or post NSFW pictures in chats unless they are labeled NSFW.\n
                        ~If you believe you have been accidentally or wrongfully warned, don't hesitate to ping or PM a mod so that they can look into it.
                        """,
                    color=red,  # TODO color
                )

                #handle the member appropriately depending on how many times they've been warned
                if warning_count == 2:
                    await member.send(embed=warning_message)
                    await std_embed.send_info(msg.channel,
                        title = f"{member} has been warned. This is their {ordinal(warning_count)} warning.", 
                        author = msg.author
                    )
                    await mute.mute(
                        m=member,
                        unmute_at=datetime.now() + timedelta(hours = 6),
                        channel=msg.channel,
                        author=msg.author,
                    )
                elif warning_count == 3:
                    await member.send(embed=warning_message)
                    await std_embed.send_info(msg.channel,
                        title = f"{member} has been warned. This is their {ordinal(warning_count)} warning.",
                        author = msg.author
                    )
                    await mute.mute(
                        m=member,
                        unmute_at=datetime.now() + timedelta(days = 3),
                        channel=msg.channel,
                        author=msg.author,
                    )
                elif warning_count > 3:  # TODO welcome back, you're still muted
                    await member.send(embed=warning_message)
                    await std_embed.send_info(msg.channel,
                        title = f"{member} has been warned. This is their {ordinal(warning_count)} warning.", 
                        author = msg.author
                    )
                    await std_embed.send_info(
                        msg.channel, title = "Notice: This user has been warned over 3 times on this server.", author = msg.author
                    )
                    await mute.mute(
                        m=member,
                        unmute_at=datetime.now() + timedelta(days = 7),
                        channel=msg.channel,
                        author=msg.author,
                    )


bot_commands.add_command(Warn_Command())
