import logging

from celery import shared_task

from .models import Feedback

logger = logging.getLogger(__name__)

@shared_task()
def send_feedback_answer() -> None:
    logger.info('Start sending feedback answers')
    answers = Feedback.objects.filter(answered=True).all()
    if not answers:
        logger.info('No feedback answers to send')
        return None

    logger.info(f'Found {len(answers)} feedback answers to send')
    for answer in answers:
        answer.send_answer()
        logger.info(f'Feedback answer was sent: id {answer.id}')

    logger.info('All feedback answers were sent')
    return None
