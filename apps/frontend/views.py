from django.views.generic import TemplateView


class IndexView(TemplateView):
    """
    Единственная точка входа для клиентского SPA (ванильный HTML/CSS/JS —
    вся логика в static/frontend/app.js, здесь только разметка-каркас).
    """

    template_name = "frontend/index.html"
