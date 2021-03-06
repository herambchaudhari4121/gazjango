from django.contrib.contenttypes        import generic
from django.contrib.contenttypes.models import ContentType
from django.db                          import models

from gazjango.media.models import ImageFile

import datetime

class SectionSpecial(models.Model):
    "A special to be advertised on section pages."
    name = models.CharField(max_length=30)
    description = models.CharField(max_length=100)
    
    section = models.ForeignKey('articles.Section', related_name="specials")
    
    target_type = models.ForeignKey(ContentType)
    target_id   = models.PositiveIntegerField()
    target      = generic.GenericForeignKey('target_type', 'target_id')
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        app_label = 'articles'
    
    def get_target_url(self):
        return self.target.get_absolute_url()
    

class Special(models.Model):
    "A special thing / article / whatever to be advertised on the homepage."
    
    title = models.CharField(max_length=80)
    date  = models.DateTimeField(default=datetime.datetime.now)
    
    SPECIALS_CATEGORIES = (
        ('c', 'Column'),
        ('f', 'Feature'),
        ('p', 'Photo Spread'),
        ('v', 'Video'),
        ('g', 'Gazette'),
    )
    category = models.CharField(max_length=1, choices=SPECIALS_CATEGORIES)
    
    image = models.ForeignKey(ImageFile)
    
    target_type = models.ForeignKey(ContentType)
    target_id   = models.PositiveIntegerField()
    target      = generic.GenericForeignKey('target_type', 'target_id')
    
    def get_target_url(self):
        return self.target.get_absolute_url()
    
    def __unicode__(self):
        return self.title
    
    class Meta:
        app_label = 'articles'
        ordering = ('-date',)
    

def _remove_is_special_flag(sender, instance, **kwargs):
    if instance.target_type.model in ('article', 'photospread'):
        article = instance.target
        article.is_special = False
        article.save()
models.signals.post_delete.connect(_remove_is_special_flag, sender=Special)

class DummySpecialTarget(models.Model):
    """
    For when the thing we're linking to doesn't have a corresponding object
    to target. Should be used only when necessary.
    """
    
    url = models.URLField(blank=True)
    specials = generic.GenericRelation(Special, 
                                       content_type_field='target_type',
                                       object_id_field='target_id')
    section_specials = generic.GenericRelation(SectionSpecial, 
                                               content_type_field='target_type',
                                               object_id_field='target_id')
    
    def get_absolute_url(self):
        return self.url
    
    def __unicode__(self):
        return self.url
    
    class Meta:
        app_label = 'articles'
    
