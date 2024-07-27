import requests

BASE_URL = 'http://127.0.0.1:5000'  # Змініть на URL вашого сервера


def test_get_events():
    response = requests.get(f'{BASE_URL}/get-events')
    print(f'Status Code: {response.status_code}')
    print(f'Response JSON: {response.json()}')


if __name__ == '__main__':
    test_get_events()
