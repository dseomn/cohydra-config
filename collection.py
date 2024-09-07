import logging
import mimetypes
import os
import pathlib
import subprocess
import urllib.parse

import mutagen
import mutagen.id3

import wand.image

import cohydra.profile


logging.getLogger().setLevel(logging.DEBUG)


mimetypes.add_type('application/CDFV2-unknown', '.jwl', False)
mimetypes.add_type('application/octet-stream', '.ncd', False)
mimetypes.add_type('application/x-cdrdao-toc', '.toc', False)
mimetypes.add_type('application/x-cue', '.cue', False)
mimetypes.add_type('text/plain', '.log', False)
mimetypes.add_type('text/url', '.url', False)
mimetypes.add_type('video/dvd', '.vob', False)
mimetypes.add_type('video/mp4', '.m4v', False)


music_master = cohydra.profile.RootProfile(
  top_dir='/home/dseomn/Music/master',
  )


def music_default_select_cb(profile, src_relpath, dst_relpath, contents):
  dir_split = os.path.normpath(src_relpath).split(os.sep)
  if dir_split == ['']:
    depth = 0
  else:
    depth = len(dir_split)

  if depth < 2:
    return contents
  elif depth > 2:
    raise RuntimeError('this should not be possible')

  keep = []
  images = []

  for entry in contents:
    if entry.is_dir():
      # Skip it.
      continue

    if entry.name.endswith('.disable'):
      continue
    elif entry.name.endswith('.original'):
      continue

    mime, encoding = mimetypes.guess_type(pathlib.PurePath(entry.path).as_uri(), strict=False)
    if mime is None:
      profile.log(
        logging.ERROR,
        'Unknown mimetype for %r',
        entry.path,
        )
      keep.append(entry)
      continue

    mime_major, __discard, __discard = mime.partition('/')

    if mime_major in (
        'audio',
        ):
      if mime in (
          'audio/mpegurl',
          'audio/x-mpegurl',
          ):
        # Skip it.
        continue
      keep.append(entry)
    elif mime_major in (
        'application',
        'text',
        'video',
        ):
      # Skip it.
      continue
    elif mime_major in (
        'image',
        ):
      images.append(entry)
    else:
      profile.log(
        logging.ERROR,
        'Unsure what to do with %r, %r',
        mime,
        entry.path,
        )
      keep.append(entry)

  folder_image_prefix = os.path.join(dst_relpath, 'folder.')
  for prefix in (
      'front',
      'cover',
      'front+spine',
      'medium',
      'cd',
      'front+spine+back',
      'back',
      'back+spine',
      #'spine',
      #'unknown',
      #'other',
      None,
      ):
    for suffix in (
        'png',
        'tif',
        'jpg',
        'gif',
        None,
        ):
      for image in images:
        if prefix is not None and suffix is not None:
          if image.name == prefix + '.' + suffix:
            return keep + [(image, folder_image_prefix + suffix)]
        elif prefix is not None:
          if image.name.startswith(prefix + '.'):
            profile.log(
              logging.INFO,
              'Using sub-optimal image %r',
              image.path,
              )
            profile.log(
              logging.WARNING,
              'Not renaming image %r',
              image.path,
              )
            return keep + [image]
        elif suffix is not None:
          if image.name.endswith('.' + suffix):
            profile.log(
              logging.INFO,
              'Using sub-optimal image %r',
              image.path,
              )
            return keep + [(image, folder_image_prefix + suffix)]
        else:
          profile.log(
            logging.WARNING,
            'Using arbitrary image %r',
            image.path,
            )
          profile.log(
            logging.WARNING,
            'Not renaming image %r',
            image.path,
            )
          return keep + [image]

  return keep

music_default = cohydra.profile.FilterProfile(
  top_dir='/home/dseomn/Music/profiles/default',
  parent=music_master,
  select_cb=music_default_select_cb,
  )


def music_large_select_cb(profile, src_relpath):
  mime, encoding = mimetypes.guess_type(pathlib.PurePath(profile.src_path(src_relpath)).as_uri(), strict=False)
  if mime is None:
    mime_major = None
  else:
    mime_major, __discard, __discard = mime.partition('/')

  if src_relpath.endswith('.flac'):
    return src_relpath + '.ogg'
  elif mime_major == 'image':
    return os.path.join(os.path.dirname(src_relpath), 'folder.png')
  else:
    return None

def music_large_convert_cb(profile, src, dst):
  if src.endswith('.flac'):
    command = [
      'oggenc',
      '-Q',
      '-q', '8',
      '-o', dst,
      '--', src,
      ]
  else:
    command = [
      'convert',
      src,
      '-resize', '1200x1200>',
      dst,
      ]

  subprocess.run(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=True,
    )

music_large = cohydra.profile.ConvertProfile(
  top_dir='/home/dseomn/Music/profiles/large',
  parent=music_default,
  select_cb=music_large_select_cb,
  convert_cb=music_large_convert_cb,
  )


music_large_sanitized = cohydra.profile.SanitizeFilenameProfile(
  top_dir='/home/dseomn/Music/profiles/large-sanitized',
  parent=music_large,
  )


def music_large_simple_mp3_select_cb(profile, src_relpath):
  mime, encoding = mimetypes.guess_type(pathlib.PurePath(profile.src_path(src_relpath)).as_uri(), strict=False)
  if mime is None:
    mime_major = None
  else:
    mime_major, __discard, __discard = mime.partition('/')

  if mime_major == 'image':
    return os.path.join(os.path.dirname(src_relpath), 'folder.jpg')
  else:
    return src_relpath + '.mp3'

def music_large_simple_mp3_convert_cb(profile, src, dst):
  if dst.endswith('/folder.jpg'):
    subprocess.run(
      [
        'convert',
        src,
        '-resize', '300x300>',
        '-quality', '90',
        dst,
        ],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      check=True,
      )

  else:
    subprocess.run(
      [
        'gst-launch-1.0',
        'giosrc', 'location=file://' + urllib.parse.quote(src),
        '!',
        'decodebin',
        '!',
        'audioconvert',
        '!',
        'rgvolume', 'pre-amp=-5.0',
        '!',
        'lamemp3enc', 'quality=0', 'encoding-engine-quality=2',
        '!',
        'xingmux',
        '!',
        'id3mux', 'v2-version=4',
        '!',
        'giosink', 'location=file://' + urllib.parse.quote(dst),
        ],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      check=True,
      )
    id3 = mutagen.id3.ID3(dst)
    id3.delall('RVA2')
    for entry in os.scandir(os.path.dirname(src)):
      if mimetypes.guess_type(pathlib.PurePath(entry.path).as_uri(), strict=False)[0].startswith('image/'):
        with wand.image.Image(filename=entry.path) as folder_img:
          folder_img.transform(resize='300x300>')
          folder_img.compression_quality = 90
          id3.setall('APIC', [
            mutagen.id3.APIC(
              encoding=mutagen.id3.Encoding.UTF8,
              mime='image/jpeg',
              type=mutagen.id3.PictureType.COVER_FRONT,
              desc='folder.jpg',
              data=folder_img.make_blob(format='jpeg'),
              ),
            ])
        break
    id3.save()


music_large_simple_mp3 = cohydra.profile.ConvertProfile(
  top_dir='/home/dseomn/Music/profiles/large-simple-mp3',
  parent=music_default,
  select_cb=music_large_simple_mp3_select_cb,
  convert_cb=music_large_simple_mp3_convert_cb,
  )


music_large_simple_mp3_sanitized = cohydra.profile.SanitizeFilenameProfile(
  top_dir='/home/dseomn/Music/profiles/large-simple-mp3-sanitized',
  parent=music_large_simple_mp3,
  )


def music_videos_select_cb(profile, src_relpath, dst_relpath, contents):
  keep = []

  for entry in contents:
    if entry.is_dir():
      keep.append(entry)
      continue

    mime, encoding = mimetypes.guess_type(pathlib.PurePath(entry.path).as_uri(), strict=False)
    if mime is None:
      continue

    if mime.startswith('video/') or mime in (
        'application/x-iso9660-image',
        ):
      keep.append(entry)

  return keep

music_videos = cohydra.profile.FilterProfile(
  top_dir='/home/dseomn/Videos/[music]',
  parent=music_master,
  select_cb=music_videos_select_cb,
  )


if __name__ == '__main__':
#  music_master.print_all()
  music_master.generate_all()
