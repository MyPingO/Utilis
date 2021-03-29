from cmd import Bot_Command

import discord


class Mute_Command(Bot_Command):
    name = "mute"

    default_time = "10 minutes"

    short_help = "Mutes user for specified time"

    long_help = f"""Mutes the specified user for specified time. Default time is {default_time}. 
    Arguments:
    `User`
    `Time (numerical value)`
    `Time unit (s, m, h, d)`
    """

    async def run(self, msg: discord.Message, args: str):
        #only admins are able to use this command
        if msg.author.guild_permissions.administrator:        
            #checks that user entered arguments for the command
            if args:
                #split arguments into an array
                parsed_args = args.split(" ")                
                if len(parsed_args) > 2:
                    print("Too many arguments were passed") 
                    await msg.channel.send("Too many arguments were passed. Type '!help mute' for command info.")
                    return

                #current server
                guild = msg.author.guild
                
                #find member in this server
                try:
                    #member id
                    member = guild.get_member(int(parsed_args[0][3:-1]))
                except:
                    print(f"User @{parsed_args[0]} could not be found")
                    await msg.channel.send(f"User @{parsed_args[0]} could not be found")
                    return

                #creates 'mute' role if it doesn't already exist in this server
                if discord.utils.get(guild.roles, name="mute") is None:
                    #disables messaging, reaction and voice channel permissions
                    perms = discord.Permissions(send_messages=False, connect=False, speak=False, add_reactions=False)
                    await guild.create_role(name="mute", hoist=True, permissions=perms)
                mute = discord.utils.get(guild.roles, name="mute")
                
                #checks if user and time are specified
                if len(parsed_args) == 2:
                    #assigns member the role
                    await member.add_roles(mute)
                    print(f"Muted @{member} for {parsed_args[1]}")
                    await msg.channel.send(f"Muted <@!{member.id}> for {parsed_args[1]}")
                #if admin only specified a user, assign them the role for the default time
                else:
                    await member.add_roles(mute)
                    print(f"Muted @{member} for {self.default_time}")
                    await msg.channel.send(f"Muted <@!{member.id}> for {self.default_time}")
            #if user didnt enter any arguments
            else:
                print("Please specify a user and (optional) duration")
                await msg.channel.send("Please specify a user and (optional) duration")
        #unauthorized user tried to use this command
        else:
            print("You do not have permission to use this command.")
            await msg.channel.send("You do not have permission to use this command.")

command = Mute_Command()
