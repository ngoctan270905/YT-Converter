celery -A app.core.celery_app worker -l info -Q default,media,maintenance --pool=solo 
celery -A app.core.celery_app beat --loglevel=info