# Configuration file for jupyterhub.

c = get_config()  # noqa

import logging
import shutil
import os
import json
from jupyterhub.spawner import LocalProcessSpawner

# --- Настройка JupyterHub ---

#c.JupyterHub.ip = '0.0.0.0'
#c.JupyterHub.port = 8000

# Запускать JupyterLab по умолчанию
c.Spawner.default_url = '/lab'
c.Authenticator.allowed_users = {"super_ya_nikitka_23_ya_ru"}
c.JupyterHub.admin_users = {'super_ya_nikitka_23_ya_ru'}
c.NotebookApp.allow_remote_access = True
c.JupyterHub.allow_rest_api_access = True  # Разрешает доступ через REST API
c.JupyterHub.api_tokens = {
    '74d33bc50adc415f83873d8ff2545017': 'super_ya_nikitka_23_ya_ru'  # Явно укажите токен и пользователя
}
# Разрешать вход всем системным пользователям
c.Authenticator.allow_all = True

# JupyterHub слушает только локальный интерфейс, т.к. внешний доступ будет через Nginx
c.JupyterHub.bind_url = 'http://127.0.0.1:8000'

# Доверять заголовкам прокси (важно для корректной работы HTTPS)
c.JupyterHub.trust_xheaders = True
# --- Логгер ---
log = logging.getLogger(__name__)

# --- Путь к файлу с ролями пользователей ---
USER_ROLES_FILE = '/opt/jupyterhub/user_roles.json'
c.JupyterHub.generate_config_tag = True
def load_user_roles():
    """
    Загружает роли пользователей из JSON-файла.
    Если файл не найден или ошибка, возвращает пустой словарь.
    """
    try:
        with open(USER_ROLES_FILE) as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Cannot load user roles file: {e}")
        return {}

def copy_course_materials(spawner):
    """
    Копирует материалы курса из шаблонной папки в домашнюю директорию пользователя,
    основываясь на роли пользователя.
    Копирование происходит только если в домашней папке отсутствует файл 'first-lesson.ipynb',
    чтобы не перезаписывать прогресс.
    """
    username = spawner.user.name
    home_dir = os.path.expanduser(f'~{username}')
    template_base = '/srv/jupyterhub/course_templates'

    user_roles = load_user_roles()
    role = user_roles.get(username)
    if not role:
        log.warning(f"No role found for user {username}, skipping copy.")
        return

    src = os.path.join(template_base, role)
    dst = home_dir

    target_file = os.path.join(dst, 'first-lesson.ipynb')
    if not os.path.exists(target_file):
        try:
            shutil.copytree(src, dst, dirs_exist_ok=True)
            log.info(f"Copied course materials for user {username} with role {role}")
        except Exception as e:
            log.error(f"Failed to copy course materials for user {username}: {e}")
    else:
        log.info(f"Course materials already exist for user {username}, skipping copy.")

c.Spawner.pre_spawn_hook = copy_course_materials

# --- Кастомный спавнер для установки стартового URL в зависимости от роли ---
class CustomSpawner(LocalProcessSpawner):
    def start(self):
        username = self.user.name
        user_roles = load_user_roles()
        role = user_roles.get(username)

        if role in {'basic', 'simple', 'intermediate', 'full'}:
            self.default_url = '/lab/tree/first-lesson.ipynb'
        else:
            self.default_url = '/lab'

        return super().start()

c.JupyterHub.spawner_class = CustomSpawner
