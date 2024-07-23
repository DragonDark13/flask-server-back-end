import peewee
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token, create_refresh_token
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from config import DATABASE
from models import Event, MainArticleTest, Subtopic, SubArticleTest, Content, User
import json
from data import events_data
from peewee import IntegrityError
from flask_bcrypt import Bcrypt

from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt  # Імпорт Flask-Bcrypt
from flask_cors import CORS

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
        DATABASE.create_tables([User, Event, MainArticleTest, Subtopic, SubArticleTest, Content], safe=True)


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
    for event in Event.select():
        # Отримання main_article_tests для кожного event
        main_article_tests = MainArticleTest.select().where(MainArticleTest.event == event)
        main_article_tests_data = []
        for mat in main_article_tests:
            main_article_tests_data.append({
                'question': mat.question,
                'options': json.loads(mat.options),
                'correct_answers': json.loads(mat.correct_answers)
            })

        # Отримання subtopics для кожного event
        subtopics = Subtopic.select().where(Subtopic.event == event)
        subtopics_data = []
        for subtopic in subtopics:
            sub_article_tests = SubArticleTest.select().where(SubArticleTest.subtopic == subtopic)
            sub_article_tests_data = []
            for sat in sub_article_tests:
                sub_article_tests_data.append({
                    'question': sat.question,
                    'options': json.loads(sat.options),
                    'correct_answers': json.loads(sat.correct_answers)
                })

            subtopics_data.append({
                'title': subtopic.title,
                'content': json.loads(subtopic.content),
                'sub_article_tests': sub_article_tests_data
            })

        # Отримання content для кожного event
        content_items = Content.select().where(Content.event == event)
        content_data = []
        for content_item in content_items:
            content_data.append({
                'type': content_item.type,
                'text': content_item.text
            })

        # Формування результатів
        results.append({
            'date': event.date,
            'text': event.text,
            'achieved': event.achieved,
            'main_article_tests': main_article_tests_data,
            'subtopics': subtopics_data,
            'content': content_data
        })

    return jsonify(results)


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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        try:
            user = User.create(email=email, password=hashed_password)
            login_user(user)
            return redirect(url_for('index'))
        except IntegrityError:
            flash('Email already exists.')


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
        'email': user.email,
        'current_level': user.current_level,
        'additional_tests_completed': user.additional_tests_completed
    }

    return jsonify({'success': True, 'user_data': user_data})


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


@app.route('/complete_test', methods=['POST'])
@login_required
def complete_test():
    user_id = current_user.id
    data = request.json
    additional_tests_completed = data.get('additional_tests_completed', 1)

    user = User.get(User.id == user_id)
    user.additional_tests_completed += additional_tests_completed
    user.save()

    return jsonify({'message': 'Test completed and user updated'}), 200


@app.route('/')
def index():
    return f'Hello, {current_user.username}!'


if __name__ == '__main__':
    app.run(debug=True)
