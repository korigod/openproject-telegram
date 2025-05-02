import os
import json
import asyncio
import aiohttp
import aiogram
import bs4
import csv

from openproject_telegram import telegram_bot

openproject_url = os.environ['OPENPROJECT_URL']
api_path = os.environ['OPENPROJECT_API_URL']
telegram_user_id = os.environ['TELEGRAM_USER_ID']


async def get_users_telegram_ids(global_api_key):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            api_path + '/users',
            auth=aiohttp.BasicAuth('api_global', global_api_key),
            params={
                'pageSize': 1000,
                'sortBy': '[["id", "asc"]]'
            }
        ) as all_users_response:
            all_users_json = await all_users_response.json()
            users = all_users_json['_embedded']['elements']
            user_id_to_telegram_id = {user['id']: user['customField1'] for user in users if user['customField1'] is not None}
            # customField1 is Telegram ID (integer)
            return user_id_to_telegram_id


def read_users_api_keys(users_api_keys_csv_file_path):
    with open(users_api_keys_csv_file_path) as f:
        csv_rows = csv.DictReader(f)
        user_id_to_api_key = {int(user['user_id']): user['api_key'] for user in csv_rows}
        return user_id_to_api_key


async def process_unread_notifications(api_key, telegram_user_id):
    unread_filter = {"readIAN": {"operator": "=", "values": "f"}}
    filters = [unread_filter]
    filters_str = json.dumps(filters)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            api_path + '/notifications',
            auth=aiohttp.BasicAuth('apikey', api_key),
            params={
                'pageSize': 1000,
                'sortBy': '[["id", "asc"]]',
                'filters': filters_str
            }
        ) as all_notifications_response:
            all_notifications_json = await all_notifications_response.json()
            notifications = all_notifications_json['_embedded']['elements']
            for notification in notifications:
                async with session.get(
                    api_path + '/notifications/' + str(notification['id']),
                    auth=aiohttp.BasicAuth('apikey', api_key)
                ) as response:
                    n = await response.json()

                    try:
                        notification_activity_type = n['_embedded']['activity']['_type']
                    except KeyError:
                        print(n)
                        await telegram_bot.bot.send_message(telegram_user_id, str(n), parse_mode='HTML')
                        continue
                    msg = None
                    match notification_activity_type:
                        case 'Activity':
                            msg = f'''Задача: <b><a href="{
                                    openproject_url + n['_links']['resource']['href'].removeprefix('/api/v3')
                                }">{n['_links']['resource']['title']}</a></b>'''
                            for d in n['_embedded']['activity']['details']:
                                msg += '\n'
                                msg += d['html']
                        case 'Activity::Comment':
                            msg = f'''Задача: <b><a href="{
                                    openproject_url + n['_links']['resource']['href'].removeprefix('/api/v3')
                                }">{n['_links']['resource']['title']}</a></b>'''
                            msg += f"\nКомментарий {n['_embedded']['actor']['name']}: "
                            comment_html = bs4.BeautifulSoup(n['_embedded']['activity']['comment']['html'], features='lxml')
                            mentions = comment_html.find_all('a', {'class': 'user-mention op-uc-link'})
                            for m in mentions:
                                m.replace_with(f'<i>{m.text}</i>')
                            msg += comment_html.get_text()
                        case _:
                            try:
                                msg = n['reason'] + '\n' + n['_embedded']['activity']['_type'] + '\n' + n['_embedded']['activity']['details']
                            except KeyError:
                                pass
                            else:
                                print(msg)
                    if msg is not None:
                        try:
                            await telegram_bot.bot.send_message(telegram_user_id, msg, parse_mode='HTML')
                        except aiogram.exceptions.TelegramBadRequest as e:
                            print(e)
                            await telegram_bot.bot.send_message(telegram_user_id, f'Error! {str(e)}', parse_mode='HTML')
                        else:
                            # Remove Unread flag from notification so we won't fetch it next time
                            async with session.post(
                                api_path + '/notifications/' + str(notification['id']) + '/read_ian',
                                auth=aiohttp.BasicAuth('apikey', api_key),
                                headers={"Content-Type": "application/json"}
                            ) as response:
                                if response.status != 204:
                                    await telegram_bot.bot.send_message(
                                        telegram_user_id,
                                        f'Read status update error, code {str(response.status)} {str(await response.text())}',
                                        parse_mode='HTML'
                                    )


if __name__ == '__main__':
    asyncio.run(process_unread_notifications(
        api_key=os.environ['OPENPROJECT_API_KEY'], telegram_user_id=telegram_user_id
    ))
    asyncio.run(get_users_telegram_ids(os.environ['OPENPROJECT_GLOBAL_API_KEY']))
    print(read_users_api_keys('users'))
