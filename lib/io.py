import logging
from lib.base import Service
from lib.db import Database, FileData, FolderData
from lib.bot import TelegramBot
from telebot import types as tt


class TelegramIO(Service):
	def __init__(self, storage: tt.Chat, tg: TelegramBot, db: Database) -> None:
		self.chat = storage
		self.tg   = tg
		self.db   = db

	def upload(self, f: tt.Document, folder: FolderData, caption: str = None) -> FileData:
		try:
			msg = self.tg.bot.send_document(self.chat.id, f.file_id, caption=caption)
			file_id = self.db.file.create_file(
							actual_file_id=f.file_id, name=f.file_name, mime_type=f.mime_type,
							user_id=self.chat.id, message_id=msg.message_id,
							parent_folder_id=folder.folder_id
			)
			return self.db.file.get_file(file_id)
		except Exception as e:
			logging.error("File upload failed:", e)
			raise ValueError("File upload failed")

	def get(self, file_id: int) -> tt.File:
		try:
			return self.tg.bot.get_file(file_id)
		except Exception as e:
			logging.error("Error retrieving file:", e)
			raise ValueError("Error retrieving file")

	def delete(self, file_id: int):
		try:
			message_id = self.db.get_file_message_id(file_id)
			if not message_id:
				raise ValueError(f"Invalid file: {file_id}")
			self.tg.bot.delete_message(self.chat.id, message_id)
			self.db.delete_file(file_id)
		except Exception as e:
			logging.error("File deletion failed:", e)
			raise ValueError("File deletion failed")