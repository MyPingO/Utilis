from cmd import Bot_Command, bot_commands
from pathlib import Path
from utils import get_member, get_role
from random import choice

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
    `Type`  The type of event being scheduled
    `Time`  Formatted as **MM/DD/YY HH:MM AM/PM**
    `Title` Descriptive name for the event. Will also be the name of the role to be pinged

    If all arguments are omitted, the schedule for this server is posted.
    To schedule an event, specify `session` and a date and time for the event.
    All participants will be pinged by a designated role 5 minutes in advance 
    as a reminder, as well as when the event starts.
    """

    colors = [
        0x000000,  # black
        0x00FF00,  # lime/bright green
        0xFF0000,  # red
        0x38E31F,  # green
        0xA434EB,  # purple
        0x0082FF,  # blue
        0xE08200,  # orange/light brown
        0xFF7DFF,  # pink
        0xFEFFFF,  # white
    ]

    restricted = ["all", "here", "everyone"]

    async def run(self, msg: discord.Message, args: str):
        with self.session_log.open("r") as file:
            self.sessions = json.load(file)
        #gets current server
        guild = msg.author.guild

        #gets a string of the server's id
        id_num = str(guild.id)

        #gets current channel
        channel = msg.channel

        #designates channel for bot messages/announcements
        #announcement = guild.get_channel()

        #if this server is not in the log file, add it
        if id_num not in self.sessions:
            self.sessions[id_num] = {}

        #if user doesn't include any arguments, post the server's schedule
        if not args:
            await self.post_schedule(channel, guild)
            return

        #admins can remove scheduled events
        if args.lower().startswith("remove"):
            if msg.author.guild_permissions.administrator:
                #clears all server events from the schedule
                if args[6:].lower().strip().startswith("all"):
                    for event in self.sessions[id_num].copy():
                        #delete the message asking for reactions to join this event
                        try:
                            m = await channel.fetch_message(list(self.sessions[id_num][event].values())[0])
                            await m.delete()
                        except discord.NotFound:
                            pass

                        #delete the role assigned to this event
                        role = await get_role(channel, event)
                        if role is not None:
                            await role.delete()
                        self.sessions[id_num].pop(event)
                        self.save()
                #removes the specified events from the schedule
                else:
                    #get any comma separated event titles
                    event_args = args[6:].strip().split(", ")
                    for event in event_args:
                        #delete the message asking for reactions to join this event
                        try:
                            m = await channel.fetch_message(list(self.sessions[id_num][event.lower()].values())[0])
                            await m.delete()
                        except discord.NotFound as nf:
                            print(nf)
                            continue
                        except KeyError:
                            print(f"One or more events trying to be removed could not be found")
                            continue

                        try:
                            #delete the role assigned to this event
                            role = await get_role(channel, event)
                            if role is not None:
                                await role.delete()
                        
                            self.sessions[id_num].pop(event.lower())
                            self.save()
                        except KeyError:
                            print(f"One or more events trying to be removed could not be found")

                #post the updated schedule to the channel
                await self.post_schedule(channel, guild)
            else:
                await channel.send("You do not have permission to remove events.")

        elif args.lower().startswith("session"):
            parsed_args = args.strip().split(" ", 4)
            #checks that user entered a properly formatted date/time
            try:
                time = parsed_args[1] + " " + parsed_args[2] + " " + parsed_args[3]
                session = datetime.datetime.strptime(time, '%m/%d/%y %I:%M %p')
                session = session.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=-4)))
            except (ValueError, IndexError):
                print("The date/time was not formatted properly. Please follow the format `MM/DD/YY HH:MM AM/PM`.")
                await channel.send("The date/time was not formatted properly. Please follow the format `MM/DD/YY HH:MM AM/PM`.")
                return

            #make sure the event has a title
            try:
                title = parsed_args[4].strip()
                #checks if the title is the same as a role that already exists
                for role in guild.roles:
                    if title.lower() == role.name.lower():
                        await channel.send("This title is restricted. Please choose a different one.")
                        return
                for mention in self.restricted:
                    if title.lower() == mention:
                        await channel.send("This title is restricted. Please choose a different one.")
                        return

            except IndexError:
                print("No title was provided")
                await channel.send("No title was provided")
                return

            #verify the user enters a future date/time
            if session < datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=-4))):
                print("This date/time has already passed. Please enter a valid date/time.")
                await channel.send("This date/time has already passed. Please enter a valid date/time")
                return

            #schedule the event
            #if an event already has the title trying to be added, return
            if title.lower() in self.sessions[id_num]:
                print(f"There is already an event scheduled called `{title}`")
                await channel.send(f"There is already an event scheduled called `{title}`")
                return
            message = await channel.send(f"React to this message to be pinged for `{title}` at `{time}`!")
            await self.log_session(id_num, time, title.lower(), message.id)

            #creates a role to ping participants for this event
            role = await guild.create_role(name=title)

            #sleep until 5 minutes before the event to notify participants ahead of time
            await discord.utils.sleep_until(session - datetime.timedelta(minutes=5))

            #checks that the event still exists
            with self.session_log.open("r") as file:
                self.sessions = json.load(file)
            if not await self.verify(id_num, time, title.lower()):
               return
            
            #get the message's reactions
            for reaction in (await channel.fetch_message(message.id)).reactions:
                #make a list of the Users who reacted to the message
                users = await reaction.users().flatten()

                #assigns the role to all users who reacted
                for user in users:
                    #convert User object into Member
                    member = channel.guild.get_member(user.id)
                    #ignore any bots that react
                    if member.bot:
                        continue
                    #assign the member the role if they don't already have it
                    if role not in member.roles:
                        await member.add_roles(role)

            #creates an embed reminder
            reminder = discord.Embed(color=choice(self.colors))
            reminder.add_field(
                name="REMINDER",
                value=f"{title.upper()} will be starting soon!",
                inline=False
            )
            m1 = await channel.send(f"{role.mention}", embed=reminder)

            #send a final message notifying participants that the event has started
            await discord.utils.sleep_until(session)
            reminder.clear_fields()
            reminder.add_field(
                name=f"{title.upper()}",
                value="THE EVENT HAS STARTED! JOIN NOW!!",
                inline=False
            )
            m2 = await channel.send(f"{role.mention}", embed=reminder)

            #allow participants 10 minutes to join before remove the pingable role from them
            await asyncio.sleep(600)
            for m in role.members:
                await m.remove_roles(role)
            #delete the role assigned to this event
            await role.delete()
            #removes the deleted role mention from the reminder messages
            await m1.edit(content=None)
            await m2.edit(content=None)
                       
        #for admins to schedule announcements - TO BE IMPLEMENTED
        elif args.lower().startswith("announcement"):
            if msg.author.guild_permissions.administrator:
                pass
                #await channel.send("@everyone")
            pass 
        
        else:
            await channel.send("Please enter a valid event type.")





    #writes to the log file the server, the date of the event and its title
    async def log_session(self, guild: str, date: str, title: str, msg_id: int):
        #add the event to this server's schedule
        self.sessions[guild][title] = {date: msg_id}
        self.save()





    #verifies that this event is still scheduled
    async def verify(self, guild: str, date: str, title: str) -> bool:
        #if the event still exists in the log, return True
        if title in self.sessions[guild]:
            if date in self.sessions[guild][title]:
                return True
        print(f"{title} no longer exists")
        return False





    async def post_schedule(self, channel: discord.channel.TextChannel, guild: discord.Guild):
        schedule = self.sessions[str(guild.id)]
        #embed of this server's scheduled events
        event = discord.Embed(
            title=f"{guild.name}'s Schedule",
            color=choice(self.colors)
        )
        months = {}
        #sort all events in order by month
        for i in schedule:
            #get the month number to sort the dict in order
            month = datetime.datetime.strptime(list(schedule[i].keys())[0], '%m/%d/%y %I:%M %p')
            month = month.strftime('%m')
            if month not in months:
                months[month] = {i: schedule[i]}
            else:
                months[month][i] = schedule[i]

        #add a new field to the embed for each month
        for month in months:
            m = datetime.datetime.strptime(month, '%m')
            #concatenate the list of events for this month
            value = ""
            #link the React message assigned to each event
            for k, v in months[month].items():
                try:
                    msg = await channel.fetch_message(list(v.values())[0])
                    value += f"[{list(v.keys())[0]} - {k}]({msg.jump_url})\n"
                except discord.NotFound:
                    pass
            if len(value):
                event.add_field(
                    name=m.strftime('%B'),
                    value=value,
                    inline=False
                )
        #if this server has no events scheduled
        if len(event.fields) == 0:
            event.description = "**There are no scheduled events for this server**"
        await channel.send(embed=event)





    #saves any writes to the log file
    def save(self):
        with self.session_log.open("w") as file:
            json.dump(self.sessions, file, indent=4)

bot_commands.add_command(Schedule_Command())
