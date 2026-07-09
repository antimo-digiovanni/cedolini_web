from django import forms
from .models import Employee, Payslip, PersonalAssetEntry


class PayslipUploadForm(forms.ModelForm):
    class Meta:
        model = Payslip
        fields = ["employee", "year", "month", "pdf"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["employee"].queryset = Employee.objects.order_by("full_name")
        self.fields["employee"].widget.attrs.update({"class": "form-select"})

        self.fields["year"].widget.attrs.update({"class": "form-control", "min": "2000", "max": "2100"})
        self.fields["month"].widget.attrs.update({"class": "form-control", "min": "1", "max": "12"})
        self.fields["pdf"].widget.attrs.update({"class": "form-control"})

    def clean_month(self):
        m = self.cleaned_data["month"]
        if not (1 <= m <= 12):
            raise forms.ValidationError("Il mese deve essere tra 1 e 12.")
        return m


class PersonalAssetEntryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['operation_type'].choices = [choice for choice in self.fields['operation_type'].choices if choice[0]]
        self.fields['amount'].widget.attrs.update({'inputmode': 'decimal', 'autofocus': 'autofocus', 'placeholder': '0,00'})
        self.fields['reimbursement_amount'].widget.attrs.update({'inputmode': 'decimal', 'placeholder': '0,00'})
        self.fields['category'].widget.attrs.update({'list': 'financeCategorySuggestions', 'placeholder': 'Scrivi o tocca una categoria rapida'})

    class Meta:
        model = PersonalAssetEntry
        fields = [
            'occurred_on',
            'operation_type',
            'category',
            'amount',
            'reimbursement_amount',
            'description',
        ]
        widgets = {
            'occurred_on': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'operation_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es: Spesa casa, Stipendio, Trasferimento'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'reimbursement_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrizione opzionale dell\'operazione'}),
        }
        labels = {
            'occurred_on': 'Data',
            'operation_type': 'Tipo operazione',
            'category': 'Categoria',
            'amount': 'Importo',
            'reimbursement_amount': 'Importo da ricevere',
            'description': 'Descrizione',
        }
        help_texts = {
            'reimbursement_amount': 'Compilare solo per le spese rimborsabili.',
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('operation_type') != PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE:
            cleaned_data['reimbursement_amount'] = None
            self.instance.reimbursement_amount = None
        return cleaned_data