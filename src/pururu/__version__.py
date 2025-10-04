import subprocess

__title__ = "Pururu"
__description__ = "Discord bot for managing attendance."
__url__ = "https://github.com/jlvadell/pururu-bot"
__author__ = "Jose Vadell"
__author_email__ = "me@jlvadell.com"
__license__ = "Apache-2.0"
__copyright__ = "Copyright Jose Vadell"
__version__ = "undefined"

def get_version():
    if __version__ != "undefined":
        return __version__
    else:
        try:
            # Get last tag (could be v1.0.0)
            tag = subprocess.check_output(
                ['git', 'describe', '--tags', '--abbrev=0'],
                encoding='utf-8'
            ).strip()

            # Get commit hash
            commit = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                encoding='utf-8'
            ).strip()

            # Get number of commits since the tag
            count = subprocess.check_output(
                ['git', 'rev-list', f'{tag}..HEAD', '--count'],
                encoding='utf-8'
            ).strip()

            return f"{tag}+{count}.{commit}_DEV"
        except Exception:
            return "0.0.0"
