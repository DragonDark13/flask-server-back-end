from peewee import DoesNotExist

from config import DATABASE
from models import MainArticleTest, User, Subtopic, UserTestCompletion, Content, SubArticleTest, Test, \
    Event, \
    Counter
from data import events_data
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


def initialize_user_test_completions():
    for user_test_completion in UserTestCompletion.select():
        user = user_test_completion.user
        test = user_test_completion.test
        completed = user_test_completion.completed

        update_user_test_completion(user, test, completed)


def create_tables():
    with DATABASE:
        DATABASE.create_tables(
            [User, Event, MainArticleTest,
             Subtopic, SubArticleTest, Content,
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
        Counter.delete().execute()

        # Додавання нових записів
        for event_data in events_data:
            # Створення запису події
            # logging.info("Processing event data: %s", event_data)

            event = Event.create(
                date=event_data["date"],
                text=event_data["text"],
                achieved=event_data.get("achieved", None),
            )
            # logging.info("Created event: %s", event)

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


def add_main_article_tests():
    for event in Event.select():
        # Перевірити, чи існує основний тест для цього event
        existing_tests = MainArticleTest.select().where(MainArticleTest.event == event)
        if existing_tests:
            # Створення запису в таблиці Test
            test = Test.create(
                title=event.text,
                test_type='Main Article',
                event=event
            )
            # Додавання test_id до події
            event.test_id = test.id
            event.save()  # Зберегти зміни до бази даних


def add_sub_article_tests():
    for subtopic in Subtopic.select():
        # Перевірити, чи існують підтести для цього subtopic
        existing_tests = SubArticleTest.select().where(SubArticleTest.subtopic == subtopic)
        if existing_tests:
            # Створення запису в таблиці Test
            test = Test.create(
                title=subtopic.title,
                test_type='Sub Article',
                event=subtopic.event  # Потрібно встановити подію через Subtopic
            )
            # Додавання test_id до події
            subtopic.test_id = test.id
            subtopic.save()  # Зберегти зміни до бази даних


def add_user_test_completions(user):
    # Отримати всі тести
    tests = Test.select()

    # Створити записи в таблиці UserTestCompletion
    with DATABASE.atomic():
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


def add_all_users_test_completions():
    # Отримати всіх користувачів
    users = User.select()
    logging.info(f"Retrieved {len(users)} users")

    # Отримати всі тести
    tests = Test.select()
    logging.info(f"Retrieved {len(tests)} tests")

    # Створити записи в таблиці UserTestCompletion
    with DATABASE.atomic():

        for user in users:
            logging.info(f"User ID: {user.id}, User Name: {user.user_name}")

            for test in tests:
                # Перевірити, чи вже існує запис для цієї комбінації
                exists = UserTestCompletion.select().where(
                    UserTestCompletion.user == user,
                    UserTestCompletion.test == test
                ).exists()

                if not exists:
                    try:
                        UserTestCompletion.create(
                            user=user,
                            user_name=user.user_name if user.user_name else "default_user_name",  # Переконайтесь, що user_name не є NULL
                            test_title=test.title,
                            event=test.event,  # Потрібно встановити подію через Test
                            test=test,
                            test_type=test.test_type,  # Додаємо поле test_type
                            completed=False,  # За замовчуванням встановлено False
                            date_completed=datetime.now()
                        )
                        logging.info(f"Created UserTestCompletion for user {user.id} and test {test.id}")
                    except Exception as e:
                        logging.error(f"Error creating UserTestCompletion for user {user.id} and test {test.id}: {e}")

    logging.info("Completed adding all users' test completions")


def update_user_test_completion(user, test, completed):
    if completed:
        if test.test_type == 'Main Article':
            user.current_level += 1
        elif test.test_type == 'Sub Article':
            user.additional_tests_completed += 1
        user.save()


def clean_user_test_completions():
    # Отримуємо всі записи з UserTestCompletion
    user_test_completions = UserTestCompletion.select()

    for completion in user_test_completions:
        try:
            # Перевіряємо, чи існує користувач у таблиці User
            User.get(User.id == completion.user_id)
        except DoesNotExist:
            # Якщо користувач не існує, видаляємо відповідний запис
            completion.delete_instance()

# Виклик функції під час ініціалізації програми
