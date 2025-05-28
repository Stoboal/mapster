import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl

from django.http import JsonResponse
from django.utils.timezone import now
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from app.settings import env
from users.models import TelegramUser

logger = logging.getLogger(__name__)

BOT_TOKEN = env("TELEGRAM_TOKEN")

def check_telegram_auth(raw_init_data: str) -> bool:
    """
    Verifies the authentication of Telegram web app data by comparing the computed hash of the
    data with the hash received from Telegram. This ensures the data integrity and authenticity.

    The function processes the raw initialization data by parsing key-value pairs, computes a
    hash using the HMAC algorithm with a secret key derived from the bot token, and compares it
    against an expected hash. If the computed hash matches the received hash, the data is
    considered authentic.
    """
    params = dict(parse_qsl(raw_init_data, keep_blank_values=True))
    received_hash = params.pop('hash', None)

    if not received_hash:
        return False

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    secret_key = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, received_hash)

@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def telegram_auth(request):
    """
    Handles user authentication via Telegram's authorized login data. Validates the
    "initData" parameter from the request to ensure it contains an authenticated
    signature and user details from Telegram. Processes the user's data to create
    or update a TelegramUser instance in the database and generates a token for
    the authenticated session. Returns a JSON response including the generated
    token and user details.

    Raises appropriate HTTP status codes (400, 403, or 500) for errors such as:
    - Missing or invalid "initData".
    - JSON decoding errors.
    - Unexpected server errors.

    This method supports authentication and session token creation for a Telegram
    user based on encrypted Telegram data.
    """
    raw_init_data = request.data.get("initData")
    if not raw_init_data:
        return JsonResponse({"error": "initData not provided"}, status=400)
    if not check_telegram_auth(raw_init_data):
        return JsonResponse({"error": "Invalid Telegram signature"}, status=403)

    try:
        parsed_data = dict(parse_qsl(raw_init_data))
        user_data_raw = parsed_data.get("user", "{}")

        if not user_data_raw:
             logger.error("User data is missing in initData.")
             return JsonResponse({"error": "User data missing in initData"}, status=400)

        user_data = json.loads(user_data_raw)
        telegram_id = user_data.get("id")

        if not telegram_id:
             logger.error("User ID is missing in user data from initData.")
             return JsonResponse({"error": "User ID missing in user data"}, status=400)

        chat_id = parsed_data.get("chatId")
        username = user_data.get("username", f"tg_{telegram_id}")

        user, created = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                "username": username,
                "chat_id": chat_id,
            }
        )
        if created:
            logger.info(f'Object was created: TelegramUser, telegram_id={telegram_id}, chat_id={chat_id} username={username}')

        if not created and user.username != username and not user.username.startswith("tg_"):
            user.username = username
            user.save(update_fields=["username"])
            logger.info(f'Object was updated: TelegramUser, telegram_id={telegram_id}, username={username}')

        if not user.chat_id:
            user.chat_id = chat_id
            user.save(update_fields=["chat_id"])
            logger.info(f'Object was updated: TelegramUser, telegram_id={telegram_id}, chat_id={chat_id}')

        token, token_created = Token.objects.get_or_create(user=user)
        if token_created:
            logger.info(f'New token was created for user: telegram_id={telegram_id}, username={username}')

        user.last_login = now()
        user.save(update_fields=["last_login"])
        logger.info(f'User was successfully logged in: telegram_id={telegram_id}, username={username}')

        return JsonResponse({
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username
            }
        })

    except json.JSONDecodeError:
        logger.error(f"Failed to decode user data JSON from initData: {user_data_raw}")
        return JsonResponse({"error": "Invalid user data format"}, status=400)

    except Exception as e:
        logger.exception(f"An unexpected error occurred during Telegram authentication: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)
