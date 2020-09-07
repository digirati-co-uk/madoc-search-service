import uuid

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from model_utils.models import TimeStampedModel

from .langbase import INTERNET_LANGUAGES


# Add Models
