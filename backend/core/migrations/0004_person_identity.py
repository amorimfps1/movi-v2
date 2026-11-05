from django.db import migrations


def rename_permissions(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    alias = schema_editor.connection.alias
    # RenameContentType injected by Django preserves content type PK and grants.
    types = ContentType.objects.using(alias).filter(app_label='core', model__in=['student', 'person'])
    for verb in ('add', 'change', 'delete', 'view'):
        Permission.objects.using(alias).filter(content_type__in=types, codename=f'{verb}_student').update(codename=f'{verb}_person')


def restore_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    for verb in ('add', 'change', 'delete', 'view'):
        Permission.objects.using(schema_editor.connection.alias).filter(
            content_type__app_label='core', content_type__model__in=['student', 'person'],
            codename=f'{verb}_person',
        ).update(codename=f'{verb}_student')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_ecowork_residence_foundation'),
        ('billing', '0004_collectionmessage'),
        ('ecowork', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]
    operations = [
        migrations.AlterModelTable(name='student', table='core_student'),
        migrations.RenameModel(old_name='Student', new_name='Person'),
        migrations.RunPython(rename_permissions, restore_permissions),
    ]
