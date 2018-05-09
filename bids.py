#!/usr/bin/env python
"""
Module with helper functions

Derived from dac2bids.py from Daniel Gomez 29.08.2016
https://github.com/dangom/dac2bids/blob/master/dac2bids.py

@author: Marcel Zwiers
"""

# Global imports (specific modules may be imported when needed)
import os.path
import glob
import warnings
import inspect
import datetime
import textwrap
import re
from ruamel_yaml import YAML
yaml = YAML()

bidsmodalities  = ('anat', 'func', 'beh', 'dwi', 'fmap')
unknownmodality = 'unknown'


def printlog(message, logfile=None):
    """
    Print an annotated logmessage to screen and to logfile (optional)
    :param message:
    :param logfile:
    :return: None
    """

    # Get the name of the caller
    frame  = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    caller = os.path.basename(module.__file__)

    # Print the logmessage
    logmessage = '{time} - {caller}:\n{message}'.format(
        time    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        caller  = caller,
        message = textwrap.indent(message, '\t'))
    print(logmessage)

    # Open or create a log-file and write the message
    if logfile:
        with open(logfile, 'a') as log_fid:
            log_fid.write(logmessage)


def lsdirs(folder, wildcard='*'):
    """
    :param folder:
    :param wildcard:
    :return: An iterable with all directories in a folder, ignores files
    """

    return filter(lambda x:
                  os.path.isdir(os.path.join(folder, x)),
                  glob.glob(os.path.join(folder, wildcard)))


def is_dicomfile(file):
    """
    Returns true if a file is a DICOM. Dicoms have the string DICM hardcoded at offset 0x80.
    :param file:
    :return: boolean
    """

    if os.path.isfile(file):
        with open(file, 'rb') as dcmfile:
            dcmfile.seek(0x80, 1)
            return dcmfile.read(4) == b'DICM'


def is_dicomfile_siemens(file):
    """
    All Siemens Dicoms contain a dump of the MrProt structure.
    The dump is marked with a header starting with 'ASCCONV BEGIN'.
    Though this check is not foolproof, it is very unlikely to fail.
    :param file:
    :return: boolean
    """

    return b'ASCCONV BEGIN' in open(file, 'rb').read()


def is_parfile(file):
    """
    :param file:
    :return: boolean
    """

    # TODO: Returns true if filetype is PAR.
    if os.path.isfile(file):
        with open(file, 'r') as parfile:
            pass
        return False


def is_p7file(file):
    """
    :param file:
    :return: boolean
    """

    # TODO: Returns true if filetype is P7.
    if os.path.isfile(file):
        with open(file, 'r') as p7file:
            pass
        return False


def is_niftifile(file):
    """
    :param file:
    :return: boolean
    """

    # TODO: Returns true if filetype is nifti.
    if os.path.isfile(file):
        with open(file, 'r') as niftifile:
            pass
        return False


def is_incomplete_acquisition(folder):
    """
    If a scan was aborted in the middle of the experiment, it is likely that DICOMs will be saved
    anyway. We want to avoid converting these incomplete directories. This function checks the
    number of measurements specified in the protocol against the number of DICOMs.
    """

    dicomfile = get_dicom_file(folder)
    nrep      = get_dicomfield('lRepetitions', dicomfile)
    nfiles    = len(os.listdir(folder))

    if nrep and nrep > nfiles:
        warnings.warn('Incomplete acquisition found in: {}'\
                      '\nExpected {}, found {} dicomfiles'.format(folder, nrep, nfiles))
        return True
    else:
        return False


def get_dicom_file(folder):
    """
    :param folder:
    :return: filename of the first dicom file from the folder.
    """

    for file in os.listdir(folder):
        if is_dicomfile(os.path.join(folder, file)):
            return os.path.join(folder, file)

    warnings.warn('Cannot find dicom files in:' + folder)
    return None


def get_par_file(folder):
    """
    :param folder:
    :return: filename of the first PAR file from the folder
    """

    for file in os.listdir(folder):
        if is_parfile(file):
            return os.path.join(folder, file)

    warnings.warn('Cannot find PAR files in:' + folder)
    return None


def get_p7_file(folder):
    """
    :param folder:
    :return: filename of the first P7 file from the folder
    """

    for file in os.listdir(folder):
        if is_p7file(file):
            return os.path.join(folder, file)

    warnings.warn('Cannot find P7 files in:' + folder)
    return None


def get_nifti_file(folder):
    """
    :param folder:
    :return: filename of the first nifti file from the folder
    """

    for file in os.listdir(folder):
        if is_niftifile(file):
            return os.path.join(folder, file)

    warnings.warn('Cannot find nifti files in:' + folder)
    return None


def parse_from_x_protocol(pattern, dicomfile):
    """
    Siemens writes a protocol structure as text into each DICOM file.
    This structure is necessary to recreate a scanning protocol from a DICOM,
    since the DICOM information alone wouldn't be sufficient.

    :param pattern:
    :param dicomfile:
    :return: string extracted values from the dicomfile according to the given pattern
    """

    if not is_dicomfile_siemens(dicomfile):
        warnings.warn('This does not seem to be a Siemens DICOM file')

    regexp = '^' + pattern + '\t = \t(.*)\n'
    regex  = re.compile(regexp.encode('utf-8'))

    with open(dicomfile, 'rb') as openfile:
        for line in openfile:
            match = regex.match(line)
            if match:
                return match.group(1).decode('utf-8')

    warnings.warn('Pattern: "' + regexp.encode('unicode_escape').decode() + '" not found in: ' + dicomfile)
    return None


# Profiling shows this is currently the most expensive function, so therefore the (primitive but effective) _DICOMDICT_MEMO optimization
_DICOMDICT_MEMO = None
_DICOMFILE_MEMO = None
def get_dicomfield(tagname, dicomfile):
    """
    Robustly reads a DICOM tag from a dictionary or from vendor specific fields
    :param tagname:
    :param dicomfile:
    :return: tagvalue
    """

    import pydicom
    global _DICOMDICT_MEMO, _DICOMFILE_MEMO

    try:

        if dicomfile != _DICOMFILE_MEMO:
            dicomdict       = pydicom.dcmread(dicomfile)
            _DICOMDICT_MEMO = dicomdict
            _DICOMFILE_MEMO = dicomfile
        else:
            dicomdict = _DICOMDICT_MEMO

        # TODO: implement regexp
        value = dicomdict.get(tagname)

    except IOError: warnings.warn('Cannot read' + dicomfile)
    except Exception:
        try:

            value = parse_from_x_protocol(tagname, dicomfile)

        except Exception:

            value = None
            warnings.warn('Could not extract {} tag from {}'.format(tagname, dicomfile))

    # Cast the dicom datatype to standard to int or str (i.e. to something that yaml.dump can handle)
    if isinstance(value, int):
        return int(value)

    elif not isinstance(value, str):    # Assume it's a MultiValue type and flatten it (TODO: deal with this properly)
        return str(value)

    else:
        return str(value)


def get_heuristics(yamlfile, folder=None):
    """
    Read the heuristics from the bidsmapper yamlfile
    :param yamlfile:
    :param folder:
    :return: yaml data structure
    """

    # Input checking
    if not folder:
        folder = __file__

    if not os.path.splitext(yamlfile)[1]:           # Add a standard file-extension if needed
        yamlfile = yamlfile + '.yaml'

    if os.path.basename(yamlfile) == yamlfile:      # Get the full paths to the bidsmapper yaml-file
        yamlfile = os.path.join(os.path.dirname(folder), 'heuristics', yamlfile)

    yamlfile = os.path.abspath(os.path.expanduser(yamlfile))

    # Read the heuristics from the bidsmapper file
    with open(yamlfile, 'r') as stream:
        heuristics = yaml.load(stream)

    return heuristics


def exist_series(series, serieslist, matchbidslabels=True):
    """
    Checks if there is already an entry in [serieslist] with the same attributes and labels as [series]
    :param series:
    :param serieslist:
    :param matchbidslabels:
    :return: Boolean
    """

    for item in serieslist:

        match = any([series['attributes'][key] is not None for key in series['attributes']])  # Make match False if all attributes are empty

        # Search for a case where all series items match with the series items
        for key in series:

            try:
                if key == 'attributes':

                    for attrkey in series['attributes']:
                        seriesvalue = series['attributes'][attrkey]
                        itemvalue   = item['attributes'][attrkey]
                        match       = match and (seriesvalue == itemvalue)

                elif matchbidslabels:

                    seriesvalue = series[key]
                    itemvalue   = item[key]
                    match       = match and (seriesvalue == itemvalue)

            except KeyError:    # Errors may be evoked when matching bids-labels which exist in one modality but not in the other
                match = False

            if not match:       # There is no point in searching further within the series now that we've found a mismatch
                break

        # Stop searching if we found a matching series (i.e. which is the case if match is still True after all item tests)
        # TODO: maybe count how many instances, could perhaps be useful info
        if match:
            return True

    return False


def cleanup_label(label):
    """
    Return the given label converted to a label that can be used as a clean BIDS label. Remove leading and trailing spaces;
    convert other spaces, special BIDS characters and anything that is not an alphanumeric to a dot.

    >> cleanup_label("Joe's reward_task")
    "Joes.reward_task"

    :param label:
    :return: validlabel
    """

    special_characters = (' ', '_', '-',)

    for special in special_characters:
        label = str(label).strip().replace(special, '.')

    return re.sub(r'(?u)[^-\w.]', '.', label)


def ask_for_mapping(heuristics, series, filename=''):
    """
    Ask the user for help to resolve the mapping from the series attributes to the BIDS labels
    :param bidsmap:
    :param series:
    :param filename:
    :return: {'modality':modality, 'series': series}
    """

    # Go through the BIDS structure as a decision tree
    # 1: Show all the series-info
    # 2: Ask: Which of the heuristics modalities is it?
    # 3: Ask: Which func suffix, anat modality, etc

    #  TODO: implement code

    return None # {'modality':'', 'series': series}


def ask_for_append(modality, series, bidsmapper):
    """
    Ask the user to add the labelled series to their bidsmapper yaml file or send it to a central database
    :param modality:
    :param series:
    :param bidsmapper:
    :return: heuristics
    """

    # TODO: implement code

    return None # heuristics