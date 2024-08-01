from peewee import SqliteDatabase, Model, CharField

# Assuming your database file is named 'mydatabase.db'
db = SqliteDatabase('history.db')


class User(Model):
    email = CharField()
    password = CharField()

    class Meta:
        database = db


db.connect()
users = User.select()

for user in users:
    print(f'Email: {user.email}, Password: {user.password}')

db.close()
