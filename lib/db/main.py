import sqlite3
from typing import List, Union, Optional



class UserData:
	def __init__(self, user_id: int, last_opened_folder_id: Optional[int] = None, root_folder_id: Optional[int] = None):
		self.user_id = user_id
		self.last_opened_folder_id = last_opened_folder_id
		self.root_folder_id = root_folder_id

	def __repr__(self):
		return f"UserData(user_id={self.user_id}, last_opened_folder_id={self.last_opened_folder_id}, root_folder_id={self.root_folder_id})"

class FileData:
    def __init__(self, file_id: str, actual_file_id: str, name: str, mime_type: str, user_id: int, message_id: int, parent_folder_id: int):
        self.file_id = file_id
        self.actual_file_id = actual_file_id
        self.name = name
        self.mime_type = mime_type
        self.user_id = user_id
        self.message_id = message_id
        self.parent_folder_id = parent_folder_id

    def __repr__(self):
        return f"FileData(file_id={self.file_id}, actual_file_id='{self.actual_file_id}', " \
               f"name='{self.name}', mime_type='{self.mime_type}', " \
               f"user_id={self.user_id}, message_id={self.message_id}, " \
               f"parent_folder_id={self.parent_folder_id})"


class FolderData:
	def __init__(self, folder_id: int, user_id: int, name: str, parent_folder_id: Optional[int]):
		self.folder_id = folder_id
		self.user_id = user_id
		self.name = name
		self.parent_folder_id = parent_folder_id

	def __repr__(self):
		return f"FolderData(folder_id={self.folder_id}, user_id={self.user_id}, name='{self.name}', " \
			f"parent_folder_id={self.parent_folder_id})"



class UserDataHandler:
	def __init__(self, db: "Database"):
		self.con: sqlite3.Connection= db.con

	def create_user(self, user_id: int) -> int:
		cursor = self.con.cursor()
		cursor.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
		cursor.close()
		return user_id

	def get_user(self, user_id: int) -> Optional[UserData]:
		cursor = self.con.cursor()
		cursor.execute("SELECT last_opened_folder_id, root_folder_id FROM users WHERE id = ?", (user_id,))
		user_data = cursor.fetchone()
		cursor.close()
		if user_data:
			return UserData(user_id, *user_data)
		return None

	def set_root_folder(self, user_id: int, root_folder_id: int) -> None:
		cursor = self.con.cursor()
		cursor.execute("UPDATE users SET root_folder_id = ? WHERE id = ?", (root_folder_id, user_id))
		cursor.close()

	def set_last_opened_folder(self, user_id: int, last_opened_folder_id: int) -> None:
		cursor = self.con.cursor()
		cursor.execute("UPDATE users SET last_opened_folder_id = ? WHERE id = ?", (last_opened_folder_id, user_id))
		cursor.close()


class FolderDataHandler:
	def __init__(self, db: "Database"):
		self.con: sqlite3.Connection= db.con
		self.db = db

	def create_folder(self, user_id: int, name: str, parent_folder_id: Optional[int] = None) -> int:
		cursor = self.con.cursor()
		cursor.execute("INSERT INTO folders (user_id, name, parent_folder_id) VALUES (?, ?, ?)",
					(user_id, name, parent_folder_id))
		folder_id = cursor.lastrowid
		cursor.close()
		return folder_id

	def get_folder(self, folder_id: int) -> Optional[FolderData]:
		cursor = self.con.cursor()
		cursor.execute("SELECT user_id, name, parent_folder_id FROM folders WHERE id = ?", (folder_id,))
		folder_data = cursor.fetchone()
		cursor.close()
		if folder_data:
			return FolderData(folder_id, *folder_data)
		return None

	def get_children(self, folder_id: int) -> List[Union[FolderData, FileData]]:
		cursor = self.con.cursor()
		cursor.execute("SELECT id, user_id, name FROM folders WHERE parent_folder_id = ?", (folder_id,))
		folders_data = cursor.fetchall()
		folders = [FolderData(*x, folder_id) for x in folders_data]
		cursor.execute("SELECT id, actual_file_id, name, mime_type, user_id, message_id FROM files WHERE parent_folder_id = ?", (folder_id,))
		files_data = cursor.fetchall()
		cursor.close()
		files = [FileData(*x, folder_id) for x in files_data]
		return folders + files

	def find_folder(self, name: str, user_id: int) -> Optional[FolderData]:
		cursor = self.con.cursor()
		cursor.execute("SELECT id, parent_folder_id FROM folders WHERE name = ? AND user_id = ?", (name, user_id))
		folder_data = cursor.fetchone()
		cursor.close()
		if folder_data:
			folder_id, parent_folder_id = folder_data
			return FolderData(folder_id, user_id, name, parent_folder_id)
		return None

	def delete_folder(self, folder_id: int) -> None:
		cursor = self.con.cursor()
		children = self.get_children(folder_id)
		child: "FileData | FolderData"
		for child in children:
			self.delete_folder(child.folder_id) if isinstance(child, FolderData) else self.db.file.delete_file(child.file_id)
		cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
		cursor.close()

	def rename_folder(self, folder_id: int, new_name: str) -> None:
		cursor = self.con.cursor()
		cursor.execute("UPDATE folders SET name = ? WHERE id = ?", (new_name, folder_id))
		cursor.close()


class FileDataHandler:
	def __init__(self, db: "Database"):
		self.con: sqlite3.Connection= db.con

	def create_file(self, actual_file_id: str, name: str, mime_type: str, user_id: int, message_id: int, parent_folder_id: int) -> str:
		cursor = self.con.cursor()
		cursor.execute("INSERT INTO files (actual_file_id, name, mime_type, user_id, message_id, parent_folder_id) VALUES (?, ?, ?, ?, ?, ?)",
					(actual_file_id, name, mime_type, user_id, message_id, parent_folder_id))
		file_id = cursor.lastrowid
		cursor.close()
		return file_id

	def get_file(self, file_id: str) -> Optional[FileData]:
		cursor = self.con.cursor()
		cursor.execute("SELECT actual_file_id, name, mime_type, user_id, message_id, parent_folder_id FROM files WHERE id = ?", (file_id,))
		file_data = cursor.fetchone()
		cursor.close()
		if file_data:
			return FileData(file_id, *file_data)
		return None

	def delete_file(self, file_id: str) -> None:
		cursor = self.con.cursor()
		cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
		cursor.close()
		#TODO remove actual file from storage (okay nvm dont do it, telegram storage is free so dont mind garbage)



class Database:
	def __init__(self, database_name: str = "data.db"):
		self.con = sqlite3.connect(database_name, isolation_level=None, check_same_thread=False)
		cursor = self.con.cursor()
		cursor.execute("""
		CREATE TABLE IF NOT EXISTS folders (
			id INTEGER PRIMARY KEY,
			user_id INTEGER,
			name TEXT,
			parent_folder_id INTEGER,
				FOREIGN KEY (parent_folder_id) REFERENCES folders(id)
		)
		""")
		cursor.execute("""
		CREATE TABLE IF NOT EXISTS files (
			id INTEGER PRIMARY KEY,
			actual_file_id TEXT,
			name TEXT,
			mime_type TEXT,
			user_id INTEGER,
			message_id INTEGER,
			parent_folder_id INTEGER,
				FOREIGN KEY (parent_folder_id) REFERENCES folders(id)
		)
		""")
		cursor.execute("""
		CREATE TABLE IF NOT EXISTS users (
			id INTEGER PRIMARY KEY,
			last_opened_folder_id INTEGER,
			root_folder_id INTEGER,
				FOREIGN KEY (last_opened_folder_id) REFERENCES folders(id),
				FOREIGN KEY (root_folder_id) REFERENCES folders(id)
		)
		""")
		cursor.close()

		self.user = UserDataHandler(self)
		self.folder = FolderDataHandler(self)
		self.file = FileDataHandler(self)