from app import DATABASE, User, save_user_result
from flask_bcrypt import Bcrypt

from models import UserResult, MainArticleTest

bcrypt = Bcrypt()


def create_test_user():
    with DATABASE.atomic():
        DATABASE.create_tables([User], safe=True)

        email = 'test@example.com'
        password = 'testpassword'
        user_name = "Test User"
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            user = User.create(email=email, password=hashed_password, user_name=user_name)
            print(f"User {email} created successfully.")
        except Exception as e:
            print(f"Error creating user: {e}")


# user_result_main = UserResult.create(
#     user=user_instance,
#     main_article_test=main_article_test_instance,
#     score=90
# )
#
# user_result_sub = UserResult.create(
#     user=user_instance,
#     sub_article_test=sub_article_test_instance,
#     score=85
# )

# user2 = User.create(user_name='Test User2', email='user2@example.com', password='password456')

if __name__ == '__main__':
    create_test_user()
