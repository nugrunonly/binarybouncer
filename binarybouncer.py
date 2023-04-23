from twitchAPI import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.types import AuthScope, ChatEvent
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatCommand
from twitchAPI.helper import first
import asyncio
import credentials
import json
from urllib.request import urlopen
import datetime

class ModeratorError(Exception):
    pass


class BinaryBouncer:
    def __init__(self, app_id, app_secret, user_scope, target_channel):
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_scope = user_scope
        self.target_channel = target_channel
        self.twitch = None
        self.chat = None
        self.bot_id = '828159307'


    async def get_user_id(self, username):
        try:
            user = await first(self.twitch.get_users(logins=[username]))
            return user.id
        except Exception as e:
            print(f"Error: {e}")
            return None

    
    async def add_bot(self, botname, id):
        with open('alivebots.json') as d:
            old_data = json.load(d)
            old_data[botname] = id
            with open('alivebots.json', mode = 'w') as db:
                json.dump(old_data, db, indent = 2, ensure_ascii = False)
            print('added', botname, 'to the alive bots', id)

    async def del_bot(self, botname, id):
        with open('deadbots.json') as d:
            old_data = json.load(d)
            old_data[botname] = id
            with open('deadbots.json', mode = 'w') as db:
                json.dump(old_data, db, indent = 2, ensure_ascii = False)
            print('added', botname, 'to the dead bots', id)
    
    async def build_banlist(self):
        url = 'https://api.twitchinsights.net/v1/bots/all'
        response = urlopen(url)
        botlist = json.loads(response.read())
        bots = botlist['bots']
        for name in range(len(bots)):
            user_id = await self.get_user_id(bots[name][0])
            if user_id == None:
                await self.del_bot(bots[name][0], user_id)
            else:
                await self.add_bot(bots[name][0], user_id)
            await asyncio.sleep(0.1)

        
    async def ban_user(self, username, channel_id, reason=None):
        user_id = await self.get_user_id(username)
        if user_id is None:
            print(f'Error: Could not find user {username}')
            await self.del_bot(username, user_id)
            return
        while True:
            try:
                if reason is None:
                    reason = "Bot"
                await self.twitch.ban_user(channel_id, self.bot_id, user_id, reason)
                print(f'Banned user {username} from channel ({channel_id})')
                break
            except Exception as e:
                print(f'Error banning user {username}: {e}')
                if isinstance(e, KeyError) and e.args[0] == 'data':
                    raise ModeratorError('Bot does not have required moderator privileges')
                elif isinstance(e, KeyError):
                    print(f'User {username} not banned, likely already banned or does not exist.')
                    break
                else:
                    break

        
    async def unban_user(self, username, channel_id):
        user_id = await self.get_user_id(username)
        if user_id is None:
            print(f'Error: Could not find user {username}')
            return
        try:
            await self.twitch.unban_user(channel_id, self.bot_id, user_id)
            print(f'Unbanned user {username} from channel ({channel_id})')
        except Exception as e:
            print(f"{self.bot_id} - Error {e}")
            return None
        

    async def on_ready(self, ready_event: EventData):
        print('Bot is ready for work, joining channels')
        await ready_event.chat.join_room(self.target_channel)
        await self.ban_target()
        await self.loop_stuff()


    async def on_message(self, msg: ChatMessage):
        print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')


    async def join(self, cmd: ChatCommand):
        id = await self.get_user_id(cmd.user.name)
        with open('channels.json') as c:
            old_data = json.load(c)
            if cmd.user.name not in old_data:
                old_data[cmd.user.name] = id
                with open('channels.json', mode = 'w') as c:
                    json.dump(old_data, c, indent = 2, ensure_ascii = False)
                print(cmd.user.name, 'added to the Bot-Free zone -- ID: ', id)
                with open('joinhistory.txt', 'r+') as joinhistory:
                    joined = joinhistory.read()
                    if cmd.user.name not in joined:
                        await self.super_ban(cmd.user.name, id)
                    

    async def leave_channel(self, cmd: ChatCommand):
        id = await self.get_user_id(cmd.user.name)
        with open('channels.json') as c:
            old_data = json.load(c)
            if cmd.user.name in old_data:
                formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')
                print('Removing a channel -- ', {cmd.user.name}, 'at ', formatted_date)
                text = f'You have left the bot-free zone, {cmd.user.name}'
                await self.chat.send_message('binarybouncer', text)
                with open('channels.json') as c:
                    old_data = json.load(c)
                    if cmd.user.name in old_data:
                        del old_data[cmd.user.name]
                        with open('channels.json', mode = 'w') as c:
                            json.dump(old_data, c, indent = 2, ensure_ascii = False)
                        print(cmd.user.name, '- You have left the bot-free zone', id)
    

    async def super_leave(self, cmd: ChatCommand):
        id = await self.get_user_id(cmd.user.name)
        with open('channels.json') as c:
            old_data = json.load(c)
            if cmd.user.name in old_data:
                formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')
                print('Removing a channel -- ', {cmd.user.name}, 'at ', formatted_date)
                text = f'You have left the bot-free zone, {cmd.user.name}'
                await self.chat.send_message('binarybouncer', text)
                with open('channels.json') as c:
                    old_data = json.load(c)
                    if cmd.user.name in old_data:
                        del old_data[cmd.user.name]
                        with open('channels.json', mode = 'w') as c:
                            json.dump(old_data, c, indent = 2, ensure_ascii = False)
                        print(cmd.user.name, '- You have left the bot-free zone', id)
        await self.mass_unban(cmd.user.name, id)
    

    async def mass_unban(self, username, id):
        await self.chat.send_message('binarybouncer', f'Starting mass unbanning of bots on {username}\'s channel. This can take a while, please be patient and do not unmod BinaryBouncer until it is over...')
        url = 'https://api.twitchinsights.net/v1/bots/all'
        response = urlopen(url)
        botlist = json.loads(response.read())
        bots = botlist['bots']
        for name in range(len(bots)):
            print(f'Mass exodus on {username}\'s channel -- {bots[name][0]}')
            await self.unban_user(bots[name][0], id)
            await asyncio.sleep(0.4)
        await self.chat.send_message('binarybouncer', f'Finished unbanning all bots on {username}\'s channel.')


    async def super_ban(self, channel, id):
        finished = True   
        await self.chat.send_message('binarybouncer', f'Starting mass exodus of bots on {channel}\'s channel. This can take a while, please be patient...')
        with open('alivebots.json') as activebots:
            active_bots = json.load(activebots)
            for active in active_bots:
                print(f'Mass exodus on {channel}\'s channel -- {active}, {active_bots[active]}')
                try:
                    await self.ban_user(active, id)
                except ModeratorError:
                    await self.chat.send_message('binarybouncer', f'Please add BinaryBouncer as a moderator and try again.')
                    print(f'No mod privileges on channel {channel}, stopping the superban')
                    with open('channels.json') as c:
                        old_data = json.load(c)
                        if channel in old_data:
                            del old_data[channel]
                            with open('channels.json', mode = 'w') as c:
                                json.dump(old_data, c, indent = 2, ensure_ascii = False)
                    finished = False
                    break
                await asyncio.sleep(0.4)
        if finished:
            await self.chat.send_message('binarybouncer', f'Finished banning all bots on {channel}\'s channel.')
            with open('joinhistory.txt', 'r+') as joinHistory:
                joinHistory.write(f'{channel}\n')
                print('Added', channel, 'to the join history')

    # async def test(self, cmd:ChatCommand):
    #     await self.unban_user('test', '1234567890')


    # async def test2(self):
    #     user = 'testtesttest'
    #     with open('channels.json') as channels:
    #         c = json.load(channels)
    #         id = await self.get_user_id(user)
    #         await self.add_bot(user, id)
    #         for ch in c:
    #             await self.ban_user(user, c[ch])
    #             await asyncio.sleep(0.4)


    # async def ban_target(self):
    #     await self.super_ban('test', '1234567890')


    async def ban_routine(self):
        url = 'https://api.twitchinsights.net/v1/bots/all'
        response = urlopen(url)
        botlist = json.loads(response.read())
        bots = botlist['bots']
        formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')
        with open('banlist.txt', 'r+') as banlist:
            banned = banlist.read()
            for name in range(len(bots)):
                if bots[name][0] not in banned:
                    print('new bot found', bots[name][0])
                    id = await self.get_user_id(bots[name][0])
                    await self.add_bot(bots[name][0], id)
                    banlist.write(f'{bots[name][0]}\n')
                    with open('channels.json') as channels:
                        c = json.load(channels)
                        for ch in c:
                            await self.ban_user(bots[name][0], c[ch])
                            await asyncio.sleep(0.4)
        print('Super_Ban list Updated at', formatted_date)
        return


    async def run_periodically(self, coro, interval_seconds):
        while True:
            await asyncio.sleep(interval_seconds)
            await coro()


    async def loop_stuff(self):
        interval_seconds = 900
        coro = self.ban_routine
        await coro()
        asyncio.create_task(self.run_periodically(coro, interval_seconds))
        

    async def run(self):
        self.twitch = await Twitch(self.app_id, self.app_secret)
        auth = UserAuthenticator(self.twitch, self.user_scope)
        token, refresh_token = await auth.authenticate()

        await self.twitch.set_user_authentication(token, self.user_scope, refresh_token)

        self.chat = await Chat(self.twitch)
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
        self.chat.register_command('join', self.join)
        self.chat.register_command('leave', self.leave_channel)
        self.chat.register_command('ilovebots', self.super_leave)
        # self.chat.register_command('test', self.test)
        # self.chat.register_command('bantarget', self.ban_target)
        # self.chat.register_command('test2', self.test2)
        self.chat.start()

        try:
            input('press ENTER to stop\n')
        finally:
            self.chat.stop()
            await self.twitch.close()


if __name__ == '__main__':
    APP_ID = credentials.APP_ID
    APP_SECRET = credentials.APP_SECRET
    USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT, AuthScope.MODERATOR_MANAGE_BANNED_USERS]
    TARGET_CHANNEL = 'binarybouncer'

    bouncer = BinaryBouncer(APP_ID, APP_SECRET, USER_SCOPE, TARGET_CHANNEL)
    asyncio.run(bouncer.run())
