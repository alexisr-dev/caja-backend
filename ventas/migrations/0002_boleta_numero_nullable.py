from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='boleta',
            name='numero',
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=30,
                null=True,
                unique=True,
            ),
        ),
    ]
