from .gitwildmatch import GrepWildMatchPattern

class GrepWildMatchPattern(GitWildMatchPattern):
  @classmethod
  def is_specfile(cls, file_path):
    return os.path.basename(file_path) == '.grepignore'

util.register_pattern('grepwildmatch', GrepWildMatchPattern)
