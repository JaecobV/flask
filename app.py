from flask import Flask, g, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

DATABASE = 'database.db'

app = Flask(__name__)
app.secret_key = "your-secret-key"

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

@app.route('/')
def home():
    #home page
    search = request.args.get("search", "").strip()
    group_type = request.args.get("type", "").strip()

    if group_type:
        sql = """
            SELECT GroupID, GroupName, TopSongs, DebutDate, GroupImage
            FROM Groups
            WHERE GroupType = ?;
            """
        results = query_db(sql, (group_type,))

    elif search: 
        sql = """   
            SELECT GroupID, GroupName, TopSongs, DebutDate, GroupImage
            FROM Groups
            WHERE GroupName LIKE ?;
            """
        results = query_db(sql, ('%' + search + '%',))
    else: 
        sql = """
            SELECT GroupID, GroupName, TopSongs, DebutDate, GroupImage
            FROM Groups;
            """
        results = query_db(sql)

    return render_template("home.html", results=results, search=search, group_type=group_type)

@app.route("/Group/<int:id>")
def Group(id):

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

    members = query_db(member_sql, (id,))
    group = query_db(group_sql, (id,), True)
    return render_template("group.html", members=members, group=group)

@app.route("/companies")
def Companies():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
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

    companies = cursor.fetchall()

    connection.close()

    return render_template("companies.html", companies=companies)

@app.route("/company/<int:company_id>")
def company(company_id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM Companies
        WHERE CompanyID = ?
    """, (company_id,))

    company = cursor.fetchone()

    conn.close()

    return render_template("company.html", company=company)

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Users WHERE Username = ?",(username,))

        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user[2], password):

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect(url_for("home"))

        else:
            return render_template("login.html",error="Incorrect username or password.")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

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

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)