from lxml import etree
from pm4py import log as log_lib
import ciso8601
import logging
import tempfile, os
import gzip, shutil

# ITERPARSE EVENTS
EVENT_END = 'end'
EVENT_START = 'start'


def import_from_xes_string(xes_string, timestamp_sort=False, timestamp_key="time:timestamp", reverse_sort=False,
                           insert_trace_indexes=False, max_no_traces_to_import=100000000):
    """
    Imports XES log from XES string

    Parameters
    ----------
    xes_string
        XES string
    timestamp_sort
        Specify if we should sort log by timestamp
    timestamp_key
        If sort is enabled, then sort the log by using this key
    reverse_sort
        Specify in which direction the log should be sorted
    index_trace_indexes
        Specify if trace indexes should be added as event attribute for each event
    max_no_traces_to_import
        Specify the maximum number of traces to import from the log (read in order in the XML file)

    Returns
    -----------
    log
        Trace log
    """
    fp = tempfile.NamedTemporaryFile(suffix='.xes')
    fp.close()
    with open(fp.name, 'w') as f:
        f.write(xes_string)
    log = import_from_file_xes(fp.name, timestamp_sort=timestamp_sort, timestamp_key=timestamp_key,
                               reverse_sort=reverse_sort,
                               insert_trace_indexes=insert_trace_indexes,
                               max_no_traces_to_import=max_no_traces_to_import)
    os.remove(fp.name)
    return log

def decompress(gzipped_xes):
    """
    Decompress a gzipped XES and returns location of the temp file created

    Parameters
    ----------
    gzipped_xes
        Gzipped XES

    Returns
    ----------
    decompressedPath
        Decompressed file path
    """
    fp = tempfile.NamedTemporaryFile(suffix='.xes')
    fp.close()
    with gzip.open(gzipped_xes, 'rb') as f_in:
        with open(fp.name, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    return fp.name

def import_from_file_xes(filename, timestamp_sort=False, timestamp_key="time:timestamp", reverse_sort=False,
                         insert_trace_indexes=False, max_no_traces_to_import=100000000):
    """
    Imports an XES file into a log object

    Parameters
    ----------
    filename:
        Absolute filename
    timestamp_sort
        Specify if we should sort log by timestamp
    timestamp_key
        If sort is enabled, then sort the log by using this key
    reverse_sort
        Specify in which direction the log should be sorted
    index_trace_indexes
        Specify if trace indexes should be added as event attribute for each event
    max_no_traces_to_import
        Specify the maximum number of traces to import from the log (read in order in the XML file)

    Returns
    -------
    log : :class:`pm4py.log.log.TraceLog`
        A trace log
    """
    if filename.endswith("gz"):
        filename = decompress(filename)

    context = etree.iterparse(filename, events=['start', 'end'])

    log = None
    trace = None
    event = None

    tree = {}

    for tree_event, elem in context:
        if tree_event == EVENT_START:  # starting to read
            parent = tree[elem.getparent()] if elem.getparent() in tree else None

            if elem.tag.endswith(log_lib.util.xes.TAG_STRING):
                if not parent is None:
                    tree = __parse_attribute(elem, parent, elem.get(log_lib.util.xes.KEY_KEY),
                                             elem.get(log_lib.util.xes.KEY_VALUE), tree)
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_DATE):
                try:
                    dt = ciso8601.parse_datetime(elem.get(log_lib.util.xes.KEY_VALUE))
                    tree = __parse_attribute(elem, parent, elem.get(log_lib.util.xes.KEY_KEY), dt, tree)
                except:
                    logging.info("failed to parse date: " + str(elem.get(log_lib.util.xes.KEY_VALUE)))
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_EVENT):
                if event is not None:
                    raise SyntaxError('file contains <event> in another <event> tag')
                event = log_lib.log.Event()
                tree[elem] = event
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_TRACE):
                if len(log) >= max_no_traces_to_import:
                    break
                if trace is not None:
                    raise SyntaxError('file contains <trace> in another <trace> tag')
                trace = log_lib.log.Trace()
                tree[elem] = trace.attributes
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_FLOAT):
                if not parent is None:
                    try:
                        val = float(elem.get(log_lib.util.xes.KEY_VALUE))
                        tree = __parse_attribute(elem, parent, elem.get(log_lib.util.xes.KEY_KEY), val, tree)
                    except:
                        logging.info("failed to parse float: " + str(elem.get(log_lib.util.xes.KEY_VALUE)))
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_INT):
                if not parent is None:
                    try:
                        val = int(elem.get(log_lib.util.xes.KEY_VALUE))
                        tree = __parse_attribute(elem, parent, elem.get(log_lib.util.xes.KEY_KEY), val, tree)
                    except:
                        logging.info("failed to parse int: " + str(elem.get(log_lib.util.xes.KEY_VALUE)))
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_BOOLEAN):
                if not parent is None:
                    try:
                        val = bool(elem.get(log_lib.util.xes.KEY_VALUE))
                        tree = __parse_attribute(elem, parent, elem.get(log_lib.util.xes.KEY_KEY), val, tree)
                    except:
                        logging.info("failed to parse boolean: " + str(elem.get(log_lib.util.xes.KEY_VALUE)))
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_LIST):
                if not parent is None:
                    # lists have no value, hence we put None as a value
                    tree = __parse_attribute(elem, parent, elem.get(log_lib.util.xes.KEY_KEY), None, tree)
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_ID):
                if not parent is None:
                    tree = __parse_attribute(elem, parent, elem.get(log_lib.util.xes.KEY_KEY),
                                             elem.get(log_lib.util.xes.KEY_VALUE), tree)
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_EXTENSION):
                if log is None:
                    raise SyntaxError('extension found outside of <log> tag')
                if elem.get(log_lib.util.xes.KEY_NAME) is not None and elem.get(
                        log_lib.util.xes.KEY_PREFIX) is not None and elem.get(log_lib.util.xes.KEY_URI) is not None:
                    log.extensions[elem.get(log_lib.util.xes.KEY_NAME)] = {
                        log_lib.util.xes.KEY_PREFIX: elem.get(log_lib.util.xes.KEY_PREFIX),
                        log_lib.util.xes.KEY_URI: elem.get(log_lib.util.xes.KEY_URI)}
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_GLOBAL):
                if log is None:
                    raise SyntaxError('global found outside of <log> tag')
                if elem.get(log_lib.util.xes.KEY_SCOPE) is not None:
                    log.omni_present[elem.get(log_lib.util.xes.KEY_SCOPE)] = {}
                    tree[elem] = log.omni_present[elem.get(log_lib.util.xes.KEY_SCOPE)]
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_CLASSIFIER):
                if log is None:
                    raise SyntaxError('classifier found outside of <log> tag')
                if elem.get(log_lib.util.xes.KEY_KEYS) is not None:
                    log.classifiers[elem.get(log_lib.util.xes.KEY_NAME)] = elem.get(log_lib.util.xes.KEY_KEYS).split()
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_LOG):
                if log is not None:
                    raise SyntaxError('file contains > 1 <log> tags')
                log = log_lib.log.TraceLog()
                tree[elem] = log.attributes
                continue

        elif tree_event == EVENT_END:
            if elem in tree:
                del tree[elem]
            elem.clear()
            if elem.getprevious() is not None:
                try:
                    del elem.getparent()[0]
                except TypeError:
                    pass

            if elem.tag.endswith(log_lib.util.xes.TAG_EVENT):
                if trace is not None:
                    trace.append(event)
                    event = None
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_TRACE):
                log.append(trace)
                trace = None
                continue

            elif elem.tag.endswith(log_lib.util.xes.TAG_LOG):
                continue

    del context

    if timestamp_sort:
        log.sort(timestamp_key=timestamp_key, reverse_sort=reverse_sort)
    if insert_trace_indexes:
        log.insert_trace_index_as_event_attribute()

    return log


def __parse_attribute(elem, store, key, value, tree):
    if len(elem.getchildren()) == 0:
        store[key] = value
    else:
        store[key] = {log_lib.util.xes.KEY_VALUE: value, log_lib.util.xes.KEY_CHILDREN: {}}
        if elem.getchildren()[0].tag.endswith(log_lib.util.xes.TAG_VALUES):
            tree[elem] = store[key][log_lib.util.xes.KEY_CHILDREN]
            tree[elem.getchildren()[0]] = tree[elem]
        else:
            tree[elem] = store[key][log_lib.util.xes.KEY_CHILDREN]
    return tree
