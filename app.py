import peewee
from flask import Flask, jsonify
from config import DATABASE
from models import Event, MainArticleTest, Subtopic, SubArticleTest, Content
from flask_cors import CORS
import json
from data import events_data
from peewee import IntegrityError

app = Flask(__name__)
CORS(app)

DATABASE.connect()
if Event.table_exists():
    Event.drop_table()
DATABASE.create_tables([Event, MainArticleTest, Subtopic, SubArticleTest, Content], safe=True)

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


if __name__ == '__main__':
    app.run(debug=True)
