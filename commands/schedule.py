from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from pathlib import Path
from utils import find, get
from utils.paged_message import Paged_Message
from utils import parse
from typing import Optional, Union
from core import client

import datetime
import json
import discord
import asyncio

class Schedule_Command(Bot_Command):
    name = "schedule"

    session_log = Path("data/schedule/scheduled_sessions.json")

    short_help = "Posts the server's schedule or schedules an event."

    long_help = f"""Schedule an event for the specified date and time.
    Usage:
    **schedule** [*year*]
    **schedule edit** *title*
    **schedule event** *date time title*

    Format date and time as *`MM/DD/YY HH:MM AM/PM`*
    """

    category = Bot_Command_Category.COMMUNITY

    #discord's global mentions or command-specific keywords
    restricted = ["all", "here", "everyone"]

    #the bot's local time zone
    tz = datetime.timezone(datetime.timedelta(hours=-4))

    #create a log file at the specified Path if it doesn't already exist
    def __init__(self):
        if not self.session_log.exists():
            self.session_log.mkdir(parents=True, exist_ok=True)

    async def run(self, msg: discord.Message, args: str):
        with self.session_log.open("r") as file:
            self.sessions = json.load(file)

        #gets current server
        guild = msg.author.guild
        #gets a string of the server's id
        guild_id = str(guild.id)
        #gets current channel
        channel = msg.channel

        #if this server is not in the log file, add it
        if guild_id not in self.sessions:
            self.sessions[guild_id] = {}
            self.save()

        #if user doesn't include any arguments, post the server's schedule
        if not args:
            await self.post_schedule(channel, guild, m=msg.author)

        #if user requests the schedule for a specific year
        elif args.isdigit():
            if int(args) >= datetime.datetime.now().year:
                await self.post_schedule(channel, guild, args, m=msg.author)

        #admins or event creators can remove scheduled events
        elif args.casefold().startswith("remove"):
            #if no events were specified to be removed
            if not args[len("remove"):].strip():
                return
            #clearing the schedule
            if args[len("remove"):].strip().casefold() == "all":
                await self.remove(msg, remove_all = True)
                await self.post_schedule(channel, guild, m=msg.author)
                return
            #attempt to remove each specified event
            for arg in args[len("remove"):].casefold().strip().split(","):
                event = self.get_event(arg.strip(), guild_id)
                #if an event is found, remove it
                if event is not None:
                    #only the event creator or admins can remove events
                    if  msg.author.id == event['author'] or msg.author.guild_permissions.administrator:
                        await self.remove(msg, event)
                    #an unauthorized user attempted to delete the event
                    else:
                        embed = discord.Embed(
                            title="[ERROR]",
                            color=discord.Color.red(),
                            description="**You do not have permission to remove this event.**"
                        )
                        await channel.send(embed=embed)
                        return

            #post the updated schedule
            await self.post_schedule(channel, guild, m=msg.author)

        #scheduling a new event
        elif args.casefold().startswith("event"):
            error_embed = discord.Embed(color=discord.Color.red())
            error_embed.set_author(
                name=f"[NEW EVENT]",
                icon_url=msg.author.avatar_url_as(format='png')
            )
            embed = error_embed.copy()
            embed.color = discord.Color.gold()

            if not args[len("event"):].strip():
                error_embed.description = "An event title was not provided."
                await channel.send(embed=error_embed)
                return

            #validate the title
            parsed_args = self.validate(guild_id, title=args[len("event"):].strip())
            if parsed_args[0] is not None:
                title = parsed_args[0]
            else:
                error_embed.description = parsed_args[3]
                await channel.send(embed=error_embed)
                return

            #prompt the user for an event date
            embed.description = f"**Please enter a date for `{title}`**"
            prompt = await channel.send(embed=embed)
            date = await get.reply(msg.author, channel, prompt)
            if date is None:
                return
            parsed_args = self.validate(guild_id, date=date.content)
            if parsed_args[1] is None:
                error_embed.description = parsed_args[3]
                await channel.send(embed=error_embed)
                return
            date = parsed_args[1]

            #prompt the user for an event time
            embed.description = f"**Please enter a time for `{title}`**"
            prompt = await channel.send(embed=embed)
            time = await get.reply(msg.author, channel, prompt)
            if time is None:
                return
            parsed_args = self.validate(guild_id, time=time.content)
            if parsed_args[2] is None:
                error_embed.description = parsed_args[3]
                await channel.send(embed=error_embed)
                return
            time = parsed_args[2]

            #combine the date and time to get a datetime object
            dt = datetime.datetime.combine(date, time)
            #make sure the time is in the future
            if dt.astimezone(tz=self.tz) < datetime.datetime.now(tz=self.tz):
                error_embed.description = "This time has already passed."
                await channel.send(embed=error_embed)
                return

            #creates a role to ping participants for this event
            role = await guild.create_role(name=title)
            #send a message asking for members to react to join the event
            embed.title = role.name
            embed.color = discord.Color.blue()
            embed.description = f"React to this message to be pinged for {role.mention} on **<t:{int(dt.timestamp())}:F>**!"
            message = await channel.send(embed=embed)

            #create a dictionary of the event details
            event = {
                "name": title,
                "datetime": str(dt),
                "msg_id": message.id,
                "role_id": role.id,
                "author": msg.author.id
            }
            await self.schedule_event(msg.author, channel, event)
            
        #edits a specified event
        elif args.casefold().startswith("edit"):
            embed = discord.Embed(color=discord.Color.red())
            embed.set_author(
                name=f"[EDIT EVENT]",
                icon_url=msg.author.avatar_url_as(format='png')
            )
            #try to find a scheduled event with the specified name
            title = args[len("edit"):].strip()
            if not title:
                embed.description = "**An event title was not provided.**"
                print("No event provided")
                await channel.send(embed=embed)
                return
            event = self.get_event(title, guild_id)
            if event is not None:
                print(f"Editing event `{title}`")
                if msg.author.id == event['author'] or msg.author.guild_permissions.administrator:
                    await self.edit_event(msg.author, event, channel, 180)
                else:
                    embed.description = f"**You do not have permission to edit this event.**"
                    await channel.send(embed=embed)
            else:
                embed.description = f"**An event with the title `{title}` could not be found**"
                print(f"No event named {title}")
                await channel.send(embed=embed)

        #catch invalid event types or incorrect command usage
        else:
            embed = discord.Embed(
                title="[ERROR]",
                color=discord.Color.red(),
                description="**Please enter a valid event type**"
            )
            await channel.send(embed=embed)





    #returns the dictionary of the event details if it exists
    def get_event(self, name: str, guild_id: str):
        with self.session_log.open("r") as file:
            self.sessions = json.load(file)
        for year, months in self.sessions[guild_id].copy().items():
            for month, items in months.copy().items():
                for item in items:
                    if item['name'].casefold() == name.casefold():
                        return item
        return None





    #validates the passed event fields
    def validate(
        self,
        guild_id: str,
        title: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None
    ):
        """
        Parameters
        ----------

        guild_id: str
        A string containing the id of the guild.

        title: Optional[str]
        The title of the event. Required if date and time are None.

        date: Optional[str]
        The date of the event. Required if title and time are None.

        time: Optional[str]
        The time of the event. Reqiuired if title and date are None.
        """

        #list to return, respectively storing title, date, time and an error message if any
        ret = [None] * 3 + ['']

        #make sure the event has a valid title
        if title is not None:
            #check that the title is unique
            if self.get_event(title, guild_id) is not None:
                ret[3] = "An event with this title already exists. "
            #check that the title isn't a restricted keyword
            elif title.casefold() in (mention.casefold() for mention in self.restricted):
                ret[3] = "This title is restricted. Please choose a different one. "
            #make sure the title is within a role name's max length
            elif len(title) > 100:
                ret[3] = "Title must be 100 characters or fewer in length. "
            #if title passes all checks, set ret[0] = to title
            else:
                ret[0] = title

        #checks that user entered a properly formatted date
        if date is not None:
            try:
                date = parse.str_to_date(date)
                if date < datetime.date.today():
                    ret[3] = "This date has already passed. "
                else:
                    ret[1] = date
            except ValueError as ve:
                print(ve)
                ret[3] = "Invalid event date. Please follow the format `MM/DD/YY`. "

        #checks that user entered a properly formatted time
        if time is not None:
            try:
                time = parse.str_to_time(time)
                ret[2] = time
            except ValueError as ve:
                print(ve)
                ret[3] = "Invalid event time. Please follow the format `HH:MM AM/PM`. "

        return ret





    #gets the reactions to a message and assigns all reactors the specified role
    async def react_for_role(self, msg: discord.Message, role: discord.Role):
        #get an updated reference to the reaction message
        msg = await msg.channel.fetch_message(msg.id)

        #get a list of users who reacted
        users = []
        for reaction in msg.reactions:
            users += await reaction.users().flatten()

        #remove duplicate Users
        users = set(users)

        #assigns the role to all users who reacted
        for user in users:
            #convert User object into Member
            member = msg.guild.get_member(user.id)
            #ignore any bots that react
            if member.bot:
                continue
            if role not in member.roles:
                await member.add_roles(role)





    #sort the server events by date
    def sort(self, guild_id: str):
        #sort by year
        self.sessions[guild_id] = dict(sorted(self.sessions[guild_id].items()))

        def event_sort_key(event):
            return (
                datetime.datetime.fromisoformat(event['datetime']),
                event['name'],
            )
        for year in self.sessions[guild_id]:
            #sort by month
            self.sessions[guild_id][year] = dict(sorted(self.sessions[guild_id][year].items()))
            for month in self.sessions[guild_id][year]:
                #sort the month's events in chronological order
                sorted_list = []
                for item in sorted(self.sessions[guild_id][year][month], key=event_sort_key):
                    dt = datetime.datetime.fromisoformat(item['datetime']).replace(tzinfo=datetime.timezone.utc)
                    sorted_list.append(item)
                self.sessions[guild_id][year][month] = sorted_list
        self.save()





    async def schedule_event(
        self,
        member: discord.Member,
        channel: discord.TextChannel,
        event_dict: dict
    ):
        """Schedules an event

        Parameters
        ----------
        member: discord.Member
        The member scheduling the event.

        channel: discord.TextChannel
        The channel to send the event info in.

        event_dict: dict
        A dictionary containing the event details.
        """

        guild = channel.guild
        guild_id = str(guild.id)

        #unpack the event dictionary
        dt = datetime.datetime.fromisoformat(event_dict['datetime'])
        message = await channel.fetch_message(event_dict['msg_id'])
        role = guild.get_role(event_dict['role_id'])

        #log the event
        try:
            year = dt.strftime('%Y')
            month = dt.strftime('%m')
            #make sure the year exists in the log file
            if year not in self.sessions[guild_id]:
                self.sessions[guild_id][year] = {month: [event_dict]}
            #make sure the month exists in the year
            elif month not in self.sessions[guild_id][year]:
                self.sessions[guild_id][year][month] = [event_dict]
            #append the event to the year and month
            else:
                self.sessions[guild_id][year][month].append(event_dict)
            self.sort(guild_id)
        except Exception as e:
            print(e)
            await message.delete()
            if role is not None:
                await role.delete()
            return

        #sleep until 5 minutes before the event to notify participants ahead of time
        await discord.utils.sleep_until(dt.astimezone(tz=self.tz) - datetime.timedelta(minutes=5))

        #verify this event still exists
        if self.get_event(event_dict['name'], guild_id) is None:
           return

        #assign all participants the designated role for this event
        await self.react_for_role(message, role)

        #creates and sends an embed reminder for the event
        reminder = discord.Embed(color=discord.Color.blue())
        reminder.add_field(
            name="REMINDER",
            value=f"""**{event_dict['name'].upper()}** will be starting soon!
            You can still join before it starts by reacting to [this message]({message.jump_url})!""",
            inline=False
        )
        m1 = await channel.send(f"{role.mention}", embed=reminder)

        #wait for event to start
        await discord.utils.sleep_until(dt.astimezone(tz=self.tz))

        #check for any last minute participants
        await self.react_for_role(message, role)

        #send a final reminder that the event has started
        reminder.clear_fields()
        reminder.add_field(
            name=f"{event_dict['name'].upper()}",
            value="THE EVENT HAS STARTED! JOIN NOW!!",
            inline=False
        )
        m2 = await channel.send(f"{role.mention}", embed=reminder)

        #leave event posted for 5 minutes before deleting it
        await asyncio.sleep(300)

        try:
            #delete the role assigned to this event
            await role.delete()
            #delete the event from the log file
            await self.remove(m1, event_dict)
            #removes the deleted role mention from the reminder messages
            await m1.edit(content=None)
            await m2.edit(content=None)
        except discord.HTTPException as httpe:
            print(httpe)
        except Exception as e:
            print(e)





    #deletes the specified event from this server's schedule
    async def remove(
        self,
        msg: discord.Message,
        event: Optional[dict] = None,
        remove_all: bool = False
    ):
        """Removes the passed event from the log file and deletes its
        associated role and reaction message.

        Parameters
        ----------
        msg: discord.Message
        A reference message to get the channel, guild and member who requested the
        event removal.

        event: Optional[dict]
        A dictionary of the event being removed. Required if remove_all is False.

        remove_all: bool
        A boolean flag to indicate whether or not to clear the guild's schedule.
        """
        #get the guild's id as a string and the channel the message was sent in
        guild_id = str(msg.guild.id)
        channel = msg.channel

        #admins can clear the schedule
        if remove_all and msg.author.guild_permissions.administrator:
            for year, months in self.sessions[guild_id].copy().items():
                for month, items in months.copy().items():
                    for item in items:
                        #delete the role assigned to this event
                        role = msg.guild.get_role(item['role_id'])
                        if role is not None:
                            await role.delete()
                        #remove the event from the log file
                        self.sessions[guild_id][year][month].remove(item)
                        self.save()

                        #delete the message asking for reactions to join this event
                        try:
                            m = await channel.fetch_message(item['msg_id'])
                            await m.delete()
                        except discord.NotFound as dnf:
                            print(dnf)
                            continue

            self.sessions[guild_id] = {}
            self.save()
        #removes the specified events from the schedule
        else:
            if event is not None:
                dt = datetime.datetime.fromisoformat(event['datetime'])
                year = dt.strftime('%Y')
                month = dt.strftime('%m')
                #try to delete the message asking for reactions to join this event
                try:
                    m = await channel.fetch_message(event['msg_id'])
                    await m.delete()
                except discord.NotFound as dnf:
                    print(dnf)
                    pass

                #remove the event from the log file
                self.sessions[guild_id][year][month].remove(event)
                if not self.sessions[guild_id][year][month]:
                    self.sessions[guild_id][year].pop(month)
                if not self.sessions[guild_id][year]:
                    self.sessions[guild_id].pop(year)
                self.save()
                #delete the role assigned to this event
                role = msg.guild.get_role(event['role_id'])
                if role is not None:
                    await role.delete()





    #allow event creator to edit edit their scheduled event
    async def edit_event(
            self,
            author: discord.Member,
            event: dict,
            channel: discord.TextChannel,
            timeout: int = 90
        ):
        """
        Parameters
        ----------
        author: discord.Member
        The member requesting the edit.

        event: dict
        The dictionary containing the information of the event being edited.

        channel: discord.TextChannel
        The channel to send the edit messages to.

        timeout: int
        Number of seconds to wait for a user response before returning and exiting the function.
        """

        fields = {
            "title_emoji": "🏷",
            "date_emoji": "🗓",
            "time_emoji": "⏰"
        }
        choice = {
            "confirm_emoji": "✅",
            "cancel_emoji": "❌"
        }

        title = event['name']
        dt = datetime.datetime.fromisoformat(event['datetime'])

        #create embed explaining how to edit the event
        embed = discord.Embed(
            color=discord.Color.gold(),
            description=f"""
            Editing `{event['name']}`. Which fields would you like to edit?
            {fields['title_emoji']} `Title`: {title}
            {fields['date_emoji']} `Date`: <t:{int(dt.timestamp())}:D>
            {fields['time_emoji']} `Time`: <t:{int(dt.timestamp())}:t>

            React with {choice['confirm_emoji']} to confirm your choices, {choice['cancel_emoji']} to cancel.
            """
        )
        embed.set_author(
            name="[EDIT EVENT]",
            icon_url=author.avatar_url_as(format='png')
        )
        guild_id = str(channel.guild.id)
        field_request = await channel.send(embed=embed)

        for emoji in fields:
            await field_request.add_reaction(fields[emoji])
        for emoji in choice:
            await field_request.add_reaction(choice[emoji])

        try:
            reaction, reactor = await client.wait_for(
                "reaction_add",
                check=lambda r, u: r.message == field_request
                and r.emoji in (choice.values())
                and u == author,
                timeout=timeout
            )
        except asyncio.TimeoutError:
            await field_request.clear_reactions()
            print("Timed out waiting for user.")
            return


        #cancel edit request
        if reaction.emoji == choice['cancel_emoji']:
            print(f"Cancelled edits to {event['name']}")
            #remove all reactions from the message
            await field_request.clear_reactions()
            embed.color = discord.Color.blue()
            embed.description = f"**Cancelled edits to `{event['name']}`**"
            await channel.send(embed=embed)
            return

        #get updated reference to field_request message
        field_request = await field_request.channel.fetch_message(field_request.id)
        #get which fields have been selected for editing
        confirmed_fields = []
        for r in field_request.reactions:
            if r.emoji in fields.values() and author in await r.users().flatten():
                confirmed_fields += r.emoji
        print(confirmed_fields)

        await field_request.clear_reactions()
        #if no fields were chosen for editing
        if not confirmed_fields:
            print("No fields chosen")
            embed.color = discord.Color.blue()
            embed.description = f"**No fields were selected. Cancelling edit request.**"
            await channel.send(embed=embed)
            return

        #make a copy of the event to contain the edited info
        new_event = event.copy()
        old_dt = dt

        error_embed = embed.copy()
        error_embed.color = discord.Color.red()
        error_embed.description = f"Cancelling all edits to `{title}`."

        edit_desc = f"**Successfully made edits to `{title}`.\nChanged:**"

        if fields['title_emoji'] in confirmed_fields:
            embed.description = f"""**Please enter a new title for `{title}`.**
            Current title: `{title}`"""
            msg = await channel.send(embed=embed)

            #prompt user for a new title
            title = await get.reply(author, channel, msg)
            if title is None:
                return
            parsed_args = self.validate(guild_id, title=title.content)
            if parsed_args[0] is None:
                error_embed.description = parsed_args[3] + error_embed.description
                await channel.send(embed=error_embed)
                return
            title = parsed_args[0]
            edit_desc += f"\n{fields['title_emoji']} `Title`: `{event['name']}` -> `{title}`"

        if fields['date_emoji'] in confirmed_fields:
            embed.description = f"""**Please enter a new date for `{title}`**
            Current date: <t:{int(old_dt.timestamp())}:D>"""
            msg = await channel.send(embed=embed)

            #prompt user for a new date
            date = await get.reply(author, channel, msg)
            if date is None:
                return
            parsed_args = self.validate(guild_id, date=date.content)
            if parsed_args[1] is None:
                error_embed.description = parsed_args[3] + error_embed.description
                await channel.send(embed=error_embed)
                return
            date = parsed_args[1]

            #replace the old date with the new date
            dt = dt.replace(year=date.year, month=date.month, day=date.day)
            edit_desc += f"\n{fields['date_emoji']} `Date`: <t:{int(old_dt.timestamp())}:D> -> <t:{int(dt.timestamp())}:D>"

        if fields['time_emoji'] in confirmed_fields:
            embed.description = f"""**Please enter a new time for `{title}`**
            Current time: <t:{int(old_dt.timestamp())}:t>"""
            msg = await channel.send(embed=embed)

            #prompt user for a new time
            time = await get.reply(author, channel, msg)
            if time is None:
                return
            parsed_args = self.validate(guild_id, time=time.content)
            if parsed_args[2] is None:
                error_embed.description = parsed_args[3] + error_embed.description
                await channel.send(embed=error_embed)
                return
            time = parsed_args[2]

            #make sure new time is in the future
            dt = dt.replace(hour=time.hour, minute=time.minute)
            if dt.astimezone(tz=self.tz) < datetime.datetime.now(tz=self.tz):
                error_embed.description = "This time has already passed. " + error_embed.description
                await channel.send(embed=error_embed)
                return
            edit_desc += f"\n{fields['time_emoji']} `Time`: <t:{int(old_dt.timestamp())}:t> -> <t:{int(dt.timestamp())}:t>"

        new_event['name'] = title
        new_event['datetime'] = str(dt)

        #delete the old event
        year = old_dt.strftime('%Y')
        month = old_dt.strftime('%m')
        self.sessions[guild_id][year][month].remove(event)
        if not self.sessions[guild_id][year][month]:
            self.sessions[guild_id][year].pop(month)
        if not self.sessions[guild_id][year]:
            self.sessions[guild_id].pop(year)
        self.save()

        #update the role for this event
        role = channel.guild.get_role(new_event['role_id'])
        if role is None:
            role = await channel.guild.create_role(name=title)
            new_event['role_id'] = role.id
        else:
            await role.edit(name=title)

        #edit the reaction message, if not found, create a new one
        try:
            m = await channel.fetch_message(new_event['msg_id'])
            e = m.embeds[0]
            e.title = title
            e.description = f"React to this message to be pinged for {role.mention} on **<t:{int(dt.timestamp())}:F>**!"
            await m.edit(embed=e)
        except discord.NotFound as dnf:
            print(dnf)
            #send a message asking for members to react to join the event
            react_embed = discord.Embed(
                title=title,
                color=discord.Color.blue(),
                description=f"React to this message to be pinged for {role.mention} on **<t:{int(dt.timestamp())}:F>**!"
            )
            message = await channel.send(embed=react_embed)
            new_event['msg_id'] = message.id

        edit_embed = embed.copy()
        edit_embed.color = discord.Color.blue()
        edit_embed.description = edit_desc
        await channel.send(embed=edit_embed)
        #schedule a new event with the edited information
        await self.schedule_event(author, channel, new_event)





    #creates and sends an embed of this guild's scheduled events
    async def post_schedule(
            self,
            channel: discord.TextChannel,
            guild: discord.Guild,
            year: Optional[str] = None,
            m: Optional[Union[discord.User, discord.Member]] = None
        ):
        """
        Parameters
        -----------
        channel: discord.TextChannel
        The server's designated schedule channel.
        All messages related to scheduled events are sent in this channel.

        guild: discord.Guild
        The server from which the schedule is being requested.

        year: Optional[str]
        A specific year that a schedule is being requested for.

        m: Optional[Union[disord.User, discord.Member]]
        The member or user requesting the schedule. If provided, only this 
        user can turn the pages of the schedule if there are multiple pages.
        """
        #get all events scheduled for this server
        schedule = self.sessions[str(guild.id)]
        #if there are no events scheduled in this server
        async def no_events():
            embed = discord.Embed(
                title = f"{guild.name}'s {year+' ' if year else ''}Schedule",
                color=discord.Color.red(),
                description=f"**There are no events scheduled{' for '+year if year else ''}**"
            )
            await channel.send(embed=embed)
            return
        if not schedule:
            await no_events()
            return

        #sort the events
        self.sort(str(guild.id))
        #post the schedule for a specified year
        if year is not None:
            #if there are no events for the specified year
            if year not in schedule:
                await no_events()
                return
            #get the list of dictionaries of this server's events for the specified year
            schedule = schedule[year]

            embeds = (Paged_Message.embed_list_from_items(
                    schedule,
                    lambda t: f"{guild.name}'s {year} Schedule",
                    None,
                    lambda i: (
                        datetime.datetime.strptime(i, "%m").strftime("%B"),
                        "\n".join(f"[<t:{int(datetime.datetime.fromisoformat(event['datetime']).timestamp())}> - {event['name']}]({channel.get_partial_message(event['msg_id']).jump_url})" for event in schedule[i]),
                        False
                    ),
                    m,
                    max_field_count = 12
                )
            )
            await Paged_Message(embeds, m).send(channel)
        #post the schedule of all server events
        else:
            #stores lists of embeds per year
            years = []
            #create a list of embeds per year
            for year in schedule:
                #appends the list of embeds associated with this year to years
                years += (Paged_Message.embed_list_from_items(
                        schedule[year],
                        lambda t: f"{guild.name}'s {year + ' ' if len(schedule) > 1 else ''}Schedule",
                        None,
                        lambda i: (
                            datetime.datetime.strptime(i, "%m").strftime("%B"),
                            "\n".join(f"[<t:{int(datetime.datetime.fromisoformat(event['datetime']).timestamp())}> - {event['name']}]({channel.get_partial_message(event['msg_id']).jump_url})" for event in schedule[year][i]),
                            False
                        ),
                        m,
                        max_field_count = 12
                    )
                )
            #post the schedule
            await Paged_Message(years, m).send(channel)





    #saves any writes to the log file
    def save(self):
        with self.session_log.open("w") as file:
            json.dump(self.sessions, file, indent=4)

bot_commands.add_command(Schedule_Command())
