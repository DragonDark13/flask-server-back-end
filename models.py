from datetime import datetime

from flask_login import UserMixin
from peewee import Model, CharField, TextField, ForeignKeyField, DateTimeField, BooleanField, IntegerField
from config import DATABASE
import json


class BaseModel(Model):
    class Meta:
        database = DATABASE


class Counter(BaseModel):
    name = CharField(primary_key=True)  # Ім'я лічильника
    value = IntegerField(default=0)  # Поточне значення лічильника


def get_next_id():
    with DATABASE.atomic():
        counter, created = Counter.get_or_create(name='global_counter', defaults={'value': 0})
        counter.value += 1
        counter.save()
        return counter.value


class Event(BaseModel):
    # id_test = IntegerField(primary_key=True, default=get_next_id)
    date = CharField(null=True)
    text = TextField(null=True)
    achieved = TextField(null=True)
    test_id = IntegerField(
        default=get_next_id)  # Зберігає строку з порядковими номерами всіх тестів для події


class Content(BaseModel):
    event = ForeignKeyField(Event, backref='contents')
    type = CharField(null=True)
    text = TextField()


class Test(BaseModel):
    title = CharField()
    test_type = CharField()
    event = ForeignKeyField(Event, backref='tests')


class MainArticleTest(BaseModel):
    event = ForeignKeyField(Event, backref='main_article_test_questions')
    question = TextField()
    options = TextField()
    correct_answers = TextField()


class Subtopic(BaseModel):
    # id_test = IntegerField(primary_key=True, default=get_next_id)
    event = ForeignKeyField(Event, backref='subtopics')
    title = CharField()
    content = TextField()  # Зберігає JSON дані
    test_id = IntegerField(
        default=get_next_id)  # Зберігає строку з порядковими номерами всіх тестів для події


class SubArticleTest(BaseModel):
    subtopic = ForeignKeyField(Subtopic, backref='sub_article_test_questions')
    question = TextField()
    options = TextField()
    correct_answers = TextField()


class User(BaseModel, UserMixin):
    email = CharField(unique=True)
    password = CharField()
    user_name = CharField(null=True)
    country = CharField(null=True)
    current_level = IntegerField(default=0)  # Додано нове поле для рівня проходження
    additional_tests_completed = IntegerField(default=0)  # Додано нове поле для кількості додаткових тестів


class UserResult(BaseModel):
    user = ForeignKeyField(User, backref='results')
    result = TextField()


class UserTestCompletion(BaseModel):
    user = ForeignKeyField(User, backref='test_completions')
    user_name = CharField()
    test_title = CharField()
    event = ForeignKeyField(Event, backref='user_test_completions')
    test = ForeignKeyField(Test, backref='user_test_completions')
    test_type = CharField()
    completed = BooleanField(default=False)
    date_completed = DateTimeField(null=True)
