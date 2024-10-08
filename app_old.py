from datetime import datetime

from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token, create_refresh_token
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from config import DATABASE
from models import Event, MainArticleTest, Subtopic, SubArticleTest, Content, User, UserResult, Test, UserTestCompletion
import json
from data import events_data
from peewee import IntegrityError

from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt  # Імпорт Flask-Bcrypt
from flask_cors import CORS
from werkzeug.security import check_password_hash

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Конфігурація
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'

# Ініціалізація
login_manager = LoginManager(app)
login_manager.login_view = 'login'
jwt = JWTManager(app)
bcrypt = Bcrypt(app)


def create_tables():
    with DATABASE:
        DATABASE.create_tables(
            [User, Event, MainArticleTest, Subtopic, SubArticleTest, Content, UserResult, Test, UserTestCompletion],
            safe=True)


create_tables()

# Збереження даних у базі
with DATABASE.atomic():
    # Видалити всі Content
    # Перша частина: Видалення всіх старих записів

    # Видалити всі SubArticleTest
    SubArticleTest.delete().execute()

    # Видалити всі MainArticleTest
    MainArticleTest.delete().execute()

    # Видалити всі Subtopic
    Subtopic.delete().execute()

    # Видалити всі Content
    Content.delete().execute()

    # Видалити всі Event
    Event.delete().execute()

    Test.delete().execute()

    UserResult.delete().execute()

    # Друга частина: Додавання нових записів

    for event_data in events_data:
        # Створення запису події
        event = Event.create(
            date=event_data["date"],
            text=event_data["text"],
            achieved=event_data.get("achieved", None)
        )

        # Зберегти Content
        if "content" in event_data:
            for content_item in event_data["content"]:
                Content.create(
                    event=event,
                    type=content_item.get("type", None),
                    text=content_item["text"]
                )

        # Зберегти MainArticleTest
        main_article_test = event_data.get("mainArticleTest", {})
        if main_article_test:
            for i, question in enumerate(main_article_test.get("questions", [])):
                MainArticleTest.create(
                    event=event,
                    question=question,
                    options=json.dumps(main_article_test.get("options", [])[i]),
                    correct_answers=json.dumps(main_article_test.get("correctAnswers", [])[i])
                )

        # Зберегти Subtopics і SubArticleTest
        subtopic_data_has = event_data.get("subtopics", [])
        if subtopic_data_has:
            for subtopic_data in subtopic_data_has:
                # Перевірка наявності Subtopic
                existing_subtopic = Subtopic.select().where(
                    Subtopic.event == event,
                    Subtopic.title == subtopic_data["title"]
                ).first()

                if not existing_subtopic:
                    # Створення нового Subtopic
                    subtopic = Subtopic.create(
                        event=event,
                        title=subtopic_data["title"],
                        content=json.dumps(subtopic_data["content"])
                    )

                    # Зберегти SubArticleTest для Subtopic
                    for i, question in enumerate(subtopic_data.get("subArticleTest", {}).get("questions", [])):
                        SubArticleTest.create(
                            subtopic=subtopic,
                            question=question,
                            options=json.dumps(subtopic_data["subArticleTest"].get("options", [])[i]),
                            correct_answers=json.dumps(subtopic_data["subArticleTest"].get("correctAnswers", [])[i])
                        )


# Перевірка даних
@app.route('/get-events')
def get_events():
    results = []

    # Обробка кожної події в базі даних
    for event in Event.select():
        # Отримання основних тестів для кожної події
        main_article_tests = MainArticleTest.select().where(MainArticleTest.event == event)
        main_article_tests_data = []

        for mat in main_article_tests:
            main_article_tests_data.append({
                'id': mat.id,  # Додаємо ID тесту
                'question': mat.question,
                'options': json.loads(mat.options),
                'correct_answers': json.loads(mat.correct_answers)
            })

        # Отримання підтестів для кожної події
        subtopics = Subtopic.select().where(Subtopic.event == event)
        subtopics_data = []

        for subtopic in subtopics:
            sub_article_tests = SubArticleTest.select().where(SubArticleTest.subtopic == subtopic)
            sub_article_tests_data = []

            for sat in sub_article_tests:
                sub_article_tests_data.append({
                    'id': sat.id,  # Додаємо ID підтесту
                    'question': sat.question,
                    'options': json.loads(sat.options),
                    'correct_answers': json.loads(sat.correct_answers)
                })

            subtopics_data.append({
                'title': subtopic.title,
                'content': json.loads(subtopic.content),
                'sub_article_tests': sub_article_tests_data
            })

        # Отримання вмісту для кожної події
        content_items = Content.select().where(Content.event == event)
        content_data = []

        for content_item in content_items:
            content_data.append({
                'type': content_item.type,
                'text': content_item.text
            })

        # Формування результатів
        results.append({
            'id': event.id,  # Додаємо ID події
            'date': event.date,
            'text': event.text,
            'achieved': event.achieved,
            'main_article_tests': main_article_tests_data,
            'subtopics': subtopics_data,
            'content': content_data
        })

    return jsonify(results)



def add_main_article_tests():
    for event in Event.select():
        # Перевірити, чи існує основний тест для цього event
        existing_tests = MainArticleTest.select().where(MainArticleTest.event == event)
        if existing_tests:
            Test.create(
                title=event.text,
                test_type='Main Article',
                event=event
            )


add_main_article_tests()


def add_sub_article_tests():
    for subtopic in Subtopic.select():
        # Перевірити, чи існують підтести для цього subtopic
        existing_tests = SubArticleTest.select().where(SubArticleTest.subtopic == subtopic)
        if existing_tests:
            Test.create(
                title=subtopic.title,
                test_type='Sub Article',
                event=subtopic.event  # Потрібно встановити подію через Subtopic
            )


add_sub_article_tests()


def add_user_test_completions():
    # Отримати всіх користувачів
    users = User.select()

    # Отримати всі тести
    tests = Test.select()

    # Створити записи в таблиці UserTestCompletion
    with DATABASE.atomic():
        for user in users:
            for test in tests:
                # Перевірити, чи вже існує запис для цієї комбінації
                exists = UserTestCompletion.select().where(
                    UserTestCompletion.user == user,
                    UserTestCompletion.test == test
                ).exists()

                if not exists:
                    UserTestCompletion.create(
                        user=user,
                        user_name=user.user_name,
                        test_title=test.title,
                        event=test.event,  # Потрібно встановити подію через Test
                        test=test,
                        test_type=test.test_type,  # Додаємо поле test_type
                        completed=False,  # За замовчуванням встановлено False
                        date_completed=datetime.now()
                    )


add_user_test_completions()


@app.route('/complete-test', methods=['POST'])
def complete_test():
    data = request.json
    user_id = data.get('user_id')
    test_id = data.get('test_id')
    completed = data.get('completed', False)

    if not user_id or not test_id:
        return jsonify({'error': 'User ID and Test ID are required'}), 400

    user = User.get_or_none(User.id == user_id)
    test = Test.get_or_none(Test.id == test_id)

    if not user or not test:
        return jsonify({'error': 'Invalid User ID or Test ID'}), 404

    # Запис виконання тесту
    UserTestCompletion.create(
        user=user,
        test=test,
        completed=completed,
        date_completed=datetime.now()
    )

    return jsonify({'success': True}), 200


def save_user_result(user_id, test_type, test_id, score):
    user = User.get(User.id == user_id)

    if test_type == 'main':
        test = MainArticleTest.get(MainArticleTest.id == test_id)
        UserResult.create(
            user=user,
            main_article_test=test,
            score=score
        )
    elif test_type == 'sub':
        test = SubArticleTest.get(SubArticleTest.id == test_id)
        UserResult.create(
            user=user,
            sub_article_test=test,
            score=score
        )


@app.before_request
def before_request():
    DATABASE.connect()


@app.after_request
def after_request(response):
    DATABASE.close()
    return response


@login_manager.user_loader
def load_user(user_id):
    return User.get(User.id == user_id)


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()  # Отримуємо дані у форматі JSON
    email = data.get('email')
    password = data.get('password')
    user_name = data.get('userName')

    # Перевірка наявності користувача з таким самим user_name
    if User.select().where(User.user_name == user_name).exists():
        return jsonify({'message': 'User name already exists.'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        user = User.create(email=email, password=hashed_password, user_name=user_name)
        login_user(user)
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        return jsonify({
            'message': 'User registered successfully.',
            'token': access_token,
            'refresh_token': refresh_token,
            'user_data': {
                'user_name': user.user_name,
                'email': user.email,
                'current_level': user.current_level,
                'additional_tests_completed': user.additional_tests_completed
            }
        }), 201
    except IntegrityError:
        return jsonify({'message': 'Email already exists.'}), 400


@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify({'access_token': new_access_token}), 200


@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email')
    password = request.json.get('password')
    user_name = request.json.get('user_name')

    try:
        user = User.get(User.email == email)
        if bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            return jsonify({
                'success': True,
                'token': access_token,
                "refresh_token": refresh_token,
                'user_data': {
                    'user_name': user.user_name,
                    'email': user.email,
                    'current_level': user.current_level,
                    'additional_tests_completed': user.additional_tests_completed
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    except User.DoesNotExist:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401


@app.route('/api/user', methods=['GET'])
@jwt_required()
def get_user_data():
    user_id = get_jwt_identity()
    user = User.get(User.id == user_id)

    user_data = {
        'user_name': user.user_name,
        'email': user.email,
        'current_level': user.current_level,
        'additional_tests_completed': user.additional_tests_completed
    }

    return jsonify({'success': True, 'user_data': user_data})


@app.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    data = request.get_json()
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')

    user_id = get_jwt_identity()
    user = User.get(User.id == user_id)

    if not bcrypt.check_password_hash(user.password, current_password):
        return jsonify({'message': 'Current password is incorrect'}), 400

    hashed_new_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.password = hashed_new_password
    user.save()

    return jsonify({'message': 'Password changed successfully'}), 200


@app.route('/update-profile', methods=['POST'])
@jwt_required()
def update_profile():
    data = request.get_json()
    user_id = get_jwt_identity()
    user = User.get(User.id == user_id)

    new_user_name = data.get('user_name')
    new_email = data.get('email')
    new_country = data.get('country')

    # Перевірка наявності користувача з таким самим user_name
    if User.select().where((User.user_name == new_user_name) & (User.id != user_id)).exists():
        return jsonify({'message': 'User name already exists.'}), 400

    if User.select().where((User.email == new_email) & (User.id != user_id)).exists():
        return jsonify({'message': 'Email already exists.'}), 400

    user.user_name = new_user_name
    user.email = new_email
    user.country = new_country  # Припустимо, що у вас є поле country у вашій моделі User
    user.save()

    return jsonify({'message': 'Profile updated successfully.'}), 200


@app.route('/delete-profile', methods=['DELETE'])
@jwt_required()
def delete_profile():
    user_id = get_jwt_identity()
    try:
        user = User.get(User.id == user_id)
    except User.DoesNotExist:
        return jsonify({'message': 'User not found'}), 404

    try:
        user.delete_instance()
        return jsonify({'message': 'Profile deleted successfully'}), 200
    except Exception as e:
        return jsonify({'message': 'Failed to delete profile', 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)


@app.route('/update_user', methods=['POST'])
@login_required
def update_user():
    user_id = current_user.id
    data = request.json
    current_level = data.get('current_level')
    additional_tests_completed = data.get('additional_tests_completed')

    user = User.get(User.id == user_id)
    if current_level is not None:
        user.current_level = current_level
    if additional_tests_completed is not None:
        user.additional_tests_completed = additional_tests_completed
    user.save()

    user_data = {
        'id': user.id,
        'email': user.email,
        'current_level': user.current_level,
        'additional_tests_completed': user.additional_tests_completed
    }

    return jsonify({'message': 'User updated successfully', 'user': user_data}), 200

if __name__ == '__main__':
    app.run(debug=True)
