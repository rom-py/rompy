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
import pandas as pd
from scipy.spatial import KDTree

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
            logger.debug(f'testing {test_url}')
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

def find_matchup_data(meas_ds,model_ds,var_map,time_thresh=None,KDtree_kwargs={}):
    """
    Finds nearest points between observed data and model output and returns corresonding nearest variable.
    
    Parameters
    ----------
    meas_ds : xarray.dataset
        Dataset containing measurements
    model_ds : xarray.dataset
        Dataset containing model output - currently only supports 
    var_map: dict
        Dictionary of key maps from variables in meas_ds to corresponding variable in model_ds
    time_thresh: 'None' (default), int or numpy.timedelta64
        Time threshold for finding matching measurements and model outputs. 
            None (Defaults): within 30 mins
            int:  passes int to np.timedelta(int,'m')
            np.timedelta
    KDtree_kwargs: dict
        Dictionary passed to scipy.spatial.KDtree function
        
    Returns
    ----------
    ds: xarray.dataset
        Xarray dataset containing measurements and nearest model outputs
    """
    
    ### Set time threshold
    if not time_thresh:
        time_thresh =  np.timedelta64(30,'m') ## Defaults to 30 mins
    elif (type(time_thresh) == int):
        time_thresh =  np.timedelta64(time_thresh,'m') ## Otherwise if user passes int or float turn this into td64
    elif (type(time_thresh) == np.timedelta64):
        None
    else: 
        raise ValueError('Unrecognised input for "time_thresh", must be "int", "np.timedelta64" or "None"')
        
    #### Find Indices of nearest point
    lats = model_ds['latitude'].values
    lons = model_ds['longitude'].values
    
    regular_grid = True # Bool flag for grid type, I dont know if this will hold for all unstructured grids? A bit unfamiliar with the outputs
    if len(lats.shape) != 1:
        regular_grid = False
        raise ValueError('Model dataset has unsupported grid type')
    
    if regular_grid: ## Regular grid = i.e. Perth domain
        mesh_lat,mesh_lon=np.meshgrid(lats,lons,indexing='ij')
        tree=KDTree(list(zip(mesh_lat.ravel(),mesh_lon.ravel())),**KDtree_kwargs)
        dist,grid_idx_r=tree.query(list(zip(meas_ds['latitude'],meas_ds['longitude'])))
        grid_idx_lat,grid_idx_lon=np.unravel_index(grid_idx_r,mesh_lon.shape)
    
    ### Initialise an output xarray dataset
    out_ds =  xr.Dataset()
    out_ds['longitude'] = xr.DataArray(meas_ds.longitude.values,dims=['longitude'],attrs={'long_name':'Measurement Longitude'})
    out_ds['latitude'] = xr.DataArray(meas_ds.latitude.values,dims=['latitude'],attrs={'long_name':'Measurement Latitude'})
    
    if regular_grid: ## Not sure if this is useful to user? Could drop to simplify 
        out_ds['model_lon_idx'] = xr.DataArray(grid_idx_lon,dims=['longitude'],attrs={'long_name':'Model longitude index'})
        out_ds['model_lat_idx'] = xr.DataArray(grid_idx_lat,dims=['latitude'],attrs={'long_name':'Model latitude index'})
        out_ds['model_lon'] = xr.DataArray(model_ds.longitude.values[grid_idx_lon],dims=['longitude'],attrs={'long_name':'Model Longitude'})
        out_ds['model_lat'] = xr.DataArray(model_ds.latitude.values[grid_idx_lat],dims=['latitude'],attrs={'long_name':'Model Latitude'})
    else: # Add other grid types
        raise ValueError('Model dataset has an unsupported grid type')

    ### Now loop through time stamp of observations 
    meas_times = meas_ds.time.values
    model_times = model_ds.time.values
    
    ## Initialise a dict that we can append to 
    out_dict =  {'time':[],'model_dt':[]}
    
    for meas_key,model_key in var_map.items():
        out_dict['meas_'+ meas_key] = []
        out_dict['model_'+ model_key] = []
        
    #loop through time, check if timestamps are within thresh and save out data
    for i,time in enumerate(meas_times):
        inds =  np.argwhere(np.abs(model_times - time) < time_thresh) ## within time_thresh
        if inds.size > 0:
            for time_idx in inds:
                out_dict['time'].append(time)
                out_dict['model_dt'].append(model_times[time_idx] - time)
                
                for meas_key,model_key in var_map.items():
                    out_dict['meas_'+meas_key].append(meas_ds[meas_key].isel({'time':i}).values)
                    if regular_grid:
                        out_dict['model_'+model_key].append(model_ds[model_key].isel({'time':time_idx,'latitude':grid_idx_lat,'longitude':grid_idx_lon}).values)
                    #else:  Add other grid types here
                    
    ### Then lets get out the measurement and model times
    out_ds['time'] =  xr.DataArray(np.asarray(out_dict.pop('time')).flatten(),dims=['time'],attrs={'long_name':'Measurement time'})
    out_ds['model_dt'] =  xr.DataArray(np.asarray(out_dict.pop('model_dt')).flatten(),dims=['time'],attrs={'long_name':'Time between measurement and model output'})
    
    for key,val in out_dict.items():
        out_ds[key] =  xr.DataArray(np.asarray(val).squeeze(),dims=['time','latitude','longitude'])
        
    out_ds['dist'] =  xr.DataArray(dist,dims=['observation'],attrs={'long_name':'Distance from observation to nearest model cell','units':'dDegrees'})
    
    #### This is to calculate which indices in the lat-lon grid contain field observations
    obs_latlon_inds = []
    for i,lat in enumerate(out_ds['latitude']):
        for j,lon in enumerate(out_ds['longitude']):
            if any(~np.isnan(out_ds['meas_hs'].values[:,i,j])):
                obs_latlon_inds.append([i,j])
    out_ds['obs_latlon_inds'] =   xr.DataArray(np.asarray(obs_latlon_inds),dims=['observation','ind'],attrs={'long_name':'Lat-lon indices for observation'})
    
    ### Add in attributes - would be nice to update the drivers to convert straight to nc's with catalog params which we could add here!
    if KDtree_kwargs:
        for val,key in KDtree_kwargs.items():
            out_ds.attrs['KDtree' + key] = val
    else: out_ds.attrs['KDtree params'] = 'Default'

    return out_ds