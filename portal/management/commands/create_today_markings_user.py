from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError

from portal.access import TODAY_MARKINGS_GROUP_NAME


class Command(BaseCommand):
    help = "Crea o aggiorna un account limitato alla pagina 'Chi ha marcato oggi'."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("password")
        parser.add_argument("--first-name", dest="first_name", default="")
        parser.add_argument("--last-name", dest="last_name", default="")
        parser.add_argument("--email", dest="email", default="")

    def handle(self, *args, **options):
        username = options["username"].strip()
        password = options["password"]
        first_name = options["first_name"].strip()
        last_name = options["last_name"].strip()
        email = options["email"].strip()

        if not username:
            raise CommandError("Lo username non puo essere vuoto.")

        group, _ = Group.objects.get_or_create(name=TODAY_MARKINGS_GROUP_NAME)
        user, created = User.objects.get_or_create(username=username)

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_password(password)
        user.save()

        user.groups.add(group)

        action = "creato" if created else "aggiornato"
        self.stdout.write(
            self.style.SUCCESS(
                f"Account {action}: {username}. Accesso limitato assegnato tramite gruppo '{TODAY_MARKINGS_GROUP_NAME}'."
            )
        )