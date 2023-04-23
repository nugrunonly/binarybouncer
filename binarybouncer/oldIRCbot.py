import config
import datetime
import time
import socket
import json
from collections import namedtuple
from urllib.request import urlopen



TEMPLATE_COMMANDS = {
    '!test': 'Testing dildotics, {message.user}',
    '!test2': 'Dildotics tested, {message.user}',
}

Message = namedtuple(
    'Message',
    'prefix user channel irc_command irc_args text text_command text_args',
)

class Bot:
    def __init__(self):
        self.irc_server = 'irc.twitch.tv'
        self.irc_port = 6667
        self.oauth_token = config.OAUTH_TOKEN
        self.username = 'dildotics'
        self.channels = self._init_channels()
        self.custom_commands = {
            '!date': self.reply_with_date,
        }
        self.join_commands = {
            '!join': self.join_channel,
            '!leave': self.leave_channel,
            '!banactive': self.ban_active,
            '!superban': self.super_ban,
            '!update': self.update_super_ban,
            # '!autoupdate': self.auto_update
        }

    def _init_channels(self):
        with open('channels.txt', 'r') as joinedChannels:
            joined = joinedChannels.read()
            return joined.split('\n')

    def send_privmsg(self, channel, text):
        self.send_command(f'PRIVMSG #{channel} :{text}')

    def send_command(self, command):
        if 'PASS' not in command:
            print(f'<- {command}')
        self.irc.send((command + '\r\n').encode())

    def connect(self):
        self.irc = socket.socket()
        self.irc.connect((self.irc_server, self.irc_port))
        self.send_command(f'PASS {self.oauth_token}')
        self.send_command(f'NICK {self.username}')
        self.send_command(f'JOIN #{self.username}')
        print('Successfully logged in to dildotics')
        self.loop_for_messages()

    def get_user_from_prefix(self, prefix):
        domain = prefix.split('!')[0]
        if domain.endswith('.tmi.twitch.tv'):
            return domain.replace('.tmi.twitch.tv', '')
        if 'tmi.twitch.tv' not in domain:
            return domain
        return None

    def parse_message(self, received_msg):
        parts = received_msg.split(' ')

        prefix = None
        user = None
        channel = None
        text = None
        text_command = None
        text_args = None
        irc_command = None
        irc_args = None

        if parts[0].startswith(':'):
            prefix = parts[0][1:]
            user = self.get_user_from_prefix(prefix)
            parts = parts[1:]

        text_start = next(
            (idx for idx, part in enumerate(parts) if part.startswith(':')),
            None
        )
        if text_start is not None:
            text_parts = parts[text_start:]
            text_parts[0] = text_parts[0][1:]
            text = ' '.join(text_parts)
            text_command = text_parts[0]
            text_args = text_parts[1:]
            parts = parts[:text_start]
        
        irc_command = parts[0]
        irc_args = parts[1:]

        hash_start = next(
            (idx for idx, part in enumerate(irc_args) if part.startswith('#')),
            None
        )
        if hash_start is not None:
            channel = irc_args[hash_start][1:]

        message = Message(
            prefix = prefix,
            user = user,
            channel = channel,
            text = text,
            text_command = text_command,
            text_args = text_args,
            irc_command = irc_command,
            irc_args = irc_args,
        )

        return message

    def handle_template_command(self, message, text_command, template):
        text = template.format(**{'message': message})
        self.send_privmsg(message.channel, text)

    def reply_with_date(self, message):
        formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')
        text = f'Here you go {message.user}, the date is: {formatted_date}.'
        self.send_privmsg(message.channel, text)
    
    def ban_active(self, message):
        with open('channels.txt', 'r+') as joinedChannels:
            joined = joinedChannels.read()
            if message.user not in joined:
                return
            else:        
                self.send_privmsg('dildotics', f'Starting an exodus of active bots on {message.user}\'s channel. This can take a while, please be patient...')
                with open ('activebots.txt', 'r') as activebots:
                    banned = activebots.readlines()
                    for name in banned:
                        self.send_privmsg(message.user, f'/ban {name}')
                        time.sleep(0.5)
                self.send_privmsg('dildotics', f'Finished banning bots on {message.user}\'s channel.')
    
    def super_ban(self, message):
        with open('channels.txt', 'r+') as joinedChannels:
            joined = joinedChannels.read()
            if message.user not in joined:
                return
            else:
                self.send_privmsg('dildotics', f'Starting mass exodus of bots on {message.user}\'s channel. This can take a while, please be patient...')
                url = 'https://api.twitchinsights.net/v1/bots/all'
                response = urlopen(url)
                botlist = json.loads(response.read())
                bots = botlist['bots']
                for name in range(len(bots)):
                    print(f'Mass exodus on {message.user}\'s channel -- {bots[name][0]}')
                    self.send_privmsg(message.user, f'/ban {bots[name][0]}')
                    time.sleep(0.4)
                self.send_privmsg('dildotics', f'Finished banning all bots on {message.user}\'s channel.')

    def update_super_ban(self, message):
        if message.user != 'nugrunonly':
            return
        else:
            url = 'https://api.twitchinsights.net/v1/bots/all'
            response = urlopen(url)
            botlist = json.loads(response.read())
            bots = botlist['bots']
            formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')
            print('Updating Super_Ban list')
            with open('banlist.txt', 'r+') as banlist:
                banned = banlist.read()
                for name in range(len(bots)):
                    if bots[name][0] not in banned:
                        banlist.write(f'{bots[name][0]}\n')
                        for channel in self.channels:
                            self.send_privmsg(channel, f'/ban {bots[name][0]}')
                            time.sleep(0.4)
            formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')                
            print(f'Banlist Updated at -- {formatted_date}')
            self.send_privmsg(message.channel, 'Updated super list')

    def join_channel(self, message):
        joinedChannels = open('channels.txt', 'r+')
        joined = joinedChannels.read()
        joinHistory = open('joinhistory.txt', 'r+')
        history = joinHistory.read()
        if message.user in joined:
            return
        else:
            if message.user in history:                            
                print('Welcome back to the bot-free zone -- ', {message.user})
                text = f'Welcome back to the bot-free zone -- {message.user}.'
                self.send_privmsg(message.channel, text)
                joinedChannels.write(f'{message.user}\n')
            else:
                print('Adding a new channel -- ', {message.user})
                text = f'Added {message.user} to the bot-free zone.'
                self.send_privmsg(message.channel, text)
                joinedChannels.write(f'{message.user}\n')
                joinHistory.write(f'{message.user}\n')
                joinedChannels.close()
                joinHistory.close()
                self.super_ban(message)

    def leave_channel(self, message):
        with open('channels.txt', 'r+') as joinedChannels:
            joined = joinedChannels.read()
            if message.user not in joined:
                print('not in list yet')
                return
            else:
                joinedChannels.seek(0)
                joinedChannels.truncate()
                print('Removing a channel -- ', {message.user})
                text = f'You have left the bot-free zone, {message.user}'
                self.send_privmsg(message.channel, text)
                lines = joined.split('\n')
                for line in lines:
                    if line != message.user and line != '':
                        joinedChannels.write(f'{line}\n')

    def handle_message(self, received_msg):
        if len(received_msg) == 0:
            return
        message = self.parse_message(received_msg)
        print(f'-> {message}')
        if message.irc_command == 'PING':
            url = 'https://api.twitchinsights.net/v1/bots/online'
            response = urlopen(url)
            botlist = json.loads(response.read())
            bots = botlist['bots']
            formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')
            self.send_command('PONG :tmi.twitch.tv')
            formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')
            print('Checking for new active bots -- found', botlist['_total'], f'online at {formatted_date}')
            with open('activebots.txt', 'r+') as activebots:
                banned = activebots.read()            
                for name in range(len(bots)):
                    if bots[name][0] not in banned:
                        print(f'New bot found -- {bots[name][0]}')
                        activebots.write(f'{bots[name][0]}\n')
                        for channel in self.channels:
                            self.send_privmsg(channel, f'/ban {bots[name][0]}')
                            time.sleep(0.5)
            url = 'https://api.twitchinsights.net/v1/bots/all'
            response = urlopen(url)
            botlist = json.loads(response.read())
            bots = botlist['bots']
            formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')
            print('Updating Super_Ban list')
            with open('banlist.txt', 'r+') as banlist:
                banned = banlist.read()
                for name in range(len(bots)):
                    if bots[name][0] not in banned:
                        banlist.write(f'{bots[name][0]}\n')
                        for channel in self.channels:
                            self.send_privmsg(channel, f'/ban {bots[name][0]}')
                            time.sleep(0.5)
            formatted_date = datetime.datetime.now().strftime('%H:%M:%S %m/%d/%Y')                
            print(f'Banlist Updated at -- {formatted_date}')
                                         
        if message.irc_command == 'PRIVMSG':
            if message.text_command in TEMPLATE_COMMANDS:
                self.handle_template_command(
                    message,
                    message.text_command,
                    TEMPLATE_COMMANDS[message.text_command],
                )

            if message.text_command in self.custom_commands:
                self.custom_commands[message.text_command](message)

            if message.text_command in self.join_commands:
                self.join_commands[message.text_command](message)
        
    def loop_for_messages(self):
        while True:
            received_msgs = self.irc.recv(2048).decode()
            for received_msg in received_msgs.split('\r\n'):
                self.handle_message(received_msg)
                # time.sleep(0.1)

def main():
    bot = Bot()
    bot.connect()

if __name__ == '__main__':
    main()
