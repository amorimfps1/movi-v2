from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('academic', '0003_lesson_replacement_end_lesson_replacement_for_and_more'), ('core', '0005_person_cpf_unique')]
    operations = [migrations.AddField(model_name='trialparticipation', name='lead', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='lead_trials', to='core.lead'))]
