import json


def get_password_user(user):
	with open("credentials.json", "r") as file:
		data = json.load(file)
		print(data)
		return data.get(user)

print(get_password_user('will@wonderbrands.co'))