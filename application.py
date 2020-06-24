import os, sys, json, requests

from flask import Flask, url_for, redirect, session, request, render_template
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.secret_key = 'This is my secret key. I hope nobody guesses it. Zamboni'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    return render_template('login.html', login_error="")

@app.route("/Login", methods=["GET"])
def login():
    return render_template('login.html', login_error="")

@app.route("/Login", methods=["POST"])
def log_user_in():
    username = request.form['username']
    password = request.form['password']

    user = db.execute("SELECT id, password FROM users WHERE user_name = :user_name ", \
                {"user_name": username}).fetchone()
    if check_password_hash(user[1], password):
        session['user_id'] = user[0]
        db.execute("UPDATE users SET logins = logins + 1, last_login = CURRENT_DATE WHERE id = :user_id", {"user_id": user[0]})
        db.commit()
        return redirect(url_for('book_search'))
    else:
        return render_template('login.html', login_error="Invalid Login, Please retry")

@app.route("/register", methods=["GET"])
def register():
    return render_template('register.html', registration_error="")

@app.route("/register", methods=["POST"])
def register_new_user():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    username = request.form['username']
    password = generate_password_hash(request.form['password'])

    if db.scalar("SELECT COUNT(*) FROM users WHERE email = :email", \
                {"email": email}) == 1:
        return render_template('register.html', registration_error="That email has already been registered!")
    if db.scalar("SELECT COUNT(*) FROM users WHERE user_name = :user_name", \
                {"user_name": username}) == 1:
        return render_template('register.html', registration_error="That user name has already been registered!")
    db.execute("INSERT INTO users (user_name, password, first_name, last_name, email, logins, last_login) \
                        VALUES (:user_name, :password, :first_name, :last_name, :email, 1, CURRENT_DATE)", \
                        {"user_name": username, "password": password, "first_name": first_name, "last_name": last_name, "email": email})
    user_id = db.scalar("SELECT LASTVAL()")
    session['user_id'] = user_id
    db.commit()
    return redirect(url_for('book_search'))

@app.route("/user_information", methods=["GET"])
def user_information():
    if not "user_id" in session:
        return render_template('login.html', login_error="Please Login First.")
    user_record = db.execute("SELECT first_name, last_name, email FROM users WHERE id = :user_id", {"user_id": session["user_id"]}).fetchone()
    return render_template('user_info.html', first_name = user_record[0], last_name = user_record[1], email = user_record[2])

@app.route("/user_information", methods=["POST"])
def update_user_information():
    if not "user_id" in session:
        return render_template('login.html', login_error="Please Login First.")
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']

    if db.scalar("SELECT COUNT(*) FROM users WHERE email = :email and id <> :user_id", \
                {"email": email, "user_id": session["user_id"]}) == 1:
        return render_template('user_info.html', registration_error="That email has already been registered!", first_name = first_name, last_name = last_name, email = email)
    db.execute("UPDATE users SET first_name = :first_name, last_name = :last_name, email = :email \
                        WHERE id = :user_id", \
                        {"first_name": first_name, "last_name": last_name, "email": email, "user_id": session["user_id"]})
    db.commit()
    return render_template('user_info.html', first_name = first_name, last_name = last_name, email = email)

@app.route("/book_search", methods=['GET'])
def book_search():
    if not "user_id" in session:
        return render_template('login.html', login_error="Please Login First.")

    search_json = db.scalar("""SELECT last_book_search_json FROM users WHERE id = :user_id""", {"user_id": session["user_id"]})
    if search_json == None:
        search_dict = dict()
    else:
        search_dict = json.loads(search_json)

    if "book_title_selector" in search_dict:
        book_title_selector = search_dict['book_title_selector']
        book_title = search_dict['book_title']
    else:
        book_title_selector = ""
        book_title = ""

    if "book_author_selector" in search_dict:
        book_author_selector = search_dict['book_author_selector']
        book_author = search_dict['book_author']
    else:
        book_author_selector = ""
        book_author = ""

    if "year_published" in search_dict:
        year_published = search_dict['year_published']
    else:
        year_published = ""

    if "isbn" in search_dict:
        isbn = search_dict['isbn']
    else:
        isbn = ""

    return render_template('book_search.html', book_title_selector = book_title_selector, book_title = book_title, \
                                                book_author_selector = book_author_selector, book_author = book_author, \
                                                year_published = year_published, isbn = isbn)

@app.route("/book_search", methods=['POST'])
def book_search_results():
    if not "user_id" in session:
        return render_template('login.html', login_error="Please Login First.")

    book_title_selector = request.form["book_title_selector"]
    book_title = request.form["book_title"]
    book_author_selector = request.form["book_author_selector"]
    book_author = request.form["book_author"]
    year_published = request.form["year_published"]
    isbn = request.form["isbn"]

    search_save = dict()

    select_where_statement = ""
    select_parameters = dict()
    if not book_title == "":
        search_save['book_title_selector'] = book_title_selector
        search_save['book_title'] = book_title
        if select_where_statement != "":
            select_where_statement += " AND "
        if book_title_selector == "starts_with":
            select_where_statement += """ b.title LIKE :book_title"""
            select_parameters["book_title"] = book_title + "%"
        elif book_title_selector == "contains":
            select_where_statement += """ b.title LIKE :book_title"""
            select_parameters["book_title"] = "%" + book_title + "%"
        elif book_title_selector == "ends_with":
            select_where_statement += """ b.title LIKE :book_title"""
            select_parameters["book_title"] = "%" + book_title
        elif book_title_selector == "exactly":
            select_where_statement += """ b.title = :book_title"""
            select_parameters["book_title"] = book_title

    if not book_author == "":
        search_save['book_author_selector'] = book_author_selector
        search_save['book_author'] = book_author
        if select_where_statement != "":
            select_where_statement += " AND "
        if book_author_selector == "starts_with":
            select_where_statement += """ a.name LIKE :book_author"""
            select_parameters["book_author"] = book_author + "%"
        elif book_author_selector == "contains":
            select_where_statement += """ a.name LIKE :book_author"""
            select_parameters["book_author"] = "%" + book_author + "%"
        elif book_author_selector == "ends_with":
            select_where_statement += """ a.name LIKE :book_author"""
            select_parameters["book_author"] = "%" + book_author
        elif book_author_selector == "exactly":
            select_where_statement += """ a.name = :book_author"""
            select_parameters["book_author"] = book_author

    if not year_published == "":
        search_save['year_published'] = year_published
        if select_where_statement != "":
            select_where_statement += " AND "
        select_where_statement += """ b.year_published = :year_published"""
        select_parameters["year_published"] = year_published

    if not isbn == "":
        search_save['isbn'] = isbn
        if select_where_statement != "":
            select_where_statement += " AND "
        select_where_statement += """ b."ISBN" = :isbn"""
        select_parameters["isbn"] = isbn

    if select_where_statement != "":
        select_where_statement = " WHERE " + select_where_statement

    json_search_save = json.dumps(search_save, indent = 4)
    db.execute("""UPDATE users SET last_book_search_json = :search WHERE id = :user_id""", {"search": json_search_save, "user_id": session["user_id"]})
    db.commit()

    select_statement = """SELECT COUNT(*)\
                        FROM books b\
                            LEFT OUTER JOIN authors a ON a.id = b.author_id""" + \
                            select_where_statement
    returned_records = db.scalar(text(select_statement), select_parameters)
    if returned_records == 0:
        return render_template('book_search.html', book_search_error="No Records Found")

    select_statement = """SELECT b.id, a.name, b.title, b.year_published, b."ISBN", COUNT(r.book_id) "review count"\
                            FROM books b \
                                LEFT OUTER JOIN authors a ON a.id = b.author_id \
                                LEFT OUTER JOIN reviews r ON r.book_id = b.id""" + \
                            select_where_statement + \
                            """ GROUP BY b.id, a.name, b.title, b.year_published, b."ISBN" """
    books = db.execute(text(select_statement), select_parameters)
    return render_template('book_search_results.html', books = books)

@app.route("/book_information", methods=["GET"])
def book_information():
    if not "user_id" in session:
        return render_template('login.html', login_error="Please Login First.")
    book_id = request.args.get('book_id', None)

    try:
        row = db.execute("""SELECT review, stars FROM reviews WHERE book_id = :book_id AND user_id = :user_id""", \
                            {"book_id": book_id, "user_id": session["user_id"]}).first()
        review = row[0]
        stars = row[1]
    except:
        review = ""
        stars = 0

    book_info = db.execute("""SELECT a.name, b.title, b."ISBN", b.year_published\
                                FROM books b \
                                    LEFT OUTER JOIN authors a ON a.id = b.author_id \
                                WHERE b.id = :book_id""", {"book_id": book_id}).first()

    more_reviews = (db.scalar("""SELECT COUNT(*) FROM reviews WHERE book_id = :book_id AND user_id <> :user_id""", \
                            {"book_id": book_id, "user_id": session["user_id"]}) > 0)

    goodreads_json = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "3tKvqXDMdbDFekFN9To0Q", "isbns": book_info[2]}).json()

    reviews = db.execute("""SELECT CONCAT(u.last_name, ', ', u.first_name) "User Name", r.stars, r.review \
                            FROM reviews r \
                            LEFT OUTER JOIN users u ON u.id = r.user_id \
                            WHERE r.book_id = :book_id AND r.user_id <> :user_id""", \
                            {"book_id": book_id, "user_id": session["user_id"]})

    return render_template('book_info_reviews.html', book_id = book_id, review = review, stars = stars, reviews = reviews, book_info = book_info, more_reviews = more_reviews, goodreads = goodreads_json['books'][0])

@app.route("/book_information", methods=["POST"])
def update_review():
    if not "user_id" in session:
        return render_template('login.html', login_error="Please Login First.")
    book_id = request.args.get('book_id', None)
    stars = request.form["stars"]
    review = request.form["review"]

    if db.scalar("""SELECT COUNT(*) FROM reviews WHERE book_id = :book_id AND user_id = :user_id""", \
                {"book_id": book_id, "user_id": session["user_id"]}) > 0:
        db.execute("""UPDATE reviews SET review = :review, stars = :stars WHERE book_id = :book_id AND user_id = :user_id""",\
                    {"review": review, "stars": stars, "book_id": book_id, "user_id": session["user_id"]})
    else:
        db.execute("""INSERT INTO reviews (book_id, user_id, review, stars) VALUES (:book_id, :user_id, :review, :stars)""",\
                    {"book_id": book_id, "user_id": session["user_id"], "review": review, "stars": stars})
    db.commit()

    return redirect(url_for('book_information', book_id = book_id))

@app.route("/my_book_reviews")
def user_book_reviews():
    if not "user_id" in session:
        return render_template('login.html', login_error="Please Login First.")

    if db.scalar("""SELECT COUNT(*) FROM reviews WHERE user_id = :user_id""", {"user_id": session["user_id"]}) == 0:
        return render_template('my_book_reviews.html', no_reviews = True)

    reviews = db.execute("""SELECT b.id, b.title, a.name, r.stars, r.review \
                    FROM reviews r\
                        LEFT OUTER JOIN books b ON r.book_id = b.id\
                        LEFT OUTER JOIN authors a ON b.author_id = a.id\
                    WHERE r.user_id = :user_id""", {"user_id": session["user_id"]})
    return render_template('my_book_reviews.html', no_reviews = False, reviews = reviews)

@app.route("/logout")
def logout():
    if "user_id" in session:
        session.pop('user_id', None)
    return render_template('login.html')

@app.route("/api", methods=["GET"])
def api():
    isbn = request.args.get('isbn', None)

    if db.scalar("""SELECT count(*) FROM books WHERE "ISBN" = :isbn""", {"isbn": isbn}) == 0:
        return json.loads({"error": "ISBN not found!"}), 404

    book = db.execute("""SELECT b.title, a.name, year_published, "ISBN"\
                        , (SELECT COUNT(*) FROM reviews WHERE book_id = b.id) \
                        , (SELECT AVG(stars) FROM reviews WHERE book_id = b.id) \
                        FROM books b \
                            LEFT OUTER JOIN authors a ON b.author_id = a.id \
                        WHERE "ISBN" = :isbn""", {"isbn": isbn}).first()
    if book[5] == None:
        x = {"title": book[0], \
                        "author": book[1], \
                        "year": book[2], \
                        "isbn": book[3], \
                        "review_count": book[4], \
                        "average_score": "N/A"}
    else:
        x = {"title": book[0], \
                        "author": book[1], \
                        "year": book[2], \
                        "isbn": book[3], \
                        "review_count": book[4], \
                        "average_score": float(book[5])}

    return json.dumps(x)

#goodreads API key
#key: 3tKvqXDMdbDFekFN9To0Q
#secret: ca1ilFbG9hLw4rBoulrd9nQsRm53EUqR7Z6DawLgAeY
