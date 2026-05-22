import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


    """Show portfolio of stocks"""
    cash = 0
    user_id = session["user_id"]

    symbol, shares, price, total = None, None, None, None

    if request.method == "GET":

        # extract all the data that needs to be displayed from finance DB
        csh = db.execute(
            "SELECT cash FROM users WHERE id = ?", user_id
        )

        for row in csh:

            currentCash = row["cash"]

        cash = usd(float(currentCash))

        portfolio = db.execute(

            "SELECT * FROM portfolio JOIN users ON portfolio.id = users.id WHERE users.id = ? GROUP BY symbol", user_id
        )

        for row in portfolio:

            symbol = row["symbol"]
            shares = row["shares"]
            price = row["price"]
            total = row["total"]

    return render_template("index.html", user_id=user_id, symbol=symbol, shares=shares, price=price, total=total, cash=cash, portfolio=portfolio)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    symbol = ""

    shrePrice = 0

    portSymbol = ""

    portShares = 0

    portTotal = 0

    newTotal = 0

    newShares = 0

    if request.method == "POST":

        user_id = session["user_id"]

        smbol = request.form.get("symbol")

        symbol = smbol.upper()

        # use lookup function from helpers, usings API
        info = lookup(symbol)

        # get amount of shares from form
        shrs = request.form.get("shares")

        try:
            if not shrs or not shrs.isdigit():
                return apology("Enter a positive integer", 400)
        except ValueError:
            return apology("Enter a positive integer", 400)

        # amount of shares
        shares = int(shrs)

        try:
            if not shrs.isdigit() or shares <= 0:
                return apology("shares must be a positive integer", 400)

        except ValueError:
            return apology("shares must be a positive integer", 400)

        if not shares:
            return apology("provide shares quantity", 400)

        if not info:
            return apology("Invalid Symbol")

        # share price from lookup function using API
        shrePrice = info["price"]

        # converting price to float
        price = float(shrePrice)

        # Total Price for shares
        total = price * shares

        total = float(total)

        if not symbol:

            return apology("please provide a valid stock symbol", 400)

        portfolio = db.execute(

            "SELECT * FROM portfolio JOIN users ON portfolio.id = users.id WHERE users.id = ?", user_id

        )

        if not symbol or not info:
            return apology("invalid stock symbol", 400)

        for row in portfolio:

            portShares = row["shares"]
            portTotal = row["total"]
            portSymbol = row["symbol"]

        if symbol == portSymbol:

            newTotal = total + portTotal
            newShares = shares + portShares

            db.execute(

                "UPDATE portfolio SET total = ?, shares =? WHERE id= ? AND symbol = ?", newTotal, newShares, user_id, symbol
            )

            db.execute(

                "INSERT INTO transactions (id,symbol,shares,price) VALUES(?,?,?,?)", user_id, symbol, shares, price
            )

        else:

            db.execute(

                "INSERT INTO portfolio (id,symbol,shares,price,total) VALUES(?,?,?,?,?)", user_id, symbol, shares, price, total

            )

            db.execute(

                "INSERT INTO transactions (id,symbol,shares,price) VALUES(?,?,?,?)", user_id, symbol, shares, price
            )

        # Obtaining cash from db
        currentCash = db.execute("SELECT cash FROM users WHERE id =?", user_id)[0]["cash"]

        currentCash = float(currentCash)

        if total > currentCash:
            return apology("OOPS! you dont have enough cash mate", 400)

         # New cash balance
        cash = round(currentCash - total, 2)

        newCash = usd(cash)

        # Update user cash balance in db
        db.execute("UPDATE users SET cash = ?", cash)

        return redirect("/")

        # return render_template("index.html", user_id=user_id, symbol=symbol, shares=shares, price=price, total=total, portfolio=portfolio, cash=newCash)

    if request.method == "GET":
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    symbol = ""

    shares = 0

    price = 0

    transacted = 0

    user_id = session["user_id"]

    transactions = db.execute(

        "SELECT * FROM transactions WHERE id =?", user_id
    )

    if request.method == "GET":

        for row in transactions:

            symbol = row["symbol"]
            shares = row["shares"]
            price = row["price"]
            transacted = row["date"]

        return render_template("history.html", symbol=symbol, shares=shares, price=price, transacted=transacted, transactions=transactions)

    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):

            return apology("invalid username and/or password", 400)
        

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout", methods=["GET"])
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    if request.method == "GET":

        return render_template("login.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
 # lookup share price
    if request.method == "POST":

        symbol = request.form.get("symbol")

        if not symbol:

            return apology("Provide a valid Stock Symbol", 400)

        quoted = lookup(symbol)

        if not quoted:
            return apology("Invalid stock symbol", 400)

        return render_template("quoted.html", quoted=quoted)

    if not request.method == "POST":

        return render_template("quote.html")

    elif quoted == None:

        return apology("Fill in a Symbol")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget user ID

    session.clear()

    userNameCheck = ""

    if request.method == "POST":

        # ensure username & password was submitted

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        hash = ()

        if not username or username == None:
            return apology("must create username!", 400)

        if not password:
            return apology("must create password", 400)

        # Ensure confirmed password and password match
        if not password == confirmation:

            return apology("Passwords Dont match!!!", 400)

        userNameChck = db.execute(
            "SELECT * FROM users WHERE username = ?", username
        )

        for row in userNameChck:

            userNameCheck = row["username"]

        # See that created username dont exist in db
        if (username == userNameCheck):

            return apology("Username already exist")

        else:
            # hash passwword
            hash = generate_password_hash(password)

            db.execute(

                "INSERT INTO users (username,hash) VALUES(?,?)", username, hash
            )

        return render_template("login.html")

    if request.method == "GET":

        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    user_id = session["user_id"]

    sellShares = request.form.get("shares")

    if not sellShares or not sellShares.isdigit() or int(sellShares) <= 0:
        return apology("Invalid number of shares", 400)

    sellShares = int(sellShares)

    sellSymbol = request.form.get("symbol")

    if not sellSymbol:

        return apology("Provide Symbol", 400)

    users = db.execute(

        "SELECT * FROM users WHERE id = ?", user_id
    )

    # Sell shares of stock

    portfolio = db.execute(

        "SELECT * FROM portfolio WHERE id = ?", user_id
    )

    if not portfolio or portfolio[0]["shares"] < sellShares:

        return apology("Not enough shares", 400)

    if request.method == "GET":

        symbol = ""

        for row in portfolio:

            symbol = row["symbol"]

        return render_template("sell.html", symbol=symbol, portfolio=portfolio,)

    if request.method == "POST":

        currentShares = 0

        for row in users:

            currentCash = row["cash"]

        for row in portfolio:
            symbol = row["symbol"]
            currentShares = int(row["shares"])
            price = int(row["price"])
            total = int(row["total"])

            if sellSymbol == symbol:

                shares = currentShares - int(sellShares)
                total = total - (int(sellShares) * price)
                cash = int(currentCash) + total

                db.execute(
                    "UPDATE portfolio SET shares = ?,total = ? WHERE id = ? AND symbol = ?", shares, total, user_id, sellSymbol
                )

                db.execute(
                    "UPDATE users SET cash =? WHERE id = ?", cash, user_id
                )

                db.execute(

                    "INSERT INTO transactions (id,symbol,shares,price) VALUES(?,?,?,?)", user_id, symbol, -int(
                        sellShares), price
                )

            return redirect("/")

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():

    user_id = session["user_id"]

    depositCash = request.form.get("amount")

    if request.method == "POST":

        user = db.execute(

            "SELECT cash FROM users WHERE id = ?", user_id
        )

        for row in user:

            currentCash = row["cash"]

            newCash = int(currentCash) + int(depositCash)

            db.execute(

                "UPDATE users SET cash = ? WHERE id = ?", newCash, user_id
            )

            portfolio = db.execute(

                "SELECT * FROM portfolio"
            )

            for row in portfolio:

                symbol = row["symbol"]
                shares = row["shares"]
                price = row["price"]
                total = row["total"]

        return render_template("index.html", cash=newCash, symbol=symbol, shares=shares, price=price, total=total)

    if request.method == "GET":

        return render_template("deposit.html")
