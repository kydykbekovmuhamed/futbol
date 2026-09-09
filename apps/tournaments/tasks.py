from celery import shared_task


@shared_task
def close_tournament_registration(tournament_id: int) -> None:
    """Срабатывает по достижении registration_deadline — см. services.close_registration."""
    from .services import close_registration

    close_registration(tournament_id)
