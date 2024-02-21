from typing import TypeVar
from random import choice
import os


def size_to_human(num, suffix="B"):
	for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
		if abs(num) < 1024.0:
			return f"{num:3.1f}{unit}{suffix}"
		num /= 1024.0
	return f"{num:.1f}Yi{suffix}"

def mime_type_to_emoji(type: str):
	a = type.split("/")[0]
	# application, audio, example, font, image, message, model, multipart, text, and video
	if (a == 'application') and ('zip' in type or 'rar' in type):
		ext = '🗃️'
	else:
		ext = {
			'audio': '🎵', 'video': '📽️', 'font': '🔤', 'image': '🖼️', 'text': '📃', 'multipart': '🗃️'
		}.get(a, None)
	if ext is None:
		ext = '📄'
	return ext

def random_str(length: int) -> str:
	a = 'abcdefghijklmnopqrstuvwxyz1234567890'
	return ''.join(choice(a) for _ in range(length))

T = TypeVar('T')
def chunks(l: list[T], limit: int) -> list[list[T]]:
	return [l[i:i + limit] for i in range(0, len(l), limit)]

def sanitize_folder_name(folder_name):
	invalid_chars = '\\/:*?"<>|'
	invalid_strs = ['..']
	folder_name = os.path.normpath(folder_name)
	sanitized_name = ''.join(char if char not in invalid_chars else '_' for char in folder_name)
	if any(x in sanitized_name for x in invalid_strs):
		return None
	return sanitized_name