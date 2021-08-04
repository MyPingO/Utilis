from bot_cmd import Bot_Command, bot_commands
from pathlib import Path
from utils import get_member, get_role,  Multi_Page_Embed_Message
from typing import Optional, Union

import datetime
import json
import discord
import asyncio

class Schedule_Command(Bot_Command):
    name = "schedule"

    session_log = Path("data/scheduled_sessions.json")

    short_help = "Posts the server's schedule or schedules an event."

    long_help = f"""Schedule an event for the specified date and time.
    Arguments:
    `Type`  [event, edit, (year)]
    `Time`  Formatted as **MM/DD/YY HH:MM AM/PM**
    `Title` Descriptive name for the event. Will also be the name of the role to be pinged

    If all arguments are omitted, the schedule for this server is posted.
    All participants will be pinged by a designated role 5 minutes in advance
    as a reminder, as well as when the event starts.
    """

    #discord's global mentions or command-specific keywords
    restricted = ["all", "here", "everyone"]

    #EST time zone
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
        id_num = str(guild.id)
        #gets current channel
        channel = msg.channel

        #if this server is not in the log file, add it
        if id_num not in self.sessions:
            self.sessions[id_num] = {}
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
            #attempt to remove each specified event
            for arg in args[len("remove"):].split(","):
                await self.remove(msg, arg.strip().casefold())
            #post the updated schedule
            await self.post_schedule(channel, guild, m=msg.author)

        #scheduling a new event
        elif args.casefold().startswith("event"):
            if not args[len("event"):].strip():
                await channel.send("No event details were specified.")
                return
            parsed_args = args.strip().split(" ", 4)
            #checks that user entered a properly formatted date/time
            try:
                #concatenate the user input for the date and time of the event
                time = " ".join(parsed_args[1:4])
                #create an iso formatted datetime object from time
                session = datetime.datetime.strptime(time, '%m/%d/%y %I:%M %p').isoformat(sep=" ")
                #convert session into a datetime object again with the correct timezone
                session = datetime.datetime.fromisoformat(session).replace(tzinfo=self.tz)
            except (ValueError, IndexError):
                print("The date/time was not formatted properly. Please follow the format `MM/DD/YY HH:MM AM/PM`.")
                await channel.send("The date/time was not formatted properly. Please follow the format `MM/DD/YY HH:MM AM/PM`.")
                return

            #verify the user enters a future date/time
            if session < datetime.datetime.now(tz=self.tz):
                print("This date/time has already passed. Please enter a valid date/time.")
                await channel.send("This date/time has already passed. Please enter a valid date/time")
                return

            #make sure the event has a valid title
            try:
                title = parsed_args[4].strip()

                #check that there isn't already a role with the same name as the event
                if title.casefold() in (role.name.casefold() for role in guild.roles):
                    await channel.send("This title is restricted. Please choose a different one.")
                    return
                #check that the title isn't a restricted keyword
                if title.casefold() in (mention.casefold() for mention in self.restricted):
                    await channel.send("This title is restricted. Please choose a different one.")
                    return
                #make sure the title is within a role name's max length
                if len(title) > 100:
                    await channel.send("Title must be 100 characters or fewer in length.")
                    return

            except IndexError:
                print("No title was provided")
                await channel.send("No title was provided")
                return

            #send a message asking for members to react to join the event
            message = await channel.send(f"React to this message to be pinged for `{title}` at `{time}`!")
            #create a dictionary of the event details
            event = {"name": title, "time": str(session), "msg_id": message.id}
            #if there is an error logging the event, delete the message requesting participants
            try:
                await self.log_session(id_num, event)
            except Exception as e:
                print(e)
                await message.delete()

            #creates a role to ping participants for this event
            role = await guild.create_role(name=title)

            #sleep until 5 minutes before the event to notify participants ahead of time
            await discord.utils.sleep_until(session - datetime.timedelta(minutes=5))

            #verify this event still exists
            if not await self.exists(id_num, event):
               return

            #assign all participants the designated role for this event
            await self.react_for_role(message, role)

            #creates and sends an embed reminder for the event
            reminder = discord.Embed(color=discord.Color.random())
            reminder.add_field(
                name="REMINDER",
                value=f"""**{title.upper()}** will be starting soon!
                You can still join before it starts by reacting to [this message]({message.jump_url})!""",
                inline=False
            )
            m1 = await channel.send(f"{role.mention}", embed=reminder)

            #wait for event to start
            await discord.utils.sleep_until(session)

            #check for any last minute participants
            await self.react_for_role(message, role)

            #send a final reminder that the event has started
            reminder.clear_fields()
            reminder.add_field(
                name=f"{title.upper()}",
                value="THE EVENT HAS STARTED! JOIN NOW!!",
                inline=False
            )
            m2 = await channel.send(f"{role.mention}", embed=reminder)

            #leave event posted for 10 minutes before deleting it
            await asyncio.sleep(600)

            #delete the role assigned to this event
            await role.delete()
            #delete the event from the log file
            await self.remove(msg, title)
            #removes the deleted role mention from the reminder messages
            await m1.edit(content=None)
            await m2.edit(content=None)

        #TODO allows admins to schedule announcements
        elif args.casefold().startswith("announcement"):
            if msg.author.guild_permissions.administrator:
                pass
                #await channel.send("@everyone", embed=)
            pass
        #TODO the event creator or admins can edit the details of an event
        elif args.casefold().startswith("edit"):
            #get the title of the event trying to be edited
            #event = args[len("edit"):].strip()
            #try to edit the event if one was specified
            #if event:
                #await edit_event(msg.author, args[len("edit"):])
            pass
        #catch invalid event types or incorrect command usage
        else:
            await channel.send("Please enter a valid event type.")





    #deletes the specified event from this server's schedule
    async def remove(self, msg: discord.Message, title: str):
        #get the guild's id as a string and the channel the message was sent in
        guild_id = str(msg.guild.id)
        channel = msg.channel

        for year, months in self.sessions[guild_id].copy().items():
            for month, items in months.copy().items():
                #admins can clear the schedule
                if title == "all" and msg.author.guild_permissions.administrator:
                    for item in items:
                        #delete the role assigned to this event
                        role = await get_role(channel, item["name"])
                        if role is not None:
                            await role.delete()
                        #remove the event from the log file
                        self.sessions[guild_id][year][month].remove(item)
                        self.save()

                        #delete the message asking for reactions to join this event
                        try:
                            m = await channel.fetch_message(item["msg_id"])
                            await m.delete()
                        except discord.NotFound as dnf:
                            print(dnf)
                            continue

                    self.sessions[guild_id] = {}
                    self.save()
                    return
                #removes the specified events from the schedule
                else:
                    event = next((item for item in items if item["name"].casefold() == title), None)
                    #if an event with the title is found, remove it
                    if event:
                        #try to get the message asking for reactions to join this event
                        try:
                            m = await msg.channel.fetch_message(event["msg_id"])
                        except discord.NotFound as dnf:
                            print(dnf)

                        year = event["time"][:4]
                        month = event["time"][5:7]
                        #only the event creator or admins can remove events
                        if  msg.author.id == m.author.id or msg.author.guild_permissions.administrator:
                            #remove the event from the log file
                            self.sessions[guild_id][year][month].remove(event)
                            self.save()
                            #delete the message requesting participants
                            await m.delete()
                            #delete the role assigned to this event
                            role = await get_role(channel, event["name"])
                            if role:
                                await role.delete()
                        #an unauthorized user attempted to delete th
                        else:
                            await channel.send("You do not have permission to remove this event")
                #if a month is empty, remove it from the log file
                if not self.sessions[guild_id][year][month]:
                    self.sessions[guild_id][year].pop(month)
                    self.save()
            #if a year is empty, remove it from the log file
            if not self.sessions[guild_id][year]:
                self.sessions[guild_id].pop(year)
                self.save()
        self.save()





    #gets the reactions to a message and assigns all reactors the specified role
    async def react_for_role(self, msg: discord.Message, role: discord.Role):
        #get an updated reference to the reaction message
        msg = await msg.channel.fetch_message(msg.id)
        #get the message's reactions
        for reaction in msg.reactions:
            #make a list of the Users who reacted to the message
            users = await reaction.users().flatten()
            #assigns the role to all users who reacted
            for user in users:
                #convert User object into Member
                member = msg.guild.get_member(user.id)
                #ignore any bots that react
                if member.bot:
                    continue
                #assign the member the role if they don't already have it
                if role not in member.roles:
                    await member.add_roles(role)





    #sort the server events by date
    def sort(self, guild_id: str):
        #sort by year
        self.sessions[guild_id] = dict(sorted(self.sessions[guild_id].items()))
        #the key to sort events into chronological order
        def event_sort_key(event):
            return (
                datetime.datetime.fromisoformat(event["time"]),
                event["name"],
            )
        for year in self.sessions[guild_id]:
            #sort by month
            self.sessions[guild_id][year] = dict(sorted(self.sessions[guild_id][year].items()))
            for month in self.sessions[guild_id][year]:
                #sort the month's events in chronological order
                sorted_list = []
                for item in sorted(self.sessions[guild_id][year][month], key=event_sort_key):
                    dt = datetime.datetime.fromisoformat(item["time"]).replace(tzinfo=datetime.timezone.utc)
                    sorted_list.append(item)
                self.sessions[guild_id][year][month] = sorted_list
        self.save()





    #writes to the log file a dictionary containing the event's details
    async def log_session(self, guild_id: str, event: dict):
        #get the year of the event
        year = event["time"][:4]
        #get the month of the event
        month = event["time"][5:7]
        #make sure the year exists in the log file
        if year not in self.sessions[guild_id]:
            self.sessions[guild_id][year] = {month: [event]}
        #make sure the month exists in the year
        elif month not in self.sessions[guild_id][year]:
            self.sessions[guild_id][year][month] = [event]
        #append the event to the year and month
        else:
            self.sessions[guild_id][year][month].append(event)
        #sort the events
        self.sort(guild_id)





    #verifies that this event still exists
    async def exists(self, guild_id: str, event: dict) -> bool:
        #update self.sessions
        with self.session_log.open("r") as file:
            self.sessions = json.load(file)
        #get the year of the event
        year = event["time"][:4]
        #get the month of the event
        month = event["time"][5:7]
        #if the event still exists in the log, return True
        if event in self.sessions[guild_id][year][month]:
            return True
        print(f"{title} no longer exists")
        return False





    #formats a datetime into a string
    def pretty_datetime_str(self, dt: datetime.datetime):
        if dt.year == datetime.datetime.now().year:
            return dt.strftime(r"%m/%d %I:%M %p")
        else:
            return dt.strftime(r"%m/%d/%y %I:%M %p")





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
        channel:
            The server's designated schedule channel.
            All messages related to scheduled events are sent in this channel
        guild:
            The server from which the schedule is being requested.
        year:
            Optional. A specific year that a schedule is being requested for.
        m:
            Optional. The member or user requesting the schedule.
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

            embeds = (Multi_Page_Embed_Message.embed_list_from_items(
                    schedule,
                    lambda t: f"{guild.name}'s {year} Schedule",
                    None,
                    lambda i: (
                        datetime.datetime.strptime(i, "%m").strftime("%B"),
                        "\n".join(f"[{self.pretty_datetime_str(datetime.datetime.fromisoformat(event['time']).replace(tzinfo=datetime.timezone.utc))} - {event['name']}]({channel.get_partial_message(event['msg_id']).jump_url})" for event in schedule[i]),
                        False
                    ),
                    m,
                    max_field_count = 12
                )
            )
            await Multi_Page_Embed_Message(embeds, m).send(channel)
        #post the schedule of all server events
        else:
            #stores lists of embeds per year
            years = []
            #create a list of embeds per year
            for year in schedule:
                #appends the list of embeds associated with this year to years
                years += (Multi_Page_Embed_Message.embed_list_from_items(
                        schedule[year],
                        lambda t: f"{guild.name}'s {year + ' ' if len(schedule) > 1 else ''}Schedule",
                        None,
                        lambda i: (
                            datetime.datetime.strptime(i, "%m").strftime("%B"),
                            "\n".join(f"[{self.pretty_datetime_str(datetime.datetime.fromisoformat(event['time']).replace(tzinfo=datetime.timezone.utc))} - {event['name']}]({channel.get_partial_message(event['msg_id']).jump_url})" for event in schedule[year][i]),
                            False
                        ),
                        m,
                        max_field_count = 12
                    )
                )
            #post the schedule
            await Multi_Page_Embed_Message(years, m).send(channel)





    #saves any writes to the log file
    def save(self):
        with self.session_log.open("w") as file:
            json.dump(self.sessions, file, indent=4)

bot_commands.add_command(Schedule_Command())
