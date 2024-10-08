from flask_bcrypt import Bcrypt

from config import DATABASE
from models import User

bcrypt = Bcrypt()


def create_test_user():
    with DATABASE.atomic():
        DATABASE.create_tables([User], safe=True)

        email = 'test1@example.com'
        password = 'c0-Fmv7*J9hl'
        user_name = "TestUser"
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            user = User.create(email=email, password=hashed_password, user_name=user_name)
            print(f"User {email} created successfully.")
        except Exception as e:
            print(f"Error creating user: {e}")


if __name__ == '__main__':
    create_test_user()
