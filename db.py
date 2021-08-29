import json
import mysql.connector
from pathlib import Path


sql_login_path = Path("data/sql_login.json")


def _get_login_info() -> dict:
    placeholder_login_info = {
        "host": "YOUR HOST",
        "user": "YOUR USER",
        "password": "YOUR PASSWORD",
    }
    # TODO: Add more info on how to log in to SQL database?
    missing_login_info_message = (
        f"Error: did not find SQL login info at {sql_login_path}."
    )
    if not sql_login_path.exists():
        sql_login_path.parent.mkdir(parents=True, exist_ok=True)
        with sql_login_path.open("w") as sql_login_file:
            json.dump(placeholder_login_info, sql_login_file, indent=4)
        raise FileNotFoundError(missing_login_info_message)

    with sql_login_path.open("r") as sql_login_file:
        login_info = json.load(sql_login_file)
        if login_info != placeholder_login_info:
            return login_info
        else:
            raise ValueError(missing_login_info_message)


mydb = mysql.connector.connect(**_get_login_info())

# If no database was provided in the login info file, default to utilis
if mydb.database is None:
    with mydb.cursor() as c:
        c.execute("CREATE DATABASE IF NOT EXISTS utilis;")
        c.execute("USE utilis;")
        mydb.commit()
