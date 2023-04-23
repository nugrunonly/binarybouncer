from login import token
from twitchio.ext import commands, routines
from urllib.request import urlopen
import json


class Bot(commands.Bot):
    def __init__(self):
        password = token.get('token')
        super().__init__(token = password, prefix='!', initial_channels=['nugrunonly'])


    async def event_ready(self):
        print(f'Logged in as {self.nick}')
        
        
    @commands.command()
    async def hello(self, ctx: commands.Context):
        await ctx.send(f'Hello {ctx.author.name}!')

    @routines.routine(minutes=10)
    async def ban_loop():
        url = 'https://api.twitchinsights.net/v1/bots/online'
        response = urlopen(url)
        botlist = json.loads(response.read())
        bots = botlist['bots']
        with open( 'banlist.txt', "r+") as banlist:
            banned = banlist.read()
            print('checking for new bots, found', botlist['_total'], 'online')
            for name in range(len(bots)):
                if bots[name][0] not in banned:
                    print('new bot found --', bots[name][0])
                    banlist.write(f'{bots[name][0]}\n')

    ban_loop.start()


if __name__  == '__main__':
    bot = Bot()
    bot.run()

