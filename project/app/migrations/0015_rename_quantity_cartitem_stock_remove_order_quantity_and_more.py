# Generated by Django 5.2 on 2025-04-27 10:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0014_alter_order_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cartitem',
            old_name='quantity',
            new_name='stock',
        ),
        migrations.RemoveField(
            model_name='order',
            name='quantity',
        ),
        migrations.RemoveField(
            model_name='product',
            name='image1',
        ),
        migrations.RemoveField(
            model_name='product',
            name='image2',
        ),
        migrations.RemoveField(
            model_name='product',
            name='image3',
        ),
        migrations.RemoveField(
            model_name='product',
            name='image4',
        ),
        migrations.RemoveField(
            model_name='product',
            name='image5',
        ),
        migrations.RemoveField(
            model_name='product',
            name='quantity',
        ),
        migrations.AddField(
            model_name='order',
            name='stock',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
