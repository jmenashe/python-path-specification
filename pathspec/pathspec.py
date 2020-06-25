# encoding: utf-8
"""
This module provides an object oriented interface for pattern matching
of files.
"""

from . import util
from .compat import Collection, iterkeys, izip_longest, string_types, unicode
import os.path


class PathSpec(object):
  """
  The :class:`PathSpec` class is a wrapper around a list of compiled
  :class:`.Pattern` instances.
  """

  def __init__(self, lines=None, pattern_factory=None, parent=None):
    """
    Initializes the :class:`PathSpec` instance.

    *patterns* (:class:`~collections.abc.Collection` or :class:`~collections.abc.Iterable`)
    yields each compiled pattern (:class:`.Pattern`).
    """
    self.pattern_factory = pattern_factory
    self.lines = lines if isinstance(lines, Collection) else list(lines)
    self.patterns = [self.pattern_factory(line) for line in self.lines if line]
    self.parent = parent
    self.child = None
    """
    *patterns* (:class:`~collections.abc.Collection` of :class:`.Pattern`)
    contains the compiled patterns.
    """

  def __eq__(self, other):
    """
    Tests the equality of this path-spec with *other* (:class:`PathSpec`)
    by comparing their :attr:`~PathSpec.patterns` attributes.
    """
    if isinstance(other, PathSpec):
      paired_patterns = izip_longest(self.patterns, other.patterns)
      return all(a == b for a, b in paired_patterns)
    else:
      return NotImplemented

  def __len__(self):
    """
    Returns the number of compiled patterns this path-spec contains
    (:class:`int`).
    """
    return len(self.patterns)

  @classmethod
  def from_lines(cls, pattern_factory, lines):
    """
    Compiles the pattern lines.

    *pattern_factory* can be either the name of a registered pattern
    factory (:class:`str`), or a :class:`~collections.abc.Callable` used
    to compile patterns. It must accept an uncompiled pattern (:class:`str`)
    and return the compiled pattern (:class:`.Pattern`).

    *lines* (:class:`~collections.abc.Iterable`) yields each uncompiled
    pattern (:class:`str`). This simply has to yield each line so it can
    be a :class:`file` (e.g., from :func:`open` or :class:`io.StringIO`)
    or the result from :meth:`str.splitlines`.

    Returns the :class:`PathSpec` instance.
    """
    if isinstance(pattern_factory, string_types):
      pattern_factory = util.lookup_pattern(pattern_factory)
    if not callable(pattern_factory):
      raise TypeError("pattern_factory:{!r} is not callable.".format(pattern_factory))

    if not util._is_iterable(lines):
      raise TypeError("lines:{!r} is not an iterable.".format(lines))

    return cls(lines=lines, pattern_factory=pattern_factory)

  @classmethod
  def from_specfile(cls, pattern_factory, specfile_path):
    """
    Compiles the pattern lines within the specified specfile.

    *pattern_factory* can be either the name of a registered pattern
    factory (:class:`str`), or a :class:`~collections.abc.Callable` used
    to compile patterns. It must accept an uncompiled pattern (:class:`str`)
    and return the compiled pattern (:class:`.Pattern`).

    *specfile_path* (:class:`str`; or :class:`pathlib.PurePath`) is the 
    location of a specfile containing a set of pattern lines that define a
    :class:`PathSpec`.

    Returns the :class:`PathSpec` instance.
    """

    if not os.path.isfile(specfile_path):
      raise TypeError("specfile_path:{!r} is not a file path.".format(specfile_path))

    with open(specfile_path, 'r') as specfile_handle:
      spec = cls.from_lines(specfile_handle)
      return spec

  def push_specfile(self, specfile_path):
    """
    Reads and compiles the pattern lines from within the specified specfile,
    and then creates a new PathSpec instance as a child of the current 
    PathSpec.
    
    *specfile_path* (:class:`str`; or :class:`pathlib.PurePath`) is the 
    location of a specfile containing a set of pattern lines that define a
    :class:`PathSpec`.
    
    Returns the amended :class:`PathSpec` instance.
    """

    child_spec = PathSpec.from_specfile(self.pattern_factory, specfile_path)
    child_spec.lines = self.lines + child_spec.lines
    child_spec.patterns = self.patterns + child_spec.patterns
    child_spec.parent = self
    self.child = child_spec
    return self.child

  def pop_specfile(self):
    if self.parent is None:
      raise AttributeError("The current specfile has no parent and cannot fulfill the pop request.")
    return self.parent

  def match_file(self, file, separators=None):
    """
    Matches the file to this path-spec.

    *file* (:class:`str` or :class:`~pathlib.PurePath`) is the file path
    to be matched against :attr:`self.patterns <PathSpec.patterns>`.

    *separators* (:class:`~collections.abc.Collection` of :class:`str`)
    optionally contains the path separators to normalize. See
    :func:`~pathspec.util.normalize_file` for more information.

    Returns :data:`True` if *file* matched; otherwise, :data:`False`.
    """
    norm_file = util.normalize_file(file, separators=separators)
    return util.match_file(self.patterns, norm_file)

  def match_entries(self, entries, separators=None):
    """
    Matches the entries to this path-spec.

    *entries* (:class:`~collections.abc.Iterable` of :class:`~util.TreeEntry`)
    contains the entries to be matched against :attr:`self.patterns <PathSpec.patterns>`.

    *separators* (:class:`~collections.abc.Collection` of :class:`str`;
    or :data:`None`) optionally contains the path separators to
    normalize. See :func:`~pathspec.util.normalize_file` for more
    information.

    Returns the matched entries (:class:`~collections.abc.Iterable` of
    :class:`~util.TreeEntry`).
    """
    if not util._is_iterable(entries):
      raise TypeError("entries:{!r} is not an iterable.".format(entries))

    entry_map = util._normalize_entries(entries, separators=separators)
    match_paths = util.match_files(self.patterns, iterkeys(entry_map))
    for path in match_paths:
      yield entry_map[path]

  def match_files(self, files, separators=None):
    """
    Matches the files to this path-spec.

    *files* (:class:`~collections.abc.Iterable` of :class:`str; or
    :class:`pathlib.PurePath`) contains the file paths to be matched
    against :attr:`self.patterns <PathSpec.patterns>`.

    *separators* (:class:`~collections.abc.Collection` of :class:`str`;
    or :data:`None`) optionally contains the path separators to
    normalize. See :func:`~pathspec.util.normalize_file` for more
    information.

    Returns the matched files (:class:`~collections.abc.Iterable` of
    :class:`str`).
    """
    if not util._is_iterable(files):
      raise TypeError("files:{!r} is not an iterable.".format(files))

    file_map = util.normalize_files(files, separators=separators)
    matched_files = util.match_files(self.patterns, iterkeys(file_map))
    for path in matched_files:
      yield file_map[path]

  def match_tree_entries(self, root, on_error=None, follow_links=None):
    """
    Walks the specified root path for all files and matches them to this
    path-spec.

    *root* (:class:`str`; or :class:`pathlib.PurePath`) is the root
    directory to search.

    *on_error* (:class:`~collections.abc.Callable` or :data:`None`)
    optionally is the error handler for file-system exceptions. See
    :func:`~pathspec.util.iter_tree_entries` for more information.

    *follow_links* (:class:`bool` or :data:`None`) optionally is whether
    to walk symbolic links that resolve to directories. See
    :func:`~pathspec.util.iter_tree_files` for more information.

    Returns the matched files (:class:`~collections.abc.Iterable` of
    :class:`str`).
    """
    entries = util.iter_tree_entries(root, on_error=on_error, follow_links=follow_links)
    return self.match_entries(entries)

  def match_tree_files(self, root, on_error=None, follow_links=None):
    """
    Walks the specified root path for all files and matches them to this
    path-spec.

    *root* (:class:`str`; or :class:`pathlib.PurePath`) is the root
    directory to search for files.

    *on_error* (:class:`~collections.abc.Callable` or :data:`None`)
    optionally is the error handler for file-system exceptions. See
    :func:`~pathspec.util.iter_tree_files` for more information.

    *follow_links* (:class:`bool` or :data:`None`) optionally is whether
    to walk symbolic links that resolve to directories. See
    :func:`~pathspec.util.iter_tree_files` for more information.

    Returns the matched files (:class:`~collections.abc.Iterable` of
    :class:`str`).
    """
    files = util.iter_tree_files(root, on_error=on_error, follow_links=follow_links)
    return self.match_files(files)

  # Alias `match_tree_files()` as `match_tree()`.
  match_tree = match_tree_files
