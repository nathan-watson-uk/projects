from flask import Flask, render_template, request, abort, redirect, url_for, session, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import uuid
import pathlib
import os.path


from data import *
from login_forms import registration_check, login_check
from datetime import timedelta, datetime, timezone

UPLOAD_FOLDER = r'C:\osgc_repo\pdf'  # Change this to the relevant upload folder
ALLOWED_EXTENSIONS = {'pdf'}


app = Flask(__name__, static_url_path='/static')
app.secret_key = b''

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Should stop flask caching files?
csrf = CSRFProtect(app)

generate_profiles_table()  # Used to make sure databases/tables are generated
generate_report_tables()

with open(".\\misc\\blacklist.txt", "r+") as ips:
    blacklist = [line.rstrip('\n') for line in ips]


# Doesn't seem to work
# limiter = Limiter(
#     app,
#     key_func=get_remote_address(),  # Maybe get_remote_address?
#     default_limits=["500 per day"]
# )
# @limiter.limit(limit_value="200/day")
# Only limit number of post requests on login/register


@app.errorhandler(429)
def page_not_found(e):
    return render_template('429.html', title="OSGC - 429"), 429


@app.errorhandler(403)
def page_not_found(e):
    return render_template('403.html', title="OSGC - 403"), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', title="OSGC - 404"), 404


@app.errorhandler(400)
def page_not_found(e):
    return render_template('400.html', title="OSGC - 400"), 400


@app.before_request
def block():
    # print(
    # request.remote_addr,
    # request.headers["User-Agent"],
    # request.headers["Accept"],
    # request.headers["Accept-Language"],
    # datetime.now(timezone.utc)
    # )
    global blacklist
    if request.remote_addr in blacklist:
        return render_template('403.html', title="OSGC - 403"), 403
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)


@app.route("/", methods=["GET", "POST"])
def home():
    if "session_id" in session:  # Checks if there is an active session for the user
        return redirect(url_for("account"))

    if request.method == "GET":
        return render_template("home.html", title="OSGC - Home", loginError=False)

    if request.method == "POST":

        if login_check(request.form["Username"], request.form["Password"]):  # Checks blank/length

            if check_user_data(request.form["Username"], request.form["Password"]):  # Checks details are valid

                user_session_id = str(uuid.uuid4())  # Creates a unique session ID
                save_session_id(request.form["Username"], user_session_id)  # Overwrites session_id in database
                session["session_id"] = user_session_id  # Creates a session

                return redirect(url_for("account"))

        else:
            return render_template("home.html", title="OSGC - Home", loginError=True)


@app.route("/account", methods=["GET"])
def account():
    if "session_id" in session:
        user_data = [get_data_from_session_id(str(session["session_id"]))]

        if not user_data:
            return render_template('403.html', title="OSGC - 403"), 403

        return render_template(  # Displays user data
            'account.html',
            title="OSGC - Account",
            data=user_data,
            admin=user_data[0]["admin"])

    else:
        return redirect(url_for("home"))


@app.route("/logout", methods=["GET"])
def logout():

    if "session_id" in session:
        session.pop("session_id", None)  # Removes the session id logging the user out
        return redirect(url_for("home"))

    else:
        return redirect(url_for("home"))


@app.route("/search", methods=["GET", "POST"])
def search():
    if "session_id" in session:
        file = None
        user_data = [get_data_from_session_id(str(session["session_id"]))]

        if request.method == "GET":
            return render_template("search.html", title="OSGC - Search", searchError=False, admin=user_data[0]["admin"])

        if request.method == "POST":

            if request.form.get("download_button", file) is not None:  # Checks if the user has requested to download
                download_file = request.form["download_button"].strip('\n')  # Gets name of file

                # Search for file clearance and compare

                with open("./misc/download_logs.txt", "a") as log:
                    log.write(f"{user_data['username']},{request.remote_addr},{download_file},"
                              f"{datetime.now(timezone.utc)}\n")  # Logs download request

                return send_from_directory(app.config['UPLOAD_FOLDER'], download_file, as_attachment=True)

            # Using request.form.get with None removes the risk of a 400 status code
            if (request.form.get("search", None).replace(" ", "")).isalnum():  # Checks search query is alphanumeric
                search_response = search_data(
                    request.form["search"],
                    get_data_from_session_id(str(session["session_id"]))["clearance"]
                )
                return render_template(
                    "search.html",
                    title="OSGC - Search",
                    files=search_response,
                    searchError=False,
                    admin=user_data[0]["admin"]
                )

            if request.form.get("search", None) == "":  # Checks the search form is empty (stops database dump)
                return render_template(
                    "search.html",
                    title="OSGC - Search",
                    searchError=True,
                    admin=user_data[0]["admin"]
                )

            # If the query isn't alphanumeric raise an error
            if not (request.form.get("search", None).replace(" ", "")).isalnum():
                return render_template(
                    "search.html",
                    title="OSGC - Search",
                    searchError=True,
                    admin=user_data[0]["admin"]
                )

            else:
                return render_template('400.html', title="OSGC - 400"), 400
    else:
        return redirect(url_for("home"))


@app.route("/contact")
def contact():
    if request.method == "GET":
        return render_template("home.html", title="OSGC - Home")  # Needs to get changed to contact.html


@app.route("/about")
def about():
    if request.method == "GET":
        return render_template("home.html", title="OSGC - Home")  # Needs to get changed to about.html


@app.route("/register", methods=["GET", "POST"])
def registration():
    if "session_id" in session:  # Prevents a client having multiple logged in sessions
        return redirect(url_for("logout"))

    if request.method == "GET":
        return render_template("register.html", title="OSGC - Register", invalidDetails=False)

    if request.method == "POST":

        # Makes sure user/pass are valid and don't
        if registration_check(request.form["Username"], request.form["Password"], request.form["Email"]):
            save_register_data(
                request.form["Username"],
                request.form["Password"],
                request.form["Email"],
                request.remote_addr
            )

            with open("./misc/registration_logs.txt", "a") as logs:
                logs.write(f"{request.form['Username']},{request.remote_addr},{datetime.now(timezone.utc)}\n")

            return render_template("register_success.html", title="OSGC - Success")

        else:
            return render_template("register.html", title="OSGC - Register", invalidDetails=True)


@app.route("/submit", methods=["GET", "POST"])
def report_submission():
    if "session_id" in session:
        user_data = get_data_from_session_id(str(session["session_id"]))
        clearance_list = get_clearance_dict(user_data["clearance"])

        if request.method == "GET":
            return render_template(
                "submit.html",
                title="OSGC - Submit",
                clear_list=clearance_list,
                admin=user_data["admin"]
            )

        if request.method == "POST":
            file = request.files["file"]

            if file.filename == "":  # Checks a file was submitted.
                return render_template(
                        "submit.html",
                        title="OSGC - Submit",
                        fileError=False,
                        noInput=True,
                        clear_list=clearance_list,
                        admin=user_data["admin"]
                    )

            #  Checks the file MIME Type / extension match and are PDF.
            if file.mimetype == "application/pdf" and \
                    "pdf" == file.filename.split(".")[len(file.filename.split("."))-1]:

                file.filename = secure_file(request.form["report_name"]) + ".pdf"

                with open("./misc/submit_logs.txt", "a") as logs:
                    logs.write(
                        f"{user_data['username']},{request.remote_addr},{file.filename},"
                        f"{request.form['clearance']},{datetime.now(timezone.utc)}\n"
                    )

                if submit_report_details(
                        file.filename,
                        request.form["author"],
                        request.form["tags"],
                        request.form["clearance"],
                        clearance_list):

                    # Function to save data to database filename, author, directory, clearance
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                    return render_template("submit_success.html", title="OSGC - Success", admin=user_data["admin"])

                else:

                    return render_template(
                            "submit.html",
                            title="OSGC - Submit",
                            fileError=False,
                            unknownError=True,
                            clear_list=clearance_list,
                            admin=user_data["admin"]
                        )

            else:

                return render_template("submit.html", title="OSGC - Submit", fileError=True, clear_list=clearance_list)

    else:
        return redirect(url_for("home"))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "session_id" in session:
        sql = None
        user = None
        user_data = get_data_from_session_id(str(session["session_id"]))

        if user_data["admin"]:
            if request.method == "GET":

                return render_template(
                    "admin.html",
                    title="OSGC - Admin",
                    admin=user_data["admin"],
                    SQL=False,
                    searchError=True,  # stops no results
                    execValue=["SQL Output"]  # Put in list so Jinja2 iterates properly
                )
                #  Jinja2 options are sqlError, error_value, noSQL, execValue

            if request.method == "POST":

                if request.form.get("user", user) is not None:  # Searches for users
                    username = request.form.get("user")

                    if not username:  # empty username
                        return render_template(
                            "admin.html",
                            title="OSGC - Admin",
                            admin=user_data["admin"],
                            SQL=False,
                            execValue=["SQL Output"],
                            users=[],
                            searchError=False
                        )

                    response, results = search_user(username)

                    return render_template(
                        "admin.html",
                        title="OSGC - Admin",
                        admin=user_data["admin"],
                        SQL=False,
                        execValue=["SQL Output"],
                        users=results,
                        searchError=response
                    )

                if request.form.get("execute_sql", sql) is not None:  # Checks for SQL execution request
                    sql_query = request.form["execute_sql"]
                    if sql_query == "":
                        return render_template(
                            "admin.html",
                            title="OSGC - Admin",
                            admin=user_data["admin"],
                            SQL=False,
                            searchError=True,
                            execValue=["Empty SQL Statement"]  # Put in list so Jinja2 iterates properly
                        )

                    database_selected = request.form["database"]
                    response, output = admin_execution(database_selected, sql_query)

                    return render_template(
                        "admin.html",
                        title="OSGC - Admin",
                        admin=user_data["admin"],
                        SQL=response,
                        searchError=True,
                        execValue=[output]
                    )

                if request.form.get("ban", None) is not None:
                    pass
                    # check the account to ban isnt an admin account

        else:
            return redirect(url_for("home"))
    else:
        return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True, threaded=True)


#############################
# SECOND FILE data.py

import sqlite3
from datetime import datetime, timezone
from argon2 import PasswordHasher, exceptions


def commit_close(connection):  # Used to commit and close the database
    connection.commit()
    connection.close()

# Table Creation #


def generate_report_tables():  # Generates the tables for reports.db
    report_tables = ["public", "confidential", "secret", "top_secret"]
    conn = sqlite3.connect("databases/reports.db")
    c = conn.cursor()
    try:
        for table in report_tables:
            c.execute(f"""CREATE TABLE {table} (
                        id integer PRIMARY KEY AUTOINCREMENT,
                        file_name text,
                        tags text,
                        author text,
                        directory text,
                        clearance text
                        )""")
        commit_close(conn)

    except sqlite3.OperationalError as e:
        with open("./misc/database_logs.txt", "a") as log:
            log.write(f"Table Creation Attempt,{e},{datetime.now(timezone.utc)}\n")  # Logs download request
        conn.close()


def generate_profiles_table():  # Generates the table for profiles.db
    conn = sqlite3.connect("databases/profiles.db")
    c = conn.cursor()
    try:
        c.execute("""CREATE TABLE profile (
                    id integer PRIMARY KEY AUTOINCREMENT,
            [        username text,
                    email text,
                    password text,
                    date text,
                    ip text,
                    clearance text,
                    session text,
                    admin numeric
                    )""")
        commit_close(conn)

    except sqlite3.OperationalError as e:
        with open("./misc/database_logs.txt", "a") as log:
            log.write(f"Table Creation Attempt,{e},{datetime.now(timezone.utc)}\n")  # Logs download request
        conn.close()

# Search #


def search_data(search_string, clearance):  # Searches the database for reports
    conn = sqlite3.connect("databases/reports.db")
    iter_list = []

    # Splits Query into list of each word
    if " " in search_string:
        iter_list.append(search_string.split(" "))

    else:  # if there aren't any spaces (one word) it will just append to the list.
        iter_list.append(search_string)

    # This should be done shorter
    clearance_list = ["public", "confidential", "secret", "top_secret"]
    clearance_dict = {"public": 1, "confidential": 2, "secret": 3, "top_secret": 4}

    # Generates parts of the SQL statements
    dynamic_statement = []
    for level in range(clearance_dict[clearance]):
        dynamic_statement.append(f"{clearance_list[level]}")

    # Inefficient but the only method we have as the statement is dynamic ^

    c = conn.cursor()
    search_list = []  # List used to store the returned results
    for pos in range(0, len(iter_list)):
        # Takes each word in query list & uses LIKE to search
        for table in dynamic_statement:
            c.execute(f"SELECT * FROM {table} WHERE tags LIKE ?", ('%' + iter_list[pos] + '%',))
            response = c.fetchall()

            for file in range(0, len(response)):

                search_list.append(
                    {"file_name": response[file][1],
                     "tags": response[file][2],
                     "author": response[file][3],
                     "directory": response[file][4],
                     "clearance": table}
                )

        for table in dynamic_statement:
            c.execute(f"SELECT * FROM {table} WHERE file_name LIKE ?", ('%' + iter_list[pos] + '%',))
            response = c.fetchall()

            for file in range(0, len(response)):

                search_list.append(
                    {"file_name": response[file][1],
                     "tags": response[file][2],
                     "author": response[file][3],
                     "directory": response[file][4],
                     "clearance": table}
                )

    conn.close()
    return [dict(t) for t in {tuple(d.items()) for d in search_list}]

# Register/Login #


def save_register_data(username, password, email, ip):  # Saves the details for registration
    conn = sqlite3.connect("databases/profiles.db")
    c = conn.cursor()
    hash_pass = PasswordHasher().hash(password)

    try:
        c.execute("SELECT * FROM profile WHERE username=? or email=?", (username, email))
        if not c.fetchall():
            c.execute(
                "INSERT INTO profile(id, username, email, password, date, ip, clearance, session, admin) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                , (None, username, email, hash_pass, datetime.now(), ip, "public", "", 0)
            )
            commit_close(conn)
            return True

        else:
            return False

    except Exception as e:
        with open("./misc/database_logs.txt", "a") as log:
            log.write(f"Table Creation Attempt,{e},{datetime.now(timezone.utc)}\n")  # Logs download request
        conn.close()
        return False


def check_user_data(username, password):  # Checks the username and password for login
    conn = sqlite3.connect("databases/profiles.db")
    c = conn.cursor()
    c.execute("SELECT * FROM profile WHERE username=?", (username,))
    try:
        profile_result = c.fetchall()[0]  # Checks if any data is returned, list with tuple inside
    except IndexError:
        return False

    try:
        if PasswordHasher().verify(profile_result[3], password):  # Checks hash, returns exception if incorrect password
            conn.close()
            return True

    except exceptions.VerifyMismatchError:
        conn.close()
        return False

# Sessions #


def get_data_from_session_id(session_id):
    conn = sqlite3.connect("databases/profiles.db")
    c = conn.cursor()

    try:
        c.execute("SELECT * FROM profile WHERE session=?", (str(session_id),))

    except Exception as e:
        with open("./misc/database_logs.txt", "a") as log:
            log.write(f"Table Creation Attempt,{e},{datetime.now(timezone.utc)}\n")  # Logs download request
        conn.close()
        return []

    try:
        results = c.fetchall()[0]
        conn.close()
        return {
            "username": results[1],
            "email": results[2],
            "created": results[4],
            "ip": results[5],
            "clearance": results[6],
            "admin": results[8]
        }
    except IndexError:
        return []


def save_session_id(username, session_id):  # Saves the details for registration
    conn = sqlite3.connect("databases/profiles.db")
    c = conn.cursor()
    try:
        c.execute("UPDATE profile SET session=? WHERE username=?", (session_id, username))
        commit_close(conn)
    except Exception as e:
        with open("./misc/database_logs.txt", "a") as log:
            log.write(f"Table Creation Attempt,{e},{datetime.now(timezone.utc)}\n")  # Logs download request
        conn.close()


# Submit #

def submit_report_details(secure_filename, author, tags, clearance, secure_clearance):

    if clearance not in secure_clearance:
        return False

    directory = f"/pdf/{secure_filename}"
    conn = sqlite3.connect("databases/reports.db")
    c = conn.cursor()

    try:
        c.execute(f"INSERT INTO {clearance}(id, file_name, tags, author, directory) VALUES (?, ?, ?, ?, ?)",
                  (None, secure_filename, tags, author, directory))
        commit_close(conn)
        return True

    except Exception as e:
        with open("./misc/database_logs.txt", "a") as log:
            log.write(f"Report Submission,{e},{directory},{datetime.now(timezone.utc)}\n")  # Logs download request
        conn.close()
        return False


# Filename #

def secure_file(filename):
    import re

    replacements = [
        ("([A-Za-z])(/)([A-Za-z])", r"\g<1>_\g<3>"),
        (r"/", "_"),
        (r"../", ""),
        (r" ", "_"),
        (r"<|>", "")
    ]

    if any(element in filename for element in ["../", " ", "/"]):
        for pattern, replacement in replacements:
            filename = re.sub(pattern, replacement, filename)
        return filename

    else:
        return filename


def get_clearance_dict(user_clearance):
    clearance_list = ["public", "confidential", "secret", "top_secret"]
    clearance_dict = {"public": 1, "confidential": 2, "secret": 3, "top_secret": 4}
    dynamic_clearance = []

    for level in range(clearance_dict[user_clearance]):
        dynamic_clearance.append(clearance_list[level])

    return dynamic_clearance


# Admin Functions #

def admin_execution(database, query):
    if database not in ["reports", "profiles"]:
        return False, f"Failed To Connect To {database}.db"

    if any(statement in query.lower() for statement in ["drop", "create", "insert"]):
        return False, "Admins Are Unable To Run DROP or DELETE statements"

    if database == "reports":
        conn = sqlite3.connect("databases/reports.db")
        c = conn.cursor()
        try:
            c.execute(f"{query}")
            sql_response = c.fetchall()

            if "update" in query.lower():

                if c.rowcount < 1:
                    c.close()
                    return False, "Failed To Update Record"

                if c.rowcount > 1:
                    c.close()
                    return False, "You Cannot Update More Than One Record At Once"

                else:
                    commit_close(conn)
                    return True, "Updated Record"

            if 0 == len(sql_response) > 1:
                return False, "You Cannot Alter More Than One Record At Once"

            else:
                return True, sql_response[0]  # Should be the only element inside

        except Exception as e:
            with open("./misc/database_logs.txt", "a") as log:
                log.write(f"AdminSQL,{query},{e},{database},{datetime.now(timezone.utc)}\n")  # Logs download request
            conn.close()
            return False, str(e)

    if database == "profiles":
        conn = sqlite3.connect("databases/profiles.db")
        c = conn.cursor()

        if "profiles" in query:
            query = query.replace("profiles", "profile")

        try:
            c.execute(f"{query}")
            sql_response = c.fetchall()

            if "update" in query.lower():

                if c.rowcount < 1:
                    c.close()
                    return False, "Failed To Update Record"

                if c.rowcount > 1:
                    c.close()
                    return False, "You Cannot Update More Than One Record At Once"

                else:
                    commit_close(conn)
                    return True, "Updated Record"

            if 0 == len(sql_response) > 1:
                return False, "You Cannot Alter More Than One Record At Once"

            else:
                return True, sql_response  # Should be the only element inside

        except Exception as e:
            with open("./misc/database_logs.txt", "a") as log:
                log.write(f"AdminSQL,{query},{e},{database},{datetime.now(timezone.utc)}\n")  # Logs download request
            conn.close()
            return False, str(e)


def search_user(name):
    conn = sqlite3.connect("databases/profiles.db")
    c = conn.cursor()
    c.execute("SELECT * FROM profile WHERE username LIKE ?", (f"%{name}%",))
    results = c.fetchall()

    if not results:  # No results
        return False, []

    filter_results = []

    for element in results:
        if element[8] == 1:
            results.remove(element) # Removes admins from results
        else:
            filter_results.append(element)

    if len(filter_results) == 0:  # Only results were admin
        return False, []

    dict_list = []
    for result in results:
        dict_list.append(
            {
                "id": result[0],
                "name": result[1],
                "email": result[2],
                "ip": result[5],
                "clearance": result[6]
            }
        )

    return True, dict_list

