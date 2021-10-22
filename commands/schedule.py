from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from utils import find, get
from utils.paged_message import Paged_Message
from utils import parse, std_embed, errors
from typing import Optional, Union
from datetime import datetime, date, timedelta, timezone

import discord
import asyncio
import db

class Schedule_Command(Bot_Command):
    name = "schedule"

    short_help = "Posts the server's schedule or schedules an event."

    long_help = f"""Schedule an event for the specified date and time.
    __Usage:__
    **schedule** [*year*]
    **schedule event** *title*
    **schedule edit** *title*
    **schedule remove** *title*
        -events can only be edited or removed by admins or the person who created it

    Format date and time as *`MM/DD/YY HH:MM AM/PM`*
    """

    category = Bot_Command_Category.COMMUNITY

    #create a table in the database to store events if it doesn't exist
    def __init__(self):
        db.execute("""CREATE TABLE IF NOT EXISTS schedule (
                Server BIGINT,
                Title VARCHAR(100),
                Datetime DATETIME NOT NULL,
                MsgID BIGINT NOT NULL,
                ChannelID BIGINT NOT NULL,
                RoleID BIGINT NOT NULL,
                AuthorID BIGINT NOT NULL,
                PRIMARY KEY (Server, Title)
            );"""
        )

    async def run(self, msg: discord.Message, args: str):
        #gets current server
        guild = msg.author.guild
        #gets current channel
        channel = msg.channel

        #if user doesn't include any arguments, post the server's schedule
        if not args:
            await self.post_schedule(channel, guild, m=msg.author)

        #if user requests the schedule for a specific year
        elif args.isdigit():
            if int(args) >= datetime.now().year:
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
                event = self.get_event(arg.strip(), guild.id)
                #if an event is found, remove it
                if event is not None:
                    #only the event creator or admins can remove events
                    if  msg.author.id == event[6] or msg.author.guild_permissions.administrator:
                        await self.remove(msg, event)
                    #an unauthorized user attempted to delete the event
                    else:
                        raise errors.ReportableError("**You do not have permission to remove this event.**")

            #post the updated schedule
            await self.post_schedule(channel, guild, m=msg.author)

        #scheduling a new event
        elif args.casefold().startswith("event"):
            embed = std_embed.get_input(title="NEW EVENT", author=msg.author)
            if not args[len("event"):].strip():
                raise errors.UserInputError("**An event title was not provided.**")
            #validate the title
            title = (self.validate(guild.id, title=args[len("event"):].strip()))[0]

            #prompt the user for an event date
            embed.description = f"**Please enter a date for `{title}`**"
            prompt = await channel.send(embed=embed)
            reply = await get.reply(msg.author, channel, prompt)
            date = (self.validate(guild.id, date=reply.content))[1]

            #prompt the user for an event time
            embed.description = f"**Please enter a time for `{title}`**"
            prompt = await channel.send(embed=embed)
            reply = await get.reply(msg.author, channel, prompt)
            time = (self.validate(guild.id, time=reply.content))[2]

            #combine the date and time to get a datetime object
            dt = datetime.combine(date, time)

            #make sure the time is in the future
            if dt.astimezone(timezone.utc) < datetime.now().astimezone(timezone.utc):
                raise errors.InvalidInputError("**This time has already passed.**")

            #creates a role to ping participants for this event
            role = await guild.create_role(name=title)
            #send a message asking for members to react to join the event
            message = await std_embed.send_info(
                channel,
                title=role.name,
                description=f"React to this message to be pinged for {role.mention} on **<t:{int(dt.timestamp())}:F>**!"
            )

            #add the event to the database table
            operation = "INSERT INTO schedule VALUES (%s, %s, %s, %s, %s, %s, %s);"
            params = (guild.id, title, dt, message.id, message.channel.id, role.id, msg.author.id)
            db.execute(operation, params)

            await self.schedule_event(message, title, dt, role)

        #edits a specified event
        elif args.casefold().startswith("edit"):
            #try to find a scheduled event with the specified name
            title = args[len("edit"):].strip()
            if not title:
                raise errors.ParseError("**An event title was not provided.**")

            event = self.get_event(title, guild.id)
            if event:
                print(f"Editing {event[1]}")
                if msg.author.id == event[6] or msg.author.guild_permissions.administrator:
                    await self.edit_event(msg.author, event, channel, 180)
                else:
                    raise errors.ReportableError("**You do not have permission to edit this event.**")
            else:
                raise errors.InvalidInputError(f"**An event with the title `{title}` could not be found**")

        #catch invalid event types or incorrect command usage
        else:
            raise errors.InvalidInputError("**Please enter a valid event type**")





    #returns the dictionary of the event details if it exists
    def get_event(self, name: str, guild_id):
        operation = "SELECT * FROM schedule WHERE Title = %s AND Server = %s;"
        params = (name, guild_id)
        item = db.read_execute(operation, params)
        if len(item) == 0:
            return None
        return item[0]






    #validates the passed event fields
    def validate(
        self,
        guild_id: Optional[int] = None,
        title: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None
    ):
        """
        Parameters
        ----------

        guild_id: int
        An int representing the id of the guild. Required if title is not None.

        title: Optional[str]
        The title of the event. Required if date and time are None.

        date: Optional[str]
        The date of the event. Required if title and time are None.

        time: Optional[str]
        The time of the event. Reqiuired if title and date are None.
        """

        #list to return, respectively storing title, date, time and an error message if any
        ret = [None] * 3

        #make sure the event has a valid title
        if title is not None:
            #check that the title is unique
            if self.get_event(title, guild_id) is not None:
                raise errors.InvalidInputError("**An event with this title already exists. **")
            #make sure the title is within a role name's max length
            elif len(title) > 100:
                raise errors.InvalidInputError("**Title must be 100 characters or fewer in length. **")
            #if title passes all checks, set ret[0] = to title
            else:
                ret[0] = title

        #checks that user entered a properly formatted date
        if date is not None:
            try:
                date = parse.str_to_date(date)
                if date < date.today():
                    raise errors.InvalidInputError("**This date has already passed. **")
                ret[1] = date
            except ValueError as ve:
                print(ve)
                raise errors.ParseError("**Invalid event date. Dates must follow the format `MM/DD/YY`. **")

        #checks that user entered a properly formatted time
        if time is not None:
            try:
                time = parse.str_to_time(time)
                ret[2] = time
            except ValueError as ve:
                print(ve)
                raise errors.ParseError("**Invalid event time. Times must follow the format `HH:MM AM/PM`. **")

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





    async def schedule_event(
        self,
        msg: discord.Message,
        title: str,
        dt: datetime,
        role: discord.Role
    ):
        """Schedules an event

        Parameters
        ----------
        msg: discord.Message
        The message requesting event participants.

        title: str
        The name of the event

        dt: datetime
        A datetime of when the event takes place.

        role: discord.Role
        The role assigned to this event
        """

        guild = msg.channel.guild
        msg = await msg.channel.fetch_message(msg.id)

        #send reminder message if event is at least 5 minutes in the future
        reminder = discord.Embed(color=discord.Color.blue())
        m1 = None
        if dt.astimezone(timezone.utc) - timedelta(minutes=5) > datetime.now().astimezone(timezone.utc):
            await discord.utils.sleep_until(dt.astimezone() - timedelta(minutes=5))

            #verify this event still exists
            event = self.get_event(title, guild.id)
            if event is None or event[1] != title or event[2] != dt:
                return

            #assign all participants the designated role for this event
            await self.react_for_role(msg, role)

            #sends an embed reminder for the event
            reminder.add_field(
                name="REMINDER",
                value=f"""**{title.upper()}** will be starting soon!
                You can still join before it starts by reacting to [this message]({msg.jump_url})!""",
                inline=False
            )
            #TODO query for server set schedule channel, if None, send to the same channel as message
            m1 = await msg.channel.send(f"{role.mention}", embed=reminder)

        #wait for event to start
        await discord.utils.sleep_until(dt.astimezone())

        event = self.get_event(title, guild.id)
        if event is None or event[1] != title or event[2] != dt:
            return

        #check for any last minute participants
        await self.react_for_role(msg, role)

        #send a final reminder that the event has started
        reminder.clear_fields()
        reminder.add_field(
            name=f"{title.upper()}",
            value="THE EVENT HAS STARTED! JOIN NOW!!",
            inline=False
        )
        #TODO query for server set schedule channel, if None, send to the same channel as message
        m2 = await msg.channel.send(f"{role.mention}", embed=reminder)

        #leave event posted for 5 minutes before deleting it
        await asyncio.sleep(300)

        event = self.get_event(title, guild.id)
        try:
            #delete the event from the table
            await self.remove(m2, event)
            #removes the deleted role mention from the reminder messages
            if m1:
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
        event: Optional[tuple] = None,
        remove_all: bool = False
    ):
        """Deletes the passed event from the database table as
        well as its associated role and reaction message.

        Parameters
        ----------
        msg: discord.Message
        A reference message to get the channel, guild and member who requested the
        event removal.

        event: Optional[tuple]
        A tuple of the event being removed. Required if remove_all is False.

        remove_all: bool
        A boolean flag to indicate whether or not to clear the guild's schedule.
        """
        #get the guild's id and the channel the message was sent in
        guild_id = msg.guild.id
        channel = msg.channel

        #admins can clear the schedule
        if remove_all and msg.author.guild_permissions.administrator:
            #get a list of tuples representing all the scheduled events in this server
            operation = "SELECT * FROM schedule WHERE Server = %s;"
            params = (guild_id,)
            events = db.read_execute(operation, params)
            for event in events:
                await self.remove(msg, event)
        #removes the specified events from the schedule
        elif event is not None:
            #delete the event from the database
            operation = "DELETE FROM schedule WHERE Server = %s AND Title = %s;"
            params = (guild_id, event[1])
            db.execute(operation, params)
            #delete the role assigned to this event
            role = msg.guild.get_role(event[5])
            if role is not None:
                await role.delete()

            #try to delete the message asking for reactions to join this event
            try:
                m = await channel.fetch_message(event[3])
                await m.delete()
            except discord.NotFound as dnf:
                print(dnf)
                pass





    #allow event creator to edit edit their scheduled event
    async def edit_event(
            self,
            author: discord.Member,
            event: tuple,
            channel: discord.TextChannel,
            timeout: int = 90
        ):
        """
        Parameters
        ----------
        author: discord.Member
        The member requesting the edit.

        event: tuple
        The tuple containing the information of the event being edited.

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

        title = event[1]
        dt = event[2]
        old_dt = dt
        description=(
            f"Editing `{title}`. Which fields would you like to edit?\n"
            f"{fields['title_emoji']} __`Title`:__ {title}\n"
            f"{fields['date_emoji']} __`Date`:__ <t:{int(dt.timestamp())}:D>\n"
            f"{fields['time_emoji']} __`Time`:__ <t:{int(dt.timestamp())}:t>\n\n"
            "React with ✅ to confirm your choices, ❌ to cancel."
        )
        guild_id = channel.guild.id

        field_request = await std_embed.send_input(
            channel,
            title="EDIT EVENT",
            description=description,
            author=author
        )
        for emoji in fields:
            await field_request.add_reaction(fields[emoji])

        #cancel edit request
        if not await get.confirmation(author, channel, msg=field_request, timeout=timeout, error_message=f"Error: You took too long to respond. **Cancelled edits to `{title}`**", timeout_returns_false=False):
            print(f"Cancelled edits to {title}")
            await field_request.clear_reactions()
            await std_embed.send_success(
                channel,
                title="EDIT EVENT",
                description=f"**Cancelled edits to `{title}`**",
                author=author
            )
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
            raise errors.InvalidInputError("**No fields were selected. Cancelling edit request.**")

        edit_desc = f"**Successfully made edits to `{title}`.\n__Changed:__**"

        if fields['title_emoji'] in confirmed_fields:
            msg = await std_embed.send_input(
                channel,
                title="EDIT EVENT",
                description=f"**Please enter a new title for `{title}`**\n__Current title:__ `{title}`",
                author=author
            )

            #prompt user for a new title
            title = (await get.reply(author, channel, msg)).content
            try:
                title = (self.validate(guild_id, title=title))[0]
            except (errors.InvalidInputError, errors.ParseError) as e:
                raise errors.UserInputError(f"{e}\n**Cancelling all edits to:** {event[1]}")
            edit_desc += f"\n{fields['title_emoji']} `Title`: `{event[1]}` -> `{title}`"

        if fields['date_emoji'] in confirmed_fields:
            msg = await std_embed.send_input(
                channel,
                title="EDIT EVENT",
                description=f"**Please enter a new date for `{title}`**\n__Current date:__ <t:{int(old_dt.timestamp())}:D>",
                author=author
            )

            #prompt user for a new date
            date = (await get.reply(author, channel, msg)).content
            try:
                date = (self.validate(date=date))[1]
            except (errors.InvalidInputError, errors.ParseError) as e:
                raise errors.UserInputError(f"{e}\n**Cancelling all edits to:** {title}")

            #replace the old date with the new date
            dt = dt.replace(year=date.year, month=date.month, day=date.day)
            edit_desc += f"\n{fields['date_emoji']} `Date`: <t:{int(old_dt.timestamp())}:D> -> <t:{int(dt.timestamp())}:D>"

        if fields['time_emoji'] in confirmed_fields:
            msg = await std_embed.send_input(
                channel,
                title="EDIT EVENT",
                description=f"**Please enter a new time for `{title}`**\n__Current time:__ <t:{int(old_dt.timestamp())}:t>",
                author=author
            )

            #prompt user for a new time
            time = (await get.reply(author, channel, msg)).content
            try:
                time = (self.validate(time=time))[2]
            except (errors.InvalidInputError, errors.ParseError) as e:
                raise errors.UserInputError(f"{e}\n**Cancelling all edits to:** {title}")

            #make sure new time is in the future
            dt = dt.replace(hour=time.hour, minute=time.minute)
            if dt.astimezone(timezone.utc) < datetime.now().astimezone(timezone.utc):
                raise errors.InvalidInputError(f"This time has already passed. Cancelling all edits to {title}")
            edit_desc += f"\n{fields['time_emoji']} `Time`: <t:{int(old_dt.timestamp())}:t> -> <t:{int(dt.timestamp())}:t>"

        #update the role for this event
        role = channel.guild.get_role(event[5])
        if role is None:
            role = await channel.guild.create_role(name=title)
        else:
            await role.edit(name=title)

        #edit the reaction message, if not found, create a new one
        try:
            msg_channel = channel.guild.get_channel(event[4])
            message = await msg_channel.fetch_message(event[3])
            e = message.embeds[0]
            e.title = title
            e.description = f"React to this message to be pinged for {role.mention} on **<t:{int(dt.timestamp())}:F>**!"
            await message.edit(embed=e)
        except discord.NotFound as dnf:
            print(dnf)
            #send a message asking for members to react to join the event
            message = await std_embed.send_info(
                channel,
                title=title,
                description=f"React to this message to be pinged for {role.mention} on **<t:{int(dt.timestamp())}:F>**!"
            )

        #replace the old event
        operation = "UPDATE schedule SET Title=%s, Datetime=%s, MsgID=%s, ChannelID=%s, RoleID=%s WHERE Server=%s AND Title=%s;"
        params = (title, dt, message.id, message.channel.id, role.id, guild_id, event[1])
        db.execute(operation, params)

        await std_embed.send_success(channel, title="EDIT EVENT", description=edit_desc + f"\n\nJoin [here]({message.jump_url})")
        #schedule a new event with the edited information
        await self.schedule_event(message, title, dt, role)





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
        #check if this guild has a schedule
        operation = "SELECT * FROM schedule WHERE Server = %s;"
        params = (guild.id,)
        #if there are no events scheduled in this server
        async def no_events():
            await std_embed.send_error(
                channel,
                title = f"{guild.name}'s {year+' ' if year else ''}Schedule",
                description=f"**There are no events scheduled{' for '+year if year else ''}**"
            )
        if not db.read_execute(operation, params):
            await no_events()
            return

        #if a year is specified check if it has events scheduled, otherwise get a tuple of all years with events scheduled
        if year is not None:
            operation = "SELECT DISTINCT YEAR(Datetime) FROM schedule WHERE Server = %s AND YEAR(Datetime) = %s;"
            params = (guild.id, year)
            years = db.read_execute(operation, params)
            if not years:
                await no_events()
                return
            years = years[0]
        else:
            operation = "SELECT DISTINCT YEAR(Datetime) FROM schedule WHERE Server = %s;"
            params = (guild.id,)
            years = [item[0] for item in db.read_execute(operation, params)]


        embeds = []
        def field_generator(item):
            #get a list of tuples representing events in this month, ordered by datetime
            operation = "SELECT * FROM schedule WHERE Server = %s AND YEAR(Datetime) = %s AND MONTH(Datetime) = %s ORDER BY Datetime;"
            params = (guild.id, year, item)
            l = db.read_execute(operation, params)
            name = datetime.strptime(str(item), '%m').strftime('%B')
            value = "\n".join(f"[<t:{int(event[2].timestamp())}> - {event[1]}]"
                f"({channel.get_partial_message(event[3]).jump_url})"
                for event in l
            )
            return (name, value, False)
        #create a list of embeds per year
        for year in years:
            #get a unique list of months with events in ascending order
            operation = "SELECT DISTINCT MONTH(Datetime) FROM schedule WHERE Server = %s AND YEAR(Datetime) = %s ORDER BY MONTH(Datetime) ASC;"
            params = (guild.id, year)
            months = [item[0] for item in db.read_execute(operation, params)]
            embeds += (Paged_Message.embed_list_from_items(
                    months,
                    lambda t: f"{guild.name}'s {str(year) + ' ' if len(years) > 1 else ''}Schedule",
                    None,
                    field_generator,
                    m,
                    max_field_count = 12,
                    color=discord.Color.blue()
                )
            )
        #post the schedule
        await Paged_Message(embeds, m).send(channel)





bot_commands.add_command(Schedule_Command())
