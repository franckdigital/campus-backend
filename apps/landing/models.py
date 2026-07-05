from django.db import models
from apps.core.models import BaseModel


class AIKeywordResponse(BaseModel):
    """A keyword → canned-response pair for the public vitrine's FAQ chat
    widget. No real LLM involved — the widget matches the visitor's question
    against `keyword` in `priority` order and returns the first match's
    `response`. `keyword` may hold several comma-separated alternatives
    (e.g. "frais, inscription") — the row matches if ANY of them appears as
    a substring of the question (case-insensitive). A row with
    keyword='default' is the fallback used when nothing matches."""
    keyword = models.CharField(max_length=100)
    question_example = models.CharField(max_length=255, blank=True)
    response = models.TextField()
    priority = models.PositiveIntegerField(default=0, help_text="0 = priorité la plus haute")

    class Meta:
        db_table = 'landing_ai_keyword_responses'
        verbose_name = "Réponse IA (mot-clé)"
        verbose_name_plural = "Réponses IA (mots-clés)"
        ordering = ['priority', 'keyword']

    def __str__(self):
        return f"{self.keyword} → {self.response[:40]}"
