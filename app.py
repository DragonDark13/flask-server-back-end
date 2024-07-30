from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from config import DATABASE
from models import MainArticleTest, User, Subtopic, UserTestCompletion, UserResult, Content, SubArticleTest, Test, \
    Event, \
    Counter
from routes import register_routes
from data import events_data
import json
from datetime import datetime
from initialize import create_tables, update_data, add_main_article_tests, add_sub_article_tests, \
    add_user_test_completions

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

create_tables()

update_data()

add_main_article_tests()

add_sub_article_tests()

add_user_test_completions()

if __name__ == '__main__':
    app.run(debug=True)
