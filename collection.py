import logging
import mimetypes
import os
import subprocess

import cohydra.profile


logging.getLogger().setLevel(logging.DEBUG)


mimetypes.add_type('application/CDFV2-unknown', '.jwl', False)
mimetypes.add_type('application/octet-stream', '.ncd', False)
mimetypes.add_type('application/x-cdrdao-toc', '.toc', False)
mimetypes.add_type('text/url', '.url', False)
mimetypes.add_type('video/mp4', '.m4v', False)


music_master = cohydra.profile.RootProfile(
  top_dir='/home/dseomn/Music/master',
  )


def music_default_select_cb(profile, dir, contents):
  dir_split = os.path.normpath(dir).split(os.sep)
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

    mime, encoding = mimetypes.guess_type(entry.path, strict=False)
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

  folder_image_prefix = os.path.join(dir, 'folder.')
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
  mime, encoding = mimetypes.guess_type(src_relpath, strict=False)
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


def music_videos_select_cb(profile, dir, contents):
  keep = []

  for entry in contents:
    if entry.is_dir():
      keep.append(entry)
      continue

    mime, encoding = mimetypes.guess_type(entry.path, strict=False)
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
