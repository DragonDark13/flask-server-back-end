from flask_bcrypt import Bcrypt

from initialize import update_user_test_completion
from models import User, Event, MainArticleTest, Subtopic, SubArticleTest, Content, UserResult, Test, UserTestCompletion
from datetime import datetime
from flask_jwt_extended import create_access_token, create_refresh_token
from peewee import IntegrityError
import json
import logging

bcrypt = Bcrypt()


def get_test_id_for_event(event):
    # Отримати ідентифікатор тесту для основних тестів
    test = Test.select().where(Test.event == event, Test.test_type == 'Main Article').first()
    return test.id if test else None


def get_test_id_for_subtopic(subtopic):
    # Отримати ідентифікатор тесту для підтем
    test = Test.select().where(Test.event == subtopic.event, Test.test_type == 'Sub Article').first()
    return test.id if test else None


def get_sub_article_tests(subtopic):
    # Отримати всі тести для підтем
    sub_article_test_questions = SubArticleTest.select().where(SubArticleTest.subtopic == subtopic)
    sub_article_tests_data = [{
        'id': test.id,  # Ідентифікатор питання
        'question': test.question,
        'options': json.loads(test.options),
        'correct_answers': json.loads(test.correct_answers)
    } for test in sub_article_test_questions]

    return sub_article_tests_data


def get_main_article_test_questions(event):
    # Отримати всі тести для події
    main_article_test_questions = MainArticleTest.select().where(MainArticleTest.event == event)
    main_article_test_questions_data = [{
        'id': test.id,  # Ідентифікатор питання
        'question': test.question,
        'options': json.loads(test.options),
        'correct_answers': json.loads(test.correct_answers),
    } for test in main_article_test_questions]

    return main_article_test_questions_data


def get_events_service():
    results = []
    for event in Event.select():
        main_article_test_questions_data = get_main_article_test_questions(event)

        subtopics_data = []
        for subtopic in Subtopic.select().where(Subtopic.event == event):
            sub_article_tests_data = get_sub_article_tests(subtopic)
            subtopics_data.append({
                'id': subtopic.id,
                'title': subtopic.title,
                'content': json.loads(subtopic.content),
                'sub_article_test_questions': sub_article_tests_data,
                'sub_article_test_id': subtopic.test_id  # Ідентифікатор тесту для підтем
            })

            content_items = Content.select().where(Content.event == event)
            content_data = []

            for content_item in content_items:
                content_data.append({
                    'type': content_item.type,
                    'text': content_item.text
                })

        results.append({
            'id': event.id,
            'date': event.date,
            'text': event.text,
            'achieved': event.achieved,
            'main_article_test_questions': main_article_test_questions_data,
            'main_article_test_id': event.test_id,  # Ідентифікатор тесту для основних тестів
            'subtopics': subtopics_data,
            'content': content_data
            # Припускаючи, що є один контент для події
        })

    return results


#
# def add_main_article_test_questions():
#     for event in Event.select():
#         # Перевірити, чи існує основний тест для цього event
#         existing_tests = MainArticleTest.select().where(MainArticleTest.event == event)
#         if existing_tests:
#             Test.create(
#                 title=event.text,
#                 test_type='Main Article',
#                 event=event
#             )
#
#
# add_main_article_test_questions()
#
#
# def add_sub_article_tests():
#     for subtopic in Subtopic.select():
#         # Перевірити, чи існують підтести для цього subtopic
#         existing_tests = SubArticleTest.select().where(SubArticleTest.subtopic == subtopic)
#         if existing_tests:
#             Test.create(
#                 title=subtopic.title,
#                 test_type='Sub Article',
#                 event=subtopic.event  # Потрібно встановити подію через Subtopic
#             )
#
#
# add_sub_article_tests()


def format_user_data(user, include_tests=False):
    user_data = {
        'user_name': user.user_name,
        'email': user.email,
        'current_level': user.current_level,
        'additional_tests_completed': user.additional_tests_completed
    }

    if include_tests:
        user_tests = UserTestCompletion.select().where(UserTestCompletion.user_id == user.id)
        user_tests_data = []
        for user_test in user_tests:
            try:
                test = user_test.test  # Отримати тест
                user_tests_data.append({
                    'test_id': test.id,
                    'test_type': user_test.test_type,
                    'event_id': test.event.id if test.event else None,
                    'parent_article_title': user_test.test_title,
                    'completed': user_test.completed
                })
            except Test.DoesNotExist:
                # Логування помилки або будь-яка інша обробка
                print(f'Test with id {user_test.test_id} does not exist.')
                user_tests_data.append({
                    'test_id': None,
                    'test_type': user_test.test_type,
                    'event_id': None,
                    'parent_article_title': user_test.test_title,
                    'completed': user_test.completed
                })

        user_data['tests_completed_list'] = user_tests_data

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


# Приклад функції для отримання user_id з токена (використовуйте свою логіку)
def complete_test_service(user_id, data):
    test_id = data.get('test_id')
    completed = data.get('completed', False)

    if not user_id or not test_id:
        return {'error': 'User ID and Test ID are required'}, 400

    user = User.get_or_none(User.id == user_id)
    test = Test.get_or_none(Test.id == test_id)

    if not user or not test:
        return {'error': 'Invalid User ID or Test ID'}, 404

    # Перевірити, чи вже існує запис для цієї комбінації
    user_test_completion = UserTestCompletion.get_or_none(
        UserTestCompletion.user == user,
        UserTestCompletion.test == test
    )

    if user_test_completion:
        # Оновити існуючий запис
        user_test_completion.completed = completed
        user_test_completion.date_completed = datetime.now()
        user_test_completion.save()
    else:
        # Створити новий запис
        UserTestCompletion.create(
            user=user,
            test=test,
            test_title=test.title,
            test_type=test.test_type,
            event=test.event,
            completed=completed,
            date_completed=datetime.now()
        )

    # Оновлення поля current_level та additional_tests_completed
    update_user_test_completion(user, test, completed)

    # Повернення даних користувача після завершення тесту
    user_data = format_user_data(user, include_tests=True)
    return {
        'success': True,
        'user_data': user_data
    }
