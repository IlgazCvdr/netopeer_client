# netconf/models.py

from django.db import models

class NetconfDevice(models.Model):
    hostname = models.CharField(max_length=100)
    port = models.IntegerField(default=830)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.hostname  # or whatever you want to display
