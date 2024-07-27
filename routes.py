from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_login import login_required, current_user
from services import (
    get_events_service,
    complete_test_service,
    register_user_service,
    login_user_service,
    change_password_service,
    update_profile_service,
    delete_profile_service,
    refresh_token_service,
    update_user_service, get_user_data_service
)


def register_routes(app):
    @app.route('/get-events', methods=['GET'])
    def get_events():
        return jsonify(get_events_service())

    @app.route('/complete-test', methods=['POST'])
    def complete_test():
        return complete_test_service(request.json)

    @app.route('/register', methods=['POST'])
    def register():
        return register_user_service(request.get_json())

    @app.route('/login', methods=['POST'])
    def login():
        return login_user_service(request.json)

    @app.route('/api/user', methods=['GET'])
    @jwt_required()
    def get_user_data():
        user_id = get_jwt_identity()
        user_data = get_user_data_service(user_id)
        return jsonify(user_data)

    @app.route('/change-password', methods=['POST'])
    @jwt_required()
    def change_password():
        return change_password_service(request.get_json(), get_jwt_identity())

    @app.route('/update-profile', methods=['POST'])
    @jwt_required()
    def update_profile():
        return update_profile_service(request.get_json(), get_jwt_identity())

    @app.route('/delete-profile', methods=['DELETE'])
    @jwt_required()
    def delete_profile():
        return delete_profile_service(get_jwt_identity())

    @app.route('/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        return refresh_token_service(get_jwt_identity())

    @app.route('/update_user', methods=['POST'])
    @login_required
    def update_user():
        return update_user_service(request.json, current_user)
