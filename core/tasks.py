import logging

from celery import shared_task

from .models import Feedback

logger = logging.getLogger(__name__)

@shared_task()
def send_feedback_answer() -> None:
    """
    Send feedback answers to the respective recipients if they are marked as answered.

    This function retrieves all feedback instances that are flagged as answered and
    processes them by sending out the respective feedback answers. It performs logging
    at each step to indicate the progress and status of the operation. The function
    ensures no feedback is left unsent if it meets the criteria.

    :return: None
    """
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
