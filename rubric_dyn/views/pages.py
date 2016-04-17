'''regular website pages'''
import os
import sqlite3
import json
from flask import Blueprint, render_template, g, request, session, redirect, \
    url_for, abort, flash, current_app
from rubric_dyn.common import pandoc_pipe

pages = Blueprint('pages', __name__)


#def get_entry_by_id(id):
#    '''return entry data from database'''
#    g.db.row_factory = sqlite3.Row
#    cur = g.db.execute( '''SELECT type, ref, title, date_norm,
#                            datetime_norm, body_html, data1, exifs_json,
#                            meta_json
#                           FROM entries
#                           WHERE id = ?''', (id,))
#    return cur.fetchone()

def get_entry_by_date_ref_path(date_ref_path, type, published=True):
    '''return entry data from db, by <date>/<ref> path'''

    date, ref = os.path.split(date_ref_path)

    if published == True:
        pub = 1
    else:
        pub = 0

    g.db.row_factory = sqlite3.Row
    cur = g.db.execute( '''SELECT type, ref, title, date_norm,
                            datetime_norm, body_html, data1, exifs_json,
                            meta_json
                           FROM entries
                           WHERE date_norm = ?
                           AND ref = ?
                           AND type = ?
                           AND pub = ?''', (date, ref, type, pub))
    row = cur.fetchone()
    # (catch not found !!!)
    if row is None:
        abort(404)

    return row

def get_entry_by_ref(ref, type, published=True):
    '''return entry data from db, by ref'''

    if published == True:
        pub = 1
    else:
        pub = 0

    g.db.row_factory = sqlite3.Row
    cur = g.db.execute( '''SELECT type, ref, title, date_norm,
                            datetime_norm, body_html, data1, exifs_json,
                            meta_json
                           FROM entries
                           WHERE ref = ?
                           AND type = ?
                           AND pub = ?''', (ref, type, pub))
    row = cur.fetchone()
    # (catch not found !!!)
    if row is None:
        abort(404)

    return row

def create_page_nav(curr_type, curr_datetime_norm):
    '''create previous/next navigation for posts (using same type)'''

    q_begin = '''SELECT date_norm, ref
                 FROM entries
                 WHERE date_norm IS NOT 'ERRONEOUS_DATE'
                 AND ( type = ? )
                 AND pub = 1
                 '''

    # get previous page
    # and create new page_nav list
    cur = g.db.execute( q_begin + \
                        '''AND datetime_norm < ?
                           ORDER BY datetime_norm DESC LIMIT 1''',
                           (curr_type, curr_datetime_norm) )
    prev_result = cur.fetchone()

    if curr_type == 'article':
        type_subpath = "/articles"

    if prev_result is not None:
        prev_date = prev_result[0]
        prev_ref = prev_result[1]
        page_nav = { 'prev_href': os.path.join(type_subpath, prev_date, prev_ref) }
    else:
        page_nav = { 'prev_href': None }

    # get next page
    # and fill in page_nav list
    cur = g.db.execute( q_begin + \
                        '''AND datetime_norm > ?
                           ORDER BY datetime_norm ASC LIMIT 1''',
                           (curr_type, curr_datetime_norm) )
    next_result = cur.fetchone()

    if next_result is not None:
        next_date = next_result[0]
        next_ref = next_result[1]
        page_nav['next_href'] = os.path.join(type_subpath, next_date, next_ref)
    else:
        page_nav['next_href'] = None

    return page_nav

def extract_tags(meta_json):
    '''extract tags from json'''
    meta = json.loads(meta_json)
    if 'tags' in meta.keys():
        return meta['tags']
    else:
        return None

def show_post(row, page_nav):
    '''show post
currently used for entry types:
- article
- special
- note
'''

    # set tags
    # --> could be changed to set _all_ meta information instead
    entry = { 'db': row }
    entry['tags'] = extract_tags(row['meta_json'])

    # title and img_exifs_json are separate because they are used
    # in parent template
    # --> is this really necessary ??
    return render_template( 'post.html',
                            title = entry['db']['title'],
                            entry = entry,
                            page_nav = page_nav,
                            img_exifs_json = entry['db']['exifs_json'] )

def show_post_by_type_ref(type, ref):
    '''helper to show an entry by type, ref
currently used for types:
- special
- note
'''
    row = get_entry_by_ref(ref, type)

    page_nav = { 'prev_href': None,
                 'next_href': None }

    return show_post(row, page_nav)

@pages.route('/')
def home():
    '''the home page'''

    # articles
    # get a list of articles
    g.db.row_factory = sqlite3.Row
    cur = g.db.execute( '''SELECT id, ref, title, date_norm, meta_json
                           FROM entries
                           WHERE type = 'article'
                           AND pub = 1
                           ORDER BY datetime_norm DESC''' )
    rows = cur.fetchall()

    # prepare data for template (tags)
    #
    # [ { 'row': row,
    #     'tags': TAGS }
    #   { 'row: row,
    #     'tags': TAGS } }
    articles = []
    for row in rows:
        d = { 'db': row }
        d['tags'] = extract_tags(row['meta_json'])
        articles.append(d)

    # create article preview
    cur = g.db.execute( '''SELECT body_md
                           FROM entries
                           WHERE id = ?''', (rows[0]['id'],))
    # --> disable sqlite3 row ???
    body_md = cur.fetchone()[0]

    body_md_prev = "\n".join(body_md.split("\n")[:5])

    body_html = pandoc_pipe( body_md_prev,
                             [ '--to=html5',
                               '--filter=rubric_dyn/filter_img_path.py' ] )

    # notes
    g.db.row_factory = sqlite3.Row
    cur = g.db.execute( '''SELECT ref, title, date_norm, meta_json
                           FROM entries
                           WHERE type = 'note'
                           AND pub = 1
                           ORDER BY datetime_norm DESC''' )
    rows = cur.fetchall()

    notes = []
    for row in rows:
        d = { 'db': row }
        notes.append(d)

    return render_template( 'home.html',
                            title = None,
                            articles = articles,
                            article_prev = body_html,
                            notes = notes )

@pages.route('/articles/<path:article_path>/')
def article(article_path):
    '''single article'''

    row = get_entry_by_date_ref_path(article_path, 'article')

    # get previous/next navigation
    page_nav = create_page_nav(row['type'], row['datetime_norm'])

#    # foto exif information
#    if row['exifs_json'] == "":
#        img_exifs_json = False
#
# --> jinja evaluates "" as not defined, as far as I can see...

    return show_post(row, page_nav)

@pages.route('/special/<ref>/')
def special(ref):
    '''special page'''

    return show_post_by_type_ref('special', ref)

@pages.route('/notes/<ref>/')
def show_note(ref):
    '''note page'''

    return show_post_by_type_ref('note', ref)
