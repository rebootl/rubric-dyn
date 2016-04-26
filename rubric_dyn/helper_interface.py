'''interface helper functions (not returning a view)'''
import os
import json
from flask import current_app, flash
from rubric_dyn.common import pandoc_pipe, date_norm2, time_norm, \
    url_encode_str
from rubric_dyn.ExifNice import ExifNiceStr

def process_image(image_file, image_dir, ref):
    '''process image data
- exif information
- insert image in db
- create thumbnail
'''
    image_file_abspath = os.path.join(image_dir, image_file)

    # extract exif into json
    if os.path.splitext(image_file)[1] in current_app.config['JPEG_EXTS']:
        img_exif = ExifNice(image_file_abspath)
        if img_exif.has_exif:
            exif_json = img_exif.get_json()
            datetime_norm = datetimesec_norm( img_exif.datetime,
                                              "%Y:%m:%d %H:%M:%S" )
        else:
            exif_json = ""
            datetime_norm = ""
    else:
        exif_json = ""
        datetime_norm = ""

    # add thumb ref
    thumb_ref = os.path.join('thumbs', image_file)

    # insert in db
    db_insert_image( ref,
                     thumb_ref,
                     datetime_norm,
                     exif_json,
                     gallery_id )

    # create thumbnail if not exists
    # (existence is checked in function --> maybe better check here ?)
    make_thumb_samename(image_file_abspath, thumbs_abspath)

def create_exifs_json(files):
    '''create image info from EXIF data as json dump'''
    img_exifs = {}
    for file in files:
        if os.path.splitext(file)[1] in current_app.config['JPEG_EXTS']:
            img_filepath = os.path.join( current_app.config['RUN_ABSPATH'],
                                         'media',
                                         file )
            exif = ExifNiceStr(img_filepath)
            if exif.display_str:
                image_exif = { os.path.join( '/media',
                                             file ) : exif.display_str }
                img_exifs.update(image_exif)
    if img_exifs:
        return json.dumps(img_exifs)
    else:
        return ""

def process_meta_json(meta_json):
    '''read out meta information from json dump
and set defaults if necessary'''
    try:
        meta = json.loads(meta_json)
    except json.decoder.JSONDecodeError:
        flash("Warning: Error in JSON data, using defaults...")
        meta = {}

    # set defaults
    for key, value in current_app.config['META_DEFAULTS'].items():
            if key not in meta.keys():
                meta[key] = value

    if type == "imagepage":
        if meta['image'] == "" or meta['image'] == None:
            meta['image'] = "NO IMAGE SET"

    return meta

def process_edit(text_input, return_md=False):
    '''process text input including meta information,
also create image information for included image files

used by:
- Page
- views.interface
'''
    # escape shit ?

    # split text in json and markdown block
    meta_json, body_md = text_input.split('%%%', 1)

    meta = process_meta_json(meta_json)

    # process text through pandoc
    body_html = pandoc_pipe( body_md,
                             [ '--to=html5',
                               '--filter=rubric_dyn/filter_img_path.py' ] )

    img_exifs_json = create_exifs_json(meta['files'])

    if not return_md:
        return meta, body_html, img_exifs_json
    else:
        return meta, meta_json, img_exifs_json, body_html, body_md

def process_input(title, date_str, time_str, body_md):
    '''page edit input processing and prepare for database
(new, replacement for process_edit above)'''

    # make ref (from title)
    ref = url_encode_str(title)

    # process date and time
    date_normed = date_norm2(date_str, "%Y-%m-%d")
    if not date_normed:
        date_normed = "NOT_SET"
        flash("Warning: bad date format..., setting to 'NOT_SET'.")
    time_normed = time_norm(time_str, "%H:%M")
    if not time_normed:
        time_normed = "NOT_SET"
        flash("Warning: bad time format..., setting to 'NOT_SET'.")

    # process markdown
    body_html = pandoc_pipe( body_md,
                             [ '--to=html5',
                               '--filter=rubric_dyn/filter_img_path.py' ] )

    # create exif json
    #img_exifs_json = create_exifs_json(meta['files'])

    return ref, date_normed, time_normed, body_html, None
