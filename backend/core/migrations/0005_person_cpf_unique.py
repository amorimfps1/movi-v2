from django.db import migrations, models
from django.db.models import Count, Q


def check_duplicate_cpfs(apps, schema_editor):
    person = apps.get_model("core", "Person")
    duplicates = (person.objects.using(schema_editor.connection.alias).exclude(cpf="")
                  .values("cpf").annotate(count=Count("id")).filter(count__gt=1))
    if duplicates.exists():
        raise RuntimeError("Existem CPFs duplicados. Resolva os cadastros antes de aplicar core.0005_person_cpf_unique.")


class Migration(migrations.Migration):
    dependencies = [("core", "0004_person_identity")]
    operations = [
        migrations.RunPython(check_duplicate_cpfs, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="person",
            constraint=models.UniqueConstraint(fields=("cpf",), condition=~Q(cpf=""), name="core_person_cpf_nonempty_unique"),
        ),
    ]
