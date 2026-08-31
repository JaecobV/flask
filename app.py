"""Flask application for browsing Korean music groups and voting."""

import os
import sqlite3

from flask import (
    Flask,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


DATABASE = os.path.join(os.path.dirname(__file__), "database.db")

app = Flask(__name__)
app.secret_key = "random-secret-key-for-me"


@app.teardown_appcontext
def close_connection(exception):
    """Close the database connection when the request ends."""

    # Gets the database connection stored for the current request.
    # If a connection exists, it is closed so the database is not
    # left open after the page has finished loading.
    db = getattr(g, "_database", None)

    if db is not None:
        db.close()


def get_db():
    """Return the current database connection."""

    # Checks whether a database connection already exists for this request.
    # This prevents the application from creating a new connection every
    # time a database query is made.
    db = getattr(g, "_database", None)

    if db is None:
        # Creates a connection to the SQLite database if one does not exist.
        db = g._database = sqlite3.connect(DATABASE)

        # Allows database columns to be accessed using their column names
        # instead of only using their numerical positions.
        db.row_factory = sqlite3.Row

    return db


def query_db(query, args=(), one=False):
    """Run a database query and return the results."""

    # Executes the SQL query using the supplied arguments.
    # Parameters are used instead of directly adding user input to
    # the SQL query.
    cur = get_db().execute(query, args)
    results = cur.fetchall()
    cur.close()

    # If only one result is requested, return the first result.
    # If there are no results, return None instead.
    if one:
        return results[0] if results else None

    return results


@app.route("/")
def home():
    """Display the homepage and allow users to search and filter groups."""

    # Gets the search text and group type from the URL.
    # strip() removes any unnecessary spaces entered by the user.
    search = request.args.get("search", "").strip()
    group_type = request.args.get("type", "").strip()

    # If a group type has been selected, only groups matching that type
    # are retrieved from the database.
    if group_type:
        sql = """
            SELECT GroupID,
                   GroupName,
                   TopSongs,
                   DebutDate,
                   GroupImage
            FROM Groups
            WHERE GroupType = ?
            ORDER BY GroupName;
        """
        results = query_db(sql, (group_type,))

    # If the user entered a search term, find groups whose names contain
    # the search text. The % symbols allow partial matches.
    elif search:
        sql = """
            SELECT GroupID,
                   GroupName,
                   TopSongs,
                   DebutDate,
                   GroupImage
            FROM Groups
            WHERE GroupName LIKE ?
            ORDER BY GroupName;
        """
        results = query_db(sql, ("%" + search + "%",))

    # If there is no search or filter, display all groups.
    else:
        sql = """
            SELECT GroupID,
                   GroupName,
                   TopSongs,
                   DebutDate,
                   GroupImage
            FROM Groups
            ORDER BY GroupName;
        """
        results = query_db(sql)

    # Sends the database results and current search/filter values
    # to the HTML template so they can be displayed on the homepage.
    return render_template(
        "home.html",
        results=results,
        search=search,
        group_type=group_type,
    )


@app.route("/group/<int:group_id>")
def group(group_id):
    """Display information about a specific music group."""

    # Retrieves member information for the selected group.
    # Members and MemberInfo are joined using MemberID so information
    # from both tables can be displayed together.
    member_sql = """
        SELECT Members.MemberNames,
               Members.MemberImage,
               MemberInfo.BirthName,
               MemberInfo.BirthDate,
               MemberInfo.Nationality,
               MemberInfo.Position,
               MemberInfo.FunFact
        FROM Members
        JOIN MemberInfo
            ON Members.MemberID = MemberInfo.MemberID
        WHERE Members.GroupID = ?;
    """

    # Retrieves the main information for the selected group.
    # The group_id from the URL is used to make sure the correct group
    # is displayed.
    group_sql = """
        SELECT Groups.GroupName,
               Groups.TopSongs,
               Groups.DebutDate,
               Groups.GroupImage,
               Groups.GroupImageAlt,
               Groups.VideoURL,
               Groups.ThemeClass,
               Groups.GroupSong
        FROM Groups
        WHERE GroupID = ?;
    """

    members = query_db(member_sql, (group_id,))
    group_data = query_db(group_sql, (group_id,), True)

    # If the group ID does not exist in the database, display the custom
    # 404 page instead of trying to display an empty group page.
    if group_data is None:
        return render_template("404.html"), 404

    # Sends the group and member information to the group HTML template.
    return render_template(
        "group.html",
        members=members,
        group=group_data,
    )


@app.route("/companies")
def companies():
    """Display all entertainment companies."""

    # Retrieves the information for all companies and sorts them
    # alphabetically by company name.
    company_list = query_db(
        """
        SELECT CompanyID,
               CompanyName,
               CompanyLogo,
               FoundedYear,
               Founder,
               CEO,
               Headquarters,
               Description
        FROM Companies
        ORDER BY CompanyName;
        """
    )

    # Sends the company information to the HTML template.
    return render_template(
        "companies.html",
        companies=company_list,
    )


@app.route("/company/<int:company_id>")
def company(company_id):
    """Display information about a specific entertainment company."""

    # Searches for the company using the ID provided in the URL.
    # Only one company should match the ID.
    company_data = query_db(
        """
        SELECT CompanyID,
               CompanyName,
               CompanyLogo,
               FoundedYear,
               Founder,
               CEO,
               Headquarters,
               Description
        FROM Companies
        WHERE CompanyID = ?;
        """,
        (company_id,),
        True,
    )

    # If the company ID does not exist, show the custom 404 page.
    if company_data is None:
        return render_template("404.html"), 404

    # Sends the selected company's information to the HTML template.
    return render_template(
        "company.html",
        company=company_data,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    """Allow a new user to create an account."""

    if request.method == "POST":
        # Gets the username and password submitted through the form.
        # strip() removes spaces from the beginning and end of the username.
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Checks that both required fields have been entered before
        # attempting to create an account.
        if not username or not password:
            return render_template(
                "register.html",
                error="Please enter a username and password.",
            )

        # Makes sure the password meets the minimum length requirement
        # before allowing the account to be created.
        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters long.",
            )

        # Hashes the password before storing it in the database.
        # This means the user's actual password is not stored directly.
        hashed_password = generate_password_hash(password)

        conn = get_db()

        try:
            # Adds the new user's details to the Users table.
            # ? placeholders are used instead of directly inserting
            # the user's input into the SQL statement.
            conn.execute(
                """
                INSERT INTO Users (Username, Password)
                VALUES (?, ?)
                """,
                (username, hashed_password),
            )

            # Saves the new account permanently to the database.
            conn.commit()

            # Sends the user to the login page after successful registration.
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            # Displays an error if the username already exists.
            return render_template(
                "register.html",
                error="Username already exists.",
            )

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Allow an existing user to log into their account."""

    if request.method == "POST":
        # Gets the login details submitted by the user.
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Checks that the user has entered both required login fields.
        if not username or not password:
            return render_template(
                "login.html",
                error="Please enter a username and password.",
            )

        # Finds the account matching the entered username.
        # The password is retrieved so it can be checked against
        # the stored password hash.
        user = query_db(
            """
            SELECT UserID,
                   Username,
                   Password
            FROM Users
            WHERE Username = ?
            """,
            (username,),
            one=True,
        )

        # Checks that the username exists and that the entered password
        # matches the stored password hash.
        if user and check_password_hash(user["Password"], password):
            # Stores the user's ID and username in the session so the
            # application knows which user is currently logged in.
            session["user_id"] = user["UserID"]
            session["username"] = user["Username"]

            return redirect(url_for("home"))

        # If the account does not exist or the password is incorrect,
        # display an error instead of logging the user in.
        return render_template(
            "login.html",
            error="Incorrect username or password.",
        )

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log the current user out and return to the homepage."""

    # Clears the user's session information so they are no longer
    # recognised as being logged in.
    session.clear()

    return redirect(url_for("home"))


@app.route("/vote", methods=["GET", "POST"])
def vote():
    """Allow logged-in users to vote for their favourite group."""

    # Voting is only available to logged-in users.
    # If the user is not logged in, they are redirected to the login page.
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    user_id = session["user_id"]

    # Checks the Votes table to see whether the current user has
    # already submitted a vote.
    existing_vote = conn.execute(
        """
        SELECT VoteID
        FROM Votes
        WHERE UserID = ?
        """,
        (user_id,),
    ).fetchone()

    # If the user has already voted, they cannot submit another vote.
    # Instead, the current voting results are displayed.
    if existing_vote:
        results = conn.execute(
            """
            SELECT Groups.GroupName,
                   COUNT(Votes.VoteID) AS VoteCount
            FROM Groups
            LEFT JOIN Votes
                ON Groups.GroupID = Votes.GroupID
            GROUP BY Groups.GroupID
            ORDER BY VoteCount DESC;
            """
        ).fetchall()

        return render_template(
            "vote.html",
            already_voted=True,
            results=results,
        )

    if request.method == "POST":
        # Gets the group selected by the user from the voting form.
        group_id = request.form.get("group_id")

        # Checks that the user actually selected a group.
        if not group_id:
            groups = query_db(
                """
                SELECT GroupID,
                       GroupName,
                       GroupImage
                FROM Groups
                ORDER BY GroupName;
                """
            )

            return render_template(
                "vote.html",
                groups=groups,
                already_voted=False,
                error="Please select a group before voting.",
            )

        # Checks that the selected group actually exists in the database.
        group_data = query_db(
            """
            SELECT GroupID
            FROM Groups
            WHERE GroupID = ?
            """,
            (group_id,),
            True,
        )

        # If the group ID does not exist, return an error instead of
        # adding an invalid vote to the database.
        if group_data is None:
            groups = query_db(
                """
                SELECT GroupID,
                       GroupName,
                       GroupImage
                FROM Groups
                ORDER BY GroupName;
                """
            )

            return render_template(
                "vote.html",
                groups=groups,
                already_voted=False,
                error="Invalid group selected.",
            )

        # Adds the user's vote to the Votes table after all validation
        # checks have passed.
        conn.execute(
            """
            INSERT INTO Votes (UserID, GroupID)
            VALUES (?, ?)
            """,
            (user_id, group_id),
        )

        # Saves the vote to the database.
        conn.commit()

        # Counts how many votes each group has received.
        # LEFT JOIN is used so groups with zero votes are also included
        # in the results instead of being left out.
        results = conn.execute(
            """
            SELECT Groups.GroupName,
                   COUNT(Votes.VoteID) AS VoteCount
            FROM Groups
            LEFT JOIN Votes
                ON Groups.GroupID = Votes.GroupID
            GROUP BY Groups.GroupID
            ORDER BY VoteCount DESC;
            """
        ).fetchall()

        return render_template(
            "vote.html",
            already_voted=True,
            results=results,
        )

    # Gets all groups so the user can choose one when they first
    # open the voting page.
    groups = query_db(
        """
        SELECT GroupID,
               GroupName,
               GroupImage
        FROM Groups
        ORDER BY GroupName;
        """
    )

    return render_template(
        "vote.html",
        groups=groups,
        already_voted=False,
    )


@app.errorhandler(404)
def page_not_found(error):
    """Display a custom page when a requested page cannot be found."""

    # Flask calls this function when a user visits a URL that does not
    # exist. The custom page gives the user an explanation and allows
    # them to return to the website.
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)