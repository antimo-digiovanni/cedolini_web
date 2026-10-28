from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from . import push
from .models import Announcement, AnnouncementRead, Employee
from .views import _create_audit_event


def visible_announcements(employee):
    """Comunicazioni destinate al dipendente (a tutti o a lui in particolare)."""
    return Announcement.objects.filter(Q(all_employees=True) | Q(recipients=employee)).distinct()


def unread_count(employee):
    read_ids = AnnouncementRead.objects.filter(employee=employee).values_list('announcement_id', flat=True)
    return visible_announcements(employee).exclude(id__in=read_ids).count()


# ------------------------------------------------------------------ dipendente

@login_required
def employee_announcements(request):
    employee = Employee.objects.filter(user=request.user).first()
    if not employee:
        return redirect('dashboard')
    read_map = dict(AnnouncementRead.objects.filter(employee=employee).values_list('announcement_id', 'read_at'))
    items = [{'a': a, 'read_at': read_map.get(a.id)} for a in visible_announcements(employee)[:100]]
    return render(request, 'portal/employee_announcements.html', {'items': items})


@login_required
def employee_announcement_detail(request, ann_id):
    employee = Employee.objects.filter(user=request.user).first()
    if not employee:
        return redirect('dashboard')
    ann = get_object_or_404(visible_announcements(employee), id=ann_id)
    if request.method == 'POST':
        _, created = AnnouncementRead.objects.get_or_create(announcement=ann, employee=employee)
        if created:
            _create_audit_event(request, 'announcement_read', employee=employee, metadata={'announcement_id': ann.id})
        return redirect('employee_announcements')
    read = AnnouncementRead.objects.filter(announcement=ann, employee=employee).first()
    return render(request, 'portal/employee_announcement_detail.html', {'a': ann, 'read': read})


# ------------------------------------------------------------------ amministrazione

def _preview(text, limit=110):
    """Prime parole del testo, su una riga, per l'anteprima nella notifica."""
    text = ' '.join((text or '').split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(' ', 1)[0].rstrip('.,;:') + '…'


def notification_text(ann, again=False):
    """Titolo e testo della notifica push di una comunicazione."""
    if again:
        return (f'Da leggere: {ann.title[:80]}',
                'Non hai ancora confermato la lettura di questa comunicazione. Tocca per aprirla.')
    return (f'San Vincenzo · {ann.title[:80]}',
            f'{_preview(ann.body)}\nTocca per leggerla e conferma con «Ho letto».')


def _notify(ann, employees, again=False):
    title, body = notification_text(ann, again)
    push.notify_many_later(
        [e.user_id for e in employees], title=title, body=body,
        url=reverse('employee_announcement_detail', args=[ann.id]), tag=f'comunicazione-{ann.id}')


@login_required
def admin_announcements(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    employees = Employee.objects.select_related('user').filter(user__is_active=True).order_by('last_name', 'first_name')
    error = None
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()[:150]
        body = (request.POST.get('body') or '').strip()
        to_all = request.POST.get('audience', 'all') == 'all'
        chosen = list(employees.filter(id__in=request.POST.getlist('recipients'))) if not to_all else []
        if not title or not body:
            error = 'Scrivi titolo e testo della comunicazione.'
        elif not to_all and not chosen:
            error = 'Scegli almeno un destinatario.'
        else:
            ann = Announcement.objects.create(title=title, body=body, all_employees=to_all, created_by=request.user)
            if chosen:
                ann.recipients.set(chosen)
            _create_audit_event(request, 'announcement_published', metadata={'announcement_id': ann.id, 'all': to_all,
                                                                             'recipients': len(chosen)})
            _notify(ann, ann.recipient_employees())
            return redirect(reverse('admin_announcement_detail', args=[ann.id]) + '?pubblicata=1')

    rows = []
    for ann in Announcement.objects.all()[:50]:
        total = ann.recipient_employees().count()
        read = ann.reads.count()
        rows.append({'a': ann, 'total': total, 'read': read, 'pct': int(round(100 * read / total)) if total else 0})
    return render(request, 'portal/admin_announcements.html', {
        'rows': rows, 'employees': employees, 'error': error, 'posted': request.POST if request.method == 'POST' else None,
    })


@login_required
def admin_announcement_detail(request, ann_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    ann = get_object_or_404(Announcement, id=ann_id)
    reads = {r.employee_id: r.read_at for r in ann.reads.all()}
    recipients = list(ann.recipient_employees().order_by('last_name', 'first_name'))
    read_list = [(e, reads[e.id]) for e in recipients if e.id in reads]
    unread_list = [e for e in recipients if e.id not in reads]
    feedback = None
    if request.method == 'POST' and request.POST.get('action') == 'remind' and unread_list:
        _notify(ann, unread_list, again=True)
        _create_audit_event(request, 'announcement_reminded', metadata={'announcement_id': ann.id, 'count': len(unread_list)})
        return redirect(reverse('admin_announcement_detail', args=[ann.id]) + '?promemoria=1')
    if request.GET.get('pubblicata'):
        feedback = 'Comunicazione pubblicata: i dipendenti con le notifiche attive hanno ricevuto l\'avviso.'
    elif request.GET.get('promemoria'):
        feedback = 'Promemoria inviato a chi non ha ancora letto.'
    return render(request, 'portal/admin_announcement_detail.html', {
        'a': ann, 'read_list': read_list, 'unread_list': unread_list, 'feedback': feedback,
        'pct': int(round(100 * len(read_list) / len(recipients))) if recipients else 0, 'total': len(recipients),
    })
