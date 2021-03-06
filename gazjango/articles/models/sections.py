from django.db import models
from gazjango.articles.models.stories import Article
import datetime
import os.path
from django.conf import settings

class Section(models.Model):
    """
    A section of coverage: news, features, opinions, columns....
    
    Each article belongs to exactly one section, and any number
    of subsections within that section.
    """
    
    name = models.CharField(max_length=40, unique=True)
    short_name = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=250, blank=True)
    is_special = models.BooleanField(blank=True, default=False,
                   help_text="Whether articles in this section will have " \
                              "the section name on the homepage.")
    
    class Meta:
        app_label = 'articles'
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name
    
    @models.permalink
    def get_absolute_url(self):
        return ('section', [self.slug])
    
    def get_stories(self, num_top=2, num_mid=3, num_low=12, **extra):
        "Calls Article.published.get_stories for stories in this section."
        return Article.published.get_stories(
            base = self.published_articles(),
            num_top = num_top,
            num_mid = num_mid,
            num_low = num_low
        )
    
    def published_articles(self):
        return self.articles.filter(status='p')
    
    def most_recent_article(self):
        "Returns the most recent story from this subsection."
        try:
            return self.published_articles().order_by('-pub_date')[0]
        except IndexError:
            return None
    
    def most_recent_articles(self, num=None):
        articles = self.published_articles().order_by('-pub_date')
        return articles[:num] if num else articles

    def shortest_name(self):
        return self.short_name or self.name
    

class Subsection(models.Model):
    """
    A subsection: Ask the Gazette, College News, a specific column, whatever.
    """
    
    name = models.CharField(max_length=40)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    section = models.ForeignKey(Section, related_name="subsections")
    is_special = models.BooleanField(default=False, blank=True,
                help_text="Whether articles in this subsection will be marked "
                          "as such on the homepage, issues, etc.")
    
    class Meta:
        app_label = 'articles'
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name
    
    @models.permalink
    def get_absolute_url(self):
        return ('subsection', [self.section.slug, self.slug])
    
    def get_stories(self, num_top=2, num_mid=3, num_low=12):
        "Calls Article.published.get_stories for stories in this subsection."
        return Article.published.get_stories(
            base = self.published_articles(),
            num_top = num_top,
            num_mid = num_mid, 
            num_low = num_low
        )
    
    def published_articles(self):
        return self.articles.filter(status='p')
    
    def most_recent_article(self):
        "Returns the most recent story from this subsection."
        try:
            return self.published_articles().order_by('-pub_date')[0]
        except IndexError:
            return None
    
    def most_recent_articles(self, num=None):
        articles = self.published_articles().order_by('-pub_date')
        return articles[:num] if num else articles
    
    def is_column(self):
        try:
            self.column
            return True
        except Column.DoesNotExist:
            return False
    

class Column(Subsection):
    """
    A column. Adds some extra information.
    
    This should really be in the Opinions category, but we're not hardcoding
    that in any way.
    
    If `is_over` is set, don't have it show up in the list in the admin. Used
    mainly for columns that are no longer running. There's nothing app-level
    that actually prevents new articles using it, however.
    """
    authors = models.ManyToManyField('accounts.UserProfile')
    is_over = models.BooleanField(default=False)
    
    SEMESTER_CHOICES = (
        ('1', 'Spring'),
        ('2', 'Fall'),
    )
    semester = models.CharField(max_length=1, choices=SEMESTER_CHOICES)
    year = models.IntegerField(blank=True, default=lambda:datetime.date.today().year)
    
    class Meta:
        app_label = 'articles'
    
    def wide_logo_url(self):
        path = '/static/images/column/%s_wide.png' % self.slug
        return path if os.path.exists(settings.BASE + path) else None
    
    def square_logo_url(self):
        path = '/static/images/column/%s_square.png' % self.slug
        return path if os.path.exists(settings.BASE + path) else None
    

