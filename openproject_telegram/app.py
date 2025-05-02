import os
import asyncio
from openproject_telegram import openproject_api


def process_all_users_notifications():
    user_id_to_telegram_id = asyncio.run(openproject_api.get_users_telegram_ids(os.environ['OPENPROJECT_GLOBAL_API_KEY']))
    user_id_to_api_key = openproject_api.read_users_api_keys('users')
    for user_id, api_key in user_id_to_api_key.items():
        asyncio.run(openproject_api.process_unread_notifications(
            api_key=api_key, telegram_user_id=user_id_to_telegram_id[user_id]
        ))


if __name__ == '__main__':
    process_all_users_notifications()
