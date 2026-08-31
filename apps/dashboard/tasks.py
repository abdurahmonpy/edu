import logging
from celery import shared_task
from apps.services.score_service import decay_student_scores

logger = logging.getLogger(__name__)

@shared_task
def decay_student_scores_task():
    logger.info('Starting scheduled score decay task...')
    result = decay_student_scores()
    logger.info(f'Finished score decay: {result}')
    return result
