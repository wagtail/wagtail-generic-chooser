from django.db import models


class Person(models.Model):
    first_name = models.CharField("First name", max_length=255)
    last_name = models.CharField("Last name", max_length=255)
    job_title = models.CharField("Job title", max_length=255)
