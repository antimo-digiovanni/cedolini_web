from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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

def register_view(request, token):
    # Il "token" nel link è lo username
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
            messages.success(request, "Registrazione completata! Ora puoi accedere.")
            return redirect('login')
        else:
            messages.error(request, "Le password non coincidono.")
    
    return render(request, 'register.html', {'employee': employee})

@login_required
def force_password_change_if_needed(request):
    # Questa è la funzione che bloccava il deploy
    employee = getattr(request.user, 'employee', None)
    if employee and employee.must_change_password:
        return redirect('dashboard') # O a una pagina di cambio password se esiste
    return redirect('dashboard')

@login_required
def admin_dashboard(request):
    # Funzione extra spesso presente nei tuoi URL
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'admin_dashboard.html')