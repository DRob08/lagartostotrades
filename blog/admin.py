from django.contrib import admin
from .models import TickerLogger
from .models import Ticker

# Register your models here.
admin.site.register(TickerLogger)
admin.site.register(Ticker)
