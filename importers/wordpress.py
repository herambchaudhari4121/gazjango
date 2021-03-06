#!/usr/bin/env python

import MySQLdb as db
from optparse import OptionParser
import os, os.path, sys, re

sys.path.extend([os.path.abspath(x) for x in (
    '..',
    '../gazjango',
    os.path.join(__file__, '..'),
    os.path.join(__file__, '../gazjango'),
)])

import settings
import django.core.management
django.core.management.setup_environ(settings)

import datetime
import urllib2
import django.db
import django.utils.text
import django.utils.html
import django.template.defaultfilters
from django.contrib.auth.models         import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models        import Site
from gazjango import tagging

from gazjango.accounts.models      import UserProfile, UserKind, Position
from gazjango.accounts.models      import ContactMethod, ContactItem
from gazjango.announcements.models import Announcement
from gazjango.articles.models      import Article, PhotoSpread, Format
from gazjango.articles.models      import Section, Subsection, Column
from gazjango.articles.models      import Special, SpecialsCategory, DummySpecialTarget
from gazjango.comments.models      import PublicComment
from gazjango.issues.models        import Issue, Menu, Weather, WeatherJoke, Event
from gazjango.media.models         import MediaFile, ImageFile, MediaBucket
from gazjango.polls.models         import Poll, Option, PollVote
from gazjango.jobs.models          import JobListing

from gazjango.scrapers import BeautifulSoup
from collections import defaultdict



# =========================
# = Miscellaneous Helpers =
# =========================

def all_in(haystack, needles):
    return all(map(lambda x: x in haystack, needles))

def merge(d, oth):
    copy = d.copy()
    for key, val in oth.items():
        copy[key] = val
    return copy


# =======================
# = Database Connection =
# =======================

parser = OptionParser()
parser.add_option("-H", "--host",     dest="host",   help="connect to HOST",      metavar="HOST",   default="localhost")
parser.add_option("-u", "--user",     dest="user",   help="authenticate as USER", metavar="USER",   default="root")
parser.add_option("-p", "--passwd",   dest="passwd", help="using PASSWD",         metavar="PASSWD", default="")
parser.add_option("-d", "--database", dest="db",     help="use database DB",      metavar="DB",     default="gazette_daily")
(options, args) = parser.parse_args()

if options.passwd == '-':
    print "db password: ",
    password = raw_input()
else:
    password = options.passwd

print "connecting to the old db..."
conn = db.connect(
    host=options.host,
    user=options.user,
    passwd=password,
    db=options.db
)

cursor = conn.cursor()

# ==========================
# = Flush the Old Database =
# ==========================

print "flushing database..."
u = django.core.management.ManagementUtility(['fakery', 'flush', '--noinput'])
u.execute()

# ========
# = Site =
# ========
print "making site object..."

Site.objects.all().delete()
site = Site.objects.create(name="The Daily Gazette", domain="daily.swarthmore.edu", pk=1)


# =========
# = Pages =
# =========
print "making static pages..."

about = site.page_set.create(
    url="/about/",
    title="About Us",
    content="""
The Daily Gazette is Swarthmore's only daily newspaper. The Gazette is sent out every work-day to more than 2,500 people, making it the most highly circulated paper at Swarthmore College.

The paper was founded in 1996 by Sam Schulhofer-Wohl '98 with the goal of providing timely coverage of campus news and Garnet sports while maintaining complete independence from the administration and student government. The only possible way to achieve this goal was through the Internet. We have retained the distinction of being a web-only institution, which has allowed us the ability to change and remain a cutting edge publication.

In Spring 2008, The Daily Gazette was named one of the top five online college news sites by the Associated Collegiate Press.

<strong>Current Staff</strong>
<strong>Editorial Board</strong>
Miles Skorpen, Editor-in-Chief
Lauren Stokes, Editor-in-Chief
Ramya Gopal, News Editor
Urooj Khan, Features Editor
Daisy Yuhas, Arts Editor
Carolyn Whipple, Photography Editor
Dougal Sutherland, Technology Director
Rio Akasaka, Business Director
Michael May, Asst. Business Director

<strong>Senior Staff</strong>
Neena Cherayil
Myles Dakan
Todd Friedman
Allison McCarthy
David Pupkin
Vy Vo

<strong>Staff</strong>
Gabriel Ramirez
Kara Stoever
Dante Fuoco
Kimberly St. Julian
Allie Lee
Angela Meng
Amelia Possanza
Alex Friedfeld
Kristen Allen
Tasha Lewis
Michelle
Rebecca

<h3>SITE INFORMATION</h3>

This site is built on using <a href="http://www.djangoproject.com/">Django</a>, an open-source Python web framework designed for newspapers. The site was developed by Dougal Sutherland '11 with layout by Miles Skorpen '09 in 2008.

<h3>HISTORY</h3>

The Daily Gazette was organized during fall semester 1996 by Sam Schulhofer-Wohl '98. The goal: to provide timely coverage of campus news and Garnet sports while maintaining complete independence from the administration and student government. Printing the Gazette every day would have been prohibitively expensive and time-consuming, so the board of editors elected to distribute the Gazette via e-mail. At first, there was no World Wide Web edition; however, back issues were available through the web.

The first Board of Editors consisted of Fred Bush '98, Kate Doty '00, Jennifer Klein '98, David Lischer '97, Eric Pakurar '97, Sylvia Weedman '97 and Sam Schulhofer-Wohl. Publication began during the first week of spring semester 1997. Midway through that semester, Rafi Dowty '98 joined the staff as weatherman after successfully lobbying for the addition of weather reports. At the end of the semester the Gazette had 512 subscribers.

The milestones have flown by. In February 1998, the number of subscribers surpassed 1000 for the first time. By the beginning of Fall '00 the number had risen to nearly 1500. In 2002-2003, the Gazette undertook such projects as installing Reading Racks in campus bathrooms and chalking the entire April Fool's issue on the college sidewalks on a bitterly cold March 31st night. In 2003, Jeremy Schifeling '03 became the first Gazette Editor to receive the Drew Pearson Prize for Journalism.

As the Gazette began its tenth year of publication in August of 2005, the subscriber list topped 1900 for the first time. In 2006, Managing Editor Alex Glick '06 was awarded Swarthmore's Pearson Prize. By 2007, subscriptions broke 2,300 and the Daily Gazette became the most circulated student publication at Swarthmore. Micaela Baranello '07 was awarded the Pearson Prize, the fourth Gazette staffer so honored.

In Fall, 2007, Lauren Stokes '09 and Miles Skorpen '09 oversaw the Gazette's transition to its first content management system, WordPress, adding comments and columns to the website. Nearly 6,000 unique visitors come the Gazette site every week. Miles Skorpen '09 was awarded the Pearson Prize, and the Gazette was named one of the five top news sites in the nation by the Associated Collegiate Press.

Throughout the Fall of 2008, Technology Director Dougal Sutherland '11 spearheaded a development team to create a custom site for the Gazette using Django. The current site is the fruit of his labors.

<h3>STAFF LISTING</h3>

2008-2009
<strong>Editorial Board</strong>
Miles Skorpen
Lauren Stokes
Ramya Gopal
Urooj Khan
Daisy Yuhas
Carolyn Whipple
Dougal Sutherland
Rio Akasaka

<strong>Staff</strong>
Neena Cherayil
Myles Dakan
Todd Friedman
Allison McCarthy
David Pupkin
Vy Vo
Gabriel Ramirez
Kara Stoever
Dante Fuoco
Kimberly St. Julian
Allie Lee
Angela Ming
Amelia Possanza
Alex Friedfeld

2007-2008
<strong>Editorial Board</strong>
Miles Skorpen
Lauren Stokes
Ramya Gopal
Urooj Khan
Daisy Yuhas
Carolyn Whipple
Dougal Sutherland
Rio Akasaka
Myles Dakan


<strong>Staff</strong>
Neena Cherayil
Todd Friedman
Allison McCarthy
David Pupkin
Vy Vo
Sara Forster
Shilpa Boppana
Zoe Davis
Finlay Logan
Mark Kharas

2006-2007
<strong>Editorial Board</strong>
Miles Skorpen
Lauren Stokes
Daisy Yuhas
Andrew Quinton
Micaela Baranello

<strong>Staff</strong>
Neena Cherayil
Myles Dakan
Todd Friedman
Allison McCarthy
David Pupkin
Vy Vo
Sara Forster
Shilpa Boppana
Zoe Davis
Finlay Logan
Mark Kharas
Urooj Khan
"""
)

policies = site.page_set.create(
    url="/policies/",
    title="Policies",
    content="""
<h2>Policies and Procedures</h2>

<p>Last revised June 28, 2008</p>

<h4>What information does the Gazette record, and what do you do with it? </h4>

<p><strong>From browsing</strong>: We record the IP address, the browser, the operating system, and the origin of all those who browse our site. If you are logged in, this information will be associated with your username. In addition, we keep track of the specific pages browsed, and the path of discovery (what links did you click to get to the content), but this browsing record is <strong>not</strong> stored linked to your username. This information will not be released to non-Gazette staff except at the request of the CJC. With an IP address, the College would be able to link browsing to specific users of the Swarthmore network.<br />

<strong>From comments</strong>: Every comment is associated with an IP address, and the email address of the user is visible to any member of our Editorial staff. As with browsing history, we will release this information to the Deans at the request of the CJC. With an IP address, the College can identify any user of its network within a limited time frame (currently approximately 1 month.)</p>

<p>Every 30 days, we will compile our records for statistic purposes, and individual users will not be identifiable.</p>

<p>We are not a business. No information collected by The Daily Gazette will be given to commerical third parties. We are 100% against spam (unsolicited commerical mail). Information on our visitors is collected solely for self-study, to help in the development of the Gazette. Only editor-level staff will have access to individualized tracking.</p>

<p>If you believe you have received spam from the Gazette, let us <a href="mailto:editor@daily.swarthmore.edu">know</a>.


<h4>How does the Gazette deal with errors and corrections?</h4>

<p>For non-substantial spelling or editing corrections, the Gazette will make the change in article.<br />
For name or title errors, the article will be corrected and a correction made at the bottom of the article.<br />
For substanial factual errors, the Gazette will make and note the change in the article, and publish a correction.</p>


<h4>What are the details of the Gazette's comment moderation policy? </h4>

<p>The Gazette relies on user moderation to show and hide the best (and worst) comments for every story. The number of votes required to hide a story is revealed by the table below. In short, posting from a Swarthmore IP address or being logged in makes it significantly harder for your comment to be moderated.</p>

<table width="340" height="134" border="0" cellpadding="0" cellspacing="0">
  <tr>
	<th width="66" scope="col">Votes</th>
	<th width="97" scope="col">Swat IP</th>
	<th width="177" scope="col">User</th>
  </tr>
  <tr>
	<td align="right">3</td>
	<td align="center" bgcolor="#FF0066"><div align="center">No</div></td>
	<td bgcolor="#FF0066"><div align="center">No</div></td>
  </tr>
  <tr>
	<td align="right">4</td>
	<td bgcolor="#999966"><div align="center">Yes</div></td>
	<td bgcolor="ff0066"><div align="center">No</div></td>
  </tr>
  <tr>
	<td align="right">5</td>
	<td bgcolor="ff0066"><div align="center">No</div></td>
	<td bgcolor="999966"><div align="center">Yes</div></td>
  </tr>
  <tr>
	<td align="right">6</td>
	<td bgcolor="999966"><div align="center">Yes</div></td>
	<td bgcolor="999966"><div align="center">Yes</div></td>
  </tr>
</table>

<p>The number of votes given to a user also changes based on their status at the Gazette's website. Any viewer who is not logged in receives one vote. Users receive two votes, while Swarthmore-based users receive three votes. Any member of the Gazette's staff receives four votes, while all Editors can show or hide comments at will.</p>
<p>The IP address and the username of the voter is attached to every vote. Abuse of this privilege could lead to loss of voting rights.</p>

<h4>How does the Gazette's staff judge comments?</h4>

<p>Our rules are fairly straightforward:</p>
<ul>
    <li>Be nice</li>
	<li>Be constructive</li>
	<li>Don't curse</li>
	<li>Don't threaten</li>
</ul>

<p>Our first two rules are the heart of our comments policy. Comments should never be hostile to the author of a story or another commentor--but we welcome active debate, discussion, and deconstruction of our stories. We will not quash substantial comments.</p>


<p>However, only in the most extreme cases will the Gazette delete comments. Our moderation system is designed to hide undesirable content, but not to make it absolutely inaccessible. We will only regularly delete comments if they are believed to be spam.</p>    
"""
)

contact = site.page_set.create(
    url="/about/contact/",
    title="Contact Us",
    content="Email us at <span style=\"font-family: monospace;\">dailygazette at swarthmore dot edu</span>.",
    parent=about
)

employment = site.page_set.create(
    url="/join/",
    title="Employment",
    content="If you show up to meetings, or even if you don't, you can probably write for us."
)


# ==========
# = Groups =
# ==========
print "making user groups..."

reader_group       = Group.objects.create(name="Readers")
ex_staff_group     = Group.objects.create(name="Ex-Staff")
reporter_group     = Group.objects.create(name="Reporters")
photographer_group = Group.objects.create(name="Photographers")
copy_editor_group  = Group.objects.create(name="Copy Editors")
editor_group       = Group.objects.create(name="Editors")
admin_group        = Group.objects.create(name="Admins")

ct = ContentType.objects.get_for_model(PublicComment)

reader_group.permissions.add(
    Permission.objects.get(content_type=ct, codename='can_post_directly')
)

ab = Permission.objects.get(content_type=ct,codename='can_moderate_absolutely')
for g in (editor_group, admin_group):
    g.permissions.add(ab)



# ==============
# = User Kinds =
# ==============
print "making user kinds..."

generic_student = UserKind.objects.create(kind='s')
generic_alum    = UserKind.objects.create(kind='a')
faculty_staff   = UserKind.objects.create(kind='f')
parent          = UserKind.objects.create(kind='p')
spec            = UserKind.objects.create(kind='k')
other           = UserKind.objects.create(kind='o')


# =============
# = Positions =
# =============

print "making positions..."
# we'll need to manually assign these
reader          = Position.objects.create(name="Reader",             rank=0)
swat_reader     = Position.objects.create(name="Swarthmore Reader",  rank=1)
columnist       = Position.objects.create(name="Columnist",          rank=4)
guest_writer    = Position.objects.create(name="Guest Writer",       rank=4)
reporter        = Position.objects.create(name="Staff Reporter",     rank=5)
photographer    = Position.objects.create(name="Staff Photographer", rank=5)
tech_director   = Position.objects.create(name="Technical Director", rank=8,  is_editor=True)
news_editor     = Position.objects.create(name="News Editor",        rank=9,  is_editor=True)
arts_editor     = Position.objects.create(name="Arts Editor",        rank=9,  is_editor=True)
features_editor = Position.objects.create(name="Features Editor",    rank=9,  is_editor=True)
photo_editor    = Position.objects.create(name="Photography Editor", rank=9,  is_editor=True)
editor_in_chief = Position.objects.create(name="Editor-In-Chief",    rank=10, is_editor=True)


# ===================
# = Contact Methods =
# ===================

print "making contact methods..."

cell  = ContactMethod.objects.create(name="Cell Phone")
phone = ContactMethod.objects.create(name="Phone")
yim   = ContactMethod.objects.create(name="Yahoo")
aim   = ContactMethod.objects.create(name="AIM")
gtalk = ContactMethod.objects.create(name="GTalk / Jabber")
msn   = ContactMethod.objects.create(name="MSN")


# =========
# = Users =
# =========

print "importing users..."

staff_groups = set([reporter_group, photographer_group, copy_editor_group,
                    editor_group, admin_group])

users = {}
cursor.execute("SELECT ID, user_nicename, user_email, display_name FROM gazette_users")
while True:
    row = cursor.fetchone()
    if row is None:
        break
    old_id, username, email, display_name = row
    
    users[int(old_id)] = defaultdict(lambda:"",
                                     username=username.replace('-', '_'),
                                     email=email,
                                     display_name=display_name
                                     )

cursor.execute("SELECT user_id, meta_key, meta_value FROM gazette_usermeta WHERE NOT meta_key IN ('rich_editing', 'admin_color', 'closedpostboxes_post', 'gazette_autosave_draft_ids')")
capabilities_regex = re.compile(r's:\d+:\"(?P<id>\w+)\";b:1;')
while True:
    row = cursor.fetchone()
    if row is None:
        break
    old_id, key, val = row
    if key == "gazette_capabilities":
        val = capabilities_regex.findall(val)
    users[old_id][key] = val

for id in users:
    u = users[id]
    groups = [reader_group]
    caps = u["gazette_capabilities"]
    if "administrator" in caps:
        groups.append(admin_group)
    if "reader" in caps:
        groups.append(reader_group)
    if "reporter" in caps or "reporters" in caps:
        groups.append(reporter_group)
    if "photographer" in caps:
        groups.append(photographer_group)
    if "editor" in caps:
        groups.append(editor_group)
    if "old_writers" in caps:
        groups.append(ex_staff_group)
    
    new_user = User.objects.create_user(u['username'], u['email'])
    if u['first_name'] or u['last_name']:
        new_user.first_name = u['first_name']
        new_user.last_name  = u['last_name']
    else:
        split = u['display_name'].split(None, 1)
        if len(split) == 1:
            split += ['']
        new_user.first_name, new_user.last_name = split
    new_user.is_staff = bool(set(groups).intersection(staff_groups))
    new_user.groups = groups
    new_user.save()
    
    profile = UserProfile.objects.create(
        user=new_user,
        bio=u['description'], 
        kind=generic_student
    )
    
    for name, method in (('aim', aim), ('jabber', gtalk), ('yim', yim)):
        if name in u:
            profile.contact_items.create(method=method, value=u[name])
    
    u["new_id"] = new_user.id


# admin user
admin = User.objects.create_user('__admin__', 'dailygazette@swarthmore.edu')
admin.first_name = 'The'
admin.last_name  = 'Daily Gazette'
admin.is_staff = True
admin.is_superuser = True
admin.set_password('test')
admin.save()
admin.userprofile_set.create()

# ============
# = Sections =
# ============

print "making sections..."

sec = lambda n, s, d, x=False: Section.objects.create(name=n, slug=s, description=d, is_special=x)
sub = lambda p, n, s, d: Subsection.objects.create(section=p, name=n, slug=s, description=d)

news = sec("News", "news", "What's going on in the world.")
students = sub(news, "Students",        "students", "Swarthmore students and their exploits.")
facstaff = sub(news, "Faculty & Staff", "facstaff", "About Swarthmore faculty and staff.")
alumni   = sub(news, "Alumni",          "alumni",   "What ex-Swarthmore students go on to do.")

features = sec("Features", "features", "The happenings around town.")
atg     = sub(features, "Ask the Gazette", "atg",             "The Gazette answers the questions you have.")
roundup = sub(features, "Weekend Roundup", "weekend-roundup", "What's going on each weekend.")

athletics = sec("Athletics", "athletics", "Swarthmore's athletes.")
opinions_and_columns = sec("Opinions & Columns", "opinions", "What the community has to say.")
editorials = sub(opinions_and_columns, "Staff Editorials", "editorials", "Opnions from the Gazette's editorial board.")
multimedia = sec("Multimedia", "multimedia", "Pictures and videos.")

platforms = sub(features, "Student Council Platforms", "stuco-platforms", "Platforms for student council elections.")


# ===========
# = Formats =
# ===========

print "making formats..."

html    = Format.objects.create(name="Raw HTML", function="html")
textile = Format.objects.create(name="Textile",  function="textile")


# ========
# = Tags =
# ========

print "making tags..."

special = tagging.models.TagGroup.objects.create(name="*Specials*")
orgs    = tagging.models.TagGroup.objects.create(name="Organizations")
depts   = tagging.models.TagGroup.objects.create(name="Departments")
places  = tagging.models.TagGroup.objects.create(name="Places")
people  = tagging.models.TagGroup.objects.create(name="People")

arts = special.tags.create(name="Living & Arts")
april_fools = special.tags.create(name="April Fools")

os = ("Amnesty International", "Anime & Manga Club", "ARC", "Ballroom & Swing Club", "Boy Meets Tractor", "Cantatrix", "Chabad", "Chaverim", "Chess Club", "Club Despertar", "College Democrats", "College Republicans", "CSC", "Cycling Club", "Daily Gazette", "Dance Forum", "Dare To Soar", "DESHI", "Drama Board", "Earthlust", "Enie", "ENLACE", "Feminist Majority", "FFS", "Folk Dance", "Free Culture", "Friends of Taiwan", "Global Health Forum", "Gospel Choir", "Grapevine", "Halcyon", "International Club", "Kitao Gallery", "Knit-Wits", "Learning For Life", "Mixed Company", "Mjumbe", "Mock Trial", "Motherpuckers", "Movie Committee", "MSA", "Multi", "Olde Club", "Outsiders", "Phoenix", "Photo Club", "Psi Phi", "Pun/ctum", "Quiz Bowl", "Rattech", "Rhythm N Motion", "Ruach", "SAC", "SAO", "SASA", "SASS", "SAVE R US", "SBA", "SBC", "SCCS", "SCF", "SCW", "SEA", "SHC", "SHIP", "Sixteen Feet", "SOCA", "Sound Machine", "SPC", "SPPC", "Spike Magazine", "SOFI", "SQU", "SSSL", "Student Council", "Swarthmore Good Food Project", "Swarthmore Massage", "Swarthmore Sudan", "Swat VOX", "Class Activists", "Van Coordinator", "Vertigo-go", "WRC", "WSRN")
for org in os:
    orgs.tags.create(name=org)

ds = ('Arabic', 'Art and Art History', 'Asian Studies', 'Astronomy', 'Biology', 'Black Studies', 'Chemistry and Biochemistry', 'Chinese', 'Classics', 'Cognitive Science', 'Comparative Literature', 'Computer Science', 'Dance', 'Economics', 'Educational Studies', 'Engineering',  'English Literature',  'Environmental Studies',  'Film and Media Studies',  'French',  'Gender and Sexuality Studies',  'German',  'German Studies',  'History',  'Interpretation Theory',  'Islamic Studies',  'Japanese',  'Latin American Studies',  'Linguistics',  'Mathematics and Statistics',  'Medieval Studies',  'Music',  'Peace and Conflict Studies',  'Philosophy',  'Physics',  'Political Science',  'Psychology',  'Public Policy',  'Religion',  'Russian',  'Sociology and Anthropology',  'Spanish',  'Theater')
for dept in ds:
    depts.tags.create(name=dept)

ps = ('Alice Paul', 'Amphitheater', 'Beardsley', 'Dana', 'David Kemp', 'Hallowell', 'Hicks', 'Kohlberg', 'Kyle', 'Lang Center', 'Lodges', 'LPAC', 'Mary Lyon', 'Mertz', 'Papazian', 'Parrish', 'Palmer', 'Pittenger', 'Roberts', 'SCCS Lounge', 'Science Center', 'Sharples', 'Strath Haven', 'Wharton', 'Willets', 'Woolman', 'Worth')
for place in ps:
    places.tags.create(name=place)

ppl = [('Al Bloom', 'President'), ('Jim Bock', 'Dean of Admissions'), ('Rachel Head', 'Housing Coordinator'), ('Jim Larimore', 'Dean of Students'), ('Martin Warner', 'Registrar'), ('Myrt Westphal', 'Dean of Student Life')]
for name, title in ppl:
    people.tags.create(name=name, long_name=("%s, %s" % (name, title)))


# =========
# = Polls =
# =========

print "importing polls..."

polls = {}
cursor.execute("SELECT pollq_id, pollq_question, pollq_timestamp, pollq_totalvotes, pollq_active, pollq_expiry, pollq_multiple, pollq_totalvoters FROM gazette_pollsq;")
while True:
    row = cursor.fetchone()
    if not row:
        break
    poll_id, question, timestamp, totalvotes, active, expiry, multiple, totalvoters = row
    polls[poll_id] = {
        'question': question,
        'timestamp': timestamp,
        'totalvotes': totalvotes,
        'active': active,
        'expiry': expiry,
        'multiple': multiple,
        'totalvoters': totalvoters,
        'answers': {}
    }


cursor.execute("SELECT polla_aid, polla_qid, polla_answers, polla_votes FROM gazette_pollsa;")
while True:
    row = cursor.fetchone()
    if not row:
        break
    answer_id, poll_id, answer, votes = row
    polls[poll_id]['answers'][int(answer_id)] = {
        'answer': answer,
        'votes': [],
    }


cursor.execute("SELECT pollip_id, pollip_qid, pollip_aid, pollip_ip, pollip_host, pollip_timestamp, pollip_user, pollip_userid FROM gazette_pollsip;")
while True:
    row = cursor.fetchone()
    if not row:
        break
    vote_id, poll_id, answer_id, ip, hostname, timestamp, user, userid = row
    polls[int(poll_id)]['answers'][int(answer_id)]['votes'].append({
        'ip': ip,
        'hostname': hostname,
        'timestamp': timestamp,
        'username': user.replace('-', '_'),
        'old_userid': userid
    })


for data in polls.values():
    date = lambda x: datetime.datetime.fromtimestamp(float(x)) if x else None
    poll = Poll.objects.create(
        name = data['question'],
        question = data['question'],
        slug = django.template.defaultfilters.slugify(data['question'])[:50],
        time_start = date(data['timestamp']),
        time_stop  = date(data['expiry']) or \
                     (None if data['active'] else datetime.datetime.now()),
        allow_anon = True
    )
    data['new_id'] = poll.pk
    for answer_id, answer in data['answers'].items():
        option = poll.options.create(name=answer['answer'])
        for vote in answer['votes']:
            old_id = int(vote['old_userid']) if 'old_userid' in vote else None
            if old_id:
                user = User.objects.get(pk=users[old_id]['new_id']).get_profile()
            else:
                user = None
            try:
                PollVote.objects.create(
                    poll=poll,
                    option=option,
                    user=user,
                    ip=vote['ip'],
                    hostname=vote['hostname'],
                    time=date(vote['timestamp']),
                    name=vote['username']
                )
            except django.db.IntegrityError, e:
                print "duplicate vote on <%s> by <%s>" % (poll, user)


# ===================
# = Posts and Media =
# ===================

print "importing posts..."

posts = {}
media = {}

# wikipedia, which there are a few external image links to, seems to
# not work without this
opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]

def download_file(url, target_dir):
    "Downloads the file at `url` to `target_dir` if it isn't there already."
    pieces = url.split('/')[-1].split('.')
    filename = '.'.join(pieces[:-1])
    ext = pieces[-1]
    
    import os.path
    target_path = os.path.join(target_dir, "%s.%s" % (filename, ext))
    
    # print "would download %s to %s" % (url, target_path)
    # return (filename, ext)
    
    if not os.path.exists(target_path):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        print 'downloading %s...' % url,
        source = opener.open(url)
        target = file(target_path, 'wb')
        # read in chunks, to avoid killing memory
        while True:
            read = source.read(128*1024)
            if not read:
                break
            target.write(read)
        source.close()
        target.close()
        print 'done.'
    return (filename, ext)

def resolve_media(url, article):
    """Takes a url and returns a media object for it."""
    url = url.replace('swatdaily.org', 'daily.swarthmore.edu')
    
    if url not in media:
        slug = article.slug[:50]
        bucket, created = MediaBucket.objects.get_or_create(slug=slug,
            defaults={'name': slug}
        )
        try:
            name, ext = download_file(url, "../gazjango/uploads/%s/" % bucket.slug)
        except urllib2.URLError:
            print "error downloading <%s> for <%s>" % (url, article)
            return url
        
        if re.match(r'jpe?g|png|gif', ext, re.IGNORECASE):
            klass = ImageFile
        else:
            klass = MediaFile
        
        media[url] = klass.objects.create(
            data="%s/%s.%s" % (bucket.slug, name, ext),
            slug=name[:50],
            pub_date=article.pub_date,
            bucket=bucket
        )
    return media[url]


query = "SELECT ID, post_author, post_date, post_title, post_content, post_excerpt, post_name FROM gazette_posts WHERE post_type='post' AND post_status='publish';"
cursor.execute(query)

while True:
    row = cursor.fetchone()
    if row is None:
        break
    old_id, author, date, title, content, excerpt, slug = row
    author
    posts[int(old_id)] = defaultdict(lambda:"",
                                     author=author,
                                     date=date,
                                     title=title,
                                     content=content,
                                     excerpt=excerpt,
                                     slug=slug)

# find the ids of the terms we care about
taxonomy_ids = {}
relevant = ('news', 'features', 'arts', 'sports', 'opinion', 'multimedia',
            'atg', 'weekend-roundup', 'editorials', 'stuco-platforms',
            'announcements', 'gazette-news', 'jobs', 'photos', 'april-fools')
columns = { 'bone-doctor': ('The Bone Doctor',       2007, 2, 'bonedoctor'),
            'denglish':    ('Honors Denglish',       2008, 1, 'lstokes'),
            'argentina':   ('Argentina with Appiah', 2008, 1, 'sappiah'),
            'deviations':  ('Standard Deviations',   2008, 1, 'm'),
            'nautical':    ('Nautical Terminology',  2008, 2, 'galbrig'),
            'henry':       ('Oh, Henry',             2008, 2, 'chris-green'),
            'fringe':      ('The Fringe Moderates',  2008, 2, 'shaun-kelly-and-dustin-trabert'),
            'lowlands':    ('Life in the Lowlands',  2008, 2, 'sgreen'),
            'strokes':     ('Dr. Strokes',           2008, 2, 'drstrokes') }
relevant += tuple(columns.keys())
relevant = ', '.join("'%s'" % slug for slug in relevant)

cursor.execute("SELECT gazette_terms.slug, gazette_term_taxonomy.term_taxonomy_id " +
               "FROM gazette_terms, gazette_term_taxonomy " +
               "WHERE gazette_terms.term_id = gazette_term_taxonomy.term_id " +
               "AND gazette_terms.slug IN (%s) " % relevant +
               "ORDER BY gazette_term_taxonomy.taxonomy DESC")
# ordering is because there's both a post_tag and a category referring to
# the same term (#18) for athletics, and we want the category, not the tag
while True:
    row = cursor.fetchone()
    if not row:
        break
    slug, taxonomy_id = row
    taxonomy_ids[slug] = taxonomy_id

section_lookup = {
    taxonomy_ids['news']:       news,
    taxonomy_ids['features']:   features,
    taxonomy_ids['sports']:     athletics,
    taxonomy_ids['opinion']:    opinions_and_columns,
    taxonomy_ids['multimedia']: multimedia,
    taxonomy_ids['photos']:     multimedia, # front-page photos belong in multimedia
}
subsection_lookup = {
    taxonomy_ids['atg']: atg,
    taxonomy_ids['weekend-roundup']: roundup,
    taxonomy_ids['stuco-platforms']: platforms,
    taxonomy_ids['editorials']: editorials
}
tag_lookup = {
    taxonomy_ids['arts']: arts,
    taxonomy_ids['april-fools']: april_fools,
}
other_types_lookup = {
    taxonomy_ids['announcements']: 'announcement',
    taxonomy_ids['gazette-news']: 'gazette-news-announcement',
    taxonomy_ids['jobs']: 'jobs'
}

for old_slug, data in columns.items():
    name, year, semester, author = data
    column = Column.objects.create(
        name = name,
        slug = django.template.defaultfilters.slugify(name),
        section = opinions_and_columns,
        year = year,
        semester = semester,
        is_over = year == 2008 and semester == 2,
    )
    user = UserProfile.objects.get(user__username=author.replace('-', '_'))
    column.authors.add(user)
    user.add_position(columnist)
    subsection_lookup[taxonomy_ids[old_slug]] = column


### not sure we necessarily want to tag based on autometa
# cursor.execute("SELECT post_id, meta_value FROM gazette_postmeta WHERE meta_key='autometa'")
# while True:
#     row = cursor.fetchone()
#     if row is None:
#         break
#     old_id, tags = row
#     try:
#         posts[int(old_id)]["tags"] = tags
#     except KeyError:
#         pass

# these are compiled to save a bit of speed, even though it kinda sucks
nextpage = re.compile(r'<!--\s*nextpage\s*-->')
part_matching = re.compile(r'''
    ^\s*                                    # start, whitespace
    (?:<div[^>]*>)?                         # optional div wrapper
    <img[^>]+src=['"]([^'"]+)['"][^>]*/\s*> # img tag -- match only the src
    \s*(?:</div>)?                          # optional div closer
    \s*                                     # eat up any whitespace
    (.*?)                                   # the caption: non-greedy match, to
                                            #           avoid ending whitespace
    \s*$                                    # whitespace, end of string
    ''', re.IGNORECASE | re.DOTALL | re.VERBOSE)

block_tags = "table|thead|tfoot|caption|colgroup|tbody|tr|td|th|div|dl|dd|dt|ul|ol|li|pre|select|form|map|area|blockquote|address|math|style|input|p|h[1-6]|hr"
block_regexp = re.compile(r'\s*<\s*(%s)\b([^>]*)>' % block_tags, re.IGNORECASE)

poll_regexp = re.compile(r'\[poll=(\d+)\]', re.IGNORECASE)

def clean_up_text(text):
    # TODO: curly quotes, etc
    text = django.utils.text.normalize_newlines(text)
    text = django.utils.html.fix_ampersands(text)
    return text

def paragraphize(text):
    paras = re.split(r'\s*\n\s*\n\s*', text)
    output = []
    while paras:
        para = paras.pop(0)
        if not para: continue
        
        block = block_regexp.match(para)
        if block:
            tag = block.group(1)
            
            if tag.lower() == "hr":
                output.append(para)
                continue
            
            this_tag = re.compile(r'<\s*(/?)\s*%s\b[^>]*>' % tag, re.IGNORECASE)
            corpus = '\0'.join([para] + paras)
            tag_depth = 1
            for match in this_tag.finditer(corpus, block.end()):
                tag_depth += -1 if match.group(1) == '/' else 1
                if tag_depth == 0:
                    para = corpus[:match.end()].replace('\0', '\n\n')
                    paras = corpus[match.end():].split('\0')
                    
                    if tag.lower() == "blockquote":
                        output.append(block.group(0))
                        
                        offset = para.count('\n\n')
                        new_text = para[block.end():match.start() + offset]
                        output.append(paragraphize(new_text))
                        
                        output.append(match.group(0))
                    else:
                        output.append(para)
                    break
            
            if tag_depth != 0:
                raise ValueError, "unbalanced %s tags" % tag
        else:
            output.append("<p>%s</p>" % para)
    
    return '\n\n'.join(output)

                 
class_reps = {
    'mainimg':        'hundred',
    'leftImage':      'imgLeft twentyfive',
    'rightImage':     'imgRight twentyfive',
    'pullQuote':      'pullQuote left',
    'pullQuoteRight': 'pullQuote right',
    'images':         'imgRight twentyfive',
    'images50':       'imgRight thirtyfive',
    'imagesLeft':     'imgLeft twentyfive',
    'imagesleft50':   'imgLeft thirtyfive',
    'linkbar':        'linkBar',
    'quote':          'pullQuote left'
}
div_or_p = re.compile(r'p|div', re.IGNORECASE)
                                              
def process_article_text(article):
    # text = paragraphize(article.text)
    soup = BeautifulSoup.BeautifulSoup(article.text)

    # process blockquotes
    for bq in soup.findAll('blockquote'):
        bq.name = 'div'
        bq['class'] = 'highlightBox center'

    # process (div|p)s
    for from_class, rep_class in class_reps.items():
        for div in soup.findAll(div_or_p, attrs={'class': from_class}):
            div['class'] = rep_class

    # process images
    for img in soup.findAll('img'):
        source = img['src']
        media = resolve_media(source, article)
        if isinstance(media, (str, unicode)):
            # print "off-site image: " + media
            continue
        img['src'] = "%s/%s" % (media.bucket, media.slug)
        if 'class' in img.attrMap:
            if img['class'] in class_reps.keys():
                img['class'] = class_reps[img['class']]
        article.media.add(media)

    article.text = paragraphize(unicode(soup))
    article.save()


for post_id, p in posts.iteritems():
    section = subsection = None
    is_article = True
    is_announcement = is_gazette_news = is_job = False
    tags = []
    
    cursor.execute("SELECT term_taxonomy_id FROM gazette_term_relationships WHERE object_id = %s" % post_id)
    while True:
        row = cursor.fetchone()
        if not row:
            break
        taxo_id = row[0]
        if taxo_id in section_lookup:
            section = section_lookup[taxo_id]
        elif taxo_id in subsection_lookup:
            subsection = subsection_lookup[taxo_id]
        elif taxo_id in tag_lookup:
            tags.append(tag_lookup[taxo_id])
        elif taxo_id in other_types_lookup:
            is_article = False
            result = other_types_lookup[taxo_id]
            if result == "announcement":
                is_announcement = True
            elif result == "gazette-news-announcement":
                is_announcement = True
                is_gazette_news = True
            elif result == "jobs":
                is_job = True
            else:
                print "Unknown lookup result: %s" % result
    
    if is_article:
        content = p['content']

        if section is None:
            if subsection:
                section = subsection.section
            elif arts in tags:
                # assume that arts articles are features
                section = features
            elif all_in(content, ("Lunch", "Dinner")) or post_id == 1121:
                continue # we're ignoring old menus for now
            elif all_in(content, ("Today", "Tonight", "Tomorrow")):
                continue # TODO: parse the weather joke
            else:
                print "post %4s doesn't have a section" % post_id
                continue
        
        # summaries:
        summary = p['excerpt']
        words = django.utils.html.strip_tags(content).split()
        summary = summary or ' '.join(words[:30]) + ' [...]'
        short_summary = ' '.join(words[:15]) + ' [...]'
        long_summary = ' '.join(words[:50]) + ' [...]'
        
        
        # polls:
        article_polls = []
        def add_poll(match):
            old_poll_id = int(match.group(1))
            article_polls.append(Poll.objects.get(pk=polls[old_poll_id]['new_id']))
            return ''
        re.sub(poll_regexp, add_poll, content)
        
        # slug; some are url-escaped
        slug = urllib2.unquote(p['slug'])
        slug = django.template.defaultfilters.slugify(slug)
        if len(slug) > 100:
            print "truncating slug <%s>" % slug
            slug = slug[:100]
        
        article_args = dict(
            headline=p['title'],
            slug=slug,
            section=section,
            subsection=subsection,
            summary=summary,
            short_summary=short_summary,
            long_summary=long_summary,
            pub_date=p['date'],
            format=html,
            status='p',
        )
        
        if not nextpage.search(content):
            article = Article.objects.create(
                text=clean_up_text(content), 
                **article_args
            )
            process_article_text(article)
        
        else: # this is probably a photospread
            content = clean_up_text(content)
            article = PhotoSpread.objects.create(**article_args)
            
            parts = nextpage.split(content)
            for part in parts:
                if part.strip() == '':
                    continue
                match = part_matching.match(part)
                if not match:
                    print "Confused by photospread (id %s): %s" % (post_id, part)
                url, caption = match.groups()
                photo = resolve_media(url, article)
                article.add_photo(photo=photo, caption=caption)
        
        author_id = users[p['author']]['new_id']
        article.add_author(User.objects.get(pk=author_id).get_profile())    
        article.polls = article_polls
        
        if tags:
            article.tags = ','.join('"%s"' % tag.name for tag in tags)
    
        p["new_id"] = article.id
    elif is_announcement:
        if is_job:
            # NOTE: Jobs need some manual updating based on whether they're
            #       paid, on-campus, filled, etc....
            JobListing.objects.create(
                name=p['title'],
                slug=p['slug'][:100],
                description=django.utils.html.linebreaks(clean_up_text(p['content'])),
                pub_date=p['date'],
                is_filled=True, # for most of them...
                is_published=True
            )
        else:
            d = p['date']
            date = datetime.date(d.year, d.month, d.day)
            Announcement.objects.create(
                kind=('s' if is_gazette_news else 'c'),
                title=p['title'],
                slug=p['slug'][:100],
                text=django.utils.html.linebreaks(clean_up_text(p['content'])),
                date_start=date,
                date_end=date,
                is_published=True,
                sponsor='' # no real way to get this automatically
            )
    else:
        print 'unsure: skipping %s' % post_id



# get front_images, for those few stories that actually use them
cursor.execute("SELECT post_id, meta_value FROM gazette_postmeta WHERE meta_key='front_image'")
while True:
    row = cursor.fetchone()
    if row is None:
        break
    old_id, front_image = row
    try:
        article = Article.objects.get(pk=posts[old_id]['new_id'])
    except:
        print "can't do front image for article #%s" % old_id
    else:
        image = resolve_media(front_image, article)
        article.front_image = image
        article.save()

# other_authors
cursor.execute("SELECT post_id, meta_value FROM gazette_postmeta WHERE meta_key='other_author'")
while True:
    row = cursor.fetchone()
    if row is None:
        break
    old_id, author = row
    try:
        article = Article.objects.get(pk=posts[old_id]['new_id'])
    except:
        print "couldn't find article #%s" % old_id
    
    if ' ' in author:
        author = UserProfile.objects.username_for_name(author, True)

    article.add_author(UserProfile.objects.get(user__username=author.replace('-', '_')))


# ============
# = Comments =
# ============
print "importing comments..."
article_type = ContentType.objects.get_for_model(Article)

cursor.execute("SELECT comment_ID, comment_post_ID, comment_author, user_id, comment_author_email, comment_author_IP, comment_agent, comment_date, comment_content, comment_approved FROM gazette_comments WHERE comment_type <> 'pingback' AND comment_approved <> 'spam' ORDER BY comment_date ASC;")
while True:
    row = cursor.fetchone()
    if not row:
        break
    
    comment_id, post_id, author, user_id, email, ip, ua, date, content, approved = row
    content = django.utils.text.normalize_newlines(content)
    content = content.replace('\n', '<br/>')
    
    if post_id not in posts:
        print "comment #%s is on non-imported article #%s" % (comment_id, post_id)
        continue
    
    post_data = posts[post_id]
    if 'new_id' not in post_data:
        # this is a job or announcement, I guess
        print "skipping comment id %s on post id %s" % (comment_id, post_id)
        continue
    
    args = {
        'subject_id': post_data['new_id'],
        'subject_type': article_type,
        
        'time': date,
        'text': content,
        
        'ip_address': ip,
        'user_agent': ua,
        'check_spam': False,
        'pre_approved': bool(approved)
    }
    
    if user_id:
        args['user'] = User.objects.get(pk=users[user_id]['new_id']).get_profile()
    else:
        args['name'] = author
        args['email'] = email
    
    PublicComment.objects.new(**args)


# this is dumb
Article.objects.update(possible_position='1')
WeatherJoke.objects.create(
    line_one='As the economy seems to fall endlessly,',
    line_two='We seniors are pretty lucky--few of us aspired to work at an investment bank.',
    line_three="No six-figure salaries, sure, but our industry can't vanish in the space of a month."
)
cursor.close()
conn.close()
