# Project 1

Web Programming with Python and JavaScript

layout.html - General page layout. Imports style sheets for website and very sparse frame.

login.html - Simple user name and password login page.
register.html - Allows new user registration. Accepts user first name, last name, email, username and password. Will reject duplicate usernames or emails.
user_info.html - Allows the logged in user to change their first name, last name or email. Rejects duplicate emails.
book_search.html - This is the "main page" of the application. Allows the logged in user to search for a book based on the title, author, publication year or ISBN. Allows for 4 different types of text matching for the author or title.
book_search_results.html - This is a basic table. It shows the return records for the book search. Honestly, this page should be part of the book_search.html page and I'd change that if I weren't about to submit this. This page allows the user to see the details about a book.
book_info_reviews.html - This page shows the detail information for a book. It allows the currently logged in user to edit their review or enter a new review. It also shows the other reviews from the other users.
my_book_reviews.html - This page shows all the books the currently logged in user has reviewed. It allows the logged in user to edit their review.

application.py - This is the server code for this project.
books.csv - This is the CVS bulk load file for this project.
import.py - This is the server code to load the CVS bulk file into the database for this project.
README.md - This is this file.
requirements.txt - This is the list of python requirements for this project.
start_flask.bat - This is a batch file that sets environment variable for FLASK and compiles the sass stylesheet and then runs the flask application.

book-review-website.scss - This is the sass stylesheet file.
book-review-website.css - This is the interpreted/compiled stylesheet file.
