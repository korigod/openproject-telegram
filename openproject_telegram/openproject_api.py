import os
import json
import asyncio
import aiohttp

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
        ) as response:
            response_json = await response.json()
            notifications = response_json['_embedded']['elements']
            print(response_json['_embedded']['elements'])
            for n in notifications:
                msg = None
                match n['reason']:
                    case 'assigned':
                        msg = f'''Новая задача: *[{
                                n['_links']['resource']['title']
                            }]({
                                openproject_url + n['_links']['resource']['href'].removeprefix('/api/v3')
                            })*'''
                    case _:
                        print(n['reason'])
                if msg is not None:
                    await bot.bot.send_message(os.environ['TELEGRAM_USER_ID'], msg, parse_mode='MarkdownV2')
    await bot.session.close()


if __name__ == '__main__':
    asyncio.run(get_all_unread_notifications(api_key=os.environ['OPENPROJECT_API_KEY']))
