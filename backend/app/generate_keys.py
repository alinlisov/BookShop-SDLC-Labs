"""Print two random keys to copy into backend/.env. Run only on your PC."""
import base64
import secrets


def make_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


if __name__ == "__main__":
    print("DATA_ENCRYPTION_KEY=" + make_key())
    print("EMAIL_LOOKUP_KEY=" + make_key())
    print("Keep these keys private, and do not regenerate after registering users.")
