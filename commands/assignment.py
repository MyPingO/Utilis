from cmd import Bot_Command, bot_commands
from random import choice
import json
from pathlib import Path
import discord
from utils import user_select_from_list
from core import client

solutions_path = Path("data/assignments/solutions")
assignments_path = Path("data/assignments/assignments.json")
commands = []  # class_name (211, 212)


def save_assignments():
    assignments_path.parent.mkdir(parents=True, exist_ok=True)
    assignment_dict = {}
    for i in commands:
        assignment_dict[i.name] = i.class_info
    with assignments_path.open("w") as file:
        json.dump(assignment_dict, file, indent=3)


class Assignment_Command(Bot_Command):

    short_help = "Shows a detailed explanation of the specified assignment including relevant links, hints and solutions."

    long_help = "Specify the assignment you want help with: $[class_number][assignment_number]\n**Sub-commands are as follows:**\n     $[class_number] add [assignment_number] [url] [title]\n     $[class-number] pending [assignment_number]\n     $[class_number] solution [assignment_number]\n"
    # **ADMINS ONLY:**\n     $[class_number] remove [assignment_number] [title_of_link]"

    def __init__(self, class_name, class_info):
        self.name = class_name  # example ($211 or $212)
        self.class_info = (
            class_info  # JSON part of the file that accesses the class_name
        )
        print(self.class_info)  # example of class_info

    # helper function to take a specific answer for reviewing pending links
    async def accept_deny_multiple(self, msg, assignment_num):
        # waits for a response from the command author and channel for 10 seconds
        try:
            response = await client.wait_for(
                "message",
                check=lambda m: m.author == msg.author and m.channel == msg.channel,
                timeout=10,
            )
            # if no response is given within 10 seconds
        except:
            await msg.channel.send("Error: You took too long to respond")
            return None

        # splits resposne into smaller parts divided by a space
        split_response = response.content.split(" ")
        """split_response[0] = accept/deny
           split_response[1:] = pending links to accept/deny """
        accept_or_deny = split_response[0]
        link_choice = split_response[1:]
        # if they dont type 'accept' or 'deny', ex: 'MyTurtlesFTW'
        if not (
            accept_or_deny.casefold() == "accept" or accept_or_deny.casefold() == "deny"
        ):
            await msg.channel.send("Error: You answered incorrectly!")
            return

        for i in link_choice:  # check if choice indices is a number
            if not i.isdigit():
                await msg.channel.send(f"{i} is not a valid number")
                return
        # checks to see if choice indices exist in queue
        for i in range(len(link_choice)):
            # converts link_choice (which is a string) to and int and then - 1 b/c french counting
            link_choice[i] = int(link_choice[i]) - 1
            if (
                link_choice[i]
                >= len(self.class_info["assignments"][assignment_num]["requested_urls"])
                or link_choice[i] < 0
            ):
                await msg.channel.send(
                    "Error: One or more of the links you want to edit doesn't exist in the queue!"
                )
                return
        # checks for duplicate numbers in response
        if len(link_choice) != len(set(link_choice)):
            await msg.channel.send("Error: You have entered duplicate numbers")
            return
        # sort the link choices in order and reverse the response due to how we remove pending urls
        link_choice.sort()
        link_choice.reverse()
        # if user wants to accept, append to the accepted urls list and remove from the pending list
        if accept_or_deny.casefold() == "accept":
            for i in link_choice:
                self.class_info["assignments"][assignment_num]["added_urls"].append(
                    self.class_info["assignments"][assignment_num]["requested_urls"][i]
                )
                self.class_info["assignments"][assignment_num]["requested_urls"].pop(i)
            save_assignments()
            await msg.channel.send("Successfully added links to Accepted URL's!")
            return
        # if user wants to deny, remove from the pending list
        if accept_or_deny.casefold() == "deny":
            for i in link_choice:
                self.class_info["assignments"][assignment_num]["requested_urls"].pop(i)
            save_assignments()
            await msg.channel.send("Successfully removed links from the queue!")
            return

    async def run(self, msg: discord.Message, args: str):
        # chooses random color for embed messages
        color = [
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
        # choice() is from random library
        randomColor = choice(color)
        # if user types [class_name] and thats it
        if not args:
            # call long_help command for this command
            await bot_commands.call("help", msg, self.name)
            return

        if (
            args in self.class_info["assignments"]
        ):  # to print embed message of the specified assignment
            assignment = self.class_info["assignments"][args]  # JSON File
            print(len(assignment["description"]))
            print(assignment["title"])
            # description is pulled from the JSON File
            description = discord.Embed(
                title=assignment["title"],
                url=assignment["url"],
                description=assignment["description"],
                color=randomColor,
            )
            # extra embed stuff
            description.add_field(
                name=assignment["name"],
                value=f"Click [here]({self.class_info['website']}) to go to professor {self.class_info['professor']}'s site.",
                inline=False,
            )
            # extra embed stuff
            description.set_footer(
                text="If you still need help with this assignmnet after reading this embed message, please don't hesitate to ask!"
            )
            await msg.channel.send(embed=description)
            urls = ""
            # goes through each added url and then displays it in a seperate embed message
            for url in assignment["added_urls"]:
                urls += f"[{url['title']}]({url['url']})\n"
            # if there are no urls
            if not urls:
                return
            else:
                added_urls_list = discord.Embed(
                    title="Added Urls", description=urls, color=randomColor
                )
                await msg.channel.send(embed=added_urls_list)
        # this shouldn't be in here but wtvr
        elif args == "test":
            print(choice(color))
            embed = discord.Embed(
                title="Test Song",
                url="https://www.youtube.com/watch?v=KmI2WhkDQqg",
                description="[This is a cool song](https://www.youtube.com/watch?v=KmI2WhkDQqg)",
                color=choice(color),
            )
            embed.set_footer(text="This song is cool")
            await msg.channel.send(embed=embed)
        # this will spam a chat, also not sure why this is here
        elif args == "echo":
            await msg.channel.send("$assignment echo")
        # adding relevant urls to specified assignments
        elif args.casefold().startswith("add "):
            # splits the command string into parts divided by a space
            split_args = args.split(" ")
            print(len(split_args))
            if len(split_args) < 4:
                await msg.channel.send(
                    "Error: Please fill out the command correctly! Type $[class_name] to learn how to use commands"
                )
                return
            if split_args[1] not in self.class_info["assignments"]:
                await msg.channel.send(
                    "The assignment you are trying to edit does not exist, please check the assignment you want to edit actually exists"
                )
                return
            """split_args[0] = add
               split_args[1] = assignment#
               split_args[2] = link.com
               split_args[3] = title"""
            assignment_num = split_args[1]
            url_add = split_args[2]
            # check if url is a valid url i.e starts with https://
            if not url_add.startswith("http"):
                await msg.channel.send(
                    "Please enter a proper link. Example: https://www.example.com **or** https://example.com"
                )
                return
            title_add = " ".join(split_args[3:])

            # checks for duplicate urls in queue
            for i in self.class_info["assignments"][assignment_num]["requested_urls"]:
                if url_add == i["url"]:
                    await msg.channel.send(
                        "The link you are trying to add is already in the queue, please wait for a mod to review it"
                    )
                    return
                # checks for duplicate titles in queue
                elif title_add == i["title"]:
                    await msg.channel.send(
                        "The title you are trying to set is already used for another link, please use another title."
                    )
                    return
            # checks for duplicate links already added
            for i in self.class_info["assignments"][assignment_num]["added_urls"]:
                if url_add == i["url"]:
                    await msg.channel.send(
                        f"The link you are trying to add has already been added to the title: \"{i['title']}\""
                    )
                    return
                # checks for duplicate titles already added
                elif title_add == i["title"]:
                    await msg.channel.send(
                        "The title you are trying to set is already used for another link, please use another title."
                    )
                    return
            # This is what will be added to queue and what will be accepted/denied
            new_add_assignment = {
                "title": title_add,
                "url": url_add,
                "user": msg.author.id,
            }
            # no need for queue if admin tries to add something
            if msg.author.guild_permissions.administrator:
                self.class_info["assignments"][assignment_num]["added_urls"].append(
                    new_add_assignment
                )
                await msg.channel.send(
                    "Since you are an admin, this got added to Added URLs right away"
                )
                save_assignments()
                return
            # adds to queue
            self.class_info["assignments"][assignment_num]["requested_urls"].append(
                new_add_assignment
            )
            # saves JSON file so queue doesnt get erased if bot crashes
            save_assignments()
            await msg.channel.send(
                "Your request to add this link will be reviewed by an admin."
            )
        # to check whats in queue for specified class (needs to be admin)
        elif (
            args.casefold().startswith("pending ")
            and msg.author.guild_permissions.administrator
        ):

            assignment_num = args[len("pending") :].strip()
            # checks if assignment number exists
            if assignment_num not in self.class_info["assignments"]:
                await msg.channel.send(
                    "The assignment you are trying to edit does not exist, please check the assignment you want to edit actually exists"
                )
                return
            # creates list of everything that pending to print/use later
            list_requested_urls = self.class_info["assignments"][assignment_num][
                "requested_urls"
            ]
            # if nothing is pending
            if not list_requested_urls:
                await msg.channel.send("There is nothing pending for this assignment")
                return

            pending_list = ""
            url = 0
            # for loop goes through requested url to print it in embed message
            for i in self.class_info["assignments"][assignment_num]["requested_urls"]:
                url += 1
                pending_list += f"**{url}**\n[{i['title']}]({i['url']})\n"
            pending_links = discord.Embed(
                title="Requested URLs", description=pending_list, color=randomColor
            )
            await msg.channel.send(embed=pending_links)

            # waits for user to accept/deny a link(s)
            await self.accept_deny_multiple(msg, assignment_num)

        # to remove a link from the accepted links list
        elif args.casefold().startswith("remove "):
            # must have admin permissions
            if msg.author.guild_permissions.administrator:
                split_args = args.split(" ")

                """split_args[0] = remove
                split_args[1] = assignment#
                split_args[2] = title """

                assignment_num = split_args[1]
                # combine title if there are spaces
                title = " ".join(split_args[2:])
                # loops through list
                for i in self.class_info["assignments"][assignment_num]["added_urls"]:
                    # if it finds a matching title
                    if title == i["title"]:
                        # remove it form the list
                        self.class_info["assignments"][assignment_num][
                            "added_urls"
                        ].remove(i)
                        # confirm that a match was found and was deleted
                        await msg.channel.send(
                            f"Removed **{i['title']}** from Added URLs"
                        )
                        # save JSON File
                        save_assignments()
                        return
                await msg.channel.send(
                    f" **{title}** not found in Added URLs. This feature is case sensitive. Make sure you typed the title exactly as it is"
                )
                return
            # if a non-admin tries to run the command
            else:
                await msg.channel.send(
                    "You need administrator permissions to use this command"
                )
                return

        # $211 solution 1
        elif args.casefold().startswith("solution "):
            # here using (" ", 1) to only split once at a " ".
            split_args = args.split(" ", 1)
            """split_args[0] = solution
               split_args[1] = assignment# """
            # make solution_choice = assignment# i.e everything after "solution "
            solution_choice = split_args[1]
            # checks if assignment# is a number
            if not solution_choice.isdigit():
                await msg.channel.send(
                    "Error: You did not enter a valid assignment number for the solution you want"
                )
                return
            # check if the assignment solution exists in $class_name folder using "pathway/self.name" (self.name = $211 or $212 command)
            for i in (solutions_path / self.name).iterdir():
                if i.name.split(".")[0] == solution_choice:
                    with i.open("r") as assignment_solution:
                        await msg.channel.send(
                            file=discord.File(
                                assignment_solution,
                                f"Assignment {i.name.split('.')[0]} Solution",
                            )
                        )
                        return
            # if the solution requested is not found in folder
            await msg.channel.send(
                "The solution to the assignment you are looking for either does not exist or hasn't been added yet. If this is the case, ping a mod!"
            )
            return

        # $211 solution 1

        # if they try to view an assignment that doesnt exist
        else:
            await msg.channel.send(
                "Either you typed in a command wrong, or the assignment you are looking for does not exist or has not yet been added to the bot. If this is the case, ping a mod.\nYou can use $[class_name] to get help with how to use this command. Example $211 **or** $212"
            )


# creates the command for every class (211 or 212) thats in the JSON File
if not assignments_path.exists():
    save_assignments()
else:

    with assignments_path.open() as file:
        assignments = json.load(file)
    # for every class name / key (211 or 212) in the JSON file
    for class_name in assignments:
        # add command to commands list, commands list is from cmd.py
        commands.append(Assignment_Command(class_name, assignments[class_name]))
