"""Handle database interactions related to texts.

Functions in this module interact with the database (MongoDB instance and local
file storage) to store and retrieve information about texts in the Tesserae
instance. This should be the first stop for clients when using Tesserae
functionality.

Functions
---------
retrieve_text_list
    Retrieve the list of available texts.
insert_text
    Insert a new text into the database.
load_text
    Open a .tess file for reading.
"""
from tesserae.db import create_filter, convert_to_entity, Text
from tesserae.utils import TessFile


class DuplicateTextError(Exception):
    """Raised when attempting to insert a duplicate text in the database"""
    def __init__(self, cts_urn, hash):
        msg = 'Text {} with hash {} already exists in the database.'. \
            format(cts_urn, hash)
        super(DuplicateTextError, self).__init__(msg)


@convert_to_entity(Text)
def retrieve_text_list(client, cts_urn=None, language=None, author=None,
                       title=None, year=None, path=None, hash=None):
    """Retrieve the list of available texts.

    Parameters
    ----------
    client : `pymongo.MongoClient`
        Client connection to the database.
    language : str or list of str, optional
        Filter the list by the supplied language(s).
    author : str or list of str, optional
        Filter the list by the supplied author(s).
    title : str or list of str, optional
        Filter the list by the supplied title(s).
    cts_urn : str or list of str, optional
        Filter the list by the supplied cts_urn(s).
    year : int or pair of int, optional
        Filter the list by the supplied year. If a tuple, limit the list to
        texts from the timespan ``year[0] <= x <= year[1]``.

    Returns
    -------
    texts : list of `tesserae.db.Text`
        The list of texts that match the filter conditions.

    """
    # Create the filter
    filter = create_filter(cts_urn=cts_urn, language=language, author=author,
                           title=title, year=year)

    # Retrieve the texts and put them into a nice format
    docs = client['texts'].find(filter)
    texts = [doc for doc in docs]
    return texts


def insert_text(connection, cts_urn, language, author, title, year, unit_types,
                path):
    """Insert a new text into the database.

    Attempt to insert a new text in the database, sanitized to match the
    fields and data types of existing texts.

    Parameters
    ----------
    cts_urn : str
        Unique collection-level identifier.
    language : str
        Language the text is written in.
    author : str
        Full name of the text author.
    title : str
        Title of the text.
    year : int
        Year of text authorship.
    unit_types : str or list of str
        Valid unit-level delimiters for this text.
    path : str
        Path to the raw text file. May be a remote URL.

    Raises
    ------
    DuplicateTextError
        Raised when attempting to insert a text that already exists in the
        database.

    Notes
    -----
    This function should not be made available to everyone. To properly secure
    the database, ensure that only MongoDB users NOT connected to a public-
    facing client application are able to write to the database. See the
    <MongoDB documentation on role-based access control>_ for more information.

    .. _MongoDB documentation on role-based access control: https://docs.mongodb.com/manual/core/authorization/
    """
    text_file = TessFile(path)
    hash = test_file.hash()
    db_texts = retrieve_text_list(cts_urn=cts_urn, hash=hash)

    if len(db_texts) == 0:
        text = Text(cts_urn=cts_urn, language=language, author=author,
                    title=title, year=year, path=path, hash=hash)
        connection.insert_one(text.json_encode())
    else:
        raise DuplicateTextError(cts_urn, hash)


def load_text(client, cts_urn, mode='r', buffer=True):
    """Open a .tess file for reading.

    Parameters
    ----------
    cts_urn : str
        Unique collection-level identifier.
    mode : str
        File open mode ('r', 'w', 'a', etc.)
    buffer : bool
        If True, load file contents into memory on-the-fly. Otherwise, load in
        contents on initialization.

    Returns
    -------
    text : `tesserae.utils.TessFile` or None
        A non-/buffered reader for the file at ``path``. If the file does not
        exit in the database, returns None.
    """
    try:
        text_obj = retrieve_text_list(client, cts_urn=cts_urn)[0]
        text = TessFile(path, mode=mode, buffer=buffer)
    except IndexError:
        text = None

    return text