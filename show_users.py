from peewee import SqliteDatabase, Model, CharField
from models import User

# Assuming your database file is named 'mydatabase.db'
db = SqliteDatabase('history.db')

db.connect()
users = User.select()

for user in users:
    print(f'Email: {user.email}, Password: {user.password}, User name {user.user_name}')

db.close()
