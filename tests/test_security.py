import re

from fastapi.testclient import TestClient

from app.main import app
from app.security import hash_password, verify_password
from tests.helpers import PASSWORD, make_user


def login(client, email, password=PASSWORD):
	page = client.get("/login")
	token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
	return client.post("/login", data={"email": email, "password": password, "csrf_token": token},
					   follow_redirects=False)


def test_password_is_hashed_not_plain(db):
	u = make_user(db)
	assert u.password_hash != PASSWORD and u.password_hash.startswith("pbkdf2_sha256$")
	assert verify_password(PASSWORD, u.password_hash) and not verify_password("wrong", u.password_hash)
	assert hash_password(PASSWORD) != hash_password(PASSWORD)  # random salt
