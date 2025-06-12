# Configuration file for jupyterhub.
c = get_config()  # noqa
import logging
import shutil
import os
import json
import pwd
import re
from oauthenticator.github import GitHubOAuthenticator
from jupyterhub.spawner import LocalProcessSpawner
import subprocess

# --- Логгер ---
log = logging.getLogger(__name__)

# --- Аутентификация через GitHub ---
c.JupyterHub.authenticator_class = GitHubOAuthenticator
c.GitHubOAuthenticator.client_id = 'Ov23liAkyE8gTISSPimN'  # Замените на ваш Client ID
c.GitHubOAuthenticator.client_secret = 'eaad5e58f0a0b62b1abed0446da32f8daec9fa22'  # Замените на ваш Client Secret
c.GitHubOAuthenticator.oauth_callback_url = 'https://aistartlab-practice.ru/hub/oauth_callback'
c.GitHubOAuthenticator.scope = ['read:user', 'user:email']
c.GitHubOAuthenticator.use_login_as_username = True

c.JupyterHub.log_level = 'DEBUG'

# Запускать JupyterLab по умолчанию
c.Spawner.default_url = '/lab'

# Администраторы и токены
c.Authenticator.admin_users = {'super_ya_nikitka_23_ya_ru'}
c.Authenticator.auto_login = True
c.Authenticator.allow_all = True  # Разрешать вход всем системным пользователям
c.JupyterHub.api_tokens = {
    '74d33bc50adc415f83873d8ff2545017': 'super_ya_nikitka_23_ya_ru'
}

# Сетевые настройки
c.JupyterHub.ip = '127.0.0.1'
c.JupyterHub.port = 8000
c.JupyterHub.base_url = '/hub'
c.JupyterHub.public_url = 'https://aistartlab-practice.ru/hub'

# --- Файл с ролями пользователей ---
USER_ROLES_FILE = '/opt/jupyterhub/user_roles.json'

def load_user_roles():
    try:
        with open(USER_ROLES_FILE) as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Cannot load user roles file: {e}")
        return {}

def copy_course_materials(username):
    home_dir = os.path.expanduser(f'~{username}')
    template_base = '/home/lessons'

    user_roles = load_user_roles()
    role = user_roles.get(username)
    if not role:
        log.warning(f"No role found for user {username}, skipping copy.")
        return

    src = os.path.join(template_base, role)
    dst = home_dir

    target_file = os.path.join(dst, 'lesson0.ipynb')
    if not os.path.exists(target_file):
        try:
            shutil.copytree(src, dst, dirs_exist_ok=True)
            log.info(f"Copied course materials for user {username} with role {role}")
        except Exception as e:
            log.error(f"Failed to copy course materials for user {username}: {e}")
    else:
        log.info(f"Course materials already exist for user {username}, skipping copy.")

def normalize_username(username):
    if not username:
        log.error("Empty name for normalize")
        return None
    username = username.lower()
    username = re.sub(r'[^a-z0-9_-]', '', username)[:32]
    return username

def user_exists(username):
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

def create_system_user(username):
    username = normalize_username(username)
    if not username:
        log.error("Empty username after normalization")
        return
    try:
        if not user_exists(username):
            log.info(f"Creating system user: {username}")
            subprocess.run(['/home/create_user_from_github.sh', username], check=True)
        else:
            log.info(f"User {username} already exists")
    except subprocess.CalledProcessError as e:
        log.error(f"Failed to create system user {username}: {e}")
        raise

def pre_spawn_hook(spawner):
    if spawner.user.name:
        username = normalize_username(spawner.user.name)
        if username:
            spawner.normalized_username = username
            create_system_user(username)
            copy_course_materials(username)
        else:
            log.error("Username empty after normalization in pre_spawn_hook")
    else:
        log.error("User.name is empty in pre_spawn_hook")

class CustomSpawner(LocalProcessSpawner):
    def start(self):
        username = getattr(self, 'normalized_username', normalize_username(self.user.name))
        user_roles = load_user_roles()
        role = user_roles.get(username)

        if role in {'basic', 'simple', 'intermediate', 'full'}:
            self.default_url = '/lab/tree/lesson0.ipynb'
        else:
            self.default_url = '/lab'

        return super().start()

c.JupyterHub.spawner_class = CustomSpawner
c.Spawner.pre_spawn_hook = pre_spawn_hook
