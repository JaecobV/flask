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
    db = getattr(g, "_database", None)


    if db is not None:
        db.close()




def get_db():
    """Return the current database connection."""
    db = getattr(g, "_database", None)


    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row


    return db




def query_db(query, args=(), one=False):
    """Run a database query and return the results."""
    cur = get_db().execute(query, args)
    results = cur.fetchall()
    cur.close()


    if one:
        return results[0] if results else None


    return results




@app.route("/")
def home():
    """Display the homepage and allow users to search and filter groups."""


    search = request.args.get("search", "").strip()
    group_type = request.args.get("type", "").strip()


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


    return render_template(
        "home.html",
        results=results,
        search=search,
        group_type=group_type,
    )




@app.route("/group/<int:group_id>")
def group(group_id):
    """Display information about a specific music group."""


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


    if group_data is None:
        return render_template("404.html"), 404


    return render_template(
        "group.html",
        members=members,
        group=group_data,
    )




@app.route("/companies")
def companies():
    """Display all entertainment companies."""


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


    return render_template(
        "companies.html",
        companies=company_list,
    )




@app.route("/company/<int:company_id>")
def company(company_id):
    """Display information about a specific entertainment company."""


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


    if company_data is None:
        return render_template("404.html"), 404


    return render_template(
        "company.html",
        company=company_data,
    )




@app.route("/register", methods=["GET", "POST"])
def register():
    """Allow a new user to create an account."""


    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")


        if not username or not password:
            return render_template(
                "register.html",
                error="Please enter a username and password.",
            )


        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters long.",
            )


        hashed_password = generate_password_hash(password)


        conn = get_db()


        try:
            conn.execute(
                """
                INSERT INTO Users (Username, Password)
                VALUES (?, ?)
                """,
                (username, hashed_password),
            )


            conn.commit()


            return redirect(url_for("login"))


        except sqlite3.IntegrityError:
            return render_template(
                "register.html",
                error="Username already exists.",
            )


    return render_template("register.html")




@app.route("/login", methods=["GET", "POST"])
def login():
    """Allow an existing user to log into their account."""


    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")


        if not username or not password:
            return render_template(
                "login.html",
                error="Please enter a username and password.",
            )


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


        if user and check_password_hash(user["Password"], password):
            session["user_id"] = user["UserID"]
            session["username"] = user["Username"]


            return redirect(url_for("home"))


        return render_template(
            "login.html",
            error="Incorrect username or password.",
        )


    return render_template("login.html")




@app.route("/logout")
def logout():
    """Log the current user out and return to the homepage."""


    session.clear()


    return redirect(url_for("home"))


@app.route("/vote", methods=["GET", "POST"])
def vote():
    """Allow logged-in users to vote for their favourite group."""

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    user_id = session["user_id"]

    existing_vote = conn.execute(
        """
        SELECT VoteID
        FROM Votes
        WHERE UserID = ?
        """,
        (user_id,),
    ).fetchone()

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
        group_id = request.form.get("group_id")

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

        group_data = query_db(
            """
            SELECT GroupID
            FROM Groups
            WHERE GroupID = ?
            """,
            (group_id,),
            True,
        )

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

        conn.execute(
            """
            INSERT INTO Votes (UserID, GroupID)
            VALUES (?, ?)
            """,
            (user_id, group_id),
        )

        conn.commit()

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
    return render_template("404.html"), 404




if __name__ == "__main__":
    app.run(debug=True)