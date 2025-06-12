#!/bin/bash
# Получаем имя пользователя из GitHub
username="$1"
echo "Script started with username: $1" >> /tmp/debug_create_user.log

# Создаем пользователя, если его нет
if ! id "$username" &>/dev/null; then
    sudo /usr/sbin/useradd -m --badname "$username"
    sudo /usr/sbin/chpasswd <<< "$username:default_password"
    mkdir -p "/home/$username"
    chown -R "$username:$username" "/home/$username"
fi

# Обновляем user_roles.json через jq
sudo -u root jq --arg user "$username" '.[$user] //= "basic"' /opt/jupyterhub/user_roles.json > /tmp/user_roles.json.tmp && \
sudo mv /tmp/user_roles.json.tmp /opt/jupyterhub/user_roles.json
