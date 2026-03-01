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
    # Funzione richiesta dal tuo urls.py
    employee = getattr(request.user, 'employee', None)
    if employee and employee.must_change_password:
        # Se deve cambiare password ma non abbiamo una pagina dedicata, 
        # per ora lo mandiamo alla dashboard o dove preferisci
        return redirect('dashboard')
    return redirect('dashboard')