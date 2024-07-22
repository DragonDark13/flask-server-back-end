from flask_login import UserMixin
from peewee import Model, CharField, AutoField, TextField, ForeignKeyField, IntegerField
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


class SubArticleTest(BaseModel):
    subtopic = ForeignKeyField(Subtopic, backref='sub_article_tests')
    question = TextField()
    options = TextField()  # Зберігає JSON дані
    correct_answers = TextField()  # Зберігає JSON дані


class User(BaseModel, UserMixin):
    email = CharField(unique=True)
    password = CharField()
    current_level = IntegerField(default=0)  # Додано нове поле для рівня проходження
    additional_tests_completed = IntegerField(default=0)  # Додано нове поле для кількості додаткових тестів
