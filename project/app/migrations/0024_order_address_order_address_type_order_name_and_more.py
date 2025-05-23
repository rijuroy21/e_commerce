# Generated by Django 5.2 on 2025-05-07 12:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0023_address_pincode'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='address',
            field=models.TextField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='address_type',
            field=models.CharField(default=1, max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='name',
            field=models.CharField(default=1, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(default=1, max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='phone',
            field=models.CharField(default=1, max_length=15),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='pincode',
            field=models.CharField(default=1, max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='razorpay_payment_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='total_price',
            field=models.FloatField(default=1),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='OrderDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=15)),
                ('pincode', models.CharField(max_length=10)),
                ('address', models.TextField()),
                ('address_type', models.CharField(max_length=50)),
                ('payment_method', models.CharField(max_length=50)),
                ('total_price', models.FloatField()),
                ('razorpay_payment_id', models.CharField(blank=True, max_length=255, null=True)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='app.order')),
            ],
        ),
    ]
