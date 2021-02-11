#-----------------------------------------------------------------------------
# Copyright (c) 2020 - 2021, CSIRO 
#
# All rights reserved.
#
# The full license is in the LICENSE file, distributed with this software.
#-----------------------------------------------------------------------------

import numpy as np
import xarray as xr
import logging

logger = logging.getLogger("rompy.util")

def dict_product(d):
    from itertools import product
    keys = d.keys()
    for element in product(*d.values()):
        yield dict(zip(keys, element))

def walk_server(urlpath, fn_fmt, fmt_fields, url_replace):
        from os.path import dirname
        from functools import reduce
        from operator import iconcat
        from dask import delayed, compute
        import dask.config as dc

        # Targetted scans of the file system based on date range
        test_urls = set([urlpath.format(**pv) for pv in dict_product(fmt_fields)])
        test_fns = set([fn_fmt.format(**pv) for pv in dict_product(fmt_fields)])

        logger.debug(f'Test URLS : {test_urls}')

        @delayed
        def check_url(test_url,test_fns):
            from fsspec import filesystem
            from fsspec.utils import get_protocol
            fs = filesystem(get_protocol(test_url))
            print(f'testing {test_url}')
            urls = []
            if fs.exists(test_url):
                for url, _ , links in fs.walk(test_url):
                    urls += [dirname(url) + '/' + fn for fn in links if fn in test_fns]
            return urls

        valid_urls = compute(*[check_url(test_url,test_fns) for test_url in test_urls],
                             traverse=False,
                             scheduler='threads')
        # valid_urls = [check_url(test_url,test_fns) for test_url in test_urls]
        valid_urls = sorted(reduce(iconcat,valid_urls,[]))

        logger.debug(f'valid_urls : {valid_urls}')

        for f,r in url_replace.items():
            valid_urls = [u.replace(f,r) for u in valid_urls]

        return valid_urls 