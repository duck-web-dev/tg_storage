from telebot import TeleBot, types as tt
from typing import Callable, TypeVar
from lib.base import Service
from utils.funcs import chunks 


T = TypeVar('T')

class TelegramBot(Service):
	def __init__(self, api_key: str, parse_mode = 'HTML'):
		self.bot = TeleBot(api_key, parse_mode=parse_mode)

	def polling(self):
		self.bot.infinity_polling()

	def delete(self, message: tt.Message):
		self.bot.delete_message(message.chat.id, message.id)

	def text(self, user_id: int, text: str, parse_mode=None, keyboard=None):
		self.bot.send_message(user_id, text, parse_mode, reply_markup=keyboard)
	
	def list(self, user_id: int, text: str, parse_mode,
		  entries: list[tt.InlineKeyboardButton],
		  cur_page: int = 0, limit: int = 50):
		c = chunks(entries, limit)
		if cur_page < 0 or cur_page >= len(c):
			raise ValueError('Page number out of range')
		keyboard = tt.InlineKeyboardMarkup(c[cur_page])
		# keyboard.keyboard.append([
		# 	tt.InlineKeyboardButton('◀️', callback_data=('none' if cur_page==0      else 'none')),
		# 	tt.InlineKeyboardButton(f'{cur_page+1}/{len(c)}', callback_data='none'),
		# 	tt.InlineKeyboardButton('▶️', callback_data=('none' if cur_page>=len(c) else 'none')),
		# ])
		self.text(user_id, text, parse_mode, keyboard)