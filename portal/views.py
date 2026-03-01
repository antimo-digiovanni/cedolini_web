from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Employee, Payslip

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

@login_required
def dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)
    payslips = Payslip.objects.filter(employee=employee).order_by('-year', '-month')
    return render(request, 'dashboard.html', {'employee': employee, 'payslips': payslips})

@login_required
def open_payslip(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id)
    if not request.user.is_staff and payslip.employee.user != request.user:
        return HttpResponse("Non autorizzato", status=403)
    response = HttpResponse(payslip.pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="cedolino_{payslip.year}_{payslip.month}.pdf"'
    return response

def register_view(request, token):
    user_obj = get_object_or_404(User, username=token)
    employee = get_object_or_404(Employee, user=user_obj)
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password and password == confirm_password:
            user_obj.set_password(password)
            user_obj.save()
            employee.must_change_password = False
            employee.save()
            messages.success(request, "Registrazione completata!")
            return redirect('login')
        messages.error(request, "Le password non coincidono.")
    return render(request, 'register.html', {'employee': employee})

@login_required
def force_password_change_if_needed(request):
    return redirect('dashboard')

@login_required
def complete_profile(request):
    # Funzione che mancava nell'ultimo errore
    return redirect('dashboard')

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'admin_dashboard.html')