from flask import Flask, g
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
        SELECT GroupName, TopSongs, DebutDate, GroupImage
        FROM Groups
        JOIN Members ON Groups.GroupID = Members.GroupID;
    """
    results = query_db(sql)
    return str(results)

if __name__ == "__main__":
    app.run(debug=True)