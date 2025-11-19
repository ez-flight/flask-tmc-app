import hashlib
password = "11337700"
salt = "(vZA){5"
hash = hashlib.sha1((password + salt).encode()).hexdigest()
print(hash)
