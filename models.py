from datetime import datetime

from flask_login import UserMixin
from peewee import Model, CharField, AutoField, TextField, ForeignKeyField, IntegerField, DateTimeField, SQL, \
    BooleanField
from config import DATABASE
import json


class BaseModel(Model):
    class Meta:
        database = DATABASE


class Event(BaseModel):
    date = CharField(null=True)
    text = TextField(null=True)
    achieved = TextField(null=True)


class Content(BaseModel):
    event = ForeignKeyField(Event, backref='contents')
    type = CharField(null=True)  # Поле type не є обов'язковим
    text = TextField()


class MainArticleTest(BaseModel):
    event = ForeignKeyField(Event, backref='main_article_tests')
    question = TextField()
    options = TextField()  # Зберігає JSON дані
    correct_answers = TextField()  # Зберігає JSON дані


class Subtopic(BaseModel):
    event = ForeignKeyField(Event, backref='subtopics')
    title = CharField()
    content = TextField()  # Зберігає JSON дані


class Test(BaseModel):
    title = CharField()  # Назва тесту або підтесту
    test_type = CharField()  # Тип тесту (Main Article або Sub Article)
    event = ForeignKeyField(Event, backref='tests')


class SubArticleTest(BaseModel):
    subtopic = ForeignKeyField(Subtopic, backref='sub_article_tests')
    question = TextField()
    options = TextField()  # Зберігає JSON дані
    correct_answers = TextField()  # Зберігає JSON дані


class User(BaseModel, UserMixin):
    email = CharField(unique=True)
    password = CharField()
    user_name = CharField(null=True)
    country = CharField(null=True)
    current_level = IntegerField(default=0)  # Додано нове поле для рівня проходження
    additional_tests_completed = IntegerField(default=0)  # Додано нове поле для кількості додаткових тестів


class UserTestCompletion(BaseModel):
    user = ForeignKeyField(User, backref='test_completions')
    user_name = CharField(null=True)
    test = ForeignKeyField(Test, backref='test_completions', null=True)
    test_title = CharField(null=True)
    completed = BooleanField(default=False)
    date_completed = DateTimeField(default=datetime.now)
    test_type = CharField()  # Додаємо нове поле для типу тесту



class UserResult(BaseModel):
    user = ForeignKeyField(User, backref='results')
    main_article_test = ForeignKeyField(MainArticleTest, backref='user_results', null=True)
    sub_article_test = ForeignKeyField(SubArticleTest, backref='user_results', null=True)
    score = IntegerField()
    date_taken = DateTimeField(default=datetime.now)  # Зберігає дату та час проходження тесту
