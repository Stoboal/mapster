import logging

from celery import shared_task
from django.utils.timezone import now

from users.models import TelegramUser, DAILY_MOVES_LIMIT

logger = logging.getLogger(__name__)

@shared_task()
def reset_daily_moves():
    today = now().date()
    logger.info(f'Trying to reset daily moves for {today}')
    updated_count = TelegramUser.objects.filter(last_move_date__lt=today).update(
        last_move_date=today,
        daily_moves_remaining=DAILY_MOVES_LIMIT
    )
    logger.info(f'Daily moves for {updated_count} users were reset')
    logger.info(f'Daily moves for {updated_count} users were updated')

