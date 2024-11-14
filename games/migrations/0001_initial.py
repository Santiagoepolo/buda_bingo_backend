# Generated by Django 4.2.16 on 2024-11-14 02:17

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('waiting', 'Waiting'), ('playing', 'Playing'), ('finished', 'Finished')], default='waiting', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('drawn_numbers', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=list, size=None)),
                ('current_number', models.IntegerField(blank=True, null=True)),
                ('winner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='won_games', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PlayerCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('card_numbers', django.contrib.postgres.fields.ArrayField(base_field=django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), size=5), size=5)),
                ('selected_numbers', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=list, size=None)),
                ('is_winner', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='games.game')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'game')},
            },
        ),
    ]
