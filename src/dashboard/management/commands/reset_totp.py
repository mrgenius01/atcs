"""
Django management command to reset TOTP for testing the first-time setup flow
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dashboard.models import UserProfile


class Command(BaseCommand):
    help = 'Reset TOTP settings for a user to test first-time setup flow'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username to reset TOTP for (default: admin)'
        )

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Reset TOTP settings
            profile.totp_enabled = False
            profile.totp_secret = ""
            profile.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully reset TOTP for user "{username}". '
                    f'They will be prompted to set up TOTP on next login.'
                )
            )
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error resetting TOTP: {str(e)}')
            )
