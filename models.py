from peewee import Model, CharField, AutoField, TextField, ForeignKeyField
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
