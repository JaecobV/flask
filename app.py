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


DATABASE = os.path.join(os.path.dirname(__file__), 'database.db')

app = Flask(__name__)
app.secret_key = "random-secret-key-for-me"


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

        
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


@app.route("/")
def home():

    #home page
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


#group page
@app.route("/group/<int:group_id>")
def group(group_id):

    member_sql = """
        SELECT Members.MemberNames,
               Members.MemberImage,
               MemberInfo.BirthName,
               MemberInfo.BirthDate,
               MemberInfo.Nationality,
               MemberInfo.Position,
               MemberInfo.FunFact
        FROM Members
        JOIN MemberInfo ON Members.MemberID = MemberInfo.MemberID
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


#companies page
@app.route("/companies")
def companies():

    company_list = query_db("""
        SELECT CompanyID,
               CompanyName,
               CompanyLogo,
               FoundedYear,
               Founder,
               CEO,
               Headquarters,
               Description
        FROM Companies
        ORDER BY CompanyName
    """)

    return render_template(
        "companies.html",
        companies=company_list,
    )


#company page
@app.route("/company/<int:company_id>")
def company(company_id):

    company_data = query_db("""
        SELECT CompanyID,
               CompanyName,
               CompanyLogo,
               FoundedYear,
               Founder,
               CEO,
               Headquarters,
               Description
        FROM Companies
        WHERE CompanyID = ?
    """, (company_id,), True)

    if company_data is None:
        return render_template("404.html"), 404


    return render_template(
        "company.html",
        company=company_data
    )

#register form page
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        #checks how long the password is
        if len(password) < 8:
            return render_template("register.html",error="Password must be at least 8 characters long.")

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO Users (Username, Password) VALUES (?, ?)",(username, hashed_password))

            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            conn.close()

            return render_template("register.html",error="Username already exists.")

    return render_template("register.html")

#login form page
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM Users WHERE Username = ?",
            (username,)
            )

        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user[2], password):

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect(url_for("home"))

        else:
            return render_template("login.html",error="Incorrect username or password.")

    return render_template("login.html")


#logout page
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

#group voting page
@app.route("/vote", methods=["GET", "POST"])
def vote():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    user_id = session["user_id"]

    #checks if the user has already voted
    cursor.execute("SELECT * FROM Votes WHERE UserID = ?",(user_id,))

    existing_vote = cursor.fetchone()

    #if the user submits a vote
    if request.method == "POST" and not existing_vote:

        group_id = request.form["group_id"]

        cursor.execute("INSERT INTO Votes (UserID, GroupID) VALUES (?, ?)",(user_id, group_id))

        conn.commit()

        #it gets the results after voting
        cursor.execute("""
            SELECT Groups.GroupName, COUNT(Votes.VoteID)
            FROM Groups
            LEFT JOIN Votes
            ON Groups.GroupID = Votes.GroupID
            GROUP BY Groups.GroupID
            ORDER BY COUNT(Votes.VoteID) DESC
        """)

        results = cursor.fetchall()

        conn.close()

        return render_template("vote.html",already_voted=True,results=results)

    #if they have already voted get the results
    if existing_vote:

        cursor.execute("""
            SELECT Groups.GroupName, COUNT(Votes.VoteID)
            FROM Groups
            LEFT JOIN Votes
            ON Groups.GroupID = Votes.GroupID
            GROUP BY Groups.GroupID
            ORDER BY COUNT(Votes.VoteID) DESC
        """)

        results = cursor.fetchall()

        conn.close()

        return render_template("vote.html",already_voted=True,results=results)

    #shows the group name for users to vote if they havent
    groups = query_db("""
        SELECT GroupID, GroupName
        FROM Groups
    """)

    conn.close()

    return render_template("vote.html",groups=groups,already_voted=False)

@app.errorhandler(404)
def page_not_found(error):
    """Display a custom page when a requested page cannot be found."""
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)