from flask_bcrypt import Bcrypt

from models import User, Event, MainArticleTest, Subtopic, SubArticleTest, Content, UserResult, Test, UserTestCompletion
from datetime import datetime
from flask_jwt_extended import create_access_token, create_refresh_token
from peewee import IntegrityError
import json
import logging

bcrypt = Bcrypt()


def get_events_service():
    results = []
    for event in Event.select():
        main_article_tests = MainArticleTest.select().where(MainArticleTest.event == event)
        main_article_tests_data = [{'id': mat.id, 'question': mat.question, 'options': json.loads(mat.options),
                                    'correct_answers': json.loads(mat.correct_answers)} for mat in main_article_tests]

        subtopics = Subtopic.select().where(Subtopic.event == event)
        subtopics_data = []
        for subtopic in subtopics:
            sub_article_tests = SubArticleTest.select().where(SubArticleTest.subtopic == subtopic)
            sub_article_tests_data = [{'id': sat.id, 'question': sat.question, 'options': json.loads(sat.options),
                                       'correct_answers': json.loads(sat.correct_answers)} for sat in sub_article_tests]
            subtopics_data.append({'title': subtopic.title, 'content': json.loads(subtopic.content),
                                   'sub_article_tests': sub_article_tests_data})

        content_items = Content.select().where(Content.event == event)
        content_data = [{'type': content_item.type, 'text': content_item.text} for content_item in content_items]

        results.append({'id': event.id,
                        'date': event.date,
                        'text': event.text,
                        'achieved': event.achieved,
                        'main_article_tests': main_article_tests_data,
                        'subtopics': subtopics_data,
                        'content': content_data})
    return results


def complete_test_service(data):
    user_id = data.get('user_id')
    test_id = data.get('test_id')
    completed = data.get('completed', False)

    if not user_id or not test_id:
        return {'error': 'User ID and Test ID are required'}, 400

    user = User.get_or_none(User.id == user_id)
    test = Test.get_or_none(Test.id == test_id)

    if not user or not test:
        return {'error': 'Invalid User ID or Test ID'}, 404

    UserTestCompletion.create(user=user, test=test, completed=completed, date_completed=datetime.now())
    return {'success': True}, 200


def format_user_data(user, include_tests=False):
    user_data = {
        'user_name': user.user_name,
        'email': user.email,
        'current_level': user.current_level,
        'additional_tests_completed': user.additional_tests_completed
    }

    if include_tests:
        user_tests = UserTestCompletion.select().where(UserTestCompletion.user_id == user.id)
        user_tests_data = [{
            'test_id': test.test.id,
            'test_type': test.test_type,
            'event_id': test.test.event.id if test.test.event else None,
            'parent_article_title': test.test_title,
            'completed': test.completed
        } for test in user_tests]
        user_data['tests'] = user_tests_data

    return user_data


def register_user_service(data):
    email = data.get('email')
    password = data.get('password')
    user_name = data.get('userName')
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    if User.select().where(User.user_name == user_name).exists():
        return {'message': 'User name already exists.'}, 400

    try:
        user = User.create(email=email, password=hashed_password, user_name=user_name)
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        user_data = format_user_data(user, include_tests=True)  # Включаємо тести
        return {
                   'message': 'User registered successfully.',
                   'token': access_token,
                   'refresh_token': refresh_token,
                   'user_data': user_data
               }, 201
    except IntegrityError:
        return {'message': 'Email already exists.'}, 400


def login_user_service(data):
    email = data.get('email')
    password = data.get('password')
    try:
        logging.info(f"Attempting to log in user with email: {email}")
        user = User.get(User.email == email)
        if bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)

            user_data = format_user_data(user, include_tests=True)  # Включаємо тести

            logging.info(f"User tests data: {user_data.get('tests')}")

            return {
                'success': True,
                'token': access_token,
                'refresh_token': refresh_token,
                'user_data': user_data
            }
        else:
            logging.warning("Invalid email or password")
            return {'success': False, 'message': 'Invalid email or password'}, 401
    except User.DoesNotExist:
        logging.error("User does not exist")
        return {'success': False, 'message': 'Invalid email or password'}, 401


def get_user_data_service(user_id):
    try:
        user = User.get(User.id == user_id)
        user_data = format_user_data(user, include_tests=True)  # Включаємо тести
        return {'success': True, 'user_data': user_data}
    except User.DoesNotExist:
        return {'success': False, 'message': 'User not found'}


def change_password_service(data, user_id):
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')

    user = User.get(User.id == user_id)
    if not bcrypt.check_password_hash(user.password, current_password):
        return {'message': 'Current password is incorrect'}, 400

    hashed_new_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.password = hashed_new_password
    user.save()
    return {'message': 'Password updated successfully'}, 200


def update_profile_service(data, user_id):
    user_name = data.get('userName')

    if not user_name:
        return {'message': 'Username is required.'}, 400

    user = User.get(User.id == user_id)
    if User.select().where((User.user_name == user_name) & (User.id != user_id)).exists():
        return {'message': 'Username already taken.'}, 400

    user.user_name = user_name
    user.save()
    return {'message': 'Profile updated successfully'}, 200


def delete_profile_service(user_id):
    user = User.get(User.id == user_id)
    user.delete_instance()
    return {'message': 'Profile deleted successfully'}, 200


def refresh_token_service(user_id):
    access_token = create_access_token(identity=user_id)
    return {'token': access_token}, 200


def update_user_service(data, current_user):
    user_name = data.get('user_name')

    if not user_name:
        return {'error': 'Username is required'}, 400

    user = User.get(User.id == current_user.id)
    user.user_name = user_name
    user.save()
    return {'success': True}, 200
