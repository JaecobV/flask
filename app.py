from flask import Flask, g, render_template, request
import sqlite3

DATABASE = 'database.db'

#initialises app
app = Flask(__name__)

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
    search = request.args.get("search", "")

    if search: 
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

    return render_template("home.html", results=results, search=search)

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

if __name__ == "__main__":
    app.run(debug=True)