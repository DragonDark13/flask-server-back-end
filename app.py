from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS

from config import DATABASE
from routes import register_routes
from initialize import create_tables, update_data, add_main_article_tests, add_sub_article_tests, \
    add_all_users_test_completions, clean_user_test_completions

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

add_all_users_test_completions()
clean_user_test_completions()


# initialize_user_test_completions()

@app.before_request
def before_request():
    DATABASE.connect()


@app.after_request
def after_request(response):
    DATABASE.close()
    return response


if __name__ == '__main__':
    app.run(debug=True)
