from diff_match_patch.diff_match_patch import diff_match_patch
from datetime import datetime

from django.db                  import models
from django.db.models           import permalink
from django.contrib.auth.models import User
from gazjango.accounts.models            import UserProfile
from gazjango.media.models               import MediaFile, ImageFile
from gazjango.articles.exceptions        import RelationshipMismatch
from gazjango.articles.models.categories import Category
import gazjango.articles.formats as formats


class PublishedArticlesManager(models.Manager):
    "A custom manager for Articles, returning only published articles."
    def get_query_set(self):
        orig = super(PublishedArticlesManager, self).get_query_set()
        return orig.filter(status='p')
    
    def get_top_story(self):
        """Returns a random published article with position=1.
        
        There should generally only be one, but just in case, we rotate."""
        return self.filter(position=1).order_by("?")[0]
    
    def get_secondary_stories(self, num=2):
        """Returns a list of ``num`` stories with position=2."""
        return self.filter(position=2).order_by("-pub_date")[:num]
    
    def get_tertiary_stories(self, num=6):
        """Returns the ``num`` most recent stories with a null position."""
        return self.filter(position=None).order_by("-pub_date")[:num]
    


class Article(models.Model):
    """
    A story or other article to be published. Includes news stories,
    editorials, etc, but not announcements or jobs.
    
    Stores major revisions of the article: whatever the author decides to
    save manually while writing, changes editors make afterwards, and then
    any changes made after publication. Comments can (and should) be attached
    to these revisions.
    """
    
    headline    = models.CharField(max_length=200)
    short_title = models.CharField(blank=True, max_length=100)
    subtitle    = models.CharField(blank=True, max_length=200)
    slug        = models.SlugField(unique_for_date="pub_date")
    
    summary = models.TextField()
    short_summary = models.CharField(max_length=150)
    long_summary  = models.TextField(blank=True)
    
    text   = models.TextField()
    format = models.ForeignKey('Format')
    
    pub_date = models.DateTimeField(default=datetime.now)
    authors  = models.ManyToManyField(UserProfile, related_name="articles")
    category = models.ForeignKey(Category)
    
    front_image = models.ForeignKey(ImageFile, null=True, related_name="articles_with_front")
    thumbnail   = models.ForeignKey(ImageFile, null=True, related_name="articles_with_thumbnail")
    media = models.ManyToManyField(MediaFile, related_name="articles")
    
    
    STATUS_CHOICES = (
        ('d', 'Draft'),
        ('e', 'Pending Review'),
        ('w', 'Scheduled'),
        ('p', 'Published')
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    
    comments_allowed = models.BooleanField(default=True)
    
    position  = models.PositiveSmallIntegerField(blank=True, null=True)
    # null = nothing special, 1 = top story, 2 = second-tier story
    
    objects = models.Manager()
    published = PublishedArticlesManager()
    
    def get_title(self):
        return (self.short_title or self.headline)
    
    
    def allow_edit(self, user):
        return self.authors.filter(user__pk=user.pk).count() > 0 \
            or user.has_perm('articles.change_article');
    
    
    def text_at_revision(self, revision):
        """Returns the text as it was at the specified revision."""
        if revision.article != self:
            raise RelationshipMismatch()
        d = diff_match_patch()
        rewound = self.text
        for r in self.revisions.filter(active=True, date__gte=revision.date):
            rewound = d.patch_apply(d.patch_fromText(r.delta), rewound)[0]
        return rewound
    
    def revise_text(self, revised_text):
        d = diff_match_patch()
        patch = d.patch_toText(d.patch_make(revised_text, self.text))
        revision = ArticleRevision.objects.create(article=self, delta=patch)
        
        self.text = revised_text
        self.save()
    
    
    def formatted_text(self):
        formatter = getattr(formats, self.format.function)
        return formatter(self.text)
    
    def formatted_text_at_revision(self, revision):
        formatter = getattr(formats, self.format.function)
        return formatter(self.text_at_revision(revision))
    
    
    def related_list(self, num=None):
        """Returns a QuerySet of related stories."""
        # TODO: improve related_list
        related = self.category.root().all_articles()
        related = related.exclude(pk=self.pk).order_by('-pub_date')
        return related[:num] if num else related
    
    
    def __unicode__(self):
        return self.slug
    
    @permalink
    def get_absolute_url(self):
        d = self.pub_date
        a = [str(x) for x in (d.year, d.month, d.day)]
        return ('articles.views.article', a + [self.slug])
    
    class Meta:
        app_label = 'articles'
    


class ArticleRevision(models.Model):
    """ A revision of an article. Only deltas are stored.
    
    Note that the most recent text is stored in the article's text attribute, while 
    earlier versions are stored as revisions...as such, these are "reverse diffs."
    For example, if an article has versions 1, 2, and 3, version 3 is stored directly
    with the article, and there are ArticleRevisions to go from 3 to 2 and from 2 to
    1."""
    
    article = models.ForeignKey('Article', related_name='revisions')
    delta   = models.TextField()
    date    = models.DateTimeField(default=datetime.now)
    active  = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-date']
        app_label = 'articles'
    
    def __unicode__(self):
        return u"%s - %s" % (self.article.slug, self.date)
    

class Format(models.Model):
    """ A format: html, textile, etc. """
    
    name     = models.CharField(max_length=30, unique=True)
    function = models.CharField(max_length=30)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        app_label = 'articles'
    
