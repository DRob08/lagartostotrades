from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Tickers(models.Model):

    symbol = models.CharField(max_length=10)
    price = models.FloatField()
    upside = models.FloatField()
    downside = models.FloatField()
    u_val = models.FloatField()
    atr = models.FloatField()
    stop = models.FloatField()
    risk_unit = models.FloatField()
    position = models.IntegerField()
    support = models.FloatField()
    resistance = models.FloatField()
    notes = models.TextField()
    concerns = models.TextField()
    date_registered = models.DateField(default=timezone.now)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.symbol
