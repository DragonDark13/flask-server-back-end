from flask import jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, create_refresh_token
from peewee import IntegrityError
from datetime import datetime
import json
import logging
from models import User, Event, MainArticleTest, Subtopic, SubArticleTest, Content, Test, UserTestCompletion
from initialize import add_user_test_completions, update_user_test_completion

bcrypt = Bcrypt()
logging.basicConfig(level=logging.INFO)


# Utility functions
def get_user_by_id(user_id):
    return User.get_or_none(User.id == user_id)


def get_user_by_name(user_name):
    return User.get_or_none(User.user_name == user_name)


def get_test_by_id(test_id):
    return Test.get_or_none(Test.id == test_id)


def hash_password(password):
    return bcrypt.generate_password_hash(password).decode('utf-8')


def verify_password(hashed_password, password):
    logging.info(f"Stored hashed password: {hashed_password}")
    logging.info(f"Provided password: {bcrypt.generate_password_hash(password).decode('utf-8')}")
    return bcrypt.check_password_hash(hashed_password, password)


def create_tokens(identity):
    return {
        'access_token': create_access_token(identity=identity),
        'refresh_token': create_refresh_token(identity=identity)
    }


def format_error(message, code=400):
    return jsonify({'message': message}), code


def format_success(message, data=None):
    response = {
        'success': True,
        'message': message}
    if data:
        response.update(data)
    return jsonify(response), 200


def format_success_for_registration(message, data=None):
    response = {
        'success': True,
        'message': message}
    if data:
        response.update(data)
    return jsonify(response), 201


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

        # Перевірка наявності main_article_test_questions та content
        if main_article_test_questions_data and content_data:
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


# Service functions
def register_user_service(data):
    email = data.get('email')
    password = data.get('password')
    user_name = data.get('userName')

    if User.select().where(User.user_name == user_name).exists():
        return format_error('User name already exists.')

    try:
        user = User.create(email=email, password=hash_password(password), user_name=user_name)
        add_user_test_completions(user)
        tokens = create_tokens(user.id)
        user_data = format_user_data(user, include_tests=True)
        return format_success_for_registration('User registered successfully.',
                                               {'tokens': tokens, 'user_data': user_data})
    except IntegrityError:
        return format_error('Email already exists.')


def login_user_service(data):
    user_name = data.get('user_name')
    password = data.get('password')

    logging.basicConfig(level=logging.INFO)

    logging.info(f"User Name: {user_name}")
    logging.info(f"Password: {password}")
    #
    # print(f"User Name: {user_name}")
    # print(f"Password: {password}")

    user = get_user_by_name(user_name)
    if not user or not verify_password(user.password, password):
        return format_error('Invalid user_name or password', 401)

    tokens = create_tokens(user.id)
    user_data = format_user_data(user, include_tests=True)
    return format_success('Login successful.', {'tokens': tokens, 'user_data': user_data})


def get_user_data_service(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return format_error('User not found', 404)

    user_data = format_user_data(user, include_tests=True)
    return format_success('User data retrieved successfully.', {'user_data': user_data})


def change_password_service(data, user_id):
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')

    user = get_user_by_id(user_id)
    if not user or not verify_password(user.password, current_password):
        return format_error('Current password is incorrect', 400)

    user.password = hash_password(new_password)
    user.save()
    return format_success('Password updated successfully.')


def update_profile_service(data, user_id):
    user_name = data.get('userName')

    if not user_name:
        return format_error('Username is required.')

    user = get_user_by_id(user_id)
    if User.select().where((User.user_name == user_name) & (User.id != user_id)).exists():
        return format_error('Username already taken.')

    user.user_name = user_name
    user.save()
    return format_success('Profile updated successfully.')


def delete_profile_service(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return format_error('User not found', 404)

    UserTestCompletion.delete().where(UserTestCompletion.user == user).execute()

    user.delete_instance()
    return format_success('Profile deleted successfully.')


def refresh_token_service(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return format_error('User not found', 404)

    token = create_access_token(identity=user_id)
    return format_success('Token refreshed successfully.', {'token': token})


def complete_test_service(user_id, data):
    test_id = data.get('test_id')
    completed = data.get('completed', False)

    if not user_id or not test_id:
        return format_error('User ID and Test ID are required', 400)

    user = get_user_by_id(user_id)
    test = get_test_by_id(test_id)

    if not user or not test:
        return format_error('Invalid User ID or Test ID', 404)

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
    return format_success('Test completed successfully.', {'user_data': user_data})


def reset_achievements_service(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return format_error('User not found', 404)

    UserTestCompletion.update(completed=0).where(UserTestCompletion.user == user).execute()

    user.current_level = 0
    user.additional_tests_completed = 0
    user.save()
    user_data = format_user_data(user, include_tests=True)
    return format_success('User achievements have been reset to the initial level.', {'user_data': user_data})
