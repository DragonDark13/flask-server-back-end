from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from services import (
    get_events_service, complete_test_service, register_user_service,
    login_user_service, change_password_service, update_profile_service,
    delete_profile_service, refresh_token_service, get_user_data_service,
    reset_achievements_service
)
import logging
from flask_caching import Cache  # Кешування
from functools import wraps

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Налаштування кешування
cache = Cache(config={'CACHE_TYPE': 'simple'})  # Simple кеш (можна змінити на Redis або інший тип кешу)


# Декоратор для автоматичного отримання user_id
def get_user_id(func):
    @wraps(func)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        return func(user_id, *args, **kwargs)

    return wrapper


# Універсальна функція для валідації, логування та обробки помилок
def validate_and_log(service_function):
    try:
        response = service_function()
        logging.info(f"Response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Реєстрація маршрутів
def register_routes(app):
    # Ініціалізація кешу
    cache.init_app(app)

    @app.route('/get-events', methods=['GET'])
    @cache.cached(timeout=300)  # Кешування на 5 хвилин (300 секунд)
    def get_events():
        args = request.args  # Параметри GET-запиту
        logging.info(f"Fetching events with parameters: {args}")
        return validate_and_log(get_events_service)

    @app.route('/complete-test', methods=['POST'])
    @get_user_id
    def complete_test(user_id):
        logging.info(f"User {user_id} is completing a test with data: {request.json}")
        return validate_and_log(lambda: complete_test_service(user_id, request.json))

    @app.route('/register', methods=['POST'])
    def register():
        logging.info("User registration attempt")
        return validate_and_log(lambda: register_user_service(request.get_json()))

    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        headers = request.headers
        logging.info(f"User login attempt with data: {data}, headers: {headers}")
        return validate_and_log(lambda: login_user_service(request.json))

    @app.route('/api/user', methods=['GET'])
    @get_user_id
    def get_user_data(user_id):
        logging.info(f"Fetching user data for user {user_id}")
        return validate_and_log(lambda: get_user_data_service(user_id))

    @app.route('/change-password', methods=['POST'])
    @get_user_id
    def change_password(user_id):
        logging.info(f"User {user_id} is changing password")
        return validate_and_log(lambda: change_password_service(request.get_json(), user_id))

    @app.route('/update-profile', methods=['POST'])
    @get_user_id
    def update_profile(user_id):
        logging.info(f"User {user_id} is updating profile with data: {request.get_json()}")
        return validate_and_log(lambda: update_profile_service(request.get_json(), user_id))

    @app.route('/delete-profile', methods=['DELETE'])
    @get_user_id
    def delete_profile(user_id):
        logging.info(f"User {user_id} is deleting profile")
        return validate_and_log(lambda: delete_profile_service(user_id))

    @app.route('/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        logging.info("Refreshing token")
        return validate_and_log(lambda: refresh_token_service(get_jwt_identity()))

    @app.route('/api/user/reset-achievements', methods=['POST'])
    @get_user_id
    def reset_achievements(user_id):
        logging.info(f"User {user_id} is resetting achievements")
        return validate_and_log(lambda: reset_achievements_service(user_id))
