import hashlib
import hmac
import json
import logging

from django.http import JsonResponse
from django.utils.timezone import now
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from urllib.parse import parse_qsl

from app.settings import env
from users.models import TelegramUser


logger = logging.getLogger(__name__)

BOT_TOKEN = env("TELEGRAM_TOKEN")
TELEGRAM_AUTH_TIMEOUT = 3600


def check_telegram_auth(raw_init_data: str) -> bool:
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
    raw_init_data = request.data.get("initData")
    if not raw_init_data or not check_telegram_auth(raw_init_data):
        return JsonResponse({"error": "Invalid Telegram signature"}, status=403)

    parsed_data = dict(parse_qsl(raw_init_data))
    user_data_raw = parsed_data.get("user", "{}")
    user_data = json.loads(user_data_raw)

    telegram_id = user_data.get("id")
    username = user_data.get("username", f"tg_{telegram_id}")

    user, created = TelegramUser.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={"username": username}
    )
    if created:
        logger.info(f'Object was created: TelegramUser, telegram_id={telegram_id}, username={username}')

    if not created and user.username != username and not user.username.startswith("tg_"):
        user.username = username
        user.save(update_fields=["username"])
        logger.info(f'Object was updated: TelegramUser, telegram_id={telegram_id}, username={username}')

    token, _ = Token.objects.get_or_create(user=user)
    user.last_login = now()
    user.save(update_fields=["last_login"])
    logger.info(f'User was logged in: telegram_id={telegram_id}, username={username}')

    return JsonResponse({
        "token": token.key,
        "user": {
            "id": user.id,
            "username": user.username
        }
    })
