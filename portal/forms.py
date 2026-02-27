from django import forms
from .models import Employee, Payslip


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