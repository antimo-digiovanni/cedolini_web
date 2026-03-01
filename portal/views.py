from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Employee

def register_view(request, token):
    # Il "token" nel link è in realtà lo username dell'utente
    user_obj = get_object_or_404(User, username=token)
    employee = get_object_or_404(Employee, user=user_obj)

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not password or password != confirm_password:
            return render(request, 'register.html', {
                'employee': employee,
                'error': 'Le password non coincidono o sono vuote.'
            })

        # Imposta la nuova password e salva
        user_obj.set_password(password)
        user_obj.save()
        
        # Segna come registrato e togli obbligo cambio password
        employee.must_change_password = False
        employee.save()
        
        messages.success(request, "Registrazione completata! Ora puoi accedere.")
        return redirect('login')

    return render(request, 'register.html', {'employee': employee})