import datetime
import random
import re

from django.contrib.auth.models         import User
from django.contrib.contenttypes        import generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions             import ObjectDoesNotExist
from django.db                          import models

from gazjango.accounts.models          import UserProfile
from gazjango.articles                 import formats
from gazjango.articles.models.concepts import StoryConcept
from gazjango.articles.models.specials import Special
from gazjango.comments.models          import PublicComment
from gazjango.diff_match_patch.diff_match_patch import diff_match_patch
from gazjango.media.models             import MediaFile, ImageFile, MediaBucket
from gazjango.misc.helpers             import smart_truncate
from gazjango.misc.exceptions          import RelationshipMismatch
from gazjango.misc.templatetags.extras import join_authors
from gazjango.scrapers.BeautifulSoup   import BeautifulSoup


class PublishedArticlesManager(models.Manager):
    "A custom manager for Articles, returning only published articles."
    
    def get_query_set(self):
        orig = super(PublishedArticlesManager, self).get_query_set()
        return orig.filter(status='p')
    
    def get_stories(self, num_top=1, num_mid=2, num_low=6, base=None):
        """
        Returns stories organized by priority. This method will do some
        rearranging to always get you the number of stories of each
        type that you request: if there are two topstories, one of them
        gets bumped down to a midstory, and if there's not enough midstories,
        we pull up the most recent article that can be a midstary, and other
        such operations.
        
        The return format looks like:
        [
            [topstory],
            [midstory1, midstory2]
            [lowstory1, lowstory2, lowstory3, ...]
        ]
        Note that these are lists, *not* QuerySets.
        
        If you need to do something more specific, you can pass `base`;
        then all the stories will come out of there. For example,
        get_stories(base=section.articles) would return stories from
        the articles in `section` (but see Section's get_stories method).
        """
        # TODO: april fools stuff
        # TODO: randomosity
        base = (base or self).order_by('-pub_date')
        
        tops = base.filter(position='1')[:num_top]
        selected_pks = list(tops.values_list('pk', flat=True))
        
        mids = base.filter(position__in=('1','2')).exclude(pk__in=selected_pks)[:num_mid]
        selected_pks += list(mids.values_list('pk', flat=True))
        
        lows = base.exclude(pk__in=selected_pks)[:num_low]
        
        return [list(tops), list(mids), list(lows)]
        
        '''
        april_fools = False
        if base:
            april_fools = True
        
        base = base or self    

        if april_fools:
            tops = list(base.filter(position='1').order_by('-pub_date')[:3])
            tops = sorted(tops, key=lambda x: random.random())
            if len(tops) < num_top:
                cands = base.filter(possible_position='1').order_by('position', '-pub_date')
                cands = cands.exclude(pk__in=[top.pk for top in tops])
                needed = num_top - len(tops)
                tops += list(cands[:needed])
            else:
                tops = tops[:num_top]
        
            exclude_pks = [top.pk for top in tops]
            mids = base.filter(position__in=('1', '2')).exclude(pk__in=exclude_pks)
            mids = list(mids.order_by('-pub_date'))
            if len(mids) < num_mid:
                cands = base.filter(possible_position__in=('1', '2'))
                exclude_pks += [mid.pk for mid in mids]
                cands = cands.exclude(pk__in=exclude_pks).order_by('-pub_date')
            
                needed = num_mid - len(mids)
                mids += list(cands[:needed])
            else:    
                mids = mids[:num_mid]
        
            exclude_pks = [el.pk for el in (tops + mids)]
            lows = list(base.exclude(pk__in=exclude_pks).order_by('-pub_date')[:num_low])
            return [tops, mids, lows]
    
        else:
            top_base = base.exclude(pub_date='2009-03-31')
            tops = list(top_base.filter(position='1').order_by('-pub_date')[:3])
            random.shuffle(tops)
            if len(tops) < num_top:
                cands = base.filter(possible_position='1').order_by('position', '-pub_date')
                cands = cands.exclude(pk__in=[top.pk for top in tops])
                needed = num_top - len(tops)
                tops += list(cands[:needed])
            else:
                tops = tops[:num_top]
        
            exclude_pks = [top.pk for top in tops]
            mids = base.filter(position__in=('1', '2')).exclude(pk__in=exclude_pks).exclude(pub_date='2009-03-31')
            mids = list(mids.order_by('-pub_date'))
            if len(mids) < num_mid:
                cands = base.filter(possible_position__in=('1', '2'))
                exclude_pks += [mid.pk for mid in mids]
                cands = cands.exclude(pk__in=exclude_pks).order_by('-pub_date')
            
                needed = num_mid - len(mids)
                mids += list(cands[:needed])
            else:    
                mids = mids[:num_mid]
        
            exclude_pks = [el.pk for el in (tops + mids)]
            lows = list(base.exclude(pk__in=exclude_pks).exclude(pub_date='2009-03-31').order_by('-pub_date')[:num_low])
            return [tops, mids, lows]
        '''
    
    def get_top_story(self):
        """
        Returns a random article with is_topstory set. (Most of the time,
        there will only be one.)
        """
        return self.get_stories(num_top=1, num_mid=0, num_low=0)[0][0]
    
    def get_recent_multimedia(self, base=None, exclude=None, num_stories=3):
        """
        Gets a recent picture out of `base`/self; will not include any that
        are in `exclude`. Returns (story, image).
        """
        # TODO: favor big images in get_recent_multimedia?
        # TODO: add video support to get_recent_multimedia
        if not base:
            base = self
        
        exclude = [i.pk for i in exclude] if exclude else []        
        stories = base.order_by('-pub_date')
        
        images = []
        article_counter = 0
        
        prepend = lambda a, lst: [(a, x) for x in lst]
        
        for story in stories:
            article_counter += 1
            
            images += prepend(story, story.images.all().exclude(pk__in=exclude))
            
            try:    photospread = story.photospread
            except ObjectDoesNotExist: pass
            else:   images += prepend(story, photospread.photos.all().exclude(pk__in=exclude))
            
            if story.main_image:
                images.append((story, story.main_image))
            
            if images and article_counter % num_stories == 0:
                return random.choice(images)
        
        # went through all the stories...
        return (None, None)
    

class Article(models.Model):
    """
    A story or other article to be published. Includes news stories,
    editorials, etc, but not announcements or jobs.
    
    Stores major revisions of the article: whatever the author decides to
    save manually while writing, changes editors make afterwards, and then
    any changes made after publication. Comments can (and should) be attached
    to these revisions.
    """
    
    headline    = models.CharField(max_length=200, help_text="Main headline.")
    short_title = models.CharField(blank=True, max_length=40,
        help_text="For the front page; keep it *short*. Only needed if the main headline is long.")
    slug        = models.SlugField(unique_for_date="pub_date", max_length=100,
        help_text="Example: global-neighbors, strong-endowment-in-recession. It's part "
                  "of the article's URL: daily.swarthmore.edu/year/month/day/slug/.")
    
    concept = models.ForeignKey(StoryConcept, null=True, blank=True, related_name="articles",
        help_text="If this story was assigned via a Story Concept, pick which one so we know you've started work on it.")
    
    summary = models.TextField()
    short_summary = models.CharField(max_length=210, blank=True, help_text="For the front page...make it look good! [max 210 chars]")
        
    text = models.TextField(blank=True, help_text="""
    Links: &lt;a href="URL"&gt;Link text&lt;/a&gt;<br />
    Placing images: &lt;div class="alignment size"&gt;&lt;img src="img://bucket/slug/size"
                    /&gt;by Photographer&lt;/div&gt;<br />
    &nbsp;&nbsp;Alignment: either imgLeft or imgRight<br />
    &nbsp;&nbsp;Size: zero through fifty, in increments of five (ex. thirtyfive)<br />
    &nbsp;&nbsp;Bucket and Slug: From a previously uploaded image<br />
    &nbsp;&nbsp;Photographer: Add the photographer's name.<br />
    Italics: _italicized text_<br />
    Bold: *bold text*
    """)
    
    format = models.CharField(max_length=1, choices=formats.FORMAT_CHOICES, default='t')
    
    pub_date = models.DateTimeField(default=datetime.datetime.now)
    authors  = models.ManyToManyField(UserProfile, related_name="articles", through='Writing')
    section = models.ForeignKey('articles.Section', related_name="articles")
    subsection = models.ForeignKey('articles.Subsection', related_name="articles", null=True, blank=True)
    
    highlighters = models.ManyToManyField(UserProfile, related_name='top_stories', through='Highlighting')
    
    main_image = models.ForeignKey(ImageFile, null=True, blank=True,
                related_name="articles_with_main",
                help_text="The image to use on the frontpage (if it's a top story), in issues (if it's the main story in the issue), archive pages, etc.")
    
    media  = models.ManyToManyField(MediaFile, related_name="articles", blank=True)
    images = models.ManyToManyField(ImageFile, related_name="articles", blank=True)
    
    comments = generic.GenericRelation(PublicComment,
                                       content_type_field='subject_type',
                                       object_id_field='subject_id')
    
    is_racy = models.BooleanField(default=False,help_text="If checked, will not appear on the faculty dashboard.")
    is_special = models.BooleanField(default=False, help_text="Whether this should show up on the specials bar.")
    
    STATUS_CHOICES = (
        ('d', 'Draft'),
        ('e', 'Pending Review'),
        ('a', 'Edited (1)'),
        ('b', 'Edited (2)'),
        ('p', 'Published'),
        ('h', 'On Hold'),
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='d')
    
    comments_allowed = models.BooleanField(default=True)
    swat_only = models.TextField(blank=True,
            help_text="If empty, not Swat-only; if there's text, show that text "
                      "to non-Swat visitors instead. (Rendered w/ textile.)")
    
    POSITION_CHOICES = (
        ('3', 'low'),
        ('2', 'middle'),
        ('1', 'top')
    )
    position = models.CharField(max_length=1, choices=POSITION_CHOICES, default=3)
    
    objects = models.Manager()
    published = PublishedArticlesManager()
    
    def get_comments(self):
        return self.comments
    
    def get_title(self):
        "Returns the shortest complete headline available."
        return self.short_title or self.headline
    
    def get_short_title(self, min_diff=8, length=50):
        "Returns a headline of length between `length` and `length`-`min_diff`."
        return self.short_title or smart_truncate(self.headline, length, min_diff)
    
    def shortest_summary(self):
        """Returns short_summary if we have it, else summary."""
        return (self.short_summary or self.summary)
    
    def get_short_summary(self):
        return self.short_summary or smart_truncate(self.summary, 210)
    
    def is_photospread(self):
        try:
            self.photospread
            return True
        except ObjectDoesNotExist:
            return False
    
    def allow_edit(self, user):
        return self.authors.filter(user__pk=user.pk).count() > 0 \
            or user.has_perm('articles.change_article');
    
    def add_author(self, *authors):
        for author in authors:
            Writing.objects.create(article=self, user=author)
    
    def text_at_revision(self, revision):
        """Returns the text as it was at the specified revision."""
        if revision.article != self:
            raise RelationshipMismatch()
        d = diff_match_patch()
        rewound = self.text
        for r in self.revisions.filter(date__gte=revision.date):
            rewound = d.patch_apply(d.patch_fromText(r.delta), rewound)[0]
        return rewound
    
    def revise_text(self, revised_text, reviser=None):
        if reviser is None:
            try:
                reviser = self.authors_in_order().all()[0]
            except IndexError:
                # TODO: better error handling when there's no authors
                reviser = None
        d = diff_match_patch()
        patch = d.patch_toText(d.patch_make(revised_text, self.text))
        
        ArticleRevision.objects.create(article=self, delta=patch, reviser=reviser)
        self.text = revised_text
        self.save()
    
    
    def formatted_text(self, revision=None):
        text = self.text_at_revision(revision) if revision else self.text
        formatter = formats.FORMAT_FUNCS[self.format]
        return formatter(text)
    
    _media_link = re.compile(r'^(?:(img|media)://)?([-\w]+)/([-\w]+)(?:/([-\w]+))?/?$',
                             re.IGNORECASE)
    def resolved_text(self, revision=None):
        """
        Formats the text (at the revision specified by ``revision``, if
        passed) and then goes through and replaces the image references within
        it to links that will actually work.
        """
        text = self.formatted_text(revision)
        if self.media.count() > 0 or re.search("<(a|img)", text, re.IGNORECASE):
            soup = BeautifulSoup(text)
            
            for image in soup.findAll("img", src=self._media_link):
                image['src'] = self.resolve_media_link(image['src'])
            for a in soup.findAll("a", href=self._media_link):
                a['href'] = self.resolve_media_link(a['href'], required_scheme=True)
            return unicode(soup)
        else:
            return text
    
    def resolve_media_link(self, path, complain=False, required_scheme=False):
        """
        Turns relative image links in articles into absolute URLs. For
        example, if an article has "<img src='some-bucket/cool-pic'/>",
        ``resolved_text`` will call this function to replace 'cool-pic' with
        '/files/some-bucket/cool-pic'.
        
        We can also use "img://bucket/slug"; this is the required format
        in a link to an image (<a href="...">). Use "media://" if you want
        a MediaFile.
        """
        match = self._media_link.match(path)
        if not match:
            return path
        
        scheme, bucket_slug, slug, size = match.groups()
        if required_scheme and not scheme:
            return path
        
        m2m  = self.media if scheme == "media" else self.images
        model = MediaFile if scheme == "media" else ImageFile
        
        try: # self.media should be cached, so we try it first
            media = m2m.get(bucket__slug=bucket_slug, slug=slug)
        except model.DoesNotExist:
            try:
                media = model.objects.get(bucket__slug=bucket_slug, slug=slug)
                m2m.add(media)
            except model.DoesNotExist:
                try:
                    media = model.objects.get(bucket__slug='articles', slug=slug)
                    m2m.add(media)
                except model.DoesNotExist:
                    if complain:
                        raise
                    else:
                        return ""

        if not size:
            return media.get_absolute_url()
        else:
            try:
                int_size = int(size)
            except ValueError:
                return media.get_absolute_url()
            else:
                if int_size <= 25:
                    return media.storytwentyfive.url
                elif int_size <= 50:
                    return media.storyfifty.url
                else:
                    return media.storyhundred.url

    
    def related_list(self, num=None):
        """Returns a QuerySet of related stories."""
        # TODO: improve related_list
        rel = self.section.published_articles().exclude(pk=self.pk).order_by('-pub_date')
        return rel[:num] if num else rel
    
    def authors_in_order(self):
        return self.authors.order_by('writing___order')
    
    def author_names(self):
        return join_authors(self.authors_in_order(), 'ptx')
    
    def section_if_special(self):
        """
        Returns the name of the subsection if it's special, 
        section if that's special, else None.
        """
        if self.subsection and self.subsection.is_special:
            return self.subsection.name
        elif self.section.is_special:
            return self.section.name
        else:
            return None

    def sub_if_special(self):
        if self.subsection and self.subsection.is_special:
            return self.subsection.name
        else:
            return None
    
    def sub_or_sec(self):
        return self.subsection or self.section
    
    def update_concept_status(self):
        concept = self.concept
        if concept:
            concept.status = ('p' if self.status == 'p' else 'a')
            for author in self.authors.all():
                concept.users.add(author)
            concept.save()
    
    def ensure_special_exists(self):
        if self.is_special and self.status == 'p' and self.main_image:
            title = self.get_title()[:80]
            if self.is_photospread():
                category = 'p'
            elif self.subsection and self.subsection.is_column():
                category = 'c'
            else:
                category = 'f'
            
            ct = ContentType.objects.get_for_model(self.__class__)
            special, created = Special.objects.get_or_create(
                target_type=ct,
                target_id=self.pk,
                defaults=dict(
                    title=title,
                    date=self.pub_date,
                    image=self.main_image,
                    category=category
                )
            )
            if not created and not (special.image and special.title and special.category):
                special.image = special.image or self.main_image
                special.title = special.title or title
                special.category = special.category or category
                special.save()
    
    def is_swat_only(self):
        return bool(self.swat_only.strip())
    
    def non_swat_text(self):
        if not self.is_swat_only():
            raise Exception("this article isn't swat-only")
        return formats.textile(self.swat_only)
    
    def __unicode__(self):
        return "%s (%s)" % (self.slug, self.pub_date.date())
    
    @models.permalink
    def get_absolute_url(self):
        d = self.pub_date
        return ('article', None, {
            'year':  str(d.year),
            'month': str(d.month),
            'day':   str(d.day),
            'slug':  self.slug
        })
    
    class Meta:
        app_label = 'articles'
        get_latest_by = 'pub_date'
    

# NOTE: concept updating is a little weird with the admin, because it
#       saves related authors after post_save signals are called, so new
#       authors don't exist when this gets run. not generally a big deal,
#       as it's unimportant and stories usually get saved a lot anyway
_update_concept = lambda sender, instance, **kwargs: instance.update_concept_status()
models.signals.post_save.connect(_update_concept, sender=Article)

_ensure_special = lambda sender, instance, **kwargs: instance.ensure_special_exists()
models.signals.post_save.connect(_ensure_special, sender=Article)


class Writing(models.Model):
    """
    Represents an author's having written a story.
    
    Its main purpose is to allow for ordering the authors.
    """
    article = models.ForeignKey(Article)
    user    = models.ForeignKey(UserProfile)
    
    class Meta:
        order_with_respect_to = 'article'
        unique_together = ('article', 'user')
        app_label = 'articles'
    
    def __unicode__(self):
        return "%s wrote %s" % (self.user.username, self.article.slug)
    

class Highlighting(models.Model):
    """
    Represents an author's having chosen to highlight a story on 
    their profile page.
    
    Mainly to allow for ordering.
    """
    article = models.ForeignKey(Article)
    user = models.ForeignKey(UserProfile)
    
    class Meta:
        order_with_respect_to = 'article'
        unique_together = ('article', 'user')
        app_label = 'articles'
    
    def __unicode__(self):
        return "%s highlited %s" % (self.user.username, self.article.slug)
    

class ArticleRevision(models.Model):
    """
    A revision of an article. Only deltas are stored.
    
    Note that the most recent text is stored in the article's text attribute,
    while earlier versions are stored as revisions...as such, these are 
    "reverse diffs." For example, if an article has versions 1, 2, and 3, 
    version 3 is stored directly with the article, and there are 
    ArticleRevisions to go from 3 to 2 and from 2 to 1.
    """
    article = models.ForeignKey(Article, related_name='revisions')
    reviser = models.ForeignKey(UserProfile, related_name='revisions')
    delta   = models.TextField()
    date    = models.DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        ordering = ['-date']
        app_label = 'articles'
    
    def __unicode__(self):
        return u"%s - %s" % (self.article.slug, self.date)
    
