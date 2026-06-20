from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from portal.models import Employee, Payslip


class Command(BaseCommand):
    help = 'Cancella cedolini per anno/mese, con eventuale filtro per dipendente, eliminando anche i PDF associati.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, required=True)
        parser.add_argument('--month', type=int, required=True)
        parser.add_argument('--employee-id', type=int)
        parser.add_argument('--yes', action='store_true', help='Conferma la cancellazione effettiva.')
        parser.add_argument('--dry-run', action='store_true', help='Mostra cosa verrebbe eliminato senza cancellare nulla.')

    def handle(self, *args, **options):
        year = options['year']
        month = options['month']
        employee_id = options.get('employee_id')
        confirmed = options['yes']
        dry_run = options['dry_run']

        if month < 1 or month > 12:
            raise CommandError('Il mese deve essere compreso tra 1 e 12.')

        queryset = Payslip.objects.select_related('employee').filter(year=year, month=month).order_by('employee__last_name', 'employee__first_name', 'id')

        employee = None
        if employee_id:
            employee = Employee.objects.filter(id=employee_id).first()
            if not employee:
                raise CommandError(f'Dipendente non trovato: {employee_id}')
            queryset = queryset.filter(employee_id=employee_id)

        count = queryset.count()
        if count == 0:
            self.stdout.write(self.style.WARNING('Nessun cedolino trovato con i filtri indicati.'))
            return

        self.stdout.write(f'Filtro: anno={year}, mese={month}, dipendente={employee_id or "tutti"}')
        self.stdout.write(f'Cedolini trovati: {count}')

        preview = list(queryset[:20])
        for payslip in preview:
            self.stdout.write(
                f'- id={payslip.id} | {payslip.employee.full_name} | {payslip.month:02d}/{payslip.year} | {payslip.pdf.name}'
            )
        if count > len(preview):
            self.stdout.write(f'... altri {count - len(preview)} cedolini non mostrati')

        if dry_run or not confirmed:
            self.stdout.write(self.style.WARNING('Nessuna cancellazione eseguita. Usa --yes per confermare oppure --dry-run per sola anteprima.'))
            return

        with transaction.atomic():
            deleted_count, _ = queryset.delete()

        self.stdout.write(self.style.SUCCESS(f'Cancellazione completata. Record eliminati: {deleted_count}'))