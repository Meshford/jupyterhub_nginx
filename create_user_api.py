from flask import Flask, request, jsonify
import subprocess
import os
import json
import requests
from functools import wraps
from flask import make_response
import urllib3
from bs4 import BeautifulSoup
urllib3.disable_warnings()
app = Flask(__name__)



@app.route('/create_user', methods=['POST', 'OPTIONS'])
def create_user():
    if request.method == 'OPTIONS':
        return '', 204

    # Используем request.form вместо request.json
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'basic')

    if not username or not password:
        return jsonify({'status': 'error', 'message': 'username and password required'}), 400

    try:
        subprocess.run(['id', username], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        user_exists = True
    except subprocess.CalledProcessError:
        user_exists = False

    if not user_exists:
        try:
            subprocess.run(['sudo', 'useradd', '-m', username], check=True)
            subprocess.run(['sudo', 'chpasswd'], input=f"{username}:{password}".encode(), check=True)
        except subprocess.CalledProcessError as e:
            return jsonify({'status': 'error', 'message': f'Failed to create user: {str(e)}'}), 500

    with open('/opt/jupyterhub/user_roles.json', 'r+') as f:
        user_roles = json.load(f)
        user_roles[username] = role
        f.seek(0)
        json.dump(user_roles, f)
        f.truncate()

    return jsonify({'status': 'ok', 'user_exists': user_exists, 'role': role})

@app.route('/get_jhub_token', methods=['POST', 'OPTIONS'])
def get_jhub_token():
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json(force=True)
    except Exception as e:
        print("Error to parsing JSON:", e)
        return jsonify({'status': 'error', 'message': 'Incorrect format of JSON'}), 400
    jhub_username = data.get('username')
    jhub_password = data.get('password')
    #xsrf_token = data.get('xsrf_token')  # ✅ Берем XSRF из тела запроса

    # if not xsrf_token:
    #     return jsonify({'status': 'error', 'message': 'XSRF-токен не передан'}), 400

    if not jhub_username or not jhub_password:
        return jsonify({'status': 'error', 'message': 'Missing username or password'}), 400

    session = requests.Session()
    
    login_page_response = session.get("https://aistartlab-practice.ru/hub/login", verify=False)
    if not login_page_response.ok:
        return jsonify({'status': 'error', 'message': f'Failed to load login page: {login_page_response.status_code}'}), 500


    html = login_page_response.text


    html = login_page_response.text
    if not isinstance(html, str):
        return jsonify({'status': 'error', 'message': 'Login page response is not a string'}), 500
    # 
    soup = BeautifulSoup(html, 'html.parser')

    # Ищем input с name="_xsrf"
    xsrf_input = soup.find('input', {'name': '_xsrf'})

    if not xsrf_input or not xsrf_input.has_attr('value'):
        return jsonify({'status': 'error', 'message': 'XSRF token not found in login page HTML'}), 500

    xsrf_token = xsrf_input['value']
    # 3. Отправляем XSRF-токен в теле POST-запроса
    login_data = {
        'username': jhub_username,
        'password': jhub_password,
        '_xsrf': xsrf_token
    }

    login_response = session.post(
        "https://aistartlab-practice.ru/hub/login",
        data=login_data,
        cookies=session.cookies,
        verify=False,
        # allow_redirects=False
    )
    
    if not login_response.ok:
        return jsonify({'status': 'error', 'message': f'{login_response.text} Login failed in JupyterHub'}), 400

    token_data = {
        'note': 'token_for_course',
        'expires_in': 86400 * 365
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'token 74d33bc50adc415f83873d8ff2545017'
    }
    token_response = session.post(
        f"https://aistartlab-practice.ru/hub/api/users/{jhub_username}/tokens",
        json=token_data,
        headers=headers,
        verify=False
    )

    if not token_response.ok:
        return jsonify({'status': 'error', 'message': 'Failed to generate token'}), 500

    return jsonify(token_response.json()), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
