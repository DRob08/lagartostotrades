from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Ticker(models.Model):

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
    date_registered = models.DateTimeField(default=timezone.now)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.symbol


class TickerLogger(models.Model):
    id = models.AutoField(primary_key=True)
    ticker = models.CharField(max_length=10)
    strategy = models.CharField(max_length=10)
    entryprice = models.FloatField()
    entrydate = models.DateTimeField(default=timezone.now)
    exitprice = models.FloatField()
    exitdate = models.DateTimeField(default=timezone.now)
    position = models.IntegerField()
    commissionfee = models.FloatField()
    status = models.CharField(max_length=10, default=None, blank=True, null=True)
    type = models.CharField(max_length=10, default=None, blank=True, null=True)
    # profit = models.FloatField()
    # loss = models.FloatField()
    # percentage = models.FloatField()
    # cummpl = models.FloatField()
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    notes = models.TextField()
    news = models.TextField(default=None, blank=True, null=True)
    prevdayhigh = models.FloatField(default=None, blank=True, null=True)
    prevdayclose = models.FloatField(default=None, blank=True, null=True)
    prevdaylow = models.FloatField(default=None, blank=True, null=True)
    # float = models.IntegerField(default=None, blank=True, null=True)
    float = models.FloatField(default=None, blank=True, null=True)
    industry = models.CharField(max_length=50,default=None, blank=True, null=True)
    category = models.CharField(max_length=50, default=None, blank=True, null=True)

    def __str__(self):
        return self.ticker
