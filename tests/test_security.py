from app.security import hash_password, verify_password
from tests.helpers import PASSWORD, make_user


def test_password_is_hashed_not_plain(db):
	u = make_user(db)
	assert u.password_hash != PASSWORD and u.password_hash.startswith("pbkdf2_sha256$")
	assert verify_password(PASSWORD, u.password_hash) and not verify_password("wrong", u.password_hash)
	assert hash_password(PASSWORD) != hash_password(PASSWORD)  # random salt

