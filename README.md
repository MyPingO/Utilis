# Utilis
Utilis is a bot aimed towards helping students stay up to date with their assignments. Users have the ability to add and view course material, add helpful tips for completing assignments, share their solutions to homework, and more. Utilis also comes with many moderation features to help you stay on top of your server. Whether you are using it for a specific class or the entire school, Utilis can help organize your assignments and everything relevant to them in a simple and intuitive system. If you ever need help with your schoolwork or want to help others with it, Utilis can assist you with your needs.

## Command Categories:
- Moderation:
Can only be used by server administrators to help moderate their server such as clearing chats or warning a member.

- Class Information: Can be used by members to help find out information about a class or view tips/solutions to assignments.

- Community: Can be used by members to engage with other members of the server such as scheduling events, creating polls or pinning important messages.

- Bot Control: Can be used by server administrators to configure Utilis such as changing Utilis prefix or other default variables such as the default user mute time.

- Miscellaneous: Can be used by members to do simple yet cumbersome tasks, such as picking a random number or flipping a coin.

## Main Features:
### Assignments and Class Info:
- Add a syllabus for a class
- Add a helpful description/guide and relevant links for assignments
- Add solutions to assignments
- Add notes for a class to help catch up on lectures or assignments


### Schedule:
- Schedule events for study sessions, school events or just to chat
- View the servers schedule and sign up for upcoming events
- Edit your events name and date/time
- Get notified when an event is about to start

### Pin Messages:
Users can pin messages if enough people react to the same message with the red 📌 (pushpin) emoji. No need to ping admins to pin messages anymore!

### Self-Assign Roles:
Members can assign public server roles to themselves if they see a role that fits them without needing an admin to do it for them.

## Running Utilis:
### Installation
Utilis requires at least Python 3.9 on the discord and mysql-connector-python packages. They can be installed with
```bash
pip install discord mysql-connector-python
```
Running Utilis also requires a MySQL database to store information, which can be downloaded [here](https://dev.mysql.com/downloads/installer/).

### Setup
Once MySQL is installed, a user should be created for Utilis so that it can save information in the database. This can be done using the interactive GUI or with the query
```sql
CREATE USER 'someusername'@'localhost' IDENTIFIED BY 'somepassword';
```
`someusername` and `somepassword` should be replaced with a username and password. This login info should be provided to Utilis in a file named `sql_login.json` in Utilis's `data` folder with the layout
```json
{
    "host": "localhost",
    "user": "someusername",
    "password": "somepassword"
}
```
In addition, you will need a bot token associated with the Discord bot you want to run with the code. Information on how to create a token can be found [here](https://discordpy.readthedocs.io/en/stable/discord.html). This token should be stored in a file named `token.txt` stored in Utilis's `data` folder.

### Running
Once everything is set up, Utilis can be run by executing `main.py`. If Utilis is missing anything it needs to run, it should let you know with an error message.


## Want to contribute?
If you are a QC student who wants to contribute to Utilis feel free to submit a pull request or contact us on Discord! Don't feel intimidated to help out with Utilis even if you're not an experienced programmer, Utilis is as much of a learning experience as it is finished product. A project started **by** QC students, **for** QC students.

### **Our discords:**
MyPing0#6370 |
PNOYsFTW#1595 |
TurtleArmy#3767

## License
[GPL-3.0 License](COPYING)
