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


db = mysql.connector.connect(**_get_login_info())

# If no database was provided in the login info file, default to utilis
if db.database is None:
    with db.cursor() as c:
        c.execute("CREATE DATABASE IF NOT EXISTS utilis;")
        c.execute("USE utilis;")
        db.commit()

#execute query and commit changes to database
def execute(query, params: tuple = None, multi: bool = False, connection = db):
    with connection.cursor() as c:
        try:
            c.execute(query, params, multi)
            connection.commit()
        except Exception as e:
            print(f"ERROR executing query: {query}.\n{e}")

#execute query and returns all or a specified amount of rows of the query result
def read_execute(query, params: tuple = None, multi: bool = False, size: int = 0, connection = db):
    with connection.cursor() as c:
        try:
            c.execute(query, params, multi)
            if size > 0:
                return c.fetchmany(size=size)
            return c.fetchall()
        except Exception as e:
            print(f"ERROR executing query: {query}.\n{e}")
