"""Notification Helper"""

import requests

def discord_webhook(webhook: str, message: str) -> bool:
    """
    Send a Discord Webhook message

    :param webhook:
    :param message:
    :return:
    """
    data = {
        "username": "CanaryCD",
        "avatar_url": "https://cdn.rehborn.org/images/canary-birb.png",
        "content": message[:2000],
    }
    try:
        response = requests.post(webhook, data, timeout=1)
        return True if response.status_code == '204' else False
    except requests.exceptions.RequestException:
        return False
