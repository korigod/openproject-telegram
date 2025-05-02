import os
import asyncio
from openproject_telegram import openproject_api, telegram_bot


async def process_all_users_notifications():
    user_id_to_telegram_id = await openproject_api.get_users_telegram_ids(os.environ['OPENPROJECT_GLOBAL_API_KEY'])
    user_id_to_api_key = openproject_api.read_users_api_keys('users')
    for user_id, api_key in user_id_to_api_key.items():
        await openproject_api.process_unread_notifications(
            api_key=api_key, telegram_user_id=user_id_to_telegram_id[user_id]
        )
    await telegram_bot.session.close()

async def main():
    while True:
        await asyncio.gather(
            process_all_users_notifications(),
            asyncio.sleep(2),
        )

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
