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


def create_tables():
    with DATABASE:
        DATABASE.create_tables(
            [User, Event, MainArticleTest,
             Subtopic, SubArticleTest, Content, UserResult,
             Test, UserTestCompletion,
             Counter],
            safe=True
        )


# Створення таблиць
create_tables()


def update_data():
    # Збереження даних у базі
    with DATABASE.atomic():
        # Видалити всі записи
        SubArticleTest.delete().execute()
        MainArticleTest.delete().execute()
        Subtopic.delete().execute()
        Content.delete().execute()
        Event.delete().execute()
        Test.delete().execute()
        UserResult.delete().execute()
        Counter.delete().execute()

        # Додавання нових записів
        for event_data in events_data:
            # Створення запису події
            print("Processing event data:", event_data)  # Додайте це тут

            event = Event.create(
                date=event_data["date"],
                text=event_data["text"],
                achieved=event_data.get("achieved", None),
            )
            print("Created event:", event)  # Додайте це тут

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
                            content=json.dumps(subtopic_data["content"]),
                        )

                        # Зберегти SubArticleTest для Subtopic
                        for i, question in enumerate(subtopic_data.get("subArticleTest", {}).get("questions", [])):
                            SubArticleTest.create(
                                subtopic=subtopic,
                                question=question,
                                options=json.dumps(subtopic_data["subArticleTest"].get("options", [])[i]),
                                correct_answers=json.dumps(subtopic_data["subArticleTest"].get("correctAnswers", [])[i])
                            )


update_data()


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


#
# def generate_test_ids():
#     event_ids_with_tests = MainArticleTest.select(MainArticleTest.event).distinct()
#     subtopic_ids_with_tests = SubArticleTest.select(SubArticleTest.subtopic).distinct()
#
#     test_ids = {}
#     current_id = 1
#     for event in event_ids_with_tests:
#         test_ids[event.event.id] = current_id
#         current_id += 1
#     for subtopic in subtopic_ids_with_tests:
#         test_ids[subtopic.subtopic.id] = current_id
#         current_id += 1
#
#     return test_ids
#
#
# def update_test_id_for_event(test_ids):
#     for event in Event.select():
#         if event.id in test_ids:
#             event.test_id = test_ids[event.id]
#         else:
#             event.test_id = None
#         event.save()
#
#
# def update_test_id_for_subtopics(test_ids):
#     for subtopic in Subtopic.select():
#         if subtopic.id in test_ids:
#             subtopic.test_id = test_ids[subtopic.id]
#         else:
#             subtopic.test_id = None
#         subtopic.save()
#
#
# test_ids = generate_test_ids()
# update_test_id_for_event(test_ids)
# update_test_id_for_subtopics(test_ids)


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


if __name__ == '__main__':
    app.run(debug=True)
