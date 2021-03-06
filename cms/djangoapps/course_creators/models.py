"""
Table for storing information about whether or not Studio users have course creation privileges.
"""
from django.db import models
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver, Signal
from django.contrib.auth.models import User

from django.utils import timezone
from django.utils.translation import ugettext as _

# A signal that will be sent when users should be added or removed from the creator group
update_creator_state = Signal(providing_args=["caller", "user", "add"])


class CourseCreator(models.Model):
    """
    Creates the database table model.
    """
    UNREQUESTED = 'unrequested'
    PENDING = 'pending'
    GRANTED = 'granted'
    DENIED = 'denied'

    # Second value is the "human-readable" version.
    STATES = (
        (UNREQUESTED, _(u'unrequested')),
        (PENDING, _(u'pending')),
        (GRANTED, _(u'granted')),
        (DENIED, _(u'denied')),
    )

    user = models.ForeignKey(User, help_text=_("Studio user"), unique=True)
    state_changed = models.DateTimeField('state last updated', auto_now_add=True,
                                         help_text=_("The date when state was last updated"))
    state = models.CharField(max_length=24, blank=False, choices=STATES, default=UNREQUESTED,
                             help_text=_("Current course creator state"))
    note = models.CharField(max_length=512, blank=True, help_text=_("Optional notes about this user (for example, "
                                                                    "why course creation access was denied)"))

    def __unicode__(self):
        return u'%str | %str [%str] | %str' % (self.user, self.state, self.state_changed, self.note)


@receiver(post_init, sender=CourseCreator)
def post_init_callback(sender, **kwargs):
    """
    Extend to store previous state.
    """
    instance = kwargs['instance']
    instance.orig_state = instance.state


@receiver(post_save, sender=CourseCreator)
def post_save_callback(sender, **kwargs):
    """
    Extend to update state_changed time and modify the course creator group in authz.py.
    """
    instance = kwargs['instance']
    # We only wish to modify the state_changed time if the state has been modified. We don't wish to
    # modify it for changes to the notes field.
    if instance.state != instance.orig_state:
        update_creator_state.send(
            sender=sender,
            caller=instance.admin,
            user=instance.user,
            add=instance.state == CourseCreator.GRANTED
        )
        instance.state_changed = timezone.now()
        instance.orig_state = instance.state
        instance.save()
