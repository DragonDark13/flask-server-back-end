from flask import jsonify
from flask_bcrypt import Bcrypt
from initialize import update_user_test_completion
from models import User, Event, MainArticleTest, Subtopic, SubArticleTest, Content, UserResult, Test, UserTestCompletion
from datetime import datetime
from flask_jwt_extended import create_access_token, create_refresh_token
from peewee import IntegrityError
import json
import logging

bcrypt = Bcrypt()

# Логування налаштувань
logging.basicConfig(level=logging.INFO)


def get_test_id(test_type, event=None, subtopic=None):
    if event:
        test = Test.select().where(Test.event == event, Test.test_type == test_type).first()
    elif subtopic:
        test = Test.select().where(Test.event == subtopic.event, Test.test_type == test_type).first()
    return test.id if test else None


def get_test_questions(test_model, event=None, subtopic=None):
    if event:
        questions = test_model.select().where(test_model.event == event)
    elif subtopic:
        questions = test_model.select().where(test_model.subtopic == subtopic)

    return [{
        'id': test.id,
        'question': test.question,
        'options': json.loads(test.options),
        'correct_answers': json.loads(test.correct_answers)
    } for test in questions]


def get_events_service():
    results = []
    for event in Event.select():
        main_article_test_questions_data = get_test_questions(MainArticleTest, event=event)

        subtopics_data = []
        for subtopic in Subtopic.select().where(Subtopic.event == event):
            sub_article_tests_data = get_test_questions(SubArticleTest, subtopic=subtopic)
            subtopics_data.append({
                'id': subtopic.id,
                'title': subtopic.title,
                'content': json.loads(subtopic.content),
                'sub_article_test_questions': sub_article_tests_data,
                'sub_article_test_id': subtopic.test_id
            })

        content_items = Content.select().where(Content.event == event)
        content_data = [{'type': item.type, 'text': item.text} for item in content_items]

        results.append({
            'id': event.id,
            'date': event.date,
            'text': event.text,
            'achieved': event.achieved,
            'main_article_test_questions': main_article_test_questions_data,
            'main_article_test_id': event.test_id,
            'subtopics': subtopics_data,
            'content': content_data
        })

    return results


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
            'test_id': user_test.test.id if user_test.test else None,
            'test_type': user_test.test_type,
            'event_id': user_test.test.event.id if user_test.test and user_test.test.event else None,
            'parent_article_title': user_test.test_title,
            'completed': user_test.completed
        } for user_test in user_tests]

        user_data['tests_completed_list'] = user_tests_data

    return user_data


def register_user_service(data):
    email = data.get('email')
    password = data.get('password')
    user_name = data.get('userName')
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    logging.info(f"Registering user with email: {email}")

    if User.select().where(User.user_name == user_name).exists():
        return {'message': 'User name already exists.'}, 400

    try:
        user = User.create(email=email, password=hashed_password, user_name=user_name)
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        user_data = format_user_data(user, include_tests=True)
        return {
                   'message': 'User registered successfully.',
                   'token': access_token,
                   'refresh_token': refresh_token,
                   'user_data': user_data
               }, 201
    except IntegrityError:
        return {'message': 'Email already exists.'}, 400


def login_user_service(data):
    user_name = data.get('user_name')
    password = data.get('password')
    logging.info(f"user_name: {user_name}")
    logging.info(f"user_name: {password}")
    try:
        logging.info(f"Attempting to log in user with user_name: {user_name}")
        user = User.get(User.user_name == user_name)

        if bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            user_data = format_user_data(user, include_tests=True)
            return {
                'success': True,
                'token': access_token,
                'refresh_token': refresh_token,
                'user_data': user_data
            }
        else:
            logging.warning("Invalid user_name or password")
            return {'success': False, 'message': 'Invalid user_name or password'}, 401
    except User.DoesNotExist:
        logging.error("User does not exist")
        return {'success': False, 'message': 'Invalid user_name or password'}, 401


def get_user_data_service(user_id):
    try:
        user = User.get(User.id == user_id)
        user_data = format_user_data(user, include_tests=True)
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


def complete_test_service(user_id, data):
    test_id = data.get('test_id')
    completed = data.get('completed', False)

    if not user_id or not test_id:
        return {'error': 'User ID and Test ID are required'}, 400

    user = User.get_or_none(User.id == user_id)
    test = Test.get_or_none(Test.id == test_id)

    if not user or not test:
        return {'error': 'Invalid User ID or Test ID'}, 404

    user_test_completion, created = UserTestCompletion.get_or_create(
        user=user,
        test=test,
        defaults={'completed': completed, 'date_completed': datetime.now()}
    )

    if not created:
        user_test_completion.completed = completed
        user_test_completion.date_completed = datetime.now()
        user_test_completion.save()

    update_user_test_completion(user, test, completed)

    user_data = format_user_data(user, include_tests=True)
    return {'success': True, 'user_data': user_data}


def reset_achievements_service(user_id):
    user = User.get(User.id == user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Видалити всі записи про завершені тести
    UserTestCompletion.delete().where(UserTestCompletion.user == user).execute()

    # Скинути рівень користувача
    user.current_level = 0
    user.additional_tests_completed = 0
    user.save()
    user_data = format_user_data(user, include_tests=True)

    return jsonify({'message': 'User achievements have been reset to the initial level', 'user_data': user_data}), 200
