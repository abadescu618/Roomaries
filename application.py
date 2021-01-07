import os
import csv
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, usd
from datetime import datetime

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///roomaries.db")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    first = request.form.get("first")
    last = request.form.get("last")
    unique = request.form.get("unique")

    # User submits form
    if request.method == "POST":

        # Error checking inputs
        if not username:
            return render_template("noinput.html")

        elif not password:
            return render_template("noinput.html")

        elif not confirmation:
            return render_template("noinput.html")

        elif not first or not last:
            return render_template("noinput.html")

        elif not unique:
            return render_template("noinput.html")

        elif "@" not in email:
            return render_template("invalidemail.html")

        elif password != confirmation:
            return render_template("invalidpw.html")

        elif len(unique) > 10 or len(unique) == 0:
            return render_template("invalidcode.html")

        # Check if user already taken
        usernames = db.execute("SELECT username FROM users WHERE username = :username", username=username)

        if len(usernames) > 0 :
            return render_template("invaliduser.html")

        # Insert into db
        pw_hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash, first, last, code, email) VALUES (:username, :hash, :first, :last, :unique, :email)", username=username, hash=pw_hash, first=first, last=last, unique=unique, email=email)

        # Create new table for roomie group
        db.execute("CREATE TABLE IF NOT EXISTS :code (grocery TEXT NOT NULL)", code=unique)

        # Remember user session
        result = db.execute("SELECT id FROM users WHERE username = :username", username=username)
        session["user_id"] = result[0]["id"]

        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("noinput.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("noinput.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("invalidlogin.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/")
@login_required
def index():
    '''Welcome/analytics page'''

    # Recognize current user
    user = session["user_id"]
    name = db.execute("SELECT first FROM users WHERE id == :user", user=user)
    name = name[0]['first']

    # Get unique identifier of roomie group
    code_db = db.execute("SELECT code FROM users WHERE id == :user", user=user)
    code = code_db[0]['code']

    # Get user's total number of roommates
    roomie_count_db = db.execute("SELECT count(id) FROM users WHERE code == :code", code=code)
    roomie_count = roomie_count_db[0]['count(id)']

    today = datetime.today()

    # Total grocery spend this month
    date_begin = datetime(today.year, today.month, 1)
    date_end = datetime(today.year, today.month, 31)

    db_output = db.execute("SELECT sum(t.bill) FROM transactions t INNER JOIN users u ON t.user_id = u.id WHERE u.code = :code AND t.updated BETWEEN :begin AND :end", code=code, begin=date_begin, end=date_end)
    total_month = db_output[0]['sum(t.bill)']

    if not total_month:
        total_month_pp = 0
    else:
        total_month_pp = round(total_month / roomie_count, 2)

    # Total grocery spend this year
    date_begin = datetime(today.year, 1, 1)
    date_end = datetime(today.year, 12, 31)

    db_output = db.execute("SELECT sum(t.bill) FROM transactions t INNER JOIN users u ON t.user_id = u.id WHERE u.code = :code AND t.updated BETWEEN :begin AND :end", code=code, begin=date_begin, end=date_end)

    total_year = db_output[0]['sum(t.bill)']

    if not total_year:
        total_year_pp = 0
    else:
        total_year_pp = round(total_year / roomie_count,2 )

    # Average monthly grocery spend
    month = datetime.now().month
    date_begin = datetime(today.year, 1, 1)
    date_end = datetime(today.year, month, 31)

    db_output = db.execute("SELECT sum(t.bill) FROM transactions t INNER JOIN users u ON t.user_id = u.id WHERE u.code = :code AND t.updated BETWEEN :begin AND :end", code=code, begin=date_begin, end=date_end)

    ytd_total = db_output[0]['sum(t.bill)']

    if not ytd_total:
        ytd_total_monthly_pp = 0
    else:
        ytd_total_monthly = ytd_total / month
        ytd_total_monthly_pp = round(ytd_total_monthly / roomie_count, 2)

    # Top 3 items purchased
    db_output = db.execute("SELECT h.grocery, count(h.grocery) FROM history h INNER JOIN users u ON h.user_id = u.id WHERE u.code = :code GROUP BY h.grocery ORDER BY count(h.grocery) DESC LIMIT 3", code=code)

    top3 = []

    if len(db_output) != 0:
        for each in range(len(db_output)):
            top3.append(db_output[each]['grocery'])

    length = len(top3)

    return render_template("index.html", user=name, code=code, total_month_pp=total_month_pp, ytd_total_monthly_pp=ytd_total_monthly_pp, total_year_pp=total_year_pp,top3=top3, length=length)

@app.route("/roomies", methods=["GET"])
@login_required
def roomies():
    '''Fetch current user's roomies'''
    # Note: buggy if different groups of roommates select the same unique identifier

    # Recognize current user
    user = session["user_id"]
    name = db.execute("SELECT first FROM users WHERE id == :user", user=user)
    name = name[0]['first']

    # Get unique identifier of roomie group
    code_db = db.execute("SELECT code FROM users WHERE id == :user", user=user)
    code = code_db[0]['code']

    # Pull current user's roommate unique identifier
    unique_db = db.execute("SELECT code FROM users WHERE id==:user", user=user)
    unique = unique_db[0]["code"]

    # Create a list of current user's roommates' names
    current_first_db = db.execute("SELECT first FROM users WHERE id==:user", user=user)
    current_first = current_first_db[0]["first"]
    current_last_db = db.execute("SELECT last FROM users WHERE id==:user", user=user)
    current_last = current_last_db[0]["last"]
    current_user = str(current_first + ' ' + current_last)

    roomies_db = db.execute("SELECT first, last FROM users WHERE code==:unique", unique=unique)
    roomies = []
    for each in roomies_db:
        full = str(each["first"] + ' ' + each["last"])
        if full != current_user:
            roomies.append(full)

    return render_template("roomies.html", roomies=roomies, count=len(roomies), code=code, user=name)

@app.route("/current")
@login_required
def current():
    '''Display current grocery list & allow user to update'''

    # Default groceries with emojis
    emoji_db = db.execute("SELECT * FROM emojis")
    groceries = []

    for each in range(len(emoji_db)):
        groceries.append(emoji_db[each]['lookup'])

    # Get unique identifier of roomie group
    # Recognize current user
    user = session["user_id"]
    name = db.execute("SELECT first FROM users WHERE id == :user", user=user)
    name = name[0]['first']
    code_db = db.execute("SELECT code FROM users WHERE id == :user", user=user)
    code = code_db[0]['code']

    # Get current grocery list
    current_list = []
    current_list_db = db.execute("SELECT * FROM :code", code=code)

    for each in range(len(current_list_db)):
        current_list.append(current_list_db[each]['grocery'])

    with open('emojis.csv', mode = 'r') as infile:
        reader = csv.reader(infile)
        emojidict = {rows[1]:rows[2] for rows in reader}

    combo = []
    for each in groceries:
        combo_item = str(emojidict[each] + ' ' + each)
        combo.append(combo_item)

    return render_template("current.html", code=code, current_list=current_list, count=len(current_list), emojidict=emojidict, user=name, combo=combo)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    '''Display current grocery list & allow user to update'''

    # Default groceries with emojis
    emoji_db = db.execute("SELECT * FROM emojis")
    groceries = []

    for each in range(len(emoji_db)):
        groceries.append(emoji_db[each]['lookup'])

    # Get unique identifier of roomie group
    # Recognize current user
    user = session["user_id"]
    name = db.execute("SELECT first FROM users WHERE id == :user", user=user)
    name = name[0]['first']
    code_db = db.execute("SELECT code FROM users WHERE id == :user", user=user)
    code = code_db[0]['code']

    # Get current grocery list
    current_list = []
    current_list_db = db.execute("SELECT * FROM :code", code=code)

    for each in range(len(current_list_db)):
        current_list.append(current_list_db[each]['grocery'])

    with open('emojis.csv', mode = 'r') as infile:
        reader = csv.reader(infile)
        emojidict = {rows[1]:rows[2] for rows in reader}

    combo = []
    for each in groceries:
        combo_item = str(emojidict[each] + ' ' + each)
        combo.append(combo_item)

    if request.method == "POST":

        # Adding to the list
        added_item = request.form.get('addedItem')
        action = 'add'

        if not added_item:
            return render_template("noinput.html")

        else:
            if added_item not in current_list:
                db.execute("INSERT INTO :code (grocery) VALUES (:item)", code=code,item=added_item)

            db.execute("INSERT INTO history (user_id, grocery, action) VALUES (:user, :item, :action)", user=user, item=added_item, action=action)

            return redirect("/current")

    else:
        return render_template("current.html", code=code, current_list=current_list, count=len(current_list), emojidict=emojidict, user=name, combo=combo)

@app.route("/remove", methods=["GET", "POST"])
@login_required
def remove():
    '''Display current grocery list & allow user to update'''

    # Default groceries with emojis
    emoji_db = db.execute("SELECT * FROM emojis")
    groceries = []

    for each in range(len(emoji_db)):
        groceries.append(emoji_db[each]['lookup'])

    # Get unique identifier of roomie group
    # Recognize current user
    user = session["user_id"]
    name = db.execute("SELECT first FROM users WHERE id == :user", user=user)
    name = name[0]['first']
    code_db = db.execute("SELECT code FROM users WHERE id == :user", user=user)
    code = code_db[0]['code']

    # Get current grocery list
    current_list = []
    current_list_db = db.execute("SELECT * FROM :code", code=code)

    for each in range(len(current_list_db)):
        current_list.append(current_list_db[each]['grocery'])

    with open('emojis.csv', mode = 'r') as infile:
        reader = csv.reader(infile)
        emojidict = {rows[1]:rows[2] for rows in reader}

    combo = []
    for each in groceries:
        combo_item = str(emojidict[each] + ' ' + each)
        combo.append(combo_item)

    if request.method == "POST":

        # Removing from the list
        removed_items = request.form.getlist('removedItem')
        action = 'remove'

        for each in range(len(removed_items)):
            if removed_items[each] in groceries:
                removed_items[each] = removed_items[each][2:]
            else:
                removed_items[each] = removed_items[each][1:]

        for each in removed_items:
            db.execute("DELETE FROM :code WHERE grocery==:item", code=code, item=each)
            db.execute("INSERT INTO history (user_id, grocery, action) VALUES (:user, :item, :action)", user=user, item=each, action=action)

        return redirect("/current")

    else:
        return render_template("current.html", code=code, current_list=current_list, count=len(current_list), emojidict=emojidict, user=name, combo=combo)

@app.route("/split", methods=["GET", "POST"])
@login_required
def split():
    '''Allow users to enter amount paid for groceries & send email notification to roommates to split bill'''

    # Recognize user
    user = session["user_id"]
    name = db.execute("SELECT first FROM users WHERE id == :user", user=user)
    name = name[0]['first']
    code_db = db.execute("SELECT code FROM users WHERE id == :user", user=user)
    code = code_db[0]['code']
    roomie_count_db = db.execute("SELECT count(id) FROM users WHERE code == :code", code=code)
    roomie_count = roomie_count_db[0]['count(id)']

    if request.method == "POST":
        total_cost = request.form.get("totalCost")

        if not total_cost:
            return render_template("noinput.html")

        else:
            db.execute("INSERT INTO transactions (user_id, bill) VALUES (:user, :bill)", user=user, bill=total_cost)
            return redirect("/")

    else:
        return render_template("split.html", user=name, code=code, roomie_count=roomie_count)

@app.route("/history", methods=["GET"])
@login_required
def history():
    '''Show history of roomate changes to grocery list'''

    # Recognize user
    user = session["user_id"]
    name = db.execute("SELECT first FROM users WHERE id == :user", user=user)
    name = name[0]['first']
    code_db = db.execute("SELECT code FROM users WHERE id == :user", user=user)
    code = code_db[0]['code']

    # Query db for history of current roomie group
    history_db = db.execute("SELECT u.first, h.grocery, h.action, h.updated FROM history h INNER JOIN users u ON h.user_id = u.id WHERE u.code = :code ORDER BY h.updated DESC", code=code)

    list_display = []
    for item in history_db:
        name = item['first']
        grocery = item['grocery']
        action = item['action']
        if action == 'add':
            action = 'added'
        else:
            action = 'removed'
        time = item['updated'][:10]

        list_display.append([name, action, grocery, time])

    return render_template("history.html", user=name, code=code, list_display=list_display)

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# Error handler
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
