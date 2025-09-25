import hashlib
# Для ez/11337700
password = "11337700"
salt = "=:h2(U*"
print(hashlib.sha1((password + salt).encode()).hexdigest())
# Результат: 6c26947c6dfc3391dc9aa9e62fa46ece76a52edb ❌
