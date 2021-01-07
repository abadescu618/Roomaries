from cs50 import SQL
from datetime import datetime
import csv

# Get unique identifier of roomie group
# Recognize current user
user = 10
db = SQL("sqlite:///roomaries.db")
code_db = db.execute("SELECT code FROM users WHERE id == :user", user=user)
code = code_db[0]['code']

roomie_count_db = db.execute("SELECT count(id) FROM users WHERE code == :code", code=code)
roomie_count = roomie_count_db[0]['count(id)']

year = datetime.now().year
month = datetime.now().month
today = datetime.today()

# Total grocery spend this year
date_begin = datetime(today.year, 1, 1)
date_end = datetime(today.year, 12, 31)

db_output = db.execute("SELECT sum(t.bill) FROM transactions t INNER JOIN users u ON t.user_id = u.id WHERE u.code = :code AND t.updated BETWEEN :begin AND :end", code=code, begin=date_begin, end=date_end)
print(db_output)

total_year = db_output[0]['sum(t.bill)']
if not total_year:
    total_year_pp = 0
else:
    total_year_pp = total_year / roomie_count

print(total_year_pp)

db_output = db.execute("SELECT h.grocery, count(h.grocery) FROM history h INNER JOIN users u ON h.user_id = u.id WHERE u.code = :code GROUP BY h.grocery ORDER BY count(h.grocery) DESC LIMIT 3", code=code)

print(db_output)