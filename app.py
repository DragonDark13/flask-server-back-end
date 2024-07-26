from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from config import DATABASE
from models import MainArticleTest, User, Subtopic, UserTestCompletion, UserResult, Content, SubArticleTest, Event, Test
from routes import register_routes

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Конфігурація
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'

# Ініціалізація
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# Реєстрація маршрутів
register_routes(app)


# Створення таблиць
def create_tables():
    with DATABASE:
        DATABASE.create_tables(
            [User, Event, MainArticleTest, Subtopic, SubArticleTest, Content, UserResult, Test, UserTestCompletion],
            safe=True)


create_tables()

if __name__ == '__main__':
    app.run(debug=True)
