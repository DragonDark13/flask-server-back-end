from flask import Flask

from services import delete_profile_service

app = Flask(__name__)

with app.app_context():
    result = delete_profile_service(4)
    print(result)