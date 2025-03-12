from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()
"""
Connect the User model and the UserProfile model.
"""
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


"""
Delete old profile picture on setting new profile picture
"""
@receiver(pre_save, sender=Profile)
def delete_old_profile_picture(sender, instance, **kwargs):
    print("method called")
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.profile_picture and old_instance.profile_picture != instance.profile_picture:
                storage = old_instance.profile_picture.storage
                if storage.exists(old_instance.profile_picture.name):
                    storage.delete(old_instance.profile_picture.name)
        except sender.DoesNotExist:
            pass

@receiver(post_delete, sender=Profile)
def delete_profile_picture_on_delete(sender, instance, **kwargs):
    print("method called")
    if instance.profile_picture:
        storage = instance.profile_picture.storage
        if storage.exists(instance.profile_picture.name):
            storage.delete(instance.profile_picture.name)