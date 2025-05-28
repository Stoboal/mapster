import logging

from celery import shared_task
from django.utils.timezone import now

from users.models import DAILY_MOVES_LIMIT, TelegramUser

logger = logging.getLogger(__name__)

@shared_task()
def reset_daily_moves() -> None:
    """
    Reset the daily moves for users who are behind the current date.

    The function identifies all Telegram users whose `last_move_date` is earlier
    than the current date and resets their `last_move_date` to the current date.
    It also updates their `daily_moves_remaining` to the predefined daily limit.
    This function is processed asynchronously as a shared task, allowing for
    background execution.
    """
    today = now().date()
    logger.info(f'Trying to reset daily moves for {today}')
    updated_count = TelegramUser.objects.filter(last_move_date__lt=today).update(
        last_move_date=today,
        daily_moves_remaining=DAILY_MOVES_LIMIT
    )
    logger.info(f'Daily moves for {updated_count} users were reset and updated')

