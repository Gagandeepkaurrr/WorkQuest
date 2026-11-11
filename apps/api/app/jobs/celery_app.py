from celery import Celery
from app.core.config import get_settings
settings=get_settings()
celery=Celery('workquest',broker=settings.redis_url.get_secret_value(),include=['app.jobs.tasks'])
celery.conf.update(task_default_queue=settings.redis_namespace+':jobs',task_serializer='json',accept_content=['json'],task_acks_late=True,task_reject_on_worker_lost=True,worker_prefetch_multiplier=1,task_ignore_result=True,task_time_limit=55,task_soft_time_limit=50,broker_connection_retry_on_startup=True,broker_transport_options={'global_keyprefix':settings.redis_namespace+':','visibility_timeout':90})
