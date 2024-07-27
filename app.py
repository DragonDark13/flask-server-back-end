from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from config import DATABASE
from models import MainArticleTest, User, Subtopic, UserTestCompletion, UserResult, Content, SubArticleTest, Event, Test
from routes import register_routes
from data import events_data
import json

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


def add_sub_article_test_questions():
    for subtopic in Subtopic.select():
        # Перевірити, чи існують підтести для цього subtopic
        existing_tests = SubArticleTest.select().where(SubArticleTest.subtopic == subtopic)
        if existing_tests:
            Test.create(
                title=subtopic.title,
                test_type='Sub Article',
                event=subtopic.event  # Потрібно встановити подію через Subtopic
            )


add_sub_article_test_questions()

if __name__ == '__main__':
    app.run(debug=True)
