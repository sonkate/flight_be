def userEntity(item) -> dict:
	return {
		'id': str(item["_id"]),
		'email': item["email"],
		'password': item["password"],
	}
 
def usersEntity(entity) -> list:
  return [userEntity(item) for item in entity]

def serializeDict(item) -> dict:
  return {**{'id': str(item[i]) for i in item if i == '_id'}, **{i: item[i] for i in item if i != '_id'}}

def serializeList(items) -> list:
  return [serializeDict(item) for item in items]