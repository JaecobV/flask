from flask import Flask, g, render_template
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
    sql = """
        SELECT GroupID, GroupName, TopSongs, DebutDate, GroupImage
        FROM Groups;
    """
    results = query_db(sql)
    print(results)   # temporary debug line
    return render_template("home.html", results=results)

@app.route("/Group/<int:id>")
def Group(id):

    member_sql = """
    SELECT MemberNames, MemberImage
    FROM Members
    WHERE GroupID = ?;
    """

    group_sql = """
    SELECT GroupName, TopSongs, DebutDate
    FROM Groups
    WHERE GroupID = ?;
    """

    memberinfo_sql = """
    SELECT BirthName, BirthDate, Nationality, Position, FunFact
    FROM MemberInfo
    WHERE GroupID = ?;
    """

    members = query_db(member_sql, (id,))
    group = query_db(group_sql, (id,), True)
    memberinfo = query_db(memberinfo_sql, (id,), True)

    return render_template("Group.html",members=members,group=group, memberinfo=memberinfo)

if __name__ == "__main__":
    app.run(debug=True)