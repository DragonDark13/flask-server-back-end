import requests

url = 'http://127.0.0.1:5000/login'  # Адреса вашого локального сервера Flask
data = {
    'email': 'test@example.com',
    'password': 'testpassword'
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())
