from typing import Literal
from time import sleep
from threading import Event, Thread
from lib.db.main import FolderData, FileData
from utils.funcs import sanitize_folder_name, size_to_human, mime_type_to_emoji
from lib.io  import TelegramIO
from lib.bot import TelegramBot
from telebot import types as tt
import logging



class TextHandler:
	def __init__(self) -> None:
		self.event = Event()
		self.result: str|None = None


def main(tg: TelegramBot, storage: TelegramIO):
	db = storage.db
	text_handlers: dict[int, TextHandler] = {}
	def wait_for_text(user_id: int, timeout: int = None):
		text_handlers[user_id] = t = TextHandler()
		t.event.wait(timeout)
		r = t.result
		del text_handlers[user_id]
		return r


	def preview_file(user_id: int, file_id: int):
		file = db.file.get_file(file_id)
		msg = tg.bot.send_document(chat_id=user_id, document=file.actual_file_id, caption="⏳ Please wait...")
		f = msg.document
		kb = tt.InlineKeyboardMarkup([
			[tt.InlineKeyboardButton("🆗", callback_data='deleteme')]
		])
		tg.bot.edit_message_caption(
f'''{mime_type_to_emoji(file.mime_type)} File <b>{file.name}</b>

<i>File size: <b>{size_to_human(f.file_size)}</b>
MIME type: <b>{file.mime_type}</b></i>
''', user_id, msg.message_id, reply_markup=kb)

	def explore_dir(user_id: int, folder_id: int | None, mode: Literal['browse', 'select'] = 'browse'):
		folder = db.folder.get_folder(folder_id)
		logging.info(f'User {user_id} accessed folder {folder}')
		if (folder is None) or (folder.user_id != user_id):
			tg.text(user_id, '❌ This folder does not exist or you do not have necessary permissions.')
			return
		current_path = []
		c_folder = folder
		while c_folder:
			current_path.append(c_folder.name)
			p = c_folder.parent_folder_id
			c_folder = db.folder.get_folder(p) if p else None
		current_path = '/'.join(current_path[::-1])
		children = db.folder.get_children(folder_id)
		buttons = [[
			tt.InlineKeyboardButton('♻️ Refresh', callback_data=f'deleteme;explorer:{folder_id}:{mode}')
		], [
			tt.InlineKeyboardButton('🗑️ Delete', callback_data=f'deleteme;explorer:{folder_id}:select'),
			tt.InlineKeyboardButton('📦 Move',   callback_data=f'deleteme;explorer:{folder_id}:select'),
			tt.InlineKeyboardButton('✏️ Rename', callback_data=f'deleteme;explorer:{folder_id}:select')
		]]
		if (mode == 'browse') and (folder.parent_folder_id is not None):
			parent = db.folder.get_folder(folder.parent_folder_id)
			buttons.append(tt.InlineKeyboardButton(f"📁 .. ({parent.name})", callback_data=f"deleteme;explorer:{parent.folder_id}:{mode}"))
		if mode != 'browse':
			buttons.append(tt.InlineKeyboardButton(f"✖️ Cancel Select", callback_data=f"deleteme;explorer:{folder_id}"))
		t = f'📂 Current directory: <b>{current_path}</b>'
		if mode == 'select':
			t = f'\n<b>Select directory or file:</b>'
		if children:
			buttons.append(tt.InlineKeyboardButton('---------', callback_data='none'))
			if mode == 'browse':
				folder_buttons = [tt.InlineKeyboardButton(f"📁 {x.name}", callback_data=f"deleteme;explorer:{x.folder_id}") for x in children if isinstance(x, FolderData)]
				file_buttons = [tt.InlineKeyboardButton(f"{mime_type_to_emoji(x.mime_type)} {x.name}", callback_data=f"file:{x.file_id}") for x in children if isinstance(x, FileData)]
			elif mode == 'select':
				folder_buttons = [tt.InlineKeyboardButton(f"[CLICK TO SELECT] 📁 {x.name}", callback_data=f"select:{x.folder_id}") for x in children if isinstance(x, FolderData)]
				file_buttons = [tt.InlineKeyboardButton(f"[CLICK TO SELECT] {mime_type_to_emoji(x.mime_type)} {x.name}", callback_data=f"select:{x.file_id}") for x in children if isinstance(x, FileData)]
			all_buttons = [x if isinstance(x, list) else [x, ] for x in (buttons + folder_buttons + file_buttons)]
			tg.list(user_id, t, None, all_buttons)
		else:
			tg.text(user_id, t + '\n\n<i>(empty)</i>', keyboard=tt.InlineKeyboardMarkup([x if isinstance(x, list) else [x, ] for x in buttons]))
		db.user.set_last_opened_folder(user_id, folder_id)


	def confirm_delete_folder(confirmed: bool, user_id: int, folder_id: int ):
		kb = tt.InlineKeyboardMarkup([[
			tt.InlineKeyboardButton(f"Yes, delete", callback_data=f'deleteme;delete_folder:{folder_id}:1'),
			tt.InlineKeyboardButton(f"No, cancel", callback_data=f'deleteme')
		]])
		folder = db.folder.get_folder(folder_id)
		if not folder:
			return tg.text(user_id, "❌ This folder has already been deleted")
		if not confirmed:
			return tg.text(user_id, f"Are you sure you want to delete folder \"{folder.name}\"?", keyboard=kb)
		try:
			db.folder.delete_folder(folder.folder_id)
			tg.text(user_id, f"✅ Folder \"{folder.name}\" deleted")
		except Exception as e:
			logging.error(f"Error deleting folder {folder_id} by user {user_id}", e)
			tg.text(user_id, "❌ Error deleting folder")
			
	def confirm_delete_file(confirmed: bool, user_id: int, file_id: int ):
		kb = tt.InlineKeyboardMarkup([[
			tt.InlineKeyboardButton(f"Yes, delete", callback_data=f'deleteme;delete_file:{file_id}:1'),
			tt.InlineKeyboardButton(f"No, cancel", callback_data=f'deleteme')
		]])
		file = db.file.get_file(file_id)
		if not file:
			return tg.text(user_id, "❌ This file has already been deleted")
		if not confirmed:
			return tg.text(user_id, f"Are you sure you want to delete file \"{file.name}\"?", keyboard=kb)
		try:
			db.file.delete_file(file.file_id)
			tg.text(user_id, f"✅ File \"{file.name}\" deleted")
		except Exception as e:
			logging.error(f"Error deleting file {file_id} by user {user_id}")
			tg.text(user_id, "❌ Error deleting file")

	def rename_folder(user_id: int, folder_id: int):
		folder = db.folder.get_folder(folder_id)
		tg.text(user_id, f'Send the new name for folder {folder.name}')
		new_folder_name = wait_for_text(user_id)
		try:
			db.folder.rename_folder(folder_id, new_folder_name)
			logging.info(f"User {user_id} renamed folder {folder_id} to \"{new_folder_name}\"")
			tg.text(user_id, f'✅ Folder renamed to \"{new_folder_name}\"')
		except Exception as e:
			logging.error(f"Error renaming folder {folder_id} by user {user_id} to \"{new_folder_name}\"")
			tg.text(user_id, f'❌ Error renaming folder')




	@tg.bot.message_handler(commands=['help'])
	def help(msg: tt.Message):
		tg.bot.reply_to(msg, '''
Use /start to go to root directory

While in a directory:
  - Send a file to have it uploaded
  - Send text message to have another folder created with that name''')

	@tg.bot.message_handler(commands=['start'])
	def start(msg: tt.Message):
		u = msg.chat.id
		user = db.user.get_user(u)
		if user is None:
			logging.info(f'New user {u}')
			user = db.user.get_user(db.user.create_user(u))
		root_dir = db.folder.get_folder(user.root_folder_id)
		if root_dir is None:
			logging.info(f'No root directory for user {u}, creating one')
			root_dir = db.folder.get_folder(db.folder.create_folder(u, 'Home', None))
			db.user.set_root_folder(u, root_dir.folder_id)
		explore_dir(u, root_dir.folder_id)
	
	@tg.bot.message_handler(content_types=['text'])
	def handle_text(msg: tt.Message):
		u = msg.chat.id
		t = msg.text # or msg.caption
		if (h := text_handlers.get(u, None)) is not None: # Answer TextHandler
			h.result = t
			h.event.set()
		else: # Create new folder
			name = sanitize_folder_name(t)
			if name:
				user = db.user.get_user(u)
				cur_folder_id = user.last_opened_folder_id if user else None
				if cur_folder_id is None: return
				db.folder.create_folder(u, name, cur_folder_id)
				tg.text(u, f"✅ Folder '{name}' created")
			else:
				tg.text(u, "❌ Invalid folder name, try again")

	@tg.bot.message_handler(content_types=['document'])
	def upload_file(msg: tt.Message):
		f = msg.document
		# TODO: Handle multiple files uploaded, to avoid rate limit (storage.upload gets rate limited too)
		# Maybe do a media group upload to storage, or wait before uploading all files user sent in a period of time
		u = msg.chat.id
		user = db.user.get_user(u)
		if (folder_id := user.last_opened_folder_id) is None: return
		folder = db.folder.get_folder(folder_id)
		logging.info(f'File from {u} to folder {folder_id}: {f.file_name} ({f.mime_type}) of size {size_to_human(f.file_size)}')
		try:
			file: FileData = storage.upload(f, folder)
			tg.text(u, f"<b>✅ File \"{file.name}\" uploaded to folder \"{folder.name}\"</b>")
			# try: tg.delete(msg)
			# except Exception as e: print(e)
		except Exception as e:
			tg.text(u, f"❌ <b>File uploading failed:</b> {e}")

	@tg.bot.callback_query_handler(func = lambda x: True)
	def buttons_handle(query: tt.CallbackQuery):
		commands = [x.split(':') for x in query.data.split(';')]
		user_id = query.from_user.id
		logging.info(f"Callback from {user_id}: {commands}")
		def handle_command(command):
			cmd = command[0]
			args = command[1:]
			try:
				if cmd == 'none':
					return
				elif cmd == 'deleteme':
					tg.delete(query.message)
				elif cmd == 'maint':
					tg.text(user_id, "🚧 Please try again later, this option is now under maintenance 🚧")
				elif cmd == 'explorer':
					explore_dir(user_id, int(args[0]), args[1] if len(args) > 1 else 'browse')
				elif cmd == 'select':
					pass
				elif cmd == 'file':
					preview_file(user_id, int(args[0]))
				elif cmd == 'delete_folder':
					confirm_delete_folder(int(args[1]) if (len(args) > 1) else 0, user_id, folder_id=int(args[0]))
				elif cmd == 'delete_file':
					confirm_delete_file(int(args[1]) if (len(args) > 1) else 0, user_id, file_id=args[0])
				elif cmd == 'rename_folder':
					rename_folder(user_id, int(args[0]))
			except Exception as e:
				logging.error(f"Error in callback command \"{cmd}\" with args {args}: {e}")
		for command in commands:
			Thread(target=handle_command, args=(command, )).start()

	tg.polling()