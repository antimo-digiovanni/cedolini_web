from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0028_portalusersetting_personal_asset_account_adjustment'),
    ]

    operations = [
        migrations.AddField(
            model_name='personalassetentry',
            name='reimbursement_settlement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='settled_reimbursement_entries', to='portal.personalassetentry'),
        ),
    ]