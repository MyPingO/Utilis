import discord
import shutil
import json
from bot_cmd import Bot_Command, bot_commands, Bot_Command_Category
from main import bot_prefix
from commands.cmd_help import help_cmd
from random import choice
from pathlib import Path
from random import choice
from utils import fmt, get
from utils.file import delete_empty_directories
from utils.parse import split_args as split_args_helper
from typing import Optional


async def link_check(link, msg):
    if link == None:
        link = "stop"
        return link
    if type(link) == discord.message.Message:
        link = link.content
    if (link.casefold().startswith("http://") and len(link) > len("http://")) or (
        link.casefold().startswith("https://") and len(link) > len("https://")
    ):
        return link
    else:
        await msg.channel.send(
            "Please enter a proper link. Example: http://example.com **or** https://example.com\nYou can also type **Stop** to exit the command."
        )
        link = await get.reply(msg.author, msg.channel)
        if link == None:
            link = "stop"
            return link
        if link.content == "stop":
            await msg.channel.send("No changes were made")
            return link.content
        else:
            return await link_check(link, msg)


class Random_Color:
    # chooses random color for embed messages
    color = [
        0xB86363,  # red
        0x63B87E,  # green
        0x8652DC,  # purple
        0x5297DC,  # blue
    ]
    tempColor = -1

    def get_color(self):
        # choice() is from random library
        randomColor = choice(self.color)
        # make sure no duplicate color i.e random picker picks same color twice+ in a row
        while self.tempColor == randomColor:
            randomColor = choice(self.color)
        self.tempColor = randomColor
        return randomColor


no_duplicate_random_color = Random_Color()


class Assignment_Command(Bot_Command):
    # TODO Fix help message [class_number]
    short_help = "Shows a detailed explanation of the specified assignment including relevant links, hints and solutions for {class_number}."

    long_help = """Specify the assignment you want help with: ${class_number} [assignment_number] Example: **$211 1** or **$212 3**

    **Sub-commands:**
        ${class_number} assignments
        ${class_number} add
        ${class_number} delete
        ${class_number} solution [assignment_number(s)]
        ${class_number} syllabus
    """

    admin_long_help = """**ADMINS ONLY:**
    ${class_number} edit
    ${class_number} pending [assignment_number(s)] """

    category = Bot_Command_Category.CLASS_INFO

    syllabus_path = Path("data/syllabus")

    def __init__(self, add_class, class_name, class_info, guild_id):
        self.name = class_name  # example (211 or 212)
        # JSON part of the file that accesses the class_name
        self.class_info = class_info  # all the info of the class
        self.add_class = add_class  # used when needed access of save_assignment() or solutions_path etc.
        self.guild_id = guild_id  # the guild_id of the specific discord server
        # print(self.class_info) <---- example of class_info

    def get_help(self, member: Optional[discord.Member], args: Optional[str]):
        if member is None or not member.guild_permissions.administrator:
            return fmt.format_maxlen(self.long_help, class_number=self.name)
        else:
            return fmt.format_maxlen(
                self.long_help + "\n" + self.admin_long_help, class_number=self.name
            )

    def get_description(self) -> str:
        return self.short_help.replace("{class_number}", self.name)

    # helper function to take a specific answer for reviewing pending links
    async def approve_deny_multiple(self, msg, assignment_num):
        # waits for a response from the command author and channel for 60 seconds
        response = await get.reply(msg.author, msg.channel)
        if response == None or response.content.casefold() == "stop":
            await msg.channel.send("No edits were made.")
            return
        # splits resposne i.e the links to approve/deny into into a list. Ex: ["Approve", "1", "3"]
        response = split_args_helper(response.content, True)
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
                "Error: You answered incorrectly! To approve or deny a link, type **Approve** or **Deny** followed by the number of the link you want to edit\nExample: **Approve 1** or **Deny 3**. You can also approve/deny multiple links at once like this **approve 1 2 3** or **deny 4 5 6**."
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
                    "Error: One or more of the links you want to edit does not exist in the queue!"
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
            for requested_url in link_choice:
                self.class_info["assignments"][assignment_num]["relevant_links"].append(
                    self.class_info["assignments"][assignment_num]["requested_urls"][
                        requested_url
                    ]
                )
                self.class_info["assignments"][assignment_num]["requested_urls"].pop(
                    requested_url
                )
            self.add_class.save_assignments(self.guild_id)
            await msg.channel.send("Successfully added links to Relevant Links!")
            return
        # if user wants to deny, remove from the pending list
        if approve_or_deny.casefold() == "deny":
            for requested_url in link_choice:
                self.class_info["assignments"][assignment_num]["requested_urls"].pop(
                    requested_url
                )
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
            if self.class_info["website"] is not None:
                # extra embed stuff
                description.add_field(
                    name=f"{self.class_info['professor']}'s Website",
                    value=f"Click [here]({self.class_info['website']}) to go to professor {self.class_info['professor']}'s website.",
                    inline=False,
                )
            # extra embed stuff
            description.set_footer(
                text="If you still need help with this assignment after reading this, please don't hesitate to ask!"
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
            await msg.channel.send(
                'Approve or Deny links by typing "Approve" or "Deny" followed by the link number(s) you want to edit. Example: **Approve 1** or **Deny 2, 3**. Type **Stop** to exit the command.'
            )
            # waits for user to approve/deny a link(s)
            await self.approve_deny_multiple(msg, assignment_num)

        # removes a url from the relevant links list for an assignment
        # Syntax: $211 removeurl 1 titl

        elif args.casefold() == "add":
            await msg.channel.send("What would you like to add?")
            add_options = [
                "An assignment",
                "A solution to an assignment",
                "Notes for the class",
                "A helpful or relevant link for an assignment",
                "The class syllabus",
            ]
            add_choice = await get.selection(
                msg.channel, add_options, lambda x: x, msg.author, "Add Options", 30
            )
            if add_choice == None:
                return
            if add_choice == "An assignment":
                # if the the user is not an admin/has admin permissions
                if not msg.author.guild_permissions.administrator:
                    await msg.channel.send(
                        "Error: You cannot use this command since you are not admin!"
                    )
                    return
                await msg.channel.send(
                    "Please enter the class number of the class you want to add"
                )
                assignment_num = get.reply(msg.author, msg.channel, timeout=30)
                if assignment_num == None:
                    return
                assignment_num = assignment_num.content
                # checks if the assignment they want to add is a number (i.e number of the assignment)
                if not assignment_num.isdigit():
                    await msg.channel.send(
                        "Error: You must provide the number for the assignment you are trying to add! Example: $211 add **10** or $220 add **7**"
                    )
                    return
                elif len(assignment_num) > 10:
                    await msg.channel.send(
                        "Error: Assignment number can't be more than 10 digits!"
                    )
                    return
                # checks to see if the assignment number already exists in the assignments list
                if assignment_num in self.class_info["assignments"]:
                    await msg.channel.send(
                        fmt.format_maxlen(
                            "Error: This assignment already exists! Type **$ {} {}** to view it.",
                            self.name,
                            assignment_num,
                        )
                    )
                    return
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
                        await msg.channel.send(
                            f"Please enter a {key} for this assignment"
                        )
                        # get their input for either title, url or description
                        key_value = await get.reply(
                            msg.author, msg.channel, timeout=300
                        )
                        if key_value == None:
                            return
                        key_value = key_value.content
                        if key_value == None:
                            return
                        # if they are setting a title (i.e key_counter == 0)
                        if key_counter == 0 and len(key_value) > 100:
                            # if the title is longer than 100 characters, send an error message
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
                    # save assignments to update the JSON file in real time
                    self.class_info["assignments"][assignment_num] = new_assignment
                    self.add_class.save_assignments(self.guild_id)
                    await msg.channel.send(
                        f"Done! You can view the added assignment by typing **${self.name} {assignment_num}**. If you want to edit this assignment in case you made a mistake, type **${self.name} edit {assignment_num}**."
                    )
                    return
            # add a solution to an assignment
            if add_choice == "A solution to an assignment":
                # get added assignment names into a list
                assignments_list = []
                for assignment_num in self.class_info["assignments"]:
                    assignments_list.append("Assignment " + assignment_num)
                await msg.channel.send(
                    "For which assignment do you want to add a solution?"
                )
                # choose which assignment to add a solution to. If no choice is given, return
                response = await get.selection(
                    msg.channel,
                    assignments_list,
                    lambda x: x,
                    msg.author,
                    f"{self.name} Assignments",
                    timeout=30,
                )
                if response == None:
                    return
                assignment_num = split_args_helper(response)[1]
                # set a directory where solutions will be stored
                solution_directory = (
                    self.add_class.solutions_path
                    / self.guild_id
                    / self.name
                    / assignment_num
                    / str(msg.author.id)
                )
                await msg.channel.send(
                    "Enter a name for your solution. Your name can only contain letters or numbers. Type **\Stop/** to stop adding a solution."
                )
                # while True loop that keeps asking to correct errors if any occur i.e file name exists or ivalid file name
                # unless user types "stop" in which case, return
                while True:
                    solution_name = await get.reply(msg.author, msg.channel)
                    if solution_name == None:
                        return
                    if solution_name.content.casefold() == "\stop/":
                        await msg.channel.send("No changes were made")
                        return
                    elif (solution_directory / solution_name.content).exists():
                        await msg.channel.send(
                            "You have already submitted a solution with that name. Please enter a different name or type **\Stop/** to stop adding a solution."
                        )
                        continue
                    # goes through each charcter in the name to check if it's either a letter, number or space. If it's not, ask for a new name.
                    elif not all(
                        character.isalnum() or character.isspace()
                        for character in solution_name.content
                    ):
                        await msg.channel.send(
                            "Your solution name contained characters that were not letters or numbers! Please enter another name or type **\Stop/** to stop adding a solution."
                        )
                        continue
                    else:
                        break
                # set a new solution directory with a folder named after the solution name given and then create that directory
                solution_directory = solution_directory / solution_name.content
                solution_directory.mkdir(parents=True)
                await msg.channel.send(
                    f"Drag in your solution file(s) to assignment {assignment_num}. When you are finished, type **Done** to stop adding files."
                )
                # keep asking for files to add to the solution folder
                while True:
                    # delete empty folders using delete_empty_directories() if no files given or user is done giving files.
                    # More info on the function in utils.file
                    solution = await get.reply(msg.author, msg.channel, timeout=15)
                    if solution == None:
                        delete_empty_directories(
                            solution_directory, self.add_class.solutions_path
                        )
                        return
                    if solution.content.casefold() == "done":
                        if not any(solution_directory.iterdir()):
                            delete_empty_directories(
                                solution_directory, self.add_class.solutions_path
                            )
                            await msg.channel.send("No changes were made.")
                            return
                        else:
                            await msg.channel.send(
                                "Your files have been added successfully!"
                            )
                            return
                    # if no attachment was given
                    elif not solution.attachments:
                        await msg.channel.send("Error: No attachments given.")
                        delete_empty_directories(
                            solution_directory, self.add_class.solutions_path
                        )
                        return

                    # using a for loop to go through attachments becuase mobile allows for multiple atachments per message
                    # just in case a mobile user tries to add a solution

                    # check if the file given is an empty file i.e file size is 0bytes
                    for attachment in solution.attachments:
                        if attachment.size == 0:
                            await msg.channel.send(
                                f"Error: **{attachment.filename}** is an empty file! Please make sure you submit attachments that are not empty."
                            )
                            delete_empty_directories(
                                solution_directory, self.add_class.solutions_path
                            )
                            return
                    # check if a solution with the same filename already exists
                    for attachment in solution.attachments:
                        same_file_name = False
                        for solution_file in solution_directory.iterdir():
                            if attachment.filename == solution_file.name:
                                same_file_name = True
                                await msg.channel.send(
                                    f"A file with the name **{attachment.filename}** already exists! Please resubmit the file with a new name."
                                )
                                break
                        if same_file_name == True:
                            break
                    if same_file_name == True:
                        continue
                    # confirm that the attachments given are valid and correct
                    confirm_or_deny = ["Confirm", "Deny"]
                    for attachment in solution.attachments:
                        await msg.channel.send(
                            f"Please confirm that **{attachment.filename}** is the correct solution file for Assignment {assignment_num}."
                        )
                        response = await get.selection(
                            msg.channel,
                            confirm_or_deny,
                            lambda x: x,
                            msg.author,
                            "Confirm or Deny",
                            timeout=30,
                        )
                        # add file to directory if user confirms
                        if response == "Confirm":
                            await attachment.save(
                                solution_directory / f"{attachment.filename}"
                            )
                            await msg.channel.send("File added!")
                        else:
                            # delete empty directories if no files were added
                            delete_empty_directories(
                                solution_directory, self.add_class.solutions_path
                            )
                            await msg.channel.send(
                                "Edits have been denied! No changes were made."
                            )
                            return
                    await msg.channel.send(
                        "Enter the next file or type **Done** if you are finished."
                    )
            # add notes to the class
            if add_choice == "Notes for the class":
                notes_directory = self.add_class.notes_path / self.guild_id / self.name
                public_notes_directory = notes_directory / "public"
                user_notes_directory = notes_directory / str(msg.author.id)
                if not notes_directory.exists():
                    notes_directory.mkdir(parents=True)
                if not public_notes_directory.exists():
                    public_notes_directory.mkdir()

                await msg.channel.send(
                    "Give a name to the folder that will store your notes and try to be descriptive. You can only use numbers and letters! Type **\Stop/** to stop adding notes."
                )
                # while True loop that keeps asking to correct errors if any occur i.e file name exists or ivalid file name
                # unless user types "stop" in which case, return
                while True:
                    notes_name = await get.reply(msg.author, msg.channel)
                    if notes_name == None:
                        return
                    if notes_name.content.casefold() == "\stop/":
                        await msg.channel.send("No changes were made")
                        return
                    elif (user_notes_directory / notes_name.content).exists():
                        await msg.channel.send(
                            "A folder with this name already exists! Please enter a different name or type **\Stop/** to exit the command."
                        )
                        continue
                    # goes through each charcter in the name to check if it's either a letter, number or space. If it's not, ask for a new name.
                    elif not all(
                        character.isalnum() or character.isspace()
                        for character in notes_name.content
                    ):
                        await msg.channel.send(
                            "Your folder name contained characters that were either not letters or numbers! Please enter another name or type **\Stop/** to exit the command."
                        )
                        continue
                    elif len(notes_name.content) > 100:
                        await msg.channel.send(
                            "Your folder name is longer than 100 characters! Please choose a shorter file name and try again or type **\Stop/** to stop adding your file."
                        )
                    else:
                        break
                user_notes_directory = user_notes_directory / notes_name.content
                user_notes_directory.mkdir(parents=True)

                await msg.channel.send(
                    "Please upload your notes as **attachments only** or **text only**! When you are done uploading your notes, type **Done** to exit the command."
                )
                counter = 0
                while True:
                    counter += 1
                    # delete empty folders using delete_empty_directories() if no files given or user is done giving files.
                    # More info on the function in utils.py
                    notes = await get.reply(msg.author, msg.channel, timeout=30)
                    if notes == None:
                        delete_empty_directories(
                            user_notes_directory, self.add_class.notes_path
                        )
                        delete_empty_directories(
                            public_notes_directory, self.add_class.notes_path
                        )
                        return
                    if notes.content.casefold() == "done":
                        if not any(user_notes_directory.iterdir()):
                            delete_empty_directories(
                                user_notes_directory, self.add_class.notes_path
                            )
                            await msg.channel.send("No changes were made.")
                            return
                        if not any(public_notes_directory.iterdir()):
                            delete_empty_directories(
                                public_notes_directory, self.add_class.notes_path
                            )
                            await msg.channel.send("No changes were made.")
                            return
                        else:
                            await msg.channel.send(
                                "Your files have been added successfully!"
                            )
                            return
                    # if both, attachment and text was given
                    if notes.attachments and len(notes.content) > 0:
                        await msg.channel.send(
                            "You can only upload your notes as **attachments only** or **text only**! Please try again or type **Done** to exit the command."
                        )
                        continue
                    # using a for loop to go through attachments becuase mobile allows for multiple atachments per message
                    # just in case a mobile user tries to add a notes
                    if len(notes.attachments) > 0:
                        # check if the file given is an empty file i.e file size is 0bytes
                        for attachment in notes.attachments:
                            if attachment.size == 0:
                                await msg.channel.send(
                                    f"Error: **{attachment.filename}** is an empty file! Please make sure you submit attachments that are not empty."
                                )
                                delete_empty_directories(
                                    notes_directory, self.add_class.notes_path
                                )
                                return
                        # check if a notes with the same filename already exists
                        for attachment in notes.attachments:
                            same_file_name = False
                            for notes_file in public_notes_directory.iterdir():
                                if attachment.filename == notes_file.name:
                                    same_file_name = True
                                    await msg.channel.send(
                                        f"A file with the name **{attachment.filename}** already exists! Please resubmit the file with a new name."
                                    )
                                    break
                            if same_file_name == True:
                                break
                        if same_file_name == True:
                            continue
                        # confirm that the attachments given are valid and correct
                        confirm_or_deny = ["Confirm", "Deny"]
                        for attachment in notes.attachments:
                            await msg.channel.send(
                                f"Please confirm that **{attachment.filename}** are the correct notes for the {self.name} class."
                            )
                            response = await get.selection(
                                msg.channel,
                                confirm_or_deny,
                                lambda x: x,
                                msg.author,
                                "Confirm or Deny",
                                timeout=30,
                            )
                            # add file to directory if user confirms
                            if response == "Confirm":
                                await attachment.save(
                                    user_notes_directory / f"{attachment.filename}"
                                )
                                await attachment.save(
                                    public_notes_directory / f"{attachment.filename}"
                                )
                                await msg.channel.send("File added!")
                            else:
                                # delete empty directories if no files were added
                                delete_empty_directories(
                                    user_notes_directory, self.add_class.notes_path
                                )
                                delete_empty_directories(
                                    public_notes_directory, self.add_class.notes_path
                                )
                                await msg.channel.send(
                                    "Uploads have been denied! No changes were made."
                                )
                                return
                        await msg.channel.send(
                            "Upload the next file or type **Done** if you are finished."
                        )
                    elif len(notes.content) > 0:
                        text_notes = notes.content
                        await msg.channel.send(
                            "Are you sure this text is correct? You won't be able to edit this text once you have submitted it."
                        )
                        confirm_or_deny = ["Confirm", "Deny"]
                        response = await get.selection(
                            msg.channel,
                            confirm_or_deny,
                            lambda x: x,
                            msg.author,
                            "Confirm or Deny",
                            timeout=30,
                        )
                        # add file to directory if user confirms
                        if response == "Confirm":
                            await msg.channel.send(
                                "Enter a name for your text file. Your name can only contain numbers or letters! Type **\Stop/** to stop adding your file."
                            )
                            while True:
                                text_file_name = await get.reply(
                                    msg.author, msg.channel
                                )
                                if text_file_name == None:
                                    return
                                if text_file_name.content.casefold() == "\stop/":
                                    await msg.channel.send("No changes were made")
                                    return
                                elif (
                                    public_notes_directory / text_file_name.content
                                ).exists() or (
                                    user_notes_directory / text_file_name.content
                                ).exists():
                                    await msg.channel.send(
                                        "There are notes that have already been added with that name! Please enter a different name or type **\Stop/** to stop adding your file."
                                    )
                                    continue
                                # goes through each charcter in the name to check if it's either a letter, number or space. If it's not, ask for a new name.
                                elif not all(
                                    character.isalnum() or character.isspace()
                                    for character in text_file_name.content
                                ):
                                    await msg.channel.send(
                                        "Your file name contained characters that were not letters or numbers! Please enter another name or type **\Stop/** to stop adding your file."
                                    )
                                    continue
                                elif len(text_file_name.content) > 100:
                                    await msg.channel.send(
                                        "Your file name is longer than 100 characters! Please choose a shorter file name and try again or type **\Stop/** to stop adding your file."
                                    )
                                else:
                                    break
                            text_file_name = text_file_name.content
                            write_user_text_notes = (
                                user_notes_directory / f"{text_file_name}.txt"
                            )
                            with write_user_text_notes.open("w") as file:
                                file.write(text_notes)
                            write_public_text_notes = (
                                public_notes_directory / f"{text_file_name}.txt"
                            )
                            with write_public_text_notes.open("w") as file:
                                file.write(text_notes)
                            await msg.channel.send("File added!")
                            await msg.channel.send(
                                "Upload the next file or type **Done** if you are finished."
                            )  # TODO check names arent more than 100 characters
                        else:
                            # delete empty directories if no files were added
                            delete_empty_directories(
                                user_notes_directory, self.add_class.notes_path
                            )
                            await msg.channel.send(
                                "Uploads have been denied! No changes were made."
                            )
                            return
            # add a syllabus to the class
            if add_choice == "The class syllabus":
                # set a directory to store the syllabus in
                syllabus_path = self.syllabus_path / self.guild_id / self.name
                # check if the directory already exists i.e syllabus already added to that class
                if syllabus_path.exists():
                    await msg.channel.send(
                        f"The syllabus to the {self.name} class has already been added. To view it type **{bot_prefix}{self.name} syllabus**. To delete it type **{bot_prefix}{self.name} syllabus delete**"
                    )
                    return
                # otherwise, create the directory
                syllabus_path.mkdir(parents=True)
                # while True loop to give user chance to retry incase of error
                # i.e no attachments given, more than one attachment given or attachment size is 0 bytes.
                while True:
                    await msg.channel.send(
                        "Please submit the syllabus as a file or type **Stop** to exit the command"
                    )
                    syllabus = await get.reply(msg.author, msg.channel)
                    if syllabus == None:
                        return
                    if syllabus.content.casefold() == "stop":
                        delete_empty_directories(syllabus_path, self.syllabus_path)
                        await msg.channel.send("No changes were made.")
                        return
                    if not syllabus.attachments:
                        await msg.channel.send("No attachments given!")
                        continue
                    if len(syllabus.attachments) > 1:
                        await msg.channel.send("You may only attach one file!")
                        continue
                    if syllabus.attachments[0].size == 0:
                        await msg.channel.send(
                            f"**{syllabus.attachments[0].filename}** is an empty file!"
                        )
                        continue
                    else:
                        break
                # confirm with user if file is valid and correct
                confirm_or_deny = ["Confirm", "Deny"]
                await msg.channel.send(
                    f"Please confirm that **{syllabus.attachments[0].filename}** is the correct syllabus for the **{self.name}** class!"
                )
                response = await get.selection(
                    msg.channel, confirm_or_deny, lambda x: x, msg.author, "", 30
                )
                if response == "Confirm":
                    # if user confirms, add file to directory
                    await syllabus.attachments[0].save(
                        syllabus_path / f"{syllabus.attachments[0].filename}"
                    )
                    await msg.channel.send("Syllabus has been added!")
                else:
                    # otherwise, delete the directory and all of its parents
                    delete_empty_directories(syllabus_path, self.syllabus_path)
                    await msg.channel.send("No changes were made.")
                return
            # add a link to an assignment
            if add_choice == "A helpful or relevant link for an assignment":
                assignments_list = []
                for assignment_num in sorted(
                    self.class_info["assignments"].keys(), key=lambda num: int(num)
                ):
                    # adds sorted numbers to a list
                    assignments_list.append(
                        f"Assignment {assignment_num} - [{self.class_info['assignments'][assignment_num]['title']}]({self.class_info['assignments'][assignment_num]['url']})"
                    )
                # if there are no assignments for that class (i.e nothing in assignments_list), send a message
                if len(assignments_list) == 0:
                    await msg.channel.send(
                        f"There are no assignments added for class **{self.name}**"
                    )
                    return
                await msg.channel.send(
                    "For which assignment do you want to add a link to?"
                )
                response = await get.selection(
                    msg.channel,
                    assignments_list,
                    lambda x: x,
                    msg.author,
                    f"{self.name} Assignments",
                    30,
                )
                if response == None:
                    return
                assignment_num = split_args_helper(response)[1]
                await msg.channel.send(
                    "Enter the link you want to add for this assignment:"
                )
                # check if url is a valid url
                url_add = await link_check(
                    await get.reply(msg.author, msg.channel), msg
                )
                if url_add == "stop":
                    return
                await msg.channel.send(
                    "Enter a title for this link. **Note** Title cannot be more than 100 characters:"
                )
                title_add = await get.reply(msg.author, msg.channel)
                if title_add == None:
                    return
                title_add = title_add.content
                while True:
                    if len(title_add) > 100:
                        await msg.channel.send(
                            "Title cannot be more than 100 characters! Please enter another title or type **\Stop/** to stop adding a link."
                        )
                        title_add = await get.reply(msg.author, msg.channel)
                        if title_add == None:
                            return
                        title_add = title_add.content
                        continue
                    else:
                        break
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
                    self.class_info["assignments"][assignment_num][
                        "relevant_links"
                    ].append(new_added_url)
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
                return
        elif args.casefold() == "delete":
            await msg.channel.send("What would you like to delete?")
            delete_options = [
                "An assignment",
                "A solution to an assignment",
                "Notes for the class",
                "A helpful or relevant link for an assignment",
                "The class syllabus",
            ]
            delete_choice = await get.selection(
                msg.channel,
                delete_options,
                lambda x: x,
                msg.author,
                "Delete Options",
                30,
            )
            if delete_choice == None:
                return
            # to delete an assignment
            if delete_choice == "An assignment":
                if not msg.author.guild_permissions.administrator:
                    await msg.channel.send(
                        "Error: You cannot use this command since you are not admin!"
                    )
                    return
                await msg.channel.send(
                    "Here is a list of the currently added assignments. Choose which ones to delete by their assignment number and seperate each number by a comma (`,`)!"
                )
                # for loop lambda function that sorts assignments in order (this is done incase assignments weren't added in order)
                # ex: added in order: 1, 2, 3, 5, 4, 9, 8, 7 ------> displays in order: 1, 2, 3, 4, 5, 6, 7, 8, 9
                # only works numerically, not with any other characters (i.e: A, a, $, -, +) | Note* converts number char into type int
                assignments_list = ""
                for assignment_num in sorted(
                    self.class_info["assignments"].keys(), key=lambda num: int(num)
                ):
                    # adds sorted numbers to a list
                    assignments_list += f"Assignment {assignment_num} - [{self.class_info['assignments'][assignment_num]['title']}]({self.class_info['assignments'][assignment_num]['url']})\n"
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
                    name=f"{self.name} Existing Assignments\n",
                    value=f"{assignments_list}",
                )
                await msg.channel.send(embed=assignments_embed)
                assignments_list = await get.reply(msg.author, msg.channel)
                if assignments_list == None:
                    return
                assignments_list = split_args_helper(assignments_list.content, True)
                assignments_list = set(assignments_list)
                for assignment_num in assignments_list:
                    # if an assignment does not exist in the JSON file
                    if assignment_num not in self.class_info["assignments"].keys():
                        await msg.channel.send(
                            f"Assignment **{assignment_num}** does not exist in the {self.name} class."
                        )
                    else:
                        # confirm deletion of assignment with user
                        await msg.channel.send(
                            f"⚠️ **__ARE YOU SURE YOU WANT TO DELETE THE ASSIGNMENT__   {assignment_num}   __FROM THE {self.name} CLASS? THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__** ⚠️"
                        )
                        yes_or_no = ["Yes", "No"]
                        response = await get.selection(
                            msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                        )
                        if response == "Yes":
                            # if user cofirms, delete assignment from the JSON file, otherwise just do nothing
                            del self.class_info["assignments"][assignment_num]
                            self.add_class.save_assignments(self.guild_id)
                            await msg.channel.send(
                                f"**{assignment_num}** was deleted from the list of classes. You will no longer be able to view or edit it!"
                            )
                        else:
                            await msg.channel.send("No assignments were deleted.")
                return
            # to delete a solution for an assignment
            if delete_choice == "A solution to an assignment":
                if not (self.add_class.solutions_path / self.guild_id).exists():
                    # if no solutions have been added for any class, AKA there's nothing to delete
                    await msg.channel.send("There are no solutions to delete yet.")
                    return
                    # if the user running the command is not an admin on the server, allow them to only delete their own solution submissions
                if not msg.author.guild_permissions.administrator:
                    user_solutions = []
                    # check if the user has submitted any solutions in the server/guild
                    for assignment_solution_folder in (
                        self.add_class.solutions_path / self.guild_id / self.name
                    ).iterdir():
                        solution_directory = (
                            self.add_class.solutions_path
                            / self.guild_id
                            / self.name
                            / assignment_solution_folder.name
                        )
                        if (solution_directory / str(msg.author.id)).exists():
                            user_solutions.append(assignment_solution_folder.name)
                    # if the user has not submitted a solution, AKA can't delete anything
                    if len(user_solutions) == 0:
                        await msg.channel.send(
                            "Error: You have not uploaded any solutions to delete! **Note** You can only delete solutions that you have submitted."
                        )
                        return
                    # if they have, ask them which of their solutions do they want to delete
                    else:
                        await msg.channel.send(
                            "Which assignment do you want to delete a solution from? **Note** You can only delete solutions that you have submitted."
                        )
                        assignment_solution_folder = await get.selection(
                            msg.channel,
                            user_solutions,
                            lambda x: x,
                            msg.author,
                            f"{self.name} Assignments",
                            timeout=30,
                        )
                        if assignment_solution_folder == None:
                            return
                        await msg.channel.send("Which solution do you want to delete?")
                        solution_directory = (
                            self.add_class.solutions_path
                            / self.guild_id
                            / self.name
                            / assignment_solution_folder
                            / str(msg.author.id)
                        )
                        user_solutions_list = []
                        for solution in solution_directory.iterdir():
                            user_solutions_list.append(solution.name)
                        solution_choice = await get.selection(
                            msg.channel,
                            user_solutions_list,
                            lambda x: x,
                            msg.author,
                            f"{self.name} Assignments",
                            timeout=30,
                        )
                        if solution_choice == None:
                            return
                        # ask user for confirmation to delete their solution
                        await msg.channel.send(
                            f"Delete your solution called **{solution_choice}** from Assignment **{assignment_solution_folder}**?"
                        )
                        yes_or_no = ["Yes", "No"]
                        response = await get.selection(
                            msg.channel,
                            yes_or_no,
                            lambda x: x,
                            msg.author,
                            "Yes or No?",
                            timeout=30,
                        )
                        if response == None:
                            return
                        elif response == "Yes":
                            # using shutil.rmtree() to remove directory if it is not empty as opposed to .rmdir() which can only remove empty directories/folders
                            shutil.rmtree(solution_directory / solution_choice)
                            await msg.channel.send(
                                f"**{solution_choice}** has been removed from **{assignment_solution_folder}**!"
                            )
                            delete_empty_directories(
                                solution_directory, self.add_class.solutions_path
                            )
                            return
                        else:
                            await msg.channel.send("No changed were made.")
                            return
                else:
                    # get assignment numbers in a list to choose from
                    assignments = []
                    for assignment_num in self.class_info["assignments"]:
                        assignments.append("Assignment " + assignment_num)
                    await msg.channel.send(
                        "Which assignment solution do you want to delete?"
                    )
                    response = await get.selection(
                        msg.channel,
                        assignments,
                        lambda x: x,
                        msg.author,
                        f"{self.name} Assignments",
                        timeout=30,
                    )
                    if response == None:
                        return
                    assignment_num = split_args_helper(response)[1]
                    # set solution directory with their assignment choice
                    solution_directory = (
                        self.add_class.solutions_path
                        / self.guild_id
                        / self.name
                        / assignment_num
                    )
                    # if there are no solutions to delete for the chosen assignment
                    if not solution_directory.exists() or not any(
                        solution_directory.iterdir()
                    ):
                        await msg.channel.send(
                            "There are no solutions added to this assignment for you to delete."
                        )
                        return
                    # ask who's solution you want to delete since there can be multiple solutions sent by different people
                    # create two lists: one with user id's to search for their directory and another for that user's discord name
                    username_list = []
                    user_id_list = []
                    for user_id in solution_directory.iterdir():
                        # discord's get_member() function to get the name of a user_id, Ex: 87954609457609458 --> EpicUsername123
                        member = msg.guild.get_member(int(user_id.name))
                        # add user ID's and usernames to respective lists
                        username_list.append(str(member))
                        user_id_list.append(user_id.name)
                    await msg.channel.send("Whose solution(s) do you want to delete?")
                    solution_author = await get.selection(
                        msg.channel, username_list, lambda x: x, msg.author, "", 30
                    )
                    if solution_author == None:
                        return
                    # get the corresponding user ID of the username chosen by user
                    user_id = user_id_list[username_list.index(solution_author)]
                    # set new solution directory to access chosen user's solutions
                    solution_directory = solution_directory / user_id
                    # get a list of all solution folders (names) uploaded by chosen user
                    solutions_list = []
                    for solution_folder in solution_directory.iterdir():
                        solutions_list.append(solution_folder.name)
                    # if there is more than one solution ask user to choose which one to delete
                    if len(solutions_list) > 1:
                        await msg.channel.send(
                            f"**{solution_author}** has uploaded multiple solution versions for Assignment {assignment_num}. Which version do you want to delete?"
                        )
                        solution_name = await get.selection(
                            msg.channel, solutions_list, lambda x: x, msg.author, "", 30
                        )
                        if solution_name == None:
                            return
                        # confirm deletion with user
                        await msg.channel.send(
                            f"⚠️  **__ARE YOU SURE YOU WANT TO DELETE__ {solution_author}'s Solution: {solution_name} __THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️"
                        )
                        yes_or_no = ["Yes", "No"]
                        response = await get.selection(
                            msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                        )
                        if response == "Yes":
                            # using shutil.rmtree() to remove directory if it is not empty as opposed to .rmdir() which can only remove empty directories/folders
                            shutil.rmtree(solution_directory / solution_name)
                            delete_empty_directories(
                                solution_directory, self.add_class.solutions_path
                            )
                            await msg.channel.send(
                                f"**{solution_name}** has been removed from **{assignment_num}**!"
                            )
                        else:
                            await msg.channel.send("No changes were made.")
                        return
                    else:
                        # if there's only one solution added by the solution author
                        solution_name = solutions_list[
                            0
                        ]  # TODO fix "ARE YOU SURE" messages
                        await msg.channel.send(
                            f"⚠️  **__ {solution_author}'s Solution: {solution_name} __THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️"
                        )
                        yes_or_no = ["Yes", "No"]
                        response = await get.selection(
                            msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                        )
                        if response == "Yes":
                            shutil.rmtree(solution_directory)
                            delete_empty_directories(
                                solution_directory.parent, self.add_class.solutions_path
                            )
                            await msg.channel.send(
                                f"**{solution_author}'s** solution has been removed from **{assignment_num}**!"
                            )
                        else:
                            await msg.channel.send("No changes were made.")
                        return
            # to delete notes from the class
            if delete_choice == "Notes for the class":
                if not (self.add_class.notes_path / self.guild_id):
                    await msg.channel.send(
                        "No notes have been added to this server to delete."
                    )
                    return
                if not msg.author.guild_permissions.administrator:
                    if not (
                        self.add_class.notes_path
                        / self.guild_id
                        / self.name
                        / str(msg.author.id)
                    ).exists():
                        await msg.channel.send(
                            "Error: You have not uploaded any notes to delete! You can only delete notes that you have submitted."
                        )
                        return
                    user_notes_directory = (
                        self.add_class.notes_path
                        / self.guild_id
                        / self.name
                        / str(msg.author.id)
                    )
                    public_notes_directory = (
                        self.add_class.notes_path / self.guild_id / self.name / "public"
                    )
                    await msg.channel.send(
                        "You can only delete the notes that you submitted. Do you want to delete an entire folder or specific notes from a folder?"
                    )
                    folder_or_notes = ["Delete a folder", "Delete notes from a folder"]
                    response = await get.selection(
                        msg.channel,
                        folder_or_notes,
                        lambda x: x,
                        msg.author,
                        "Delete Options",
                        30,
                    )
                    if response == None:
                        return
                    if response == "Delete a folder":
                        user_notes_folders = [
                            folder.name for folder in user_notes_directory.iterdir()
                        ]
                        await msg.channel.send("Which folder do you want to delete?")
                        response = await get.selection(
                            msg.channel,
                            user_notes_folders,
                            lambda x: x,
                            msg.author,
                            "Delete Options",
                            30,
                        )
                        if response == None:
                            return
                        notes_folder_name = response
                        notes_filenames_list = [
                            notes.name
                            for notes in user_notes_directory / notes_folder_name
                        ]
                        await msg.channel.send(
                            f"⚠️  **__ARE YOU SURE YOU WANT TO DELETE YOUR NOTES FOLDER CALLED:__  {notes_folder_name}  __THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️"
                        )
                        yes_or_no = ["Yes", "No"]
                        response = await get.selection(
                            msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                        )
                        if response == "Yes":  # TODO delete from public
                            # using shutil.rmtree() to remove directory if it is not empty as opposed to .rmdir() which can only remove empty directories/folders
                            shutil.rmtree(user_notes_directory / notes_folder_name)
                            for filename in notes_filenames_list:
                                Path.unlink(public_notes_directory / filename)
                            delete_empty_directories(
                                user_notes_directory, self.add_class.notes_path
                            )
                            delete_empty_directories(
                                public_notes_directory, self.add_class.notes_path
                            )
                            await msg.channel.send(
                                f"**{notes_folder_name}** has been removed from the **{self.name}** class!"
                            )
                        else:
                            await msg.channel.send("No changes were made.")
                        return
                    if response == "Delete notes from a folder":
                        user_notes_folders = [
                            folder.name for folder in user_notes_directory.iterdir()
                        ]
                        await msg.channel.send("Select a folder to delete notes from")
                        response = await get.selection(
                            msg.channel,
                            user_notes_folders,
                            lambda x: x,
                            msg.author,
                            "Select Options",
                            30,
                        )
                        if response == None:
                            return
                        user_notes_directory = user_notes_directory / response
                        delete_notes_list = [
                            notes.name for notes in user_notes_directory.iterdir()
                        ]
                        await msg.channel.send("Which notes do you want to delete?")
                        notes_list = await get.selections(
                            msg.channel,
                            delete_notes_list,
                            lambda x: x,
                            msg.author,
                            "Delete Options",
                        )  # TODO change to user_select_from_multiple_list where appropriate
                        if response == None:  # TODO see if this ^ works
                            return
                        for filename in notes_list:
                            await msg.channel.send(
                                f"⚠️  **__ARE YOU SURE YOU WANT TO DELETE YOUR NOTES CALLED:__  {filename}  __THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️"
                            )
                            yes_or_no = ["Yes", "No"]
                            response = await get.selection(
                                msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                            )
                            if response == "Yes":
                                # using Path.unlink() to remove a file
                                Path.unlink(
                                    user_notes_directory / filename
                                )  # TODO delete from public
                                Path.unlink(public_notes_directory / filename)
                                await msg.channel.send(
                                    f"**{filename}** has been removed from the **{self.name}** class!"
                                )
                            else:
                                await msg.channel.send("No changes were made.")
                        # delete potentially empty folder
                        delete_empty_directories(
                            user_notes_directory, self.add_class.notes_path
                        )
                        return
                else:
                    user_notes_directory = (
                        self.add_class.notes_path / self.guild_id / self.name
                    )
                    public_notes_directory = (
                        self.add_class.notes_path / self.guild_id / self.name / "public"
                    )
                    await msg.channel.send("What do you want to delete?")
                    folder_or_notes = ["Delete a folder", "Delete notes from a folder"]
                    response = await get.selection(
                        msg.channel,
                        folder_or_notes,
                        lambda x: x,
                        msg.author,
                        "Delete Options",
                        30,
                    )
                    if response == None:
                        return
                    if response == "Delete a folder":
                        username_list = []
                        user_id_list = []
                        for user_id in user_notes_directory.iterdir():
                            if user_id.name != "public":
                                member = msg.guild.get_member(int(user_id.name))
                                username_list.append(str(member))
                                user_id_list.append(user_id.name)
                        await msg.channel.send("Whose folder do you want to delete?")
                        response = await get.selection(
                            msg.channel, username_list, lambda x: x, msg.author, "", 30
                        )
                        if response == None:
                            return
                        user_name = response
                        user_id = user_id_list[username_list.index(response)]
                        user_notes_directory = user_notes_directory / user_id
                        user_notes_folders = [
                            folder.name for folder in user_notes_directory.iterdir()
                        ]
                        await msg.channel.send("Which folder do you want to delete?")
                        response = await get.selection(
                            msg.channel,
                            user_notes_folders,
                            lambda x: x,
                            msg.author,
                            "",
                            30,
                        )
                        if response == None:
                            return
                        notes_folder_name = response
                        notes_filenames_list = [
                            notes.name
                            for notes in (
                                user_notes_directory / notes_folder_name
                            ).iterdir()
                        ]
                        await msg.channel.send(
                            f"⚠️  **__ARE YOU SURE YOU WANT TO DELETE {user_name}'s FOLDER CALLED:__  {notes_folder_name}  __THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️"
                        )
                        yes_or_no = ["Yes", "No"]
                        response = await get.selection(
                            msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                        )
                        if response == "Yes":
                            # using shutil.rmtree() to remove directory if it is not empty as opposed to .rmdir() which can only remove empty directories/folders
                            shutil.rmtree(user_notes_directory / notes_folder_name)
                            for filename in notes_filenames_list:
                                Path.unlink(public_notes_directory / filename)
                            delete_empty_directories(
                                user_notes_directory, self.add_class.notes_path
                            )
                            delete_empty_directories(
                                public_notes_directory, self.add_class.notes_path
                            )
                            await msg.channel.send(
                                f"**{notes_folder_name}** has been removed from the **{self.name}** class!"
                            )
                        else:
                            await msg.channel.send("No changes were made.")
                        return
                    if response == "Delete notes from a folder":
                        usernames_list = [
                            str(msg.guild.get_member(int(folder.name)))
                            for folder in user_notes_directory.iterdir()
                            if folder.name != "public"
                        ]
                        user_ids_list = [
                            folder.name
                            for folder in user_notes_directory.iterdir()
                            if folder.name != "public"
                        ]
                        await msg.channel.send(
                            "Whose folder do you want to delete notes from?"
                        )
                        response = await get.selection(
                            msg.channel,
                            usernames_list,
                            lambda x: x,
                            msg.author,
                            "Select Options",
                            30,
                        )
                        if response == None:
                            return
                        user_notes_directory = (
                            user_notes_directory
                            / user_ids_list[usernames_list.index(response)]
                        )
                        user_folders_list = [
                            folder.name for folder in user_notes_directory.iterdir()
                        ]
                        await msg.channel.send(
                            "Which folder do you want to delete notes from?"
                        )
                        response = await get.selection(
                            msg.channel,
                            user_folders_list,
                            lambda x: x,
                            msg.author,
                            "Select Options",
                            30,
                        )
                        if response == None:
                            return
                        user_notes_directory = user_notes_directory / response
                        delete_notes_list = [
                            notes.name for notes in user_notes_directory.iterdir()
                        ]

                        await msg.channel.send(
                            "Which notes do you want to delete?"
                        )  # TODO Whose notes do you want to delete?
                        notes_list = await get.selections(
                            msg.channel,
                            delete_notes_list,
                            lambda x: x,
                            msg.author,
                            "Delete Options",
                        )  # TODO change to user_select_from_multiple_list where appropriate
                        if notes_list == None:
                            return
                        for filename in notes_list:
                            await msg.channel.send(
                                f"⚠️  **__ARE YOU SURE YOU WANT TO DELETE YOUR NOTES CALLED:__  {filename}  __THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️"
                            )
                            yes_or_no = ["Yes", "No"]
                            response = await get.selection(
                                msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                            )
                            if response == "Yes":
                                # using Path.unlink() to remove a file
                                Path.unlink(
                                    user_notes_directory / filename
                                )  # TODO delete from public
                                Path.unlink(public_notes_directory / filename)
                                await msg.channel.send(
                                    f"**{filename}** has been removed from the **{self.name}** class!"
                                )
                            else:
                                await msg.channel.send("No changes were made.")
                        # deletes potentially empty folder
                        delete_empty_directories(
                            user_notes_directory, self.add_class.notes_path
                        )
                        return
            # to delete the class syllabus
            if delete_choice == "The class syllabus":
                if not msg.author.guild_permissions.administrator:
                    await msg.channel.send(
                        "Error: You cannot use this command since you are not admin!"
                    )
                    return
                # if the user tries to delete a syllabus that doesn't exist
                if not (self.syllabus_path / self.guild_id / self.name).exists():
                    await msg.channel.send(
                        f"Error: There are no syllabuses added to the **{self.name}** class to delete."
                    )
                    return
                # otherwise, set a directory to access the syllabus file
                syllabus_path = self.syllabus_path / self.guild_id / self.name
                # confirm with user about deleting the syllabus
                await msg.channel.send(
                    f"⚠️  **__ARE YOU SURE YOU WANT TO DELETE THE SYLLABUS FOR THE CLASS__   {self.name}   __THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️"
                )
                yes_or_no = ["Yes", "No"]
                response = await get.selection(
                    msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                )
                if response == "Yes":
                    # if user confirms, delete directory and all parent directories
                    shutil.rmtree(syllabus_path)
                    delete_empty_directories(
                        syllabus_path, self.add_class.solutions_path
                    )
                    await msg.channel.send(f"{self.name} Syllabus deleted.")
                    return
                else:
                    # otherwise do nothing
                    await msg.channel.send("No changes were made.")
                    return
            # to delete a link from an assignment
            if delete_choice == "A helpful or relevant link for an assignment":
                # to remove a link from the relevant links list
                # must have admin permissions
                if not msg.author.guild_permissions.administrator:
                    await msg.channel.send(
                        "Error: You cannot use this command since you are not admin!"
                    )
                    return
                assignments_list = []
                for assignment_num in sorted(
                    self.class_info["assignments"].keys(), key=lambda num: int(num)
                ):
                    # adds sorted numbers to a list
                    assignments_list.append(
                        f"Assignment {assignment_num} - [{self.class_info['assignments'][assignment_num]['title']}]({self.class_info['assignments'][assignment_num]['url']})"
                    )
                # if there are no assignments for that class (i.e nothing in assignments_list), send a message
                if len(assignments_list) == 0:
                    await msg.channel.send(
                        f"There are no assignments added for class **{self.name}**"
                    )
                    return
                await msg.channel.send(
                    "For which assignment do you want to delete a link from?"
                )
                response = await get.selection(
                    msg.channel,
                    assignments_list,
                    lambda x: x,
                    msg.author,
                    f"{self.name} Assignments",
                    30,
                )
                if response == None:
                    return
                assignment_num = split_args_helper(response)[1]
                relevant_links = self.class_info["assignments"][assignment_num][
                    "relevant_links"
                ]
                urls = []
                # goes through each relevant link and then displays it in a seperate embed message
                for url in relevant_links:
                    urls.append(f"{url['title']} - {url['url']}")
                # if there are no urls
                if not urls:
                    await msg.channel.send(
                        "There are no links added to this assignment for you to delete!"
                    )
                    return
                await msg.channel.send("Which link do you want to delete?")
                response = await get.selection(
                    msg.channel,
                    urls,
                    lambda x: x,
                    msg.author,
                    f"Assignment {assignment_num} Relevant Links",
                    30,
                )
                title = relevant_links[urls.index(response)]["title"]
                # loops through list
                for i in self.class_info["assignments"][assignment_num][
                    "relevant_links"
                ]:
                    # if it finds a matching title
                    if title == i["title"]:
                        # confirm deletion with user
                        await msg.channel.send(
                            f"⚠️  **__ARE YOU SURE YOU WANT TO DELETE THE LINK NAMED:__   {title}   __THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️"
                        )
                        yes_or_no = ["Yes", "No"]
                        response = await get.selection(
                            msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                        )
                        if response == "Yes":
                            # remove it form the list
                            self.class_info["assignments"][assignment_num][
                                "relevant_links"
                            ].remove(i)
                            # confirm that a match was found and was deleted
                            await msg.channel.send(
                                f"Removed **{i['title']}** from Relevant Links"
                            )
                            # save JSON File
                            self.add_class.save_assignments(self.guild_id)
                            return
                        else:
                            await msg.channel.send("No changes were made.")
                            return

                await msg.channel.send(
                    f"Error: **{title}** not found in Relevant Links. This feature is case sensitive. Make sure you typed the title exactly as it is"
                )
                return
        elif args.casefold() == "edit":
            if not msg.author.guild_permissions.administrator:
                await msg.channel.send(
                    "Error: You cannot use this command since you are not admin!"
                )
                return
            await msg.channel.send("What would you like to edit?")
            edit_options = ["An assignment"]
            edit_choice = await get.selection(
                msg.channel, edit_options, lambda x: x, msg.author, "Edit Options", 30
            )
            if edit_choice == None:
                return
            # to edit the title, url, or description of an assignment
            if edit_choice == "An assignment":
                assignments_list = []
                for assignment_num in sorted(
                    self.class_info["assignments"].keys(), key=lambda num: int(num)
                ):
                    # adds sorted numbers to a list
                    assignments_list.append(
                        f"Assignment {assignment_num} - [{self.class_info['assignments'][assignment_num]['title']}]({self.class_info['assignments'][assignment_num]['url']})"
                    )
                # if there are no assignments for that class (i.e nothing in assignments_list), send a message
                if len(assignments_list) == 0:
                    await msg.channel.send(
                        f"There are no assignments added for class **{self.name}**"
                    )
                    return
                await msg.channel.send("Which assignment do you want to edit?")
                response = await get.selection(
                    msg.channel,
                    assignments_list,
                    lambda x: x,
                    msg.author,
                    f"{self.name} Assignments",
                    30,
                )
                if response == None:
                    return
                assignment_num = split_args_helper(response)[1]
                edit_list = ["title", "url", "description"]
                await msg.channel.send(
                    f"What would you like to edit from **assignment {assignment_num}**?"
                )
                # asks them what they want to edit using the edit_list
                # edit_choice can either be a title, url or description
                edit_choice = await get.selection(
                    msg.channel,
                    edit_list,
                    lambda x: x,
                    msg.author,
                    f"Edit Options For Assignment {assignment_num}",
                    timeout=30,
                )
                if edit_choice == None:
                    return
                # if what is already stored in their edit_choice for the assignment is longer than 1850 characters,
                # display another message because of discord's 2000 word count limit (This is done because the bot won't be able to display edit_choice properly)
                if (
                    len(self.class_info["assignments"][assignment_num][edit_choice])
                    >= 1850
                    or len(self.class_info["assignments"][assignment_num][edit_choice])
                    == 0
                ):
                    await msg.channel.send(
                        f"Please enter a new {edit_choice} for this assignment or type **Stop** to exit the command."
                    )
                # if current edit_choice is less than 1850 characters, print default message (includes preview of existing edit_choice)
                else:
                    await msg.channel.send(
                        f"The current {edit_choice} for assignment {assignment_num} is: **{self.class_info['assignments'][assignment_num][edit_choice]}**\nPlease enter the new {edit_choice} for this assignment or type **Stop** to exit the command."
                    )
                # if the new title they are trying to add is more than 100 characters, send an error message
                edit = await get.reply(msg.author, msg.channel)
                if edit == None:
                    return
                edit = edit.content
                if edit == "stop":
                    await msg.channel.send("No changes were made.")
                    return
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
                apply_choice = await get.selection(
                    msg.channel,
                    accept_deny,
                    lambda x: x,
                    msg.author,
                    "Accept or Deny",
                    timeout=30,
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

        # view a solution to an assignment
        # 211 solution 1 || $211 solutions 1
        elif args.casefold().startswith("solution ") or args.casefold().startswith(
            "solutions "
        ):
            # adding this "if else" because it may be intuitive to type "solutions" when viewing an assignment with multiple solutions
            if args.casefold().startswith("solution "):
                solution_choice = args[len("solution") :].strip()
            else:
                solution_choice = args[len("solutions") :].strip()
            print("Getting Solutions")
            if not (self.add_class.solutions_path / self.guild_id).exists():
                await msg.channel.send(
                    "There are no assignment solutions added to this server yet!"
                )
                return
            solution_choice_list = split_args_helper(solution_choice, True)
            # user might intuitively try to run the command like this: $211 solution add 1 or $211 solution delete 1
            # since this is the wrong syntax because assignment number isn't specified with adding or deleting a solution
            # send a message to let them know the format is wrong
            if "add" in solution_choice_list:
                await msg.channel.send(
                    f"Error: To add a solution to an assignment in the **{self.name}** class. Type **{bot_prefix}{self.name} add**"
                )
                return
            if "delete" in solution_choice_list:
                await msg.channel.send(
                    f"Error: To delete a solution to an assignment in the **{self.name}** class. Type **{bot_prefix}{self.name} delete**"
                )
                return
            for assignment_num in solution_choice_list.copy():
                solution_directory = (
                    self.add_class.solutions_path
                    / self.guild_id
                    / self.name
                    / assignment_num
                )
                # if an assignment doesn't exist in the specified class i.e 211 or 212
                if assignment_num not in self.class_info["assignments"]:
                    # let user know assignment doesn't exist
                    await msg.channel.send(
                        f"Assignment **{assignment_num}** does not exist!"
                    )
                    solution_choice_list.remove(assignment_num)
                    continue
                # if the solution to an assignment doesn't exist, remove it from the solution_choice_list
                if not solution_directory.exists() or not any(
                    solution_directory.iterdir()
                ):
                    await msg.channel.send(
                        f"There are no solutions for Assignment **{assignment_num}** yet!"
                    )
                    solution_choice_list.remove(assignment_num)
            # go through each solution in the each assignment's directory
            for assignment_num in solution_choice_list:
                solution_directory = (
                    self.add_class.solutions_path
                    / self.guild_id
                    / self.name
                    / assignment_num
                )
                username_list = []
                user_id_list = []
                # do the same thing with names and user ID's as mentioned above when deleting solutions
                for user_id in solution_directory.iterdir():
                    member = msg.guild.get_member(int(user_id.name))
                    username_list.append(str(member))
                    user_id_list.append(user_id.name)
                await msg.channel.send(
                    f"Whose solution do you want to view for Assignment **{assignment_num}**?"
                )
                solution_author = await get.selection(
                    msg.channel, username_list, lambda x: x, msg.author, "", 30
                )
                if solution_author == None:
                    return
                user_id = user_id_list[username_list.index(solution_author)]
                # set a new directory
                solution_directory = solution_directory / user_id
                # get a list of all solutions added by the solution_author
                solutions_list = []
                for solution_folder in solution_directory.iterdir():
                    solutions_list.append(solution_folder.name)
                # if the solution_author has uploaded multiple solution versions ask which one to view
                if len(solutions_list) > 1:
                    await msg.channel.send(
                        f"**{solution_author}** has uploaded multiple solution versions for Assignment {assignment_num}. Which version do you want to view?"
                    )
                    solution_version = await get.selection(
                        msg.channel,
                        solutions_list,
                        lambda x: x,
                        msg.author,
                        "Solution Versions",
                        30,
                    )
                    if solution_version == None:
                        return
                    await msg.channel.send(
                        f"Here are all the files in the **{solution_version}** folder"
                    )
                    for solution_file in (
                        solution_directory / solution_version
                    ).iterdir():
                        with solution_file.open("rb") as download_file:
                            await msg.channel.send(
                                file=discord.File(download_file, solution_file.name)
                            )
                # if the solution_author has uploaded one solution verson, send the files in it to the server to download
                else:
                    await msg.channel.send(
                        f"Here are the solution files **{solution_author}** submitted for Assignment {assignment_num}."
                    )
                    for solution_file in (
                        solution_directory / solutions_list[0]
                    ).iterdir():
                        with solution_file.open("rb") as download_file:
                            await msg.channel.send(
                                file=discord.File(download_file, solution_file.name)
                            )
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
                assignments_list += f"Assignment {assignment_num} - [{self.class_info['assignments'][assignment_num]['title']}]({self.class_info['assignments'][assignment_num]['url']})\n"
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
                name=f"{self.name} Existing Assignments\n", value=f"{assignments_list}"
            )
            await msg.channel.send(embed=assignments_embed)

        # notes
        # $211 notes
        elif args.casefold() == "notes":
            if not (self.add_class.notes_path / self.guild_id).exists():
                await msg.channel.send("No notes have been added to the server yet!")
                return
            public_notes_directory = (
                self.add_class.notes_path / self.guild_id / self.name / "public"
            )
            await msg.channel.send("Which notes do you want to view?")
            all_notes_list = [notes.name for notes in public_notes_directory.iterdir()]
            response = await get.selections(
                msg.channel, all_notes_list, lambda x: x, msg.author, "View options"
            )
            for notes_name in response:
                notes_file = public_notes_directory / notes_name
                with notes_file.open("rb") as download_file:
                    await msg.channel.send(file=discord.File(download_file, notes_name))
            return
        # get the syllabus for a class
        # $211 syllabus
        elif args.casefold().startswith("syllabus"):
            print(args)
            if args.casefold() == "syllabus":
                # next() returns the next item in an iterator, in this case the next thing in the directory which is the syllabus file
                with next(
                    (self.syllabus_path / self.guild_id / self.name).iterdir()
                ).open("rb") as download_file:
                    await msg.channel.send(
                        f"Here is the syllabus file for the **{self.name}** class."
                    )
                    await msg.channel.send(
                        file=discord.File(download_file, download_file.name)
                    )
                return
            args = args[len("syllabus") :].strip()

        # if they try to view an assignment or class that doesnt exist
        # $211 %^7 or $lmao 69
        else:
            await msg.channel.send(
                "Error: Either you typed in a command wrong, or the assignment you are looking for does not exist or has not yet been added to the bot. If this is the case, ping a mod.\nYou can use $[class_name] to get help with how to use this command. Example **$211** or **$212**"
            )
            return


# creates the command for every class dictionary (211 or 212) thats in the JSON File
class addClass(Bot_Command):
    short_help = "Add or delete a class command or view all pending links in a class."
    long_help = "View all classes on the server with **$class list**\n"
    admin_long_help = """**ADMINS ONLY:**
    $class add [class_number(s)]
    $class delete [class_number(s)]
    $class pending [class_number(s)] **View pending links in a class**
    """

    category = Bot_Command_Category.MODERATION

    name = "class"
    # set variables to path of folders to call them later easily
    assignments_path = Path("data/assignments/assignments.json")
    notes_path = Path("data/assignments/notes")
    solutions_path = Path("data/assignments/solutions")
    commands = []  # all commands on all servers (211, 212, 69, 420)

    def __init__(self):
        if not self.assignments_path.exists():
            # if the JSON file doesn't exist i.e fresh bot with no added class commands
            # create an empty dictionary to later put into a JSON file
            self.assignments_dict = {}
        else:
            # if it does exist, set a dictionary = to the contents inside of the JSON file
            # this dictionary will be used to store class information about assignments and whatnot
            with self.assignments_path.open() as file:
                self.assignments_dict = json.load(file)
            # for every guild_id (Which is a dictionary) in the JSON file
            for guild_id in self.assignments_dict.keys():
                # and for every class inside each guild_id dictionary i.e 211 or 212
                for class_name in self.assignments_dict[guild_id]:
                    # add a command to the bot, that is server/guild specific to that command
                    # Ex: One discord server may have a 211 command and another server might also have a 211 command
                    # However one 211 command will be associated with some guild_id 975903478509349850 and the other with 234325894390853049
                    # this makes it possible to use the same command but store different info for them and prevents use of same command on another server
                    self.add_Class(
                        class_name,
                        self.assignments_dict[guild_id][class_name],
                        guild_id,
                    )

    def get_help(self, member: Optional[discord.Member], args: Optional[str]):
        if member is None or not member.guild_permissions.administrator:
            return self.long_help
        else:
            return self.long_help + "\n" + self.admin_long_help

    # saves/updates all the info in a class
    def save_assignments(self, guild_id):
        self.assignments_path.parent.mkdir(parents=True, exist_ok=True)
        # goes through all the commands across all servers
        for i in self.commands:
            print(i.name)
            # if a command associated guild_id mathes that of the guild_id passed into the function
            if i.guild_id == guild_id:
                # update he JSON file for the guild_id dictionary with the class_info of the command
                self.assignments_dict[guild_id][i.name] = i.class_info
        # open the JSON file as a file in write mode
        with self.assignments_path.open("w") as file:
            # dump all changes made to the JSON file i.e self.assignments_dict, into the JSON file
            json.dump(self.assignments_dict, file, indent=3)

    def add_Class(self, class_name, class_info, guild_id):
        # add command to commands list and add it as a global command
        new_assignment = Assignment_Command(self, class_name, class_info, guild_id)
        # assignments[class_name] = class_info ^ at the start
        self.commands.append(new_assignment)
        bot_commands.add_command(new_assignment, guild_id)

    def create_class(self, class_name, professor, website, course_title, guild_id):
        # sets the class info for the class that's being added
        class_info = {
            "assignments": {},
            "professor": professor,
            "website": website,
            "course_title": course_title,
        }
        # add the class to list of commands to make it a useable command
        self.add_Class(class_name, class_info, guild_id)
        # save the class and it's info to the JSON file
        self.save_assignments(guild_id)

    # adding a class to use as a command
    async def run(self, msg: discord.Message, args: str):
        # get the guild_id of where the message came from
        guild_id = str(msg.guild.id)
        # class add 211, 212, 213
        if args.casefold().startswith("add "):
            if not msg.author.guild_permissions.administrator:
                await msg.channel.send(
                    "Error: You cannot use this command since you are not admin!"
                )
                return
            if guild_id not in self.assignments_dict:
                self.assignments_dict[guild_id] = {}
            split_args = args.split(" ", 1)
            """ split_args[0] = add
                split_args[1:] = class_name(s) """
            # get a list of the class names
            class_list = split_args_helper(split_args[1], True)
            # run through the list to check for invalid class numbers
            # i.e class number isn't a digit (includes characters or spaces) or if the class number is too big (in the billions)
            for class_name in class_list:
                if not class_name.isdigit():
                    await msg.channel.send(
                        f"Error: **{class_name}** is not a class number! Please enter the class number of the class you are trying to add"
                    )
                    return
                elif len(class_name) > 10:
                    await msg.channel.send(
                        "Error: Assignment number can't be more than 10 digits!"
                    )
                    return
            # if a class already exists remove it from the class_list list
            for class_name in class_list.copy():
                if class_name in self.assignments_dict[guild_id]:
                    await msg.channel.send(
                        f"Error: The class command **{class_name}** has already been added to the bot. Type **${class_name}** to see how to use it."
                    )
                    class_list.remove(class_name)
            # if class_list still has classes in it to add, ask user if they want to add the remaining classes
            if len(class_list) != 0:
                await msg.channel.send(
                    "Do you still want to add the other classes that were not yet added to the server?"
                )
                yes_or_no = ["Yes", "No"]
                response = await get.selection(
                    msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                )
                if response == "No" or response == None:
                    await msg.channel.send("No classes were added.")
                    return
            # loop through each class in class_list and ask user to fill in info about the class to later add to the JSON file
            for class_name in class_list:
                await msg.channel.send(
                    f"Please enter the professor's name for the **{class_name}** class:"
                )
                professor = await get.reply(msg.author, msg.channel)
                if professor == None:
                    return
                await msg.channel.send(
                    f"Please enter {professor.content}'s website for the **{class_name}** class. If the professor does not have a website, type **None**."
                )
                website = await get.reply(msg.author, msg.channel)
                if website == None:
                    return
                if website.content.casefold() == "none":
                    website = None
                else:
                    website = await link_check(website, msg)
                    if website == "stop" or website == None:
                        return
                await msg.channel.send(
                    f"Please enter the course title for the **{class_name}** class:"
                )
                course_title = await get.reply(msg.author, msg.channel)
                if course_title == None:
                    return
                # website doesn't need a .content becuase link_check() deals with that
                self.create_class(
                    class_name,
                    professor.content,
                    website,
                    course_title.content,
                    guild_id,
                )
                await msg.channel.send(
                    f"You have successfully added the **{class_name}** class!\nTo add assignments to this class, type **${class_name} add [assignment_number]** or do **$help {class_name}** to see an example of how to add an assignment."
                )
            return
        elif args.casefold() == "list":
            # for loop lambda function that sorts assignments_dict in order (this is done incase assignments weren't added in order)
            # ex: added in order: 1, 2, 3, 5, 4, 9, 8, 7 ------> displays in order: 1, 2, 3, 4, 5, 6, 7, 8, 9
            # only works numerically, not with any other characters (i.e: A, a, $, -, +) | Note* converts number char into type int
            class_list = ""
            for class_num in sorted(
                self.assignments_dict[guild_id], key=lambda num: int(num)
            ):
                # adds sorted numbers to a list
                class_list += f"**{class_num}** - {self.assignments_dict[guild_id][class_num]['course_title']}\n[{self.assignments_dict[guild_id][class_num]['professor']}]({self.assignments_dict[guild_id][class_num]['website']})\n\n"
            # if there are no assignments for that class (i.e nothing in class_list), send a message
            if len(class_list) == 0:
                await msg.channel.send(f"There are no classes added to the bot yet!")
                return
            classes_embed = discord.Embed(
                color=0x00FEA7,  # cyan
            )
            # using the embed field to increase character limit to 6000 and printing the class_list using the field
            classes_embed.add_field(name=f"Existing Classes", value=f"{class_list}")
            await msg.channel.send(embed=classes_embed)
        # class delete 211, 212, 213
        elif args.casefold().startswith("delete "):
            if not msg.author.guild_permissions.administrator:
                await msg.channel.send(
                    "Error: You cannot use this command since you are not admin!"
                )
                return
            split_args = args.split(" ", 1)
            """ split_args[0] = delete
                split_args[1] = classes to delete """
            # get a list of classes to delete
            class_list = split_args_helper(split_args[1], True)
            # if a class doesn't exist, let the user know, otherwise confirm with the user if they want to delete the class
            for class_num in class_list:
                if class_num not in self.assignments_dict[guild_id]:
                    await msg.channel.send(
                        f"**{class_num}** has not been added to the list of classes."
                    )
                else:
                    await msg.channel.send(
                        f"⚠️  **__ARE YOU SURE YOU WANT TO DELETE THE CLASS__   {class_num}   __THIS CANNOT BE UNDONE AND SHOULD BE CONSIDERED CAREFULLY!__**  ⚠️"
                    )
                    yes_or_no = ["Yes", "No"]
                    response = await get.selection(
                        msg.channel, yes_or_no, lambda x: x, msg.author, "", 30
                    )
                    if response == "Yes":
                        # deleting the class_num command from JSON file, self.commands list, and bot_commands. Then saving the JSON file
                        for i in self.commands:
                            if i.name == class_num:
                                del self.assignments_dict[guild_id][i.name]
                                self.commands.remove(i)
                                bot_commands.remove_command(i, guild_id)
                                self.save_assignments(guild_id)
                                break
                        await msg.channel.send(
                            f"**{class_num}** was deleted from the list of classes. You will no longer be able to view or edit it!"
                        )
                    else:
                        # otherwise, do nothing
                        await msg.channel.send("No classes were deleted.")
            return
        # to view all pending links for specified classes
        # $class pending 211, 212, 213
        elif args.casefold().startswith("pending "):
            if not msg.author.guild_permissions.administrator:
                await msg.channel.send(
                    "Error: You cannot use this command since you are not admin!"
                )
                return
            split_args = args.split(" ", 1)
            """ split_args[0] = pending
                split_args[1] = class numbers """
            # get a list of specified classes
            class_list = split_args_helper(split_args[1], True)
            for class_name in class_list.copy():
                # if the class does not exist in the JSON file, remove it from the class_list list
                if class_name not in self.assignments_dict[guild_id]:
                    await msg.channel.send(f"**{class_name}** is not an added class.")
                    class_list.remove(class_name)
            # if the class does exist but has no pending links
            for class_name in class_list.copy():
                assignments = self.assignments_dict[guild_id][class_name]["assignments"]
                does_exist = False
                for assignment in assignments:
                    # if there is a pending link, set does_exist = True, otherwise set it to False to get rid of the class from class_list
                    if assignments[assignment]["requested_urls"]:
                        does_exist = True
                if does_exist == False:
                    await msg.channel.send(
                        f"There are no pending links in the **{class_name}** class"
                    )
                    class_list.remove(class_name)
                does_exist = False
            # if after all of these checks, there are no classes in class_list, return
            if not class_list:
                return
            # though the name is pending_list, it is not a list but will act lile one when viewed in discord
            pending_list = ""
            # for loop goes through each class in class_list to access the requested_urls of the assignments in it
            for class_name in sorted(class_list, key=lambda x: int(x)):
                assignments = self.assignments_dict[guild_id][class_name]["assignments"]
                url = 0
                # sort the assignments numerically to display assignments in order
                for assignment in sorted(assignments):
                    # if there is a requested url in the assignment, add the assignment name and requested_urls in it
                    if assignments[assignment]["requested_urls"]:
                        pending_list += f"**Assignment {assignment}**\n"
                    for link in assignments[assignment]["requested_urls"]:
                        url += 1
                        pending_list += f"[{link['title']}]({link['url']})\n"
                # send the requested_urls as an embed message for the class
                pending_links = discord.Embed(
                    title=f"{class_name} Pending Links",
                    description=pending_list,
                    color=no_duplicate_random_color.get_color(),
                )
                await msg.channel.send(embed=pending_links)
                # reset the pending list for the next class's requested_urls list
                pending_list = ""
            return


bot_commands.add_command(addClass())
