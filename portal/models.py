from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import secrets


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    first_name = models.CharField(max_length=80, blank=True, null=True)
    last_name = models.CharField(max_length=80, blank=True, null=True)
    email_invio = models.EmailField(max_length=255, blank=True, null=True)
    invito_inviato = models.BooleanField(default=False)
    external_code = models.CharField(max_length=10, blank=True, null=True)
    must_change_password = models.BooleanField(default=True)
    privacy_accepted = models.BooleanField(default=False)
    privacy_accepted_at = models.DateTimeField(null=True, blank=True)

    @property
    def full_name(self):
        parts = [p for p in (self.first_name, self.last_name) if p]
        if parts:
            return " ".join(parts)
        # fallback to username if names missing
        try:
            return self.user.username
        except Exception:
            return ""

    def __str__(self):
        return self.full_name


class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payslips")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    pdf = models.FileField(upload_to="payslips/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("employee", "year", "month")]


class Cud(models.Model):
    """Documento CUD annuale per dipendente."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="cuds")
    year = models.PositiveIntegerField()
    pdf = models.FileField(upload_to="cud/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("employee", "year")]
        ordering = ["-year"]

    def __str__(self):
        return f"CUD {self.year} - {self.employee.full_name}"


class PayslipView(models.Model):
    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)


class CudView(models.Model):
    cud = models.ForeignKey(Cud, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)


class AuditEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)
    actor_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    payslip = models.ForeignKey(Payslip, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True, default=dict)


class ImportJob(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    total_files = models.IntegerField(default=0)
    processed_files = models.IntegerField(default=0)
    created_users = models.IntegerField(default=0)
    created_payslips = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="processing")  # processing | completed | error
    error_message = models.TextField(blank=True, null=True)


# =========================================
# INVITE TOKEN (PRODUCTION READY)
# =========================================

class InviteToken(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="invite_tokens")
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    def mark_used(self):
        self.used = True
        self.used_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Invite for {self.employee.full_name}"


class WorkZone(models.Model):
    """Zona di lavoro geolocalizzata configurata dall'admin."""

    name = models.CharField(max_length=120)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_meters = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.radius_meters}m)"


class EmployeeWorkZone(models.Model):
    """Assegnazione zona-dipendente (storica e attivabile/disattivabile)."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="zone_assignments")
    zone = models.ForeignKey(WorkZone, on_delete=models.CASCADE, related_name="employee_assignments")
    is_active = models.BooleanField(default=True)
    strict_geofence = models.BooleanField(default=False)
    valid_from = models.DateField(default=timezone.now)
    valid_to = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("employee", "zone", "valid_from")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.full_name} -> {self.zone.name}"


class WorkSession(models.Model):
    """Marcatura giornaliera del dipendente (ingresso/uscita)."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="work_sessions")
    work_date = models.DateField(default=timezone.localdate)
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    start_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    end_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    end_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    start_zone = models.ForeignKey(
        WorkZone,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="start_sessions",
    )
    end_zone = models.ForeignKey(
        WorkZone,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="end_sessions",
    )
    start_within_zone = models.BooleanField(default=False)
    end_within_zone = models.BooleanField(default=False)

    corrected_started_at = models.DateTimeField(blank=True, null=True)
    corrected_ended_at = models.DateTimeField(blank=True, null=True)
    correction_note = models.CharField(max_length=255, blank=True, null=True)
    corrected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="corrected_work_sessions",
    )
    corrected_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("employee", "work_date")]
        ordering = ["-work_date", "-created_at"]

    def effective_started_at(self):
        return self.corrected_started_at or self.started_at

    def effective_ended_at(self):
        return self.corrected_ended_at or self.ended_at

    def worked_minutes(self):
        start_dt = self.effective_started_at()
        end_dt = self.effective_ended_at()
        if not start_dt or not end_dt:
            return 0
        delta = end_dt - start_dt
        total_minutes = int(delta.total_seconds() // 60)
        return max(total_minutes, 0)

    def worked_hours_display(self):
        minutes = self.worked_minutes()
        hours = minutes // 60
        rem = minutes % 60
        return f"{hours:02d}:{rem:02d}"

    def __str__(self):
        return f"{self.employee.full_name} {self.work_date}"


class WorkMarkRequest(models.Model):
    """Richiesta dipendente per autorizzare marcatura fuori zona nel giorno indicato."""

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'In attesa'),
        (STATUS_APPROVED, 'Approvata'),
        (STATUS_REJECTED, 'Rifiutata'),
    ]

    MARK_TYPE_START = 'start'
    MARK_TYPE_END = 'end'
    MARK_TYPE_BOTH = 'both'  # compatibilita storica
    MARK_TYPE_CHOICES = [
        (MARK_TYPE_START, 'Entrata'),
        (MARK_TYPE_END, 'Uscita'),
        (MARK_TYPE_BOTH, 'Entrata e uscita'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='work_mark_requests')
    work_date = models.DateField(default=timezone.localdate)
    mark_type = models.CharField(max_length=10, choices=MARK_TYPE_CHOICES, default=MARK_TYPE_BOTH)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    review_note = models.CharField(max_length=255, blank=True, null=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reviewed_work_mark_requests',
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.full_name} {self.work_date} [{self.status}]"