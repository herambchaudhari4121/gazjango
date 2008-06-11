import unittest
from django.contrib.auth.models import User, Permission
from articles.models            import Article, ArticleRevision, Category
from accounts.models            import UserProfile

class ArticleTestCase(unittest.TestCase):
    
    def setUp(self):
        self.bob = User.objects.create_user("bob", 'bob@example.com')
        self.bob.userprofile_set.add(UserProfile())
        self.bob_profile = self.bob.get_profile()
        
        self.news = Category.objects.create(name="News")
        self.boring_article = Article.objects.create(headline = "...Boring",
                                                     text     = "Boring Text",
                                                     slug     = 'boring',
                                                     category = self.news)
    
    def tearDown(self):
        for m in (User, UserProfile, Category, Article, ArticleRevision):
            m.objects.all().delete()
    
    def test_articles_empty(self):
        self.assertEquals(len(self.bob_profile.articles.all()), 0)
        self.assertEquals(len(self.boring_article.authors.all()), 0)
    
    def test_article_creation(self):
        self.bob.get_profile().articles.add(self.boring_article)
        self.assert_(self.boring_article in self.bob_profile.articles.all())
        self.assert_(self.bob_profile in self.boring_article.authors.all())
        self.assertTrue(self.boring_article.allow_edit(self.bob))
    
    def test_article_revision(self):
        a = self.boring_article
        strs = (a.text,
                "Boring Text (!)", 
                "Boring Text (with some boring revisions)",
                "Lame-Text-Extreme (with moderately less-boring revisions made)")
        
        for i in range(1, len(strs)):
            a.revise_text(strs[i])
            self.assertEquals(a.text, strs[i])
            rs = a.revisions.reverse()
            for j in range(i):
                self.assertEquals(a.text_at_revision(rs[j]), strs[j])
    

