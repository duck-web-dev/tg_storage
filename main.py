from utils.funcs import size_to_human
from lib.env import cfg
from lib.db  import Database
from lib.io  import TelegramIO
from lib.bot import TelegramBot
from lib.ui  import main

import logging
logging.basicConfig(level=logging.INFO)


tg = TelegramBot(cfg.get('TG_BOT_KEY'))

db = Database()

storage_chat = tg.bot.get_chat(int(cfg.get('STORAGE_CHAT')))
storage = TelegramIO(storage_chat, tg, db)


main(tg, storage)