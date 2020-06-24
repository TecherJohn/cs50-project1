import requests, os, csv, sys, time

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#code to read data from a CSV file:

print("Truncating Tables")
db.execute("TRUNCATE TABLE authors, books, reviews RESTART IDENTITY")
db.commit()
print("Creating Temp Tables", flush = True)
db.execute('CREATE TABLE public.bulk_load \
            ( \
                "ISBN" character varying(13) COLLATE pg_catalog."default", \
                title character varying(256) COLLATE pg_catalog."default", \
                author character varying(256) COLLATE pg_catalog."default", \
                year character varying(4) COLLATE pg_catalog."default" \
            )')

print("Bulk Loading Data", end = "", flush = True)
f = open("books.csv")
reader = csv.reader(f)
csv_row_count = 0
#insert_statement = text("""INSERT INTO bulk_load ("ISBN", title, author, year) VALUES (:ISBN, :title, :author, :year)""")
insert_statement = """INSERT INTO bulk_load ("ISBN", title, author, year) VALUES (:ISBN, :title, :author, :year)"""
for isbn, title, author, year in reader:
  if isbn != 'isbn' and title != 'title' and author != 'author' and year != 'year': #skip the header row
    csv_row_count += 1
    db.execute(insert_statement, {"ISBN": isbn, "title": title, "author": author, "year": year})
  if csv_row_count % 100 == 0:
    print(".", end = "", flush = True)
db.commit()
print(f"loaded {csv_row_count} books.")

print("Loading Authors Table", flush = True)
db.execute('INSERT INTO authors (name) SELECT author FROM bulk_load GROUP BY author')
print("Loading Books Table", flush = True)
db.execute('INSERT INTO books (author_id, title, "ISBN", year_published) \
            SELECT a.id, bl.title, bl."ISBN", CAST(bl.year AS INT) \
            FROM bulk_load bl \
              LEFT OUTER JOIN authors a ON a.name = bl.author')
print("Cleaning Up Temp Tables", flush = True)
db.execute('DROP TABLE public.bulk_load')
db.commit()

#Heroku
# URI: postgres://mybglcdrnmrnhp:dcad3c3b410483bb0bec28a51f580485b929799195b035a8b66e0d99db250a77@ec2-54-236-169-55.compute-1.amazonaws.com:5432/deat8gcsv4b5im
# Host: ec2-54-236-169-55.compute-1.amazonaws.com
# Database: deat8gcsv4b5im
# User: mybglcdrnmrnhp
# Port: 5432
# Password: dcad3c3b410483bb0bec28a51f580485b929799195b035a8b66e0d99db250a77