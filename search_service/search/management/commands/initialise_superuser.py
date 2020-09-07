from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.utils import IntegrityError


class Command(BaseCommand):
    help = "Management command to add a super user "

    def add_arguments(self, parser):
        parser.add_argument("--user", nargs="?", type=str, default=None)
        parser.add_argument("--password", nargs="?", type=str, default=None)
        parser.add_argument("--email", nargs="?", type=str, default=None)

    def handle(self, *args, **options):
        if not options.get("user") or not options.get("email") or not options.get("password"):
            raise CommandError("User, Password and Email must all be provided.")
        try:
            admin_user = User.objects.create_superuser(
                options["user"], options["email"], options["password"]
            )
            admin_user.save()
        except IntegrityError:
            print(f'User {options["user"]} already exists.')
