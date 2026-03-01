from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Employee, Payslip

def home(request):
    # Se l'utente è loggato va alla dashboard, altrimenti al login
    if request.user.is_authenticated:
        return redirect('admin_dashboard' if request.user.is_staff else 'dashboard')
    return redirect('login')

@login_required
def dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)
    payslips = employee.payslips.all().order_index('-year', '-month')
    return render(request, 'dashboard.html', {'employee': employee, 'payslips': payslips})

def register_view(request, token):
    # Il "token" è lo username
    user_obj = get_object_or_404(User, username=token)
    employee = get_object_or_404(Employee, user=user_obj)

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not password or password != confirm_password:
            return render(request, 'register.html', {
                'employee': employee,
                'error': 'Le password non coincidono.'
            })

        user_obj.set_password(password)
        user_obj.save()
        employee.must_change_password = False
        employee.save()
        
        messages.success(request, "Registrazione completata! Accedi ora.")
        return redirect('login')

    return render(request, 'register.html', {'employee': employee})