import json
import re
import discord
from cmd import Bot_Command, bot_commands

from discord import guild
from commands.help import help_cmd
from random import choice
from pathlib import Path
from random import choice
from utils import user_select_from_list, wait_for_reply, format_max_utf16_len_string
from core import client
from typing import Optional

async def link_check(link, msg):
    if (link.casefold().startswith("http://") and len(link) > len("http://")) or (
        link.casefold().startswith("https://") and len(link) > len("https://")):
        return link
    else: 
        await msg.channel.send("Please enter a proper link. Example: http://example.com **or** https://example.com\nYou can also type **stop** to remove all changes and stop the command.")
        link = await wait_for_reply(msg.author, msg.channel)
        if link == "stop":
            await msg.channel.send("Stopping command. No changes were made")
            return link
        else:
            return await link_check(link, msg)


class Random_Color:
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
    tempColor = -1

    def get_color(self):
        # choice() is from random library
        randomColor = choice(self.color)
        while self.tempColor == randomColor:
            randomColor = choice(self.color)
        self.tempColor = randomColor
        return randomColor


no_duplicate_random_color = Random_Color()


class Assignment_Command(Bot_Command):

    short_help = "Shows a detailed explanation of the specified assignment including relevant links, hints and solutions for the specified class."

    long_help = """Specify the assignment you want help with: $[class_number][assignment_number] Example: $211 1 **or** $212 3

    **Sub-commands:**
        $[class_number] assignments
        $[class_number] addurl [assignment_number] [url] [title]
        $[class_number] solution [assignment_number] **NOTE:** Solutions to assignments are only available after their due date!

    """

    admin_long_help = """**ADMINS ONLY:**
    $[class_number] add [assignment_number]
    $[class_number] edit [assignment_number]
    $[class-number] pending [assignment_number]
    $[class_number] removeurl [assignment_number] [title_of_link]"""

    def __init__(self, add_class, class_name, class_info, guild_id): #TODO: SEE IF NEEDED
        self.name = class_name  # example (211 or 212)
        # JSON part of the file that accesses the class_name
        self.class_info = class_info # all the info of the class
        self.add_class = add_class
        self.guild_id = guild_id #the guild_id of the specific discord server
        #print(self.class_info) <---- example of class_info

    def get_help(self, member: Optional[discord.Member], args: Optional[str]):
        if member is None or not member.guild_permissions.administrator:
            return self.long_help
        else:
            return self.long_help + "\n" + self.admin_long_help

    # helper function to take a specific answer for reviewing pending links
    async def approve_deny_multiple(self, msg, assignment_num):
        # waits for a response from the command author and channel for 10 seconds
        try:
            response = await client.wait_for(
                "message",
                check=lambda m: m.author == msg.author and m.channel == msg.channel,
                timeout=30,
            )
            # if no response is given within 10 seconds
        except:
            await msg.channel.send("Error: You took too long to respond")
            return None

        # splits resposne into smaller parts divided by a space
        response = re.split(r"[,，\s]\s*", response.content)

        """split_response[0] = approve/deny
           split_response[1:] = pending links to approve/deny """
        approve_or_deny = response[0]
        link_choice = response[1:]

        # if they dont type 'approve' or 'deny', ex:
        if not (
            approve_or_deny.casefold() == "approve"
            or approve_or_deny.casefold() == "deny"
        ):
            await msg.channel.send(
                "Error: You answered incorrectly! To approve or deny a link, type **approve** or **deny** followed by the number of the link you want to approve/deny\n Example: **approve 1** or **deny 3**. You can also approve/deny multiple links at once like this **approve 1 2 3** or **deny 4 5 6**."
            )
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
        # if user wants to approve, append to the Relevant Links list and remove from the pending list
        if approve_or_deny.casefold() == "approve":
            for i in link_choice:
                self.class_info["assignments"][assignment_num]["relevant_links"].append(
                    self.class_info["assignments"][assignment_num]["requested_urls"][i]
                )
                self.class_info["assignments"][assignment_num]["requested_urls"].pop(i)
            self.add_class.save_assignments(self.guild_id)
            await msg.channel.send("Successfully added links to Relevant Links!")
            return
        # if user wants to deny, remove from the pending list
        if approve_or_deny.casefold() == "deny":
            for i in link_choice:
                self.class_info["assignments"][assignment_num]["requested_urls"].pop(i)
            self.add_class.save_assignments(self.guild_id)
            await msg.channel.send("Successfully removed links from the queue!")
            return

    async def run(self, msg: discord.Message, args: str):
        # if user types [class_name] and thats it ex: $211
        if not args:
            # call long_help command for this command
            await help_cmd.get_command_info(self, msg.channel, msg.author)
            return
        if (
            args in self.class_info["assignments"]
        ):  # to print embed message of the specified assignment
            assignment = self.class_info["assignments"][args]  # JSON File
            # description is pulled from the JSON File
            color = no_duplicate_random_color.get_color()
            description = discord.Embed(
                title=assignment["title"],
                url=assignment["url"],
                description=assignment["description"],
                color=color,
            )
            # extra embed stuff
            description.add_field(
                name=f"{self.class_info['professor']}'s Website",
                value=f"Click [here]({self.class_info['website']}) to go to professor {self.class_info['professor']}'s website.",
                inline=False,
            )
            # extra embed stuff
            description.set_footer(
                text="If you still need help with this assignment after reading this embed message, please don't hesitate to ask!"
            )
            await msg.channel.send(embed=description)
            urls = ""
            # goes through each relevant link and then displays it in a seperate embed message
            for url in assignment["relevant_links"]:
                urls += f"[{url['title']}]({url['url']})\n"
            # if there are no urls
            if not urls:
                return
            else:
                relevant_links_list = discord.Embed(
                    title="Relevant Links", description=urls, color=color
                )
                await msg.channel.send(embed=relevant_links_list)

        # adding relevant urls to specified assignments
        # Syntax: $211 addurl 1 https://example.com Example
        elif args.casefold().startswith("addurl "):
            # splits the command string into parts divided by a space
            temp_split_args = args.split(" ")
            split_args = []
            for arg in temp_split_args:
                if arg != "":
                    split_args.append(arg)
            if len(split_args) < 4:
                await msg.channel.send(
                    "Error: Please fill out the command correctly! Type $[class_name] to learn how to use commands"
                )
                return
            if split_args[1] not in self.class_info["assignments"]:
                await msg.channel.send(
                    f"Error: The assignment you are trying to edit does not exist, please check the assignment you want to edit actually exists using **${self.name} assignments"
                )
                return
            """split_args[0] = add
               split_args[1] = assignment#
               split_args[2] = link.com
               split_args[3] = title"""
            assignment_num = split_args[1]
            url_add = await link_check(split_args[2], msg)
            if url_add == "stop":
                return
            # check if url is a valid url i.e starts with https// and has something after https://

            title_add = " ".join(split_args[3:])
            if len(title_add) > 100:
                await msg.channel.send(
                    "Error: Title cannot be more than 100 characters"
                )
                return
            
            # checks for duplicate urls in queue
            for requested_dict in self.class_info["assignments"][assignment_num][
                "requested_urls"
            ]:
                if url_add == requested_dict["url"]:
                    await msg.channel.send(
                        "Error: The link you are trying to add is already in the queue, please wait for a mod to review it"
                    )
                    return
                # checks for duplicate titles in queue
                elif title_add == requested_dict["title"]:
                    await msg.channel.send(
                        "Error: The title you are trying to set for this link is already used for another link, please use another title."
                    )
                    return
            # checks for duplicate links already added
            for link_dict in self.class_info["assignments"][assignment_num][
                "relevant_links"
            ]:
                if url_add == link_dict["url"]:
                    await msg.channel.send(
                        f"Error: The link you are trying to add has already been added to another link in this assignment titled: **{link_dict['title']}**"
                    )
                    return
                # checks for duplicate titles already added
                elif title_add == link_dict["title"]:
                    await msg.channel.send(
                        "Error: The title you are trying to set is already used for another link for this assignment, please use another title."
                    )
                    return
            # This is what will be added to queue and what will be approveed/denied
            new_added_url = {
                "title": title_add,
                "url": url_add,
                "user": msg.author.id,
            }
            # no need for queue if admin tries to add something
            if msg.author.guild_permissions.administrator:
                self.class_info["assignments"][assignment_num]["relevant_links"].append(
                    new_added_url
                )
                await msg.channel.send(
                    "Since you are an admin, this got added to Relevant Links right away!"
                )
                self.add_class.save_assignments(self.guild_id)
                return
            # adds to queue
            self.class_info["assignments"][assignment_num]["requested_urls"].append(
                new_added_url
            )
            # saves JSON file so queue doesnt get erased if bot crashes
            self.add_class.save_assignments(self.guild_id)
            await msg.channel.send(
                "Your request to add this link will be reviewed by an admin."
            )

        # to check whats in queue for specified class (needs to be admin)
        # Syntax: $211 pending 1
        elif args.casefold().startswith("pending "):
            if not msg.author.guild_permissions.administrator:
                await msg.channel.send(
                    "Error: You need administrator permissions to use this command!"
                )
                return
            assignment_num = args[len("pending") :].strip()
            # checks if assignment number exists
            if assignment_num not in self.class_info["assignments"]:
                await msg.channel.send(
                    f"Error: The assignment you are trying to view does not exist, please check the assignment you want to view actually exists using **${self.name} assignments"
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
                title="Requested URLs",
                description=pending_list,
                color=no_duplicate_random_color.get_color(),
            )
            await msg.channel.send(embed=pending_links)

            # waits for user to approve/deny a link(s)
            await self.approve_deny_multiple(msg, assignment_num)

        # removes a url from the relevant links list for an assignment
        # Syntax: $211 removeurl 1 title
        elif args.casefold().startswith("removeurl "):
            # to remove a link from the relevant links list
            # must have admin permissions
            if not msg.author.guild_permissions.administrator:
                await msg.channel.send(
                    "Error: You cannot use this command since you are not admin!"
                )
                return
            temp_split_args = args.split(" ")
            split_args = []
            for arg in temp_split_args:
                if arg != "":
                    split_args.append(arg)

            """split_args[0] = remove
            split_args[1] = assignment#
            split_args[2] = title """

            assignment_num = split_args[1]
            if assignment_num not in self.class_info["assignments"]:
                await msg.channel.send(
                    f"Error: The assignment you are trying to view does not exist, please check the assignment you want to view actually exists using **${self.name} assignments**"
                )
                return
            # combine title if there are spaces
            title = " ".join(split_args[2:])
            # loops through list
            for i in self.class_info["assignments"][assignment_num][
                "relevant_links"
            ]:
                # if it finds a matching title
                if title == i["title"]:
                    # remove it form the list
                    self.class_info["assignments"][assignment_num]["relevant_links"].remove(i)
                    # confirm that a match was found and was deleted
                    await msg.channel.send(
                        f"Removed **{i['title']}** from Relevant Links"
                    )
                    # save JSON File
                    self.add_class.save_assignments(self.guild_id)
                    return
            await msg.channel.send(
                f"Error: **{title}** not found in Relevant Links. This feature is case sensitive. Make sure you typed the title exactly as it is"
            )
            return

        # gives the solution to an assignment (solutions should be added after their due date)
        # $211 solution 1
        elif args.casefold().startswith("solution "):
            # make solution_choice = assignment# i.e everything after "solution "
            solution_choice = args[len("solution") :].strip()
            # checks if assignment# is a number
            if not solution_choice.isdigit():
                await msg.channel.send(
                    "Error: You did not enter a valid assignment number for the solution you want"
                )
                return
            if not (self.add_class.solutions_path / self.name).exists():
                await msg.channel.send("Error: There are no assignment solutions for this class yet!")
                return
            # check if the assignment solution exists in $class_name folder using "pathway/self.name" (self.name = $211 or $212 command)
            for i in (self.add_class.solutions_path / self.name).iterdir():
                # gets rid of .cpp Ex: 1.cpp -> 1
                if i.name.split(".")[0] == solution_choice:
                    # opens the file that was matched with i.name.split (ex: 1.cpp) as a variable
                    with i.open("r") as assignment_solution:
                        # send the file as an embed msg
                        await msg.channel.send(
                            file=discord.File(
                                assignment_solution,
                                f"Assignment {i.name.split('.')[0]} Solution",
                            )
                        )

            # if the solution requested is not found in folder
            await msg.channel.send(
                "Error: The solution to the assignment you are looking for either does not exist or hasn't been added yet. If this is the case, ping a mod!"
            )
            return

        # to add an assignment to a class
        # $211 add 1
        elif args.casefold().startswith("add "):
            # if the the user is not an admin/has admin permissions
            if not msg.author.guild_permissions.administrator:
                await msg.channel.send(
                    "Error: You cannot use this command since you are not admin!"
                )
                return
            # get the number of the assignment they want to add by getting everything after "add"
            assignment_num = args[len("add") :].strip()
            # checks if the assignment they want to add is a number (i.e number of the assignment)
            if not assignment_num.isdigit():
                await msg.channel.send(
                    "Error: You must provide the number for the assignment you are trying to add! Example: $211 add **10** or $220 add **7**"
                )
                return
            elif len(assignment_num) > 10:
                await msg.channel.send("Error: Assignment number can't be more than 10 digits!")
                return
            # checks to see if the assignment number already exists in the assignments list
            if assignment_num in self.class_info["assignments"]:
                await msg.channel.send(format_max_utf16_len_string("Error: This assignment already exists! Type **$ {} {}** to view it.", self.name, assignment_num)
                )
            # if it doesn't exist in the assignments list, we create it
            if assignment_num not in self.class_info["assignments"]:
                # this is the standard layout of every assignment
                new_assignment = {
                    "title": "",
                    "url": "",
                    "description": "",
                    "relevant_links": [],
                    "requested_urls": [],
                }
                # go through each key (i.e "title", "url", "description", etc) but only
                # 3 times so that they can't add a relevant link or add a requested url straight away
                key_counter = 0
                for key in new_assignment:
                    if key_counter == 3:
                        break
                    await msg.channel.send(f"Please enter a {key} for this assignment")
                    # get their input for either title, url or description
                    key_value = await wait_for_reply(msg.author, msg.channel)
                    if key_value == None:
                        return
                    # if they are setting a title (i.e key_counter == 0)
                    if key_counter == 0 and len(key_value) > 100:
                    #if the title is longer than 100 characters, send an error message
                        await msg.channel.send(
                            "Error: Title cannot be more than 100 characters"
                        )
                        return
                    # if they are making a url (i.e key_counter == 1) check to see if the link is valid
                    if key_counter == 1:
                        key_value = await link_check(key_value, msg)
                        if key_value == "stop":
                            return
                    # if they are making a url (i.e key_counter == 2)
                    # set their edits to what they wanted to edit if it passes all tests
                    new_assignment[key] = key_value
                    key_counter += 1
                # save assignments to update the json file in real time
                self.class_info["assignments"][assignment_num] = new_assignment
                self.add_class.save_assignments(self.guild_id)
                await msg.channel.send(
                    f"Done! You can view the added assignment by typing **${self.name} {assignment_num}**. If you want to edit this assignment in case you made a mistake, type **${self.name} edit {assignment_num}**."
                )
                return

        # allows admin/user with admin permissions to edit assignments without having to open the json file (i.e in discord)
        # 211 edit 1
        elif args.casefold().startswith("edit "):
            # if the user is not an admin/has admin permissions
            if not msg.author.guild_permissions.administrator:
                await msg.channel.send(
                    "Error: You cannot use this command since you are not admin!"
                )
                return
            # get the number of the assignment they want to add by getting everything after "add"
            assignment_num = args[len("edit") :].strip()
            # checks if the assignment they want to edit is a number (i.e number of the assignment)
            if not assignment_num.isdigit():
                await msg.channel.send(
                    "Error: You must provide the number for the assignment you are trying to edit! Example: $211 edit **10** or $220 edit **7**"
                )
                return
            # if the assignment does not exist in that class (i.e they can't edit it)
            if assignment_num not in self.class_info["assignments"]:
                await msg.channel.send(
                    "Error: The assignment you are trying to edit has not been added yet!"
                )
                return
            # if the assignment exists in the class, ask what they want to edit (Note* users can only edit either the title, url or description of an assignment)
            if assignment_num in self.class_info["assignments"]:
                edit_list = ["title", "url", "description"]
                await msg.channel.send(
                    f"What would you like to edit from **assignment {assignment_num}**?"
                )
                # asks them what they want to edit using the edit_list (user_select_from_list is a function from utils.py)
                # edit_choice can either be a title, url or description
                edit_choice = await user_select_from_list(msg.channel, edit_list, lambda x: x, msg.author, f"Edit Options For Assignment {assignment_num}", timeout=30,
                )
                # if what is already stored in their edit_choice for the assignment is longer than 1900 characters,
                # display another message because of discord's 2000 word count limit (This is done because the bot won't be able to display edit_choice properly)
                if (
                    len(self.class_info["assignments"][assignment_num][edit_choice])
                    >= 1900
                    or len(self.class_info["assignments"][assignment_num][edit_choice])
                    == 0
                ):
                    await msg.channel.send(
                        f"Please enter a new {edit_choice} for this assignment."
                    )
                # if current edit_choice is less than 1900 characters, print default message (includes preview of existing edit_choice)
                else:
                    await msg.channel.send(
                        f"The current {edit_choice} for assignment {assignment_num} is: **{self.class_info['assignments'][assignment_num][edit_choice]}**\n\nPlease enter the new {edit_choice} for this assignment."
                    )
                # if the new title they are trying to add is more than 100 characters, send an error message
                edit = await wait_for_reply(msg.author, msg.channel)
                if edit_choice == "title":
                    if len(edit) > 100:
                        await msg.channel.send(
                            "Error: Title cannot be more than 100 characters"
                        )
                        return
                # if the new url they are trying to add is not clickable (i.e does not start with https:// or http://), send an error message
                if edit_choice == "url":
                    edit = await link_check(edit, msg)
                    if edit == "stop":
                        return
                # if the new edit is the same as the old one, send an error message
                if edit == self.class_info["assignments"][assignment_num][edit_choice]:
                    await msg.channel.send(
                        f"Error: You are trying to edit the {edit_choice} with the same {edit_choice} it already had!"
                    )
                    return
                # if the new edit is the same as one for another assignment in the same class (i.e same title, url, or description as another assignment )
                for assignment_number in self.class_info["assignments"].values():
                    if assignment_number[edit_choice] == edit:
                        await msg.channel.send(
                            f"Error: The {edit_choice} you are trying to add is the same {edit_choice} for assignment **{assignment_number}** in the **{self.class_info}** class!"
                        )
                        return
                # if the length of the edit is more than 1900 characters (i.e bot can't display a preview), send another message
                if len(edit) > 1900:
                    await msg.channel.send(
                        "Since your edit is longer than the character limit, I cannot show you a preview of your edit. Please make sure your edits are correct before accepting them!"
                    )
                # if the length of the edit is less that 1900 characters (i.e bot can display preview), send defualt message
                else:
                    await msg.channel.send(
                        f"Assignment {assignment_num}'s {edit_choice} will look like this:\n **{edit}**\n Is this okay?"
                    )
                # list that the user chooses either "Accept or Deny" from
                accept_deny = ["Accept", "Deny"]
                apply_choice = await user_select_from_list(msg.channel, accept_deny, lambda x: x, msg.author, "Accept or Deny", timeout=30,
                )
                # if they chose "Accept", save and apply changes made
                if apply_choice == "Accept":
                    self.class_info["assignments"][assignment_num][edit_choice] = edit
                    self.add_class.save_assignments(self.guild_id)
                    await msg.channel.send(
                        f"Edits have been accepted and applied! To view your changed, type **${self.name} {assignment_num}**."
                    )
                    return
                # if they chose "Deny", make no changes to the original assignment
                else:
                    await msg.channel.send(
                        "Edits have been denied! No changed were made."
                    )
                    return
            return
        elif args.casefold().startswith("delete "):
            split_args = args.split(" ", 1)
            """ split_args[0] = delete
                split_args[1] = assignments to delete """
            class_list = re.split(r"[,，\s]\s*", split_args[1])
            for assignment_num in class_list:
                if assignment_num not in self.class_info["assignments"].keys():
                    await msg.channel.send(f"Assignment **{assignment_num}** does not exist in the {self.name} class.")
                else:
                    await msg.channel.send(f"**ARE YOU SURE YOU WANT TO DELETE THE ASSIGNMENT `{assignment_num}` FROM THE {self.name} CLASS? THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!**")
                    yes_or_no = ["Yes", "No"]
                    response = await user_select_from_list(msg.channel, yes_or_no, lambda x: x, msg.author, "", 30)
                    if response == "No" or response == None:
                        await msg.channel.send("No assignments were deleted.")
                    else:
                        del self.class_info["assignments"][assignment_num]
                        self.add_class.save_assignments(self.guild_id)
                        await msg.channel.send(f"**{assignment_num}** was deleted from the list of classes. You will no longer be able to view or edit it!")
            return
        # Send a list of all existing/added assignments for the class (self.name) listed in self.class_info["assignments"]
        # Syntax: $211 assignments
        elif args.casefold() == "assignments":
            # for loop lambda function that sorts assignments in order (this is done incase assignments weren't added in order)
            # ex: added in order: 1, 2, 3, 5, 4, 9, 8, 7 ------> displays in order: 1, 2, 3, 4, 5, 6, 7, 8, 9
            # only works numerically, not with any other characters (i.e: A, a, $, -, +) | Note* converts number char into type int
            assignments_list = ""
            for assignment_num in sorted(
                self.class_info["assignments"].keys(), key=lambda num: int(num)
            ):
                # adds sorted numbers to a list
                assignments_list += f"**{assignment_num}**\n{self.class_info['assignments'][assignment_num]['title']}\n"
            # if there are no assignments for that class (i.e nothing in assignments_list), send a message
            if len(assignments_list) == 0:
                await msg.channel.send(
                    f"There are no assignments added for class **{self.name}**"
                )
                return
            assignments_embed = discord.Embed(
                color=0x00A7FE,  # cyan
            )
            # using the embed field to increase character limit to 6000 and printing the assignments_list using the field
            assignments_embed.add_field(
                name=f"{self.name} Existing Assignments", value=f"{assignments_list}"
            )
            await msg.channel.send(embed=assignments_embed)

        # if they try to view an assignment that doesnt exist
        # $869 %^7
        else:
            await msg.channel.send(
                "Error: Either you typed in a command wrong, or the assignment you are looking for does not exist or has not yet been added to the bot. If this is the case, ping a mod.\nYou can use $[class_name] to get help with how to use this command. Example **$211** or **$212**"
            )

# creates the command for every class dictionary (211 or 212) thats in the JSON File
class addClass(Bot_Command):
    
    name = "class"
    # set variable to path of folders to call them later easier
    solutions_path = Path("data/assignments/solutions")
    assignments_path = Path("data/assignments/assignments.json") # TODO: change back the file
    commands = []  # class_name (211, 212)
    def __init__(self):
        if not self.assignments_path.exists():
            self.assignments_dict = {}
        else:
            with self.assignments_path.open() as file:
                self.assignments_dict = json.load(file)
            for guild_id in self.assignments_dict.keys():
                for class_name in self.assignments_dict[guild_id]:
                    self.add_Class(class_name, self.assignments_dict[guild_id][class_name], guild_id)

    def save_assignments(self, guild_id):
        self.assignments_path.parent.mkdir(parents=True, exist_ok=True)
        for i in self.commands:
            if i.guild_id == guild_id:
                self.assignments_dict[guild_id][i.name] = i.class_info
        with self.assignments_path.open("w") as file:
            json.dump(self.assignments_dict, file, indent=3)


    def add_Class(self, class_name, class_info, guild_id):
        # add command to commands list and add it as a global command
        new_assignment = Assignment_Command(self, class_name, class_info, guild_id)
        # assignments[class_name] = class_info ^ at the start
        self.commands.append(new_assignment)
        bot_commands.add_command(new_assignment, guild_id)

    def create_class(self, class_name, professor, website, guild_id):
        class_info = {
            "assignments": {},
            "professor": professor,
            "website": website
        }
        self.add_Class(class_name, class_info, guild_id)
        self.save_assignments(guild_id)

    def can_run(self, location, member):
        return member is not None and member.guild_permissions.administrator

    async def run(self, msg: discord.Message, args: str):
        if args.casefold().startswith("add "):
            guild_id = str(msg.guild.id)
            if guild_id not in self.assignments_dict:
                self.assignments_dict[guild_id] = {}
            split_args = args.split(" ", 1)
            """ split_args[0] = add
                split_args[1:] = class_name(s) """
            class_list = re.split(r"[,，\s]\s*", split_args[1])
            for class_name in class_list:
                if not class_name.isdigit():
                    await msg.channel.send(f"Error: **{class_name}** is not a class number! Please enter the class number of the class you are trying to add")
                    return
                elif len(class_name) > 10:
                    await msg.channel.send("Error: Assignment number can't be more than 10 digits!")
                    return
            does_class_exist = False
            for class_name in self.commands:
                if class_name.name in class_list and class_name.name in self.assignments_dict[guild_id]:
                    does_class_exist = True
                    await msg.channel.send(f"Error: The class command {class_name} has already been added to the bot. Type **${class_name}** to see how to use it.")
                    class_list.remove(class_name.name)
            if does_class_exist and len(class_list) != 0: 
                await msg.channel.send("Do you still want to add the other classes that were not yet added to the server?")
                yes_or_no = ["Yes", "No"]
                response = await user_select_from_list(msg.channel, yes_or_no, lambda x: x, msg.author, "", 30)
                if response == "No" or response == None:
                    await msg.channel.send("No classes were added.")
                    return
            for class_name in class_list:
                await msg.channel.send(f"Please enter the professor's name for the **{class_name}** class:")
                professor = await wait_for_reply(msg.author, msg.channel)
                if professor == None:
                    return
                await msg.channel.send(f"Please enter the professor's website for the **{class_name}** class:")
                website = await link_check(await wait_for_reply(msg.author, msg.channel), msg)
                if website == "stop" or website == None:
                    return
                self.create_class(class_name, professor, website, guild_id)
                await msg.channel.send(f"You have successfully added the **{class_name}** class!\nTo add assignments to this class, type **${class_name} add [assignment_number]** or do **$help {class_name}** to see an example of how to add an assignment.")
            return
        elif args.casefold() == "list":
            guild_id = str(msg.guild.id)
            # for loop lambda function that sorts assignments_dict in order (this is done incase assignments weren't added in order)
            # ex: added in order: 1, 2, 3, 5, 4, 9, 8, 7 ------> displays in order: 1, 2, 3, 4, 5, 6, 7, 8, 9
            # only works numerically, not with any other characters (i.e: A, a, $, -, +) | Note* converts number char into type int
            class_list = ""
            for class_num in sorted(self.assignments_dict[guild_id], key=lambda num: int(num)):
                # adds sorted numbers to a list
                class_list += f"**{class_num}** - [{self.assignments_dict[guild_id][class_num]['professor']}]({self.assignments_dict[guild_id][class_num]['website']})\n\n"
            # if there are no assignments for that class (i.e nothing in class_list), send a message
            if len(class_list) == 0:
                await msg.channel.send(
                    f"There are no classes added to the bot yet!"
                )
                return
            classes_embed = discord.Embed(
                color=0x00FEA7,  # cyan
            )
            # using the embed field to increase character limit to 6000 and printing the class_list using the field
            classes_embed.add_field(
                name=f"Existing Classes", value=f"{class_list}"
            )
            await msg.channel.send(embed=classes_embed)
        elif args.casefold().startswith("delete "):
            split_args = args.split(" ", 1)
            """ split_args[0] = delete
                split_args[1] = classes to delete """
            class_list = re.split(r"[,，\s]\s*", split_args[1])
            with self.assignments_path.open() as file:
                classes = json.load(file)
            for class_num in class_list:
                if class_num not in classes.keys():
                    await msg.channel.send(f"**{class_num}** has not been added to the list of classes.")
                else:
                    await msg.channel.send(f"⚠️  **__ARE YOU SURE YOU WANT TO DELETE THE CLASS__**   **{class_num}**   **__THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️")
                    yes_or_no = ["Yes", "No"]
                    response = await user_select_from_list(msg.channel, yes_or_no, lambda x: x, msg.author, "", 30)
                    if response == "No" or response == None:
                        await msg.channel.send("No classes were deleted.")
                    else:
                        for index, i in enumerate(self.commands):
                            if i.name == class_num:
                                del self.commands[index]
                                self.save_assignments(self.guild_id)
                                break
                        await msg.channel.send(f"**{class_num}** was deleted from the list of classes. You will no longer be able to view or edit it!")
            return

bot_commands.add_command(addClass())
