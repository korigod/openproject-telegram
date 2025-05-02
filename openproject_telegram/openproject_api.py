import os
import json
import asyncio
import aiohttp
import aiogram
import bs4

from openproject_telegram import bot

openproject_url = os.environ['OPENPROJECT_URL']
api_path = os.environ['OPENPROJECT_API_URL']


async def get_all_unread_notifications(api_key):
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

                    msg = None
                    match n['_embedded']['activity']['_type']:
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
                            comment_html = bs4.BeautifulSoup(n['_embedded']['activity']['comment']['html'], features="lxml")
                            mentions = comment_html.find_all('a', {'class': 'user-mention op-uc-link'})
                            for m in mentions:
                                m.replace_with(f'<i>{m.text}</i>')
                            msg += comment_html.get_text()
                        case _:
                            print(n['reason'], n['_embedded']['activity']['_type'])
                    if msg is not None:
                        try:
                            await bot.bot.send_message(os.environ['TELEGRAM_USER_ID'], msg, parse_mode='HTML')
                        except aiogram.exceptions.TelegramBadRequest as e:
                            await bot.bot.send_message(os.environ['TELEGRAM_USER_ID'], f'Error! {str(e)}', parse_mode='HTML')
                        else:
                            # Remove Unread flag from notification so we won't fetch it next time
                            async with session.post(
                                api_path + '/notifications/' + str(notification['id']) + '/read_ian',
                                auth=aiohttp.BasicAuth('apikey', api_key),
                                headers={"Content-Type": "application/json"}
                            ) as response:
                                if response.status != 204:
                                    await bot.bot.send_message(
                                        os.environ['TELEGRAM_USER_ID'],
                                        f'Read status update error, code {str(response.status)} {str(await response.text())}',
                                        parse_mode='HTML'
                                    )
    await bot.session.close()


if __name__ == '__main__':
    asyncio.run(get_all_unread_notifications(api_key=os.environ['OPENPROJECT_API_KEY']))
