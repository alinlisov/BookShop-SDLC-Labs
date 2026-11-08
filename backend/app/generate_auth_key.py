"""Run once to make an additional JWT secret; preserve your earlier keys."""
import base64, secrets
if __name__ == "__main__":
    key=base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    print("AUTH_SIGNING_KEY="+key)
    print("Додайте до backend/.env. Не публікуйте ключ і не змінюйте старі ключі.")
