# Generated by Django 5.1.3 on 2024-11-20 09:27

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('full_name', models.CharField(max_length=255)),
                ('username', models.CharField(max_length=150, unique=True)),
                ('department', models.CharField(choices=[('Digital Marketing', 'Digital Marketing'), ('Web Development', 'Web Development'), ('Graphic Designing', 'Graphic Designing'), ('Social Media', 'Social Media')], max_length=50)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True)),
                ('position', models.CharField(max_length=150)),
                ('role', models.CharField(choices=[('Staff', 'Staff'), ('Manager', 'Manager'), ('Admin', 'Admin')], default='Staff', max_length=10)),
                ('password', models.CharField(max_length=128)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
