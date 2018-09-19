# -*- coding:UTF-8 -*-
from copy import deepcopy
from inspect import stack as INSPECTstack
from numpy import sign as NUMPYsign
from numpy import sqrt as NUMPYsqrt
from numpy import square as NUMPYsquare

# ENSO_metrics package functions:
from EnsoCollectionsLib import ReferenceRegions
import EnsoErrorsWarnings
from EnsoUvcdatToolsLib import ArrayOnes, arrayToList, ApplyLandmask, ApplyLandmaskToArea, AverageMeridional,\
    AverageZonal, CheckTime, Composite, DetectEvents, LinearRegressionAndNonlinearity, MyDerive, PreProcessTS,\
    ReadAreaSelectRegion, ReadLandmaskSelectRegion, ReadSelectRegionCheckUnits, RmsAxis, RmsHorizontal, RmsMeridional,\
    RmsTemporal, RmsZonal, SeasonalMean, Std, TimeBounds, TwoVarRegrid
from KeyArgLib import DefaultArgValues


# ---------------------------------------------------------------------------------------------------------------------#
#
# Library to compute ENSO metrics
# These functions have file names and variable names as inputs and metric as output
#
def BiasSstRmse(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                sstlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                sstlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The BiasSstRmse() function computes the SST spatial root mean square error (RMSE) in a 'box' (usually the tropical
    Pacific)

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param sstareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for SST
    :param sstareanamemodel: string
        name of areacell variable (areacella, areacello) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for SST
    :param sstlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param sstareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for SST
    :param sstareanameobs: string
        name of areacell variable (areacella, areacello) in 'sstareafileobs'
    :param sstlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for SST
    :param sstlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfileobs'
    :param box: string
        name of box ('tropical_pacific') for SST
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return rmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO RMSE'
    Units = 'C'
    Method = 'Spatial root mean square error of ' + box + ' sst'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'BiasSstRmse', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=box,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=box,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                                  **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
    del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasSstRmse: the modeled time-period is too short: " + str(len(sst_model))
                            + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasSstRmse: the observed time-period is too short: " + str(len(sst_obs))
                            + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    sst_model, Method = PreProcessTS(sst_model, Method, areacell=model_areacell, average='time', compute_anom=False,
                                     **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average='time', compute_anom=False, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        sst_model, sst_obs, Method = TwoVarRegrid(sst_model, sst_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                          'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Computes the root mean square difference
    sstRmse = RmsHorizontal(sst_model, sst_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(sst_model), 'observations': arrayToList(sst_obs),
                      'axisLat': list(sst_model.getAxis(0)[:]), 'axisLon': list(sst_model.getAxis(1)[:])}

    # Create output
    rmseMetric = {
        'name': Name, 'value': sstRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return rmseMetric


def BiasSstLatRmse(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                   sstlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                   sstlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The BiasSstLatRmse() function computes the SST meridional (latitude) root mean square error (RMSE) in a 'box'
    (usually 'nino3.3_LatExt')

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param sstareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for SST
    :param sstareanamemodel: string
        name of areacell variable (areacella, areacello) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for SST
    :param sstlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param sstareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for SST
    :param sstareanameobs: string
        name of areacell variable (areacella, areacello) in 'sstareafileobs'
    :param sstlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for SST
    :param sstlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfileobs'
    :param box: string
        name of box ('nino3.3_LatExt') for SST
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return LatRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO Meridional RMSE'
    Units = 'C'
    Method = 'Meridional root mean square error of ' + box + ' sst'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'BiasSstLatRmse', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=box,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=box,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                                  **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasSstLatRmse: the modeled time-period is too short: " + str(len(sst_model))
                            + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasSstLatRmse: the observed time-period is too short: "
                            + str(len(sst_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    sst_model, Method = PreProcessTS(sst_model, Method, areacell=model_areacell, average='time', compute_anom=False,
                                     **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average='time', compute_anom=False, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        sst_model, sst_obs, Method = TwoVarRegrid(sst_model, sst_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                          'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Zonal average
    sst_model = AverageZonal(sst_model)
    sst_obs = AverageZonal(sst_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageZonal', 15, **dict_debug)

    # Computes the root mean square difference
    sstRmse = RmsMeridional(sst_model, sst_obs, centered=centered_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(sst_model), 'observations': arrayToList(sst_obs),
                      'axis': list(sst_model.getAxis(0)[:])}

    # Create output
    LatRmseMetric = {
        'name': Name, 'value': sstRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return LatRmseMetric


def BiasSstLonRmse(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                   sstlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                   sstlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The BiasSstLonRmse() function computes the SST zonal (longitude) root mean square error (RMSE) in a 'box'
    (usually the Equatorial Pacific)

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param sstareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for SST
    :param sstareanamemodel: string
        name of areacell variable (areacella, areacello) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for SST
    :param sstlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param sstareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for SST
    :param sstareanameobs: string
        name of areacell variable (areacella, areacello) in 'sstareafileobs'
    :param sstlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for SST
    :param sstlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfileobs'
    :param box: string
        name of box ('equatorial_pacific') for SST
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return LonRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO Zonal RMSE'
    Units = 'C'
    Method = 'Zonal root mean square error of ' + box + ' sst'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'BiasSstLonRmse', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=box,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=box,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                              **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasSstLonRmse: the modeled time-period is too short: "
                            + str(len(sst_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasSstLonRmse: the observed time-period is too short: "
                            + str(len(sst_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    sst_model, Method = PreProcessTS(sst_model, Method, areacell=model_areacell, average='time', compute_anom=False,
                                     **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average='time', compute_anom=False, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        sst_model, sst_obs, Method = TwoVarRegrid(sst_model, sst_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                          'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Meridional average
    sst_model = AverageMeridional(sst_model)
    sst_obs = AverageMeridional(sst_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageMeridional', 15, **dict_debug)

    # Computes the root mean square difference
    sstRmse = RmsZonal(sst_model, sst_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(sst_model), 'observations': arrayToList(sst_obs),
                      'axis': list(sst_model.getAxis(0)[:])}

    # Create output
    LonRmseMetric = {
        'name': Name, 'value': sstRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return LonRmseMetric


def BiasPrRmse(prfilemodel, prnamemodel, prareafilemodel, prareanamemodel, prlandmaskfilemodel, prlandmasknamemodel,
               prfileobs, prnameobs, prareafileobs, prareanameobs, prlandmaskfileobs, prlandmasknameobs, box,
               centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The BiasPrRmse() function computes the PR (precipitation) spatial root mean square error (RMSE) in a 'box' (usually
    the tropical Pacific)

    Inputs:
    ------
    :param prfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled PR
    :param prnamemodel: string
        name of PR variable (pr, precip) in 'prfilemodel'
    :param prareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for PR
    :param prareanamemodel: string
        name of areacell variable (areacella, areacello) in 'prareafilemodel'
    :param prlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for PR
    :param prlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfilemodel'
    :param prfileobs: string
        path_to/filename of the file (NetCDF) of the observed PR
    :param prnameobs: string
        name of PR variable (pr, prec) in 'prfileobs'
    :param prareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for PR
    :param prareanameobs: string
        name of areacell variable (areacella, areacello) in 'prareafileobs'
    :param prlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for PR
    :param prlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfileobs'
    :param box: string
        name of box ('tropical_pacific') for PR
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return PrRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO Pr RMSE'
    Units = 'mm/day'
    Method = 'Spatial root mean square error of ' + box + ' Pr'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'BiasPrRmse', 10)
        dict_debug = {'file1': '(model) ' + prfilemodel, 'file2': '(obs) ' + prfileobs,
                      'var1': '(model) ' + prnamemodel, 'var2': '(obs) ' + prnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    pr_model = ReadSelectRegionCheckUnits(prfilemodel, prnamemodel, 'precipitations', box=box,
                                          time_bounds=kwargs['time_bounds_model'], **kwargs)
    pr_obs = ReadSelectRegionCheckUnits(prfileobs, prnameobs, 'precipitations', box=box,
                                        time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(pr_model)), 'time2': '(obs) ' + str(TimeBounds(pr_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

        # Read areacell
        if prareafilemodel:
            model_areacell = ReadAreaSelectRegion(prareafilemodel, areaname=prareanamemodel, box=box, **kwargs)
        else:
            model_areacell = ReadAreaSelectRegion(prfilemodel, areaname=prareanamemodel, box=box, **kwargs)
        if prareafileobs:
            obs_areacell = ReadAreaSelectRegion(prareafileobs, areaname=prareanameobs, box=box, **kwargs)
        else:
            obs_areacell = ReadAreaSelectRegion(prfileobs, areaname=prareanameobs, box=box, **kwargs)
        if debug is True:
            dict_debug = {}
            if model_areacell is not None:
                dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
                dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
            if obs_areacell is not None:
                dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
                dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

        # Read landmask
        if prlandmaskfilemodel:
            model_landmask = ReadLandmaskSelectRegion(prlandmaskfilemodel, landmaskname=prlandmasknamemodel, box=box,
                                                      **kwargs)
        else:
            model_landmask = ReadLandmaskSelectRegion(prfilemodel, landmaskname=prlandmasknamemodel, box=box,
                                                      **kwargs)
        if prlandmaskfileobs:
            obs_landmask = ReadLandmaskSelectRegion(prlandmaskfileobs, landmaskname=prlandmasknameobs, box=box,
                                                    **kwargs)
        else:
            obs_landmask = ReadLandmaskSelectRegion(prfileobs, landmaskname=prlandmasknameobs, box=box, **kwargs)
        if debug is True:
            dict_debug = {}
            if model_landmask is not None:
                dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
                dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
            if obs_landmask is not None:
                dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
                dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

        # Apply landmask
        if model_landmask is not None:
            pr_model = ApplyLandmask(pr_model, model_landmask, maskland=True, maskocean=False)
            if model_areacell is None:
                model_areacell = ArrayOnes(model_landmask, id='areacell')
            model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
            del model_landmask
        if obs_landmask is not None:
            pr_obs = ApplyLandmask(pr_obs, obs_landmask, maskland=True, maskocean=False)
            if obs_areacell is None:
                obs_areacell = ArrayOnes(obs_landmask, id='areacell')
            obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(pr_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasPrRmse: the modeled time-period is too short: " + str(len(pr_model))
                            + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(pr_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasPrRmse: the observed time-period is too short: " + str(len(pr_obs))
                            + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = pr_model.shape[0] / 12
    yearN_obs = pr_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(pr_model)
    actualtimeboundsobs = TimeBounds(pr_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    pr_model, Method = PreProcessTS(pr_model, Method, areacell=model_areacell, average='time', compute_anom=False,
                                    **kwargs)
    pr_obs, unneeded = PreProcessTS(pr_obs, '', areacell=obs_areacell, average='time', compute_anom=False, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        pr_model, pr_obs, Method = TwoVarRegrid(pr_model, pr_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                          'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Computes the root mean square difference
    pr_rmse = RmsHorizontal(pr_model, pr_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(pr_model), 'observations': arrayToList(pr_obs),
                      'axisLat': list(pr_model.getAxis(0)[:]), 'axisLon': list(pr_model.getAxis(1)[:])}

    # Create output
    PrRmseMetric = {
        'name': Name, 'value': pr_rmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return PrRmseMetric


def BiasPrLatRmse(prfilemodel, prnamemodel, prareafilemodel, prareanamemodel, prlandmaskfilemodel, prlandmasknamemodel,
                  prfileobs, prnameobs, prareafileobs, prareanameobs, prlandmaskfileobs, prlandmasknameobs, box,
                  centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The BiasPrLatRmse() function computes the PR (zonal wind stress) meridional (latitude) root mean square error (RMSE)
    in a 'box' (usually 'nino3.3_LatExt')

    Inputs:
    ------
    :param prfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled PR
    :param prnamemodel: string
        name of PR variable (pr, precip) in 'prfilemodel'
    :param prareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for PR
    :param prareanamemodel: string
        name of areacell variable (areacella, areacello) in 'prareafilemodel'
    :param prlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for PR
    :param prlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfilemodel'
    :param prfileobs: string
        path_to/filename of the file (NetCDF) of the observed PR
    :param prnameobs: string
        name of PR variable (pr, prec) in 'prfileobs'
    :param prareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for PR
    :param prareanameobs: string
        name of areacell variable (areacella, areacello) in 'prareafileobs'
    :param prlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for PR
    :param prlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfileobs'
    :param box: string
        name of box ('nino3.3_LatExt') for PR
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return PrLatRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO Pr Meridional RMSE'
    Units = 'mm/day'
    Method = 'Meridional root mean square error of ' + box + ' Pr'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'BiasPrLatRmse', 10)
        dict_debug = {'file1': '(model) ' + prfilemodel, 'file2': '(obs) ' + prfileobs,
                      'var1': '(model) ' + prnamemodel, 'var2': '(obs) ' + prnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    pr_model = ReadSelectRegionCheckUnits(prfilemodel, prnamemodel, 'precipitations', box=box,
                                          time_bounds=kwargs['time_bounds_model'], **kwargs)
    pr_obs = ReadSelectRegionCheckUnits(prfileobs, prnameobs, 'precipitations', box=box,
                                        time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(pr_model)), 'time2': '(obs) ' + str(TimeBounds(pr_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if prareafilemodel:
        model_areacell = ReadAreaSelectRegion(prareafilemodel, areaname=prareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(prfilemodel, areaname=prareanamemodel, box=box, **kwargs)
    if prareafileobs:
        obs_areacell = ReadAreaSelectRegion(prareafileobs, areaname=prareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(prfileobs, areaname=prareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if prlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(prlandmaskfilemodel, landmaskname=prlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(prfilemodel, landmaskname=prlandmasknamemodel, box=box,
                                                  **kwargs)
    if prlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(prlandmaskfileobs, landmaskname=prlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(prfileobs, landmaskname=prlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        pr_model = ApplyLandmask(pr_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        pr_obs = ApplyLandmask(pr_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
    del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(pr_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasPrLatRmse: the modeled time-period is too short: "
                            + str(len(pr_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(pr_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasPrLatRmse: the observed time-period is too short: "
                            + str(len(pr_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = pr_model.shape[0] / 12
    yearN_obs = pr_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(pr_model)
    actualtimeboundsobs = TimeBounds(pr_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    pr_model, Method = PreProcessTS(pr_model, Method, areacell=model_areacell, average='time', compute_anom=False,
                                    **kwargs)
    pr_obs, unneeded = PreProcessTS(pr_obs, '', areacell=obs_areacell, average='time', compute_anom=False, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        pr_model, pr_obs, Method = TwoVarRegrid(pr_model, pr_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                          'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Zonal average
    pr_model = AverageZonal(pr_model)
    pr_obs = AverageZonal(pr_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageZonal', 15, **dict_debug)

    # Computes the root mean square difference
    pr_rmse = RmsMeridional(pr_model, pr_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(pr_model), 'observations': arrayToList(pr_obs),
                      'axis': list(pr_model.getAxis(0)[:])}

    # Create output
    PrLatRmseMetric = {
        'name': Name, 'value': pr_rmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return PrLatRmseMetric


def BiasPrLonRmse(prfilemodel, prnamemodel, prareafilemodel, prareanamemodel, prlandmaskfilemodel, prlandmasknamemodel,
                  prfileobs, prnameobs, prareafileobs, prareanameobs, prlandmaskfileobs, prlandmasknameobs, box,
                  centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The BiasPrLonRmse() function computes the PR (zonal wind stress) zonal (longitude) root mean square error (RMSE) in
    a 'box' (usually the Equatorial Pacific)

    Inputs:
    ------
    :param prfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled PR
    :param prnamemodel: string
        name of PR variable (pr, precip) in 'prfilemodel'
    :param prareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for PR
    :param prareanamemodel: string
        name of areacell variable (areacella, areacello) in 'prareafilemodel'
    :param prlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for PR
    :param prlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfilemodel'
    :param prfileobs: string
        path_to/filename of the file (NetCDF) of the observed PR
    :param prnameobs: string
        name of PR variable (pr, prec) in 'prfileobs'
    :param prareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for PR
    :param prareanameobs: string
        name of areacell variable (areacella, areacello) in 'prareafileobs'
    :param prlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for PR
    :param prlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfileobs'
    :param box: string
        name of box (equatorial_pacific') for PR
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return PrLonRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO Pr Zonal RMSE'
    Units = 'mm/day'
    Method = 'Zonal root mean square error of ' + box + ' Pr'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'BiasPrLonRmse', 10)
        dict_debug = {'file1': '(model) ' + prfilemodel, 'file2': '(obs) ' + prfileobs,
                      'var1': '(model) ' + prnamemodel, 'var2': '(obs) ' + prnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    pr_model = ReadSelectRegionCheckUnits(prfilemodel, prnamemodel, 'precipitations', box=box,
                                          time_bounds=kwargs['time_bounds_model'], **kwargs)
    pr_obs = ReadSelectRegionCheckUnits(prfileobs, prnameobs, 'precipitations', box=box,
                                        time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(pr_model)), 'time2': '(obs) ' + str(TimeBounds(pr_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if prareafilemodel:
        model_areacell = ReadAreaSelectRegion(prareafilemodel, areaname=prareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(prfilemodel, areaname=prareanamemodel, box=box, **kwargs)
    if prareafileobs:
        obs_areacell = ReadAreaSelectRegion(prareafileobs, areaname=prareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(prfileobs, areaname=prareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if prlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(prlandmaskfilemodel, landmaskname=prlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(prfilemodel, landmaskname=prlandmasknamemodel, box=box,
                                                  **kwargs)
    if prlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(prlandmaskfileobs, landmaskname=prlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(prfileobs, landmaskname=prlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        pr_model = ApplyLandmask(pr_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        pr_obs = ApplyLandmask(pr_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
    del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(pr_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasPrLonRmse: the modeled time-period is too short: "
                            + str(len(pr_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(pr_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasPrLonRmse: the observed time-period is too short: "
                            + str(len(pr_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = pr_model.shape[0] / 12
    yearN_obs = pr_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(pr_model)
    actualtimeboundsobs = TimeBounds(pr_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    pr_model, Method = PreProcessTS(pr_model, Method, areacell=model_areacell, average='time', compute_anom=False,
                                    **kwargs)
    pr_obs, unneeded = PreProcessTS(pr_obs, '', areacell=obs_areacell, average='time', compute_anom=False, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        pr_model, pr_obs, Method = TwoVarRegrid(pr_model, pr_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                          'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Meridional average
    pr_model = AverageMeridional(pr_model)
    pr_obs = AverageMeridional(pr_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageMeridional', 15, **dict_debug)

    # Computes the root mean square difference
    pr_rmse = RmsZonal(pr_model, pr_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(pr_model), 'observations': arrayToList(pr_obs),
                      'axis': list(pr_model.getAxis(0)[:])}

    # Create output
    PrLonRmseMetric = {
        'name': Name, 'value': pr_rmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return PrLonRmseMetric


def BiasTauxRmse(tauxfilemodel, tauxnamemodel, tauxareafilemodel, tauxareanamemodel, tauxlandmaskfilemodel,
                 tauxlandmasknamemodel, tauxfileobs, tauxnameobs, tauxareafileobs, tauxareanameobs, tauxlandmaskfileobs,
                 tauxlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The BiasTauxRmse() function computes the TAUX (zonal wind stress) spatial root mean square error (RMSE) in a 'box'
    (usually the tropical Pacific)

    Inputs:
    ------
    :param tauxfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled TAUX
    :param tauxnamemodel: string
        name of TAUX variable (taux, tauu) in 'tauxfilemodel'
    :param tauxareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for TAUX
    :param tauxareanamemodel: string
        name of areacell variable (areacella, areacello) in 'tauxareafilemodel'
    :param tauxlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for TAUX
    :param tauxlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'tauxlandmaskfilemodel'
    :param tauxfileobs: string
        path_to/filename of the file (NetCDF) of the observed TAUX
    :param tauxnameobs: string
        name of TAUX variable (taux, tauu) in 'tauxfileobs'
    :param tauxareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for TAUX
    :param tauxareanameobs: string
        name of areacell variable (areacella, areacello) in 'tauxareafileobs'
    :param tauxlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for TAUX
    :param tauxlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'tauxlandmaskfileobs'
    :param box: string
        name of box (tropical_pacific') for TAUX
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled TAUX file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed TAUX file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return TauxRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO Taux RMSE'
    Units = '1e-3 N/m2'
    Method = 'Spatial root mean square error of ' + box + ' Taux'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'BiasTauxRmse', 10)
        dict_debug = {'file1': '(model) ' + tauxfilemodel, 'file2': '(obs) ' + tauxfileobs,
                      'var1': '(model) ' + tauxnamemodel, 'var2': '(obs) ' + tauxnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    taux_model = ReadSelectRegionCheckUnits(tauxfilemodel, tauxnamemodel, 'wind stress', box=box,
                                            time_bounds=kwargs['time_bounds_model'], **kwargs)
    taux_obs = ReadSelectRegionCheckUnits(tauxfileobs, tauxnameobs, 'wind stress', box=box,
                                          time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                      'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(taux_model)), 'time2': '(obs) ' + str(TimeBounds(taux_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if tauxareafilemodel:
        model_areacell = ReadAreaSelectRegion(tauxareafilemodel, areaname=tauxareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(tauxfilemodel, areaname=tauxareanamemodel, box=box, **kwargs)
    if tauxareafileobs:
        obs_areacell = ReadAreaSelectRegion(tauxareafileobs, areaname=tauxareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(tauxfileobs, areaname=tauxareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if tauxlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(tauxlandmaskfilemodel, landmaskname=tauxlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(tauxfilemodel, landmaskname=tauxlandmasknamemodel, box=box,
                                                  **kwargs)
    if tauxlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(tauxlandmaskfileobs, landmaskname=tauxlandmasknameobs, box=box,
                                                **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(tauxfileobs, landmaskname=tauxlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        taux_model = ApplyLandmask(taux_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        taux_obs = ApplyLandmask(taux_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
    del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(taux_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasTauxRmse: the modeled time-period is too short: "
                            + str(len(taux_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(taux_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasTauxRmse: the observed time-period is too short: "
                            + str(len(taux_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = taux_model.shape[0] / 12
    yearN_obs = taux_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(taux_model)
    actualtimeboundsobs = TimeBounds(taux_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    taux_model, Method = PreProcessTS(taux_model, Method, areacell=model_areacell, average='time', compute_anom=False,
                                      **kwargs)
    taux_obs, unneeded = PreProcessTS(taux_obs, '', areacell=obs_areacell, average='time', compute_anom=False, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                      'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        taux_model, taux_obs, Method = TwoVarRegrid(taux_model, taux_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                          'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Computes the root mean square difference
    taux_rmse = RmsHorizontal(taux_model, taux_obs, centered=centered_rmse, biased=biased_rmse) * 1e3

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(taux_model), 'observations': arrayToList(taux_obs),
                      'axisLat': list(taux_model.getAxis(0)[:]), 'axisLon': list(taux_model.getAxis(1)[:])}

    # Create output
    TauxRmseMetric = {
        'name': Name, 'value': taux_rmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return TauxRmseMetric


def BiasTauxLatRmse(tauxfilemodel, tauxnamemodel, tauxareafilemodel, tauxareanamemodel, tauxlandmaskfilemodel,
                    tauxlandmasknamemodel, tauxfileobs, tauxnameobs, tauxareafileobs, tauxareanameobs,
                    tauxlandmaskfileobs, tauxlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False,
                    **kwargs):
    """
    The BiasTauxLatRmse() function computes the TAUX (zonal wind stress) meridional (latitude) root mean square error
    (RMSE) in a 'box' (usually 'equatorial_pacific_LatExt')

    Inputs:
    ------
    :param tauxfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled TAUX
    :param tauxnamemodel: string
        name of TAUX variable (taux, tauu) in 'tauxfilemodel'
    :param tauxareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for TAUX
    :param tauxareanamemodel: string
        name of areacell variable (areacella, areacello) in 'tauxareafilemodel'
    :param tauxlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for TAUX
    :param tauxlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'tauxlandmaskfilemodel'
    :param tauxfileobs: string
        path_to/filename of the file (NetCDF) of the observed TAUX
    :param tauxnameobs: string
        name of TAUX variable (taux, tauu) in 'tauxfileobs'
    :param tauxareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for TAUX
    :param tauxareanameobs: string
        name of areacell variable (areacella, areacello) in 'tauxareafileobs'
    :param tauxlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for TAUX
    :param tauxlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'tauxlandmaskfileobs'
    :param box: string
        name of box (equatorial_pacific_LatExt') for TAUX
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled TAUX file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed TAUX file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return TauxLatRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO Taux Meridional RMSE'
    Units = '1e-3 N/m2'
    Method = 'Meridional root mean square error of ' + box + ' Taux'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'BiasTauxLatRmse', 10)
        dict_debug = {'file1': '(model) ' + tauxfilemodel, 'file2': '(obs) ' + tauxfileobs,
                      'var1': '(model) ' + tauxnamemodel, 'var2': '(obs) ' + tauxnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    taux_model = ReadSelectRegionCheckUnits(tauxfilemodel, tauxnamemodel, 'wind stress', box=box,
                                            time_bounds=kwargs['time_bounds_model'], **kwargs)
    taux_obs = ReadSelectRegionCheckUnits(tauxfileobs, tauxnameobs, 'wind stress', box=box,
                                          time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                      'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(taux_model)), 'time2': '(obs) ' + str(TimeBounds(taux_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if tauxareafilemodel:
        model_areacell = ReadAreaSelectRegion(tauxareafilemodel, areaname=tauxareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(tauxfilemodel, areaname=tauxareanamemodel, box=box, **kwargs)
    if tauxareafileobs:
        obs_areacell = ReadAreaSelectRegion(tauxareafileobs, areaname=tauxareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(tauxfileobs, areaname=tauxareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if tauxlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(tauxlandmaskfilemodel, landmaskname=tauxlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(tauxfilemodel, landmaskname=tauxlandmasknamemodel, box=box,
                                                  **kwargs)
    if tauxlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(tauxlandmaskfileobs, landmaskname=tauxlandmasknameobs, box=box,
                                                **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(tauxfileobs, landmaskname=tauxlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        taux_model = ApplyLandmask(taux_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        taux_obs = ApplyLandmask(taux_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
    del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(taux_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasTauxLatRmse: the modeled time-period is too short: "
                            + str(len(taux_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(taux_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasTauxLatRmse: the observed time-period is too short: "
                            + str(len(taux_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = taux_model.shape[0] / 12
    yearN_obs = taux_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(taux_model)
    actualtimeboundsobs = TimeBounds(taux_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    taux_model, Method = PreProcessTS(taux_model, Method, areacell=model_areacell, average='time', compute_anom=False,
                                      **kwargs)
    taux_obs, unneeded = PreProcessTS(taux_obs, '', areacell=obs_areacell, average='time', compute_anom=False, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                      'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        taux_model, taux_obs, Method = TwoVarRegrid(taux_model, taux_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                          'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Zonal average
    taux_model = AverageZonal(taux_model) * 1e3
    taux_obs = AverageZonal(taux_obs) * 1e3
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                      'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageZonal', 15, **dict_debug)

    # Computes the root mean square difference
    taux_rmse = RmsMeridional(taux_model, taux_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(taux_model), 'observations': arrayToList(taux_obs),
                      'axis': list(taux_model.getAxis(0)[:])}

    # Create output
    TauxLatRmseMetric = {
        'name': Name, 'value': taux_rmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return TauxLatRmseMetric


def BiasTauxLonRmse(tauxfilemodel, tauxnamemodel, tauxareafilemodel, tauxareanamemodel, tauxlandmaskfilemodel,
                    tauxlandmasknamemodel, tauxfileobs, tauxnameobs, tauxareafileobs, tauxareanameobs,
                    tauxlandmaskfileobs, tauxlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False,
                    **kwargs):
    """
    The BiasTauxLonRmse() function computes the TAUX (zonal wind stress) zonal (longitude) root mean square error (RMSE)
    in a 'box' (usually the Equatorial Pacific)

    Inputs:
    ------
    :param tauxfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled TAUX
    :param tauxnamemodel: string
        name of TAUX variable (taux, tauu) in 'tauxfilemodel'
    :param tauxareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for TAUX
    :param tauxareanamemodel: string
        name of areacell variable (areacella, areacello) in 'tauxareafilemodel'
    :param tauxlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for TAUX
    :param tauxlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'tauxlandmaskfilemodel'
    :param tauxfileobs: string
        path_to/filename of the file (NetCDF) of the observed TAUX
    :param tauxnameobs: string
        name of TAUX variable (taux, tauu) in 'tauxfileobs'
    :param tauxareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for TAUX
    :param tauxareanameobs: string
        name of areacell variable (areacella, areacello) in 'tauxareafileobs'
    :param tauxlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for TAUX
    :param tauxlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'tauxlandmaskfileobs'
    :param box: string
        name of box (equatorial_pacific') for TAUX
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled TAUX file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed TAUX file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return TauxLonRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO Taux Zonal RMSE'
    Units = '1e-3 N/m2'
    Method = 'Zonal root mean square error of ' + box + ' Taux'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'BiasTauxLonRmse', 10)
        dict_debug = {'file1': '(model) ' + tauxfilemodel, 'file2': '(obs) ' + tauxfileobs,
                      'var1': '(model) ' + tauxnamemodel, 'var2': '(obs) ' + tauxnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    taux_model = ReadSelectRegionCheckUnits(tauxfilemodel, tauxnamemodel, 'wind stress', box=box,
                                            time_bounds=kwargs['time_bounds_model'], **kwargs)
    taux_obs = ReadSelectRegionCheckUnits(tauxfileobs, tauxnameobs, 'wind stress', box=box,
                                          time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                      'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(taux_model)), 'time2': '(obs) ' + str(TimeBounds(taux_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if tauxareafilemodel:
        model_areacell = ReadAreaSelectRegion(tauxareafilemodel, areaname=tauxareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(tauxfilemodel, areaname=tauxareanamemodel, box=box, **kwargs)
    if tauxareafileobs:
        obs_areacell = ReadAreaSelectRegion(tauxareafileobs, areaname=tauxareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(tauxfileobs, areaname=tauxareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if tauxlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(tauxlandmaskfilemodel, landmaskname=tauxlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(tauxfilemodel, landmaskname=tauxlandmasknamemodel, box=box,
                                                  **kwargs)
    if tauxlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(tauxlandmaskfileobs, landmaskname=tauxlandmasknameobs, box=box,
                                                **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(tauxfileobs, landmaskname=tauxlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        taux_model = ApplyLandmask(taux_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        taux_obs = ApplyLandmask(taux_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
    del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(taux_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasTauxLonRmse: the modeled time-period is too short: "
                            + str(len(taux_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(taux_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "BiasTauxLonRmse: the observed time-period is too short: "
                            + str(len(taux_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = taux_model.shape[0] / 12
    yearN_obs = taux_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(taux_model)
    actualtimeboundsobs = TimeBounds(taux_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    taux_model, Method = PreProcessTS(taux_model, Method, areacell=model_areacell, average='time', compute_anom=False,
                                      **kwargs)
    taux_obs, unneeded = PreProcessTS(taux_obs, '', areacell=obs_areacell, average='time', compute_anom=False, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                      'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        taux_model, taux_obs, Method = TwoVarRegrid(taux_model, taux_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                          'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Meridional average
    taux_model = AverageMeridional(taux_model) * 1e3
    taux_obs = AverageMeridional(taux_obs) * 1e3
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in taux_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in taux_obs.getAxisList()]),
                      'shape1': '(model) ' + str(taux_model.shape), 'shape2': '(obs) ' + str(taux_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageMeridional', 15, **dict_debug)

    # Computes the root mean square difference
    taux_rmse = RmsZonal(taux_model, taux_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(taux_model), 'observations': arrayToList(taux_obs),
                      'axis': list(taux_model.getAxis(0)[:])}

    # Create output
    TauxLonRmseMetric = {
        'name': Name, 'value': taux_rmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return TauxLonRmseMetric


def EnsoAlphaLhf(sstfile, sstname, sstareafile, sstareaname, sstlandmaskfile, sstlandmaskname, sstbox, lhffile, lhfname,
                 lhfareafile, lhfareaname, lhflandmaskfile, lhflandmaskname, lhfbox, debug=False, **kwargs):
    """
    The EnsoAlphaLhf() function computes the regression of 'lhfbox' lhfA (latent heat flux anomalies) over 'sstbox' sstA
    (usually the regression of nino3 lhfA over nino3 sstA)

    Author:	Yann Planton : yann.planton@locean-ipsl.upmc.fr
    Co-author:

    Created on Thu Oct  5 2017

    Inputs:
    ------
    :param sstfile: string
        path_to/filename of the file (NetCDF) of SST
    :param sstname: string
        name of SST variable (tos, ts) in 'sstfile'
    :param sstareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SST
    :param sstareaname: string
        name of areacell variable (areacella, areacello) in 'sstareafile'
    :param sstlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SST
    :param sstlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfile'
    :param sstbox: string
        name of box (nino3') for SST
    :param lhffile: string
        path_to/filename of the file (NetCDF) of LHF
    :param lhfname: string
        name of LHF variable (lhf, hfls) in 'lhffile'
    :param lhfareafile: string
        path_to/filename of the file (NetCDF) of the areacell for LHF
    :param lhfareaname: string
        name of areacell variable (areacella, areacello) in 'lhfareafile'
    :param lhflandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for LHF
    :param lhflandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'lhflandmaskfile'
    :param lhfbox: string
        name of box (nino3') for LHF
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return alphaLhfMetric: dict
        name, value, value_error, units, method, nyears, time_frequency, time_period, ref, nonlinearity,
        nonlinearity_error

    Method:
    -------
        uses tools from uvcdat library

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Latent feedback (alpha_lh)'
    Units = 'W/m2/C'
    Method = 'Regression of ' + lhfbox + ' lhfA over ' + sstbox + ' sstA'
    Method_NL = 'The nonlinearity is the regression computed when sstA<0 minus the regression computed when sstA>0'
    Ref = 'Using CDAT regression calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'EnsoAlphaLhf', 10)
        dict_debug = {'file1': '(sst) ' + sstfile, 'file2': '(lhf) ' + lhffile, 'var1': '(sst) ' + sstname,
                      'var2': '(lhf) ' + lhfname}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst = ReadSelectRegionCheckUnits(sstfile, sstname, 'temperature', box=sstbox, **kwargs)
    lhf = ReadSelectRegionCheckUnits(lhffile, lhfname, 'heat flux', box=lhfbox, **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(lhf) ' + str([ax.id for ax in lhf.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(lhf) ' + str(lhf.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(lhf) ' + str(TimeBounds(lhf))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafile:
        sst_areacell = ReadAreaSelectRegion(sstareafile, areaname=sstareaname, box=sstbox, **kwargs)
    else:
        sst_areacell = ReadAreaSelectRegion(sstfile, areaname=sstareaname, box=sstbox, **kwargs)
    if lhfareafile:
        lhf_areacell = ReadAreaSelectRegion(lhfareafile, areaname=lhfareaname, box=lhfbox, **kwargs)
    else:
        lhf_areacell = ReadAreaSelectRegion(lhffile, areaname=lhfareaname, box=lhfbox, **kwargs)
    if debug is True:
        dict_debug = {}
        if sst_areacell is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_areacell.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_areacell.shape)
        if lhf_areacell is not None:
            dict_debug['axes2'] = '(lhf) ' + str([ax.id for ax in lhf_areacell.getAxisList()])
            dict_debug['shape2'] = '(lhf) ' + str(lhf_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfile:
        sst_landmask = ReadLandmaskSelectRegion(sstlandmaskfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    else:
        sst_landmask = ReadLandmaskSelectRegion(sstfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    if lhflandmaskfile:
        lhf_landmask = ReadLandmaskSelectRegion(lhflandmaskfile, landmaskname=lhflandmaskname, box=lhfbox, **kwargs)
    else:
        lhf_landmask = ReadLandmaskSelectRegion(lhffile, landmaskname=lhflandmaskname, box=lhfbox, **kwargs)
    if debug is True:
        dict_debug = {}
        if sst_landmask is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_landmask.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_landmask.shape)
        if lhf_landmask is not None:
            dict_debug['axes2'] = '(lhf) ' + str([ax.id for ax in lhf_landmask.getAxisList()])
            dict_debug['shape2'] = '(lhf) ' + str(lhf_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if sst_landmask is not None:
        sst = ApplyLandmask(sst, sst_landmask, maskland=True, maskocean=False)
        if sst_areacell is None:
            sst_areacell = ArrayOnes(sst_landmask, id='areacell')
        sst_areacell = ApplyLandmaskToArea(sst_areacell, sst_landmask, maskland=True, maskocean=False)
        del sst_landmask
    if lhf_landmask is not None:
        lhf = ApplyLandmask(lhf, lhf_landmask, maskland=True, maskocean=False)
        if lhf_areacell is None:
            lhf_areacell = ArrayOnes(lhf_landmask, id='areacell')
        lhf_areacell = ApplyLandmaskToArea(lhf_areacell, lhf_landmask, maskland=True, maskocean=False)
    del lhf_landmask

    # Checks if the same time period is used for both variables and if the minimum number of time steps is respected
    sst, lhf = CheckTime(sst, lhf, metric_name='EnsoAlphaLhf', **kwargs)

    # Number of years
    yearN = sst.shape[0] / 12

    # Time period
    actualtimebounds = TimeBounds(sst)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smooths TS, averages horizontally)
    sst, Method = PreProcessTS(sst, Method, areacell=sst_areacell, average='horizontal', compute_anom=True, **kwargs)
    lhf, unneeded = PreProcessTS(lhf, '', areacell=lhf_areacell, average='horizontal', compute_anom=True, **kwargs)
    del sst_areacell, lhf_areacell
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(lhf) ' + str([ax.id for ax in lhf.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(lhf) ' + str(lhf.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(lhf) ' + str(TimeBounds(lhf))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Computes the linear regression for all points, for SSTA >=0 and for SSTA<=0
    alphaLhf, alphaLhfPos, alphaLhfNeg = LinearRegressionAndNonlinearity(lhf, sst, return_stderr=True)

    # Create output
    alphaLhfMetric = {
        'name': Name, 'value': alphaLhf[0], 'value_error': alphaLhf[1], 'units': Units, 'method': Method,
        'method_nonlinearity': Method_NL, 'nyears': yearN, 'time_frequency': kwargs['frequency'],
        'time_period': actualtimebounds, 'ref': Ref, 'nonlinearity': alphaLhfNeg[0] - alphaLhfPos[0],
        'nonlinearity_error': alphaLhfNeg[1] + alphaLhfPos[1],
    }
    return alphaLhfMetric


def EnsoAlphaLwr(sstfile, sstname, sstareafile, sstareaname, sstlandmaskfile, sstlandmaskname, sstbox, lwrfile, lwrname,
                 lwrareafile, lwrareaname, lwrlandmaskfile, lwrlandmaskname, lwrbox, debug=False, **kwargs):
    """
    The EnsoAlphaLwr() function computes the regression of 'lwrbox' lwrA (net surface longwave radiation anomalies) over
    'sstbox' sstA (usually the regression of nino3 lwrA over nino3 sstA)

    The net surface longwave radiation is not a CMIP variable.
    Either the user computes it and sends the filename and the varname or he feeds into lwrfile and lwrname of this
    function a list() of downward and upward radiations files and variable names (CMIP: rlds and rlus)

    Author:	Yann Planton : yann.planton@locean-ipsl.upmc.fr
    Co-author:

    Created on Thu Oct  5 2017

    Inputs:
    ------
    :param sstfile: string
        path_to/filename of the file (NetCDF) of SST
    :param sstname: string
        name of SST variable (tos, ts) in 'sstfile'
    :param sstareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SST
    :param sstareaname: string
        name of areacell variable (areacella, areacello) in 'sstareafile'
    :param sstlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SST
    :param sstlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfile'
    :param sstbox: string
        name of box (nino3') for SST
    :param lwrfile: string
        path_to/filename of the file (NetCDF) of LWR
    :param lwrname: string
        name of LWR variable (lwr, rlds - rlus) (may be a list of variables) in 'lwrfile'
    :param lwrareafile: string
        path_to/filename of the file (NetCDF) of the areacell for LWR
    :param lwrareaname: string
        name of areacell variable (areacella, areacello) in 'lwrareafile'
    :param lwrlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for LWR
    :param lwrlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'lwrlandmaskfile'
    :param lwrbox: string
        name of box (nino3') for LWR
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return alphaLwrMetric: dict
        name, value, value_error, units, method, nyears, time_frequency, time_period, ref, nonlinearity,
        nonlinearity_error

    Method:
    -------
        uses tools from uvcdat library

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Longwave feedback (alpha_lwr)'
    Units = 'W/m2/C'
    Method = 'Regression of ' + lwrbox + ' lwrA over ' + sstbox + ' sstA'
    Method_NL = 'The nonlinearity is the regression computed when sstA<0 minus the regression computed when sstA>0'
    Ref = 'Using CDAT regression calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'EnsoAlphaLwr', 10)
        dict_debug = {'file1': '(sst) ' + sstfile, 'file2': '(lwr) ' + lwrfile, 'var1': '(sst) ' + sstname,
                      'var2': '(lwr) ' + lwrname}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst = ReadSelectRegionCheckUnits(sstfile, sstname, 'temperature', box=sstbox, **kwargs)
    dict_var = dict()
    if isinstance(lwrfile, basestring):
        dict_var[lwrname] = ReadSelectRegionCheckUnits(lwrfile, lwrname, 'heat flux', box=lwrbox, **kwargs)
    else:
        for ii in range(len(lwrfile)):
            filename, varname = lwrfile[ii], lwrname[ii]
            dict_var[varname] = ReadSelectRegionCheckUnits(filename, varname, 'heat flux', box=lwrbox, **kwargs)
    lwr = MyDerive(kwargs['project_interpreter_var2'], 'lwr', dict_var)
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(lwr) ' + str([ax.id for ax in lwr.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(lwr) ' + str(lwr.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(lwr) ' + str(TimeBounds(lwr))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafile:
        sst_areacell = ReadAreaSelectRegion(sstareafile, areaname=sstareaname, box=sstbox, **kwargs)
    else:
        sst_areacell = ReadAreaSelectRegion(sstfile, areaname=sstareaname, box=sstbox, **kwargs)
    if lwrareafile:
        if isinstance(lwrareafile, basestring):
            lwr_areacell = ReadAreaSelectRegion(lwrareafile, areaname=lwrareaname, box=lwrbox, **kwargs)
        else:
            for ii in range(len(lwrareafile)):
                lwr_areacell = ReadAreaSelectRegion(lwrareafile[ii], areaname=lwrareaname[ii], box=lwrbox, **kwargs)
                if lwr_areacell is not None:
                    break
    else:
        if isinstance(lwrfile, basestring):
            lwr_areacell = ReadAreaSelectRegion(lwrfile, areaname=lwrareaname, box=lwrbox, **kwargs)
        else:
            for ii in range(len(lwrfile)):
                lwr_areacell = ReadAreaSelectRegion(lwrfile[ii], areaname=lwrareaname[ii], box=lwrbox, **kwargs)
                if lwr_areacell is not None:
                    break
    if debug is True:
        dict_debug = {}
        if sst_areacell is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_areacell.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_areacell.shape)
        if lwr_areacell is not None:
            dict_debug['axes2'] = '(lwr) ' + str([ax.id for ax in lwr_areacell.getAxisList()])
            dict_debug['shape2'] = '(lwr) ' + str(lwr_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfile:
        sst_landmask = ReadLandmaskSelectRegion(sstlandmaskfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    else:
        sst_landmask = ReadLandmaskSelectRegion(sstfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    if lwrlandmaskfile:
        if isinstance(lwrlandmaskfile, basestring):
            lwr_landmask = ReadAreaSelectRegion(lwrlandmaskfile, areaname=lwrlandmaskname, box=lwrbox, **kwargs)
        else:
            for ii in range(len(lwrlandmaskfile)):
                lwr_landmask = ReadAreaSelectRegion(lwrlandmaskfile[ii], areaname=lwrlandmaskname[ii], box=lwrbox,
                                                    **kwargs)
                if lwr_landmask is not None:
                    break
    else:
        if isinstance(lwrfile, basestring):
            lwr_landmask = ReadAreaSelectRegion(lwrfile, areaname=lwrlandmaskname, box=lwrbox, **kwargs)
        else:
            for ii in range(len(lwrfile)):
                lwr_landmask = ReadAreaSelectRegion(lwrfile[ii], areaname=lwrlandmaskname[ii], box=lwrbox, **kwargs)
                if lwr_landmask is not None:
                    break
    if debug is True:
        dict_debug = {}
        if sst_landmask is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_landmask.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_landmask.shape)
        if lwr_landmask is not None:
            dict_debug['axes2'] = '(lwr) ' + str([ax.id for ax in lwr_landmask.getAxisList()])
            dict_debug['shape2'] = '(lwr) ' + str(lwr_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if sst_landmask is not None:
        sst = ApplyLandmask(sst, sst_landmask, maskland=True, maskocean=False)
        if sst_areacell is None:
            sst_areacell = ArrayOnes(sst_landmask, id='areacell')
        sst_areacell = ApplyLandmaskToArea(sst_areacell, sst_landmask, maskland=True, maskocean=False)
        del sst_landmask
    if lwr_landmask is not None:
        lwr = ApplyLandmask(lwr, lwr_landmask, maskland=True, maskocean=False)
        if lwr_areacell is None:
            lwr_areacell = ArrayOnes(lwr_landmask, id='areacell')
        lwr_areacell = ApplyLandmaskToArea(lwr_areacell, lwr_landmask, maskland=True, maskocean=False)
    del lwr_landmask

    # Checks if the same time period is used for both variables and if the minimum number of time steps is respected
    sst, lwr = CheckTime(sst, lwr, metric_name='EnsoAlphaLwr', **kwargs)

    # Number of years
    yearN = sst.shape[0] / 12

    # Time period
    actualtimebounds = TimeBounds(sst)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smooths TS, averages horizontally)
    sst, Method = PreProcessTS(sst, Method, areacell=sst_areacell, average='horizontal', compute_anom=True, **kwargs)
    lwr, unneeded = PreProcessTS(lwr, '', areacell=lwr_areacell, average='horizontal', compute_anom=True, **kwargs)
    del sst_areacell, lwr_areacell
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(lwr) ' + str([ax.id for ax in lwr.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(lwr) ' + str(lwr.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(lwr) ' + str(TimeBounds(lwr))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Computes the linear regression for all points, for SSTA >=0 and for SSTA<=0
    alphaLwr, alphaLwrPos, alphaLwrNeg = LinearRegressionAndNonlinearity(lwr, sst, return_stderr=True)

    # Create output
    alphaLwrMetric = {
        'name': Name, 'value': alphaLwr[0], 'value_error': alphaLwr[1], 'units': Units, 'method': Method,
        'method_nonlinearity': Method_NL, 'nyears': yearN, 'time_frequency': kwargs['frequency'],
        'time_period': actualtimebounds, 'ref': Ref, 'nonlinearity': alphaLwrNeg[0] - alphaLwrPos[0],
        'nonlinearity_error': alphaLwrNeg[1] + alphaLwrPos[1],
    }
    return alphaLwrMetric


def EnsoAlphaShf(sstfile, sstname, sstareafile, sstareaname, sstlandmaskfile, sstlandmaskname, sstbox, shffile, shfname,
                 shfareafile, shfareaname, shflandmaskfile, shflandmaskname, shfbox, debug=False, **kwargs):
    """
    The EnsoAlphaShf() function computes the regression of 'shfbox' shfA (sensible heat flux anomalies) over 'sstbox'
    sstA (usually the regression of nino3 shfA over nino3 sstA)

    Author:	Yann Planton : yann.planton@locean-ipsl.upmc.fr
    Co-author:

    Created on Thu Oct  5 2017

    Inputs:
    ------
    :param sstfile: string
        path_to/filename of the file (NetCDF) of SST
    :param sstname: string
        name of SST variable (tos, ts) in 'sstfile'
    :param sstareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SST
    :param sstareaname: string
        name of areacell variable (areacella, areacello) in 'sstareafile'
    :param sstlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SST
    :param sstlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfile'
    :param sstbox: string
        name of box (nino3') for SST
    :param shffile: string
        path_to/filename of the file (NetCDF) of SHF
    :param shfname: string
        name of SHF variable (shf, hfss) in 'shffile'
    :param shfareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SHF
    :param shfareaname: string
        name of areacell variable (areacella, areacello) in 'shfareafile'
    :param shflandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SHF
    :param shflandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'shflandmaskfile'
    :param shfbox: string
        name of box (nino3') for SHF
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return alphaShfMetric: dict
        name, value, value_error, units, method, nyears, time_frequency, time_period, ref, nonlinearity,
        nonlinearity_error

    Method:
    -------
        uses tools from uvcdat library

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Sensible feedback (alpha_sh)'
    Units = 'W/m2/C'
    Method = 'Regression of ' + shfbox + ' shfA over ' + sstbox + ' sstA'
    Method_NL = 'The nonlinearity is the regression computed when sstA<0 minus the regression computed when sstA>0'
    Ref = 'Using CDAT regression calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'EnsoAlphaShf', 10)
        dict_debug = {'file1': '(sst) ' + sstfile, 'file2': '(shf) ' + shffile, 'var1': '(sst) ' + sstname,
                      'var2': '(shf) ' + shfname}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst = ReadSelectRegionCheckUnits(sstfile, sstname, 'temperature', box=sstbox, **kwargs)
    shf = ReadSelectRegionCheckUnits(shffile, shfname, 'heat flux', box=shfbox, **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(shf) ' + str([ax.id for ax in shf.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(shf) ' + str(shf.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(shf) ' + str(TimeBounds(shf))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafile:
        sst_areacell = ReadAreaSelectRegion(sstareafile, areaname=sstareaname, box=sstbox, **kwargs)
    else:
        sst_areacell = ReadAreaSelectRegion(sstfile, areaname=sstareaname, box=sstbox, **kwargs)
    if shfareafile:
        shf_areacell = ReadAreaSelectRegion(shfareafile, areaname=shfareaname, box=shfbox, **kwargs)
    else:
        shf_areacell = ReadAreaSelectRegion(shffile, areaname=shfareaname, box=shfbox, **kwargs)
    if debug is True:
        dict_debug = {}
        if sst_areacell is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_areacell.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_areacell.shape)
        if shf_areacell is not None:
            dict_debug['axes2'] = '(shf) ' + str([ax.id for ax in shf_areacell.getAxisList()])
            dict_debug['shape2'] = '(shf) ' + str(shf_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfile:
        sst_landmask = ReadLandmaskSelectRegion(sstlandmaskfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    else:
        sst_landmask = ReadLandmaskSelectRegion(sstfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    if shflandmaskfile:
        shf_landmask = ReadLandmaskSelectRegion(shflandmaskfile, landmaskname=shflandmaskname, box=shfbox, **kwargs)
    else:
        shf_landmask = ReadLandmaskSelectRegion(shffile, landmaskname=shflandmaskname, box=shfbox, **kwargs)
    if debug is True:
        dict_debug = {}
        if sst_landmask is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_landmask.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_landmask.shape)
        if shf_landmask is not None:
            dict_debug['axes2'] = '(shf) ' + str([ax.id for ax in shf_landmask.getAxisList()])
            dict_debug['shape2'] = '(shf) ' + str(shf_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if sst_landmask is not None:
        sst = ApplyLandmask(sst, sst_landmask, maskland=True, maskocean=False)
        if sst_areacell is None:
            sst_areacell = ArrayOnes(sst_landmask, id='areacell')
        sst_areacell = ApplyLandmaskToArea(sst_areacell, sst_landmask, maskland=True, maskocean=False)
        del sst_landmask
    if shf_landmask is not None:
        shf = ApplyLandmask(shf, shf_landmask, maskland=True, maskocean=False)
        if shf_areacell is None:
            shf_areacell = ArrayOnes(shf_landmask, id='areacell')
        shf_areacell = ApplyLandmaskToArea(shf_areacell, shf_landmask, maskland=True, maskocean=False)
    del shf_landmask

    # Checks if the same time period is used for both variables and if the minimum number of time steps is respected
    sst, shf = CheckTime(sst, shf, metric_name='EnsoAlphaShf', **kwargs)

    # Number of years
    yearN = sst.shape[0] / 12

    # Time period
    actualtimebounds = TimeBounds(sst)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smooths TS, averages horizontally)
    sst, Method = PreProcessTS(sst, Method, areacell=sst_areacell, average='horizontal', compute_anom=True, **kwargs)
    shf, unneeded = PreProcessTS(shf, '', areacell=shf_areacell, average='horizontal', compute_anom=True, **kwargs)
    del sst_areacell, shf_areacell
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(shf) ' + str([ax.id for ax in shf.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(shf) ' + str(shf.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(shf) ' + str(TimeBounds(shf))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Computes the linear regression for all points, for SSTA >=0 and for SSTA<=0
    alphaShf, alphaShfPos, alphaShfNeg = LinearRegressionAndNonlinearity(shf, sst, return_stderr=True)

    # Create output
    alphaShfMetric = {
        'name': Name, 'value': alphaShf[0], 'value_error': alphaShf[1], 'units': Units, 'method': Method,
        'method_nonlinearity': Method_NL, 'nyears': yearN, 'time_frequency': kwargs['frequency'],
        'time_period': actualtimebounds, 'ref': Ref, 'nonlinearity': alphaShfNeg[0] - alphaShfPos[0],
        'nonlinearity_error': alphaShfNeg[1] + alphaShfPos[1],
    }
    return alphaShfMetric


def EnsoAlphaSwr(sstfile, sstname, sstareafile, sstareaname, sstlandmaskfile, sstlandmaskname, sstbox, swrfile, swrname,
                 swrareafile, swrareaname, swrlandmaskfile, swrlandmaskname, swrbox, debug=False, **kwargs):
    """
    The EnsoAlphaSwr() function computes the regression of 'swrbox' swrA (net surface shortwave radiation anomalies)
    over 'sstbox' sstA (usually the regression of nino3 swrA over nino3 sstA)

    The net surface shortwave radiation is not a CMIP variable.
    Either the user computes it and sends the filename and the varname or he feeds into swrfile and swrname of this
    function a list() of downward and upward radiations files and variable names (CMIP: rsds and rsus)

    Author:	Yann Planton : yann.planton@locean-ipsl.upmc.fr
    Co-author:

    Created on Thu Oct  5 2017

    Inputs:
    ------
    :param sstfile: string
        path_to/filename of the file (NetCDF) of SST
    :param sstname: string
        name of SST variable (tos, ts) in 'sstfile'
    :param sstareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SST
    :param sstareaname: string
        name of areacell variable (areacella, areacello) in 'sstareafile'
    :param sstlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SST
    :param sstlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfile'
    :param sstbox: string
        name of box (nino3') for SST
    :param swrfile: string
        path_to/filename of the file (NetCDF) of SWR
    :param swrname: string
        name of SWR variable (swr, rsds - rsus) (may be a list of variables) in 'swrfile'
    :param swrareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SWR
    :param swrareaname: string
        name of areacell variable (areacella, areacello) in 'swrareafile'
    :param swrlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SWR
    :param swrlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'swrlandmaskfile'
    :param swrbox: string
        name of box (nino3') for SWR
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return alphaSwrMetric: dict
        name, value, value_error, units, method, nyears, time_frequency, time_period, ref, nonlinearity,
        nonlinearity_error

    Method:
    -------
        uses tools from uvcdat library

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Shortwave feedback (alpha_swr)'
    Units = 'W/m2/C'
    Method = 'Regression of ' + swrbox + ' swrA over ' + sstbox + ' sstA'
    Method_NL = 'The nonlinearity is the regression computed when sstA<0 minus the regression computed when sstA>0'
    Ref = 'Using CDAT regression calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'EnsoAlphaSwr', 10)
        dict_debug = {'file1': '(sst) ' + sstfile, 'file2': '(swr) ' + swrfile, 'var1': '(sst) ' + sstname,
                      'var2': '(swr) ' + swrname}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst = ReadSelectRegionCheckUnits(sstfile, sstname, 'temperature', box=sstbox, **kwargs)
    dict_var = dict()
    if isinstance(swrfile, basestring):
        dict_var[swrname] = ReadSelectRegionCheckUnits(swrfile, swrname, 'heat flux', box=swrbox, **kwargs)
    else:
        for ii in range(len(swrfile)):
            filename, varname = swrfile[ii], swrname[ii]
            dict_var[varname] = ReadSelectRegionCheckUnits(filename, varname, 'heat flux', box=swrbox, **kwargs)
    swr = MyDerive(kwargs['project_interpreter_var2'], 'swr', dict_var)
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(swr) ' + str([ax.id for ax in swr.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(swr) ' + str(swr.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(swr) ' + str(TimeBounds(swr))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafile:
        sst_areacell = ReadAreaSelectRegion(sstareafile, areaname=sstareaname, box=sstbox, **kwargs)
    else:
        sst_areacell = ReadAreaSelectRegion(sstfile, areaname=sstareaname, box=sstbox, **kwargs)
    if swrareafile:
        if isinstance(swrareafile, basestring):
            swr_areacell = ReadAreaSelectRegion(swrareafile, areaname=swrareaname, box=swrbox, **kwargs)
        else:
            for ii in range(len(swrareafile)):
                swr_areacell = ReadAreaSelectRegion(swrareafile[ii], areaname=swrareaname[ii], box=swrbox, **kwargs)
                if swr_areacell is not None:
                    break
    else:
        if isinstance(swrfile, basestring):
            swr_areacell = ReadAreaSelectRegion(swrfile, areaname=swrareaname, box=swrbox, **kwargs)
        else:
            for ii in range(len(swrfile)):
                swr_areacell = ReadAreaSelectRegion(swrfile[ii], areaname=swrareaname[ii], box=swrbox, **kwargs)
                if swr_areacell is not None:
                    break
    if debug is True:
        dict_debug = {}
        if sst_areacell is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_areacell.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_areacell.shape)
        if swr_areacell is not None:
            dict_debug['axes2'] = '(swr) ' + str([ax.id for ax in swr_areacell.getAxisList()])
            dict_debug['shape2'] = '(swr) ' + str(swr_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfile:
        sst_landmask = ReadLandmaskSelectRegion(sstlandmaskfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    else:
        sst_landmask = ReadLandmaskSelectRegion(sstfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    if swrlandmaskfile:
        if isinstance(swrlandmaskfile, basestring):
            swr_landmask = ReadAreaSelectRegion(swrlandmaskfile, areaname=swrlandmaskname, box=swrbox, **kwargs)
        else:
            for ii in range(len(swrlandmaskfile)):
                swr_landmask = ReadAreaSelectRegion(swrlandmaskfile[ii], areaname=swrlandmaskname[ii], box=swrbox,
                                                    **kwargs)
                if swr_landmask is not None:
                    break
    else:
        if isinstance(swrfile, basestring):
            swr_landmask = ReadAreaSelectRegion(swrfile, areaname=swrlandmaskname, box=swrbox, **kwargs)
        else:
            for ii in range(len(swrfile)):
                swr_landmask = ReadAreaSelectRegion(swrfile[ii], areaname=swrlandmaskname[ii], box=swrbox, **kwargs)
                if swr_landmask is not None:
                    break
    if debug is True:
        dict_debug = {}
        if sst_landmask is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_landmask.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_landmask.shape)
        if swr_landmask is not None:
            dict_debug['axes2'] = '(swr) ' + str([ax.id for ax in swr_landmask.getAxisList()])
            dict_debug['shape2'] = '(swr) ' + str(swr_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if sst_landmask is not None:
        sst = ApplyLandmask(sst, sst_landmask, maskland=True, maskocean=False)
        if sst_areacell is None:
            sst_areacell = ArrayOnes(sst_landmask, id='areacell')
        sst_areacell = ApplyLandmaskToArea(sst_areacell, sst_landmask, maskland=True, maskocean=False)
        del sst_landmask
    if swr_landmask is not None:
        swr = ApplyLandmask(swr, swr_landmask, maskland=True, maskocean=False)
        if swr_areacell is None:
            swr_areacell = ArrayOnes(swr_landmask, id='areacell')
        swr_areacell = ApplyLandmaskToArea(swr_areacell, swr_landmask, maskland=True, maskocean=False)
    del swr_landmask

    # Checks if the same time period is used for both variables and if the minimum number of time steps is respected
    sst, swr = CheckTime(sst, swr, metric_name='EnsoAlphaSwr', **kwargs)

    # Number of years
    yearN = sst.shape[0] / 12

    # Time period
    actualtimebounds = TimeBounds(sst)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smooths TS, averages horizontally)
    sst, Method = PreProcessTS(sst, Method, areacell=sst_areacell, average='horizontal', compute_anom=True, **kwargs)
    swr, unneeded = PreProcessTS(swr, '', areacell=swr_areacell, average='horizontal', compute_anom=True, **kwargs)
    del sst_areacell, swr_areacell
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(swr) ' + str([ax.id for ax in swr.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(swr) ' + str(swr.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(swr) ' + str(TimeBounds(swr))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Computes the linear regression for all points, for SSTA >=0 and for SSTA<=0
    alphaSwr, alphaSwrPos, alphaSwrNeg = LinearRegressionAndNonlinearity(swr, sst, return_stderr=True)

    # Create output
    alphaSwrMetric = {
        'name': Name, 'value': alphaSwr[0], 'value_error': alphaSwr[1], 'units': Units, 'method': Method,
        'method_nonlinearity': Method_NL, 'nyears': yearN, 'time_frequency': kwargs['frequency'],
        'time_period': actualtimebounds, 'ref': Ref, 'nonlinearity': alphaSwrNeg[0] - alphaSwrPos[0],
        'nonlinearity_error': alphaSwrNeg[1] + alphaSwrPos[1],
    }
    return alphaSwrMetric


def EnsoAlphaThf(sstfile, sstname, sstareafile, sstareaname, sstlandmaskfile, sstlandmaskname, sstbox, thffile, thfname,
                 thfareafile, thfareaname, thflandmaskfile, thflandmaskname, thfbox, debug=False, **kwargs):
    """
    The EnsoAlphaThf() function computes the regression of 'thfbox' thfA (total heat flux anomalies) over 'sstbox' sstA
    (usually the regression of nino3 thfA over nino3 sstA)
    The total heat flux is the sum of four term:
         - net surface shortwave radiation,
         - net surface longwave radiation,
         - latent heat flux,
         - sensible heat flux

    The total heat flux is not always available is models or observations.
    Either the user computes it and sends the filename and the varname or he feeds into thffile and thfname of this
    function a list() of the four needed files and variable names (CMIP: rsds-rsus, rlds-rlus, hfls, hfss)

    Author:	Yann Planton : yann.planton@locean-ipsl.upmc.fr
    Co-author:

    Created on Thu Oct  5 2017

    Inputs:
    ------
    :param sstfile: string
        path_to/filename of the file (NetCDF) of SST
    :param sstname: string
        name of SST variable (tos, ts) in 'sstfile'
    :param sstareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SST
    :param sstareaname: string
        name of areacell variable (areacella, areacello) in 'sstareafile'
    :param sstlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SST
    :param sstlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfile'
    :param sstbox: string
        name of box (nino3') for SST
    :param thffile: string
        path_to/filename of the file (NetCDF) of THF
    :param thfname: string
        name of THF variable (thf, netflux, thflx, thf + lwr + lhf + shf) (may be a list of variables) in 'thffile'
    :param thfareafile: string
        path_to/filename of the file (NetCDF) of the areacell for THF
    :param thfareaname: string
        name of areacell variable (areacella, areacello) in 'thfareafile'
    :param thflandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for THF
    :param thflandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'thflandmaskfile'
    :param thfbox: string
        name of box (nino3') for THF
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return alphaMetric: dict
        name, value, value_error, units, method, nyears, time_frequency, time_period, ref, nonlinearity,
        nonlinearity_error

    Method:
    -------
        uses tools from uvcdat library

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Heat flux feedback (alpha)'
    Units = 'W/m2/C'
    Method = 'Regression of ' + thfbox + ' thfA over ' + sstbox + ' sstA'
    Method_NL = 'The nonlinearity is the regression computed when sstA<0 minus the regression computed when sstA>0'
    Ref = 'Using CDAT regression calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'EnsoAlphaThf', 10)
        dict_debug = {'file1': '(sst) ' + sstfile, 'file2': '(thf) ' + thffile, 'var1': '(sst) ' + sstname,
                      'var2': '(thf) ' + thfname}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst = ReadSelectRegionCheckUnits(sstfile, sstname, 'temperature', box=sstbox, **kwargs)
    dict_var = dict()
    if isinstance(thffile, basestring):
        dict_var[thfname] = ReadSelectRegionCheckUnits(thffile, thfname, 'heat flux', box=thfbox, **kwargs)
    else:
        for ii in range(len(thffile)):
            filename, varname = thffile[ii], thfname[ii]
            dict_var[varname] = ReadSelectRegionCheckUnits(filename, varname, 'heat flux', box=thfbox, **kwargs)
    thf = MyDerive(kwargs['project_interpreter_var2'], 'thf', dict_var)
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(thf) ' + str([ax.id for ax in thf.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(thf) ' + str(thf.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(thf) ' + str(TimeBounds(thf))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafile:
        sst_areacell = ReadAreaSelectRegion(sstareafile, areaname=sstareaname, box=sstbox, **kwargs)
    else:
        sst_areacell = ReadAreaSelectRegion(sstfile, areaname=sstareaname, box=sstbox, **kwargs)
    if thfareafile:
        if isinstance(thfareafile, basestring):
            thf_areacell = ReadAreaSelectRegion(thfareafile, areaname=thfareaname, box=thfbox, **kwargs)
        else:
            for ii in range(len(thfareafile)):
                thf_areacell = ReadAreaSelectRegion(thfareafile[ii], areaname=thfareaname[ii], box=thfbox, **kwargs)
                if thf_areacell is not None:
                    break
    else:
        if isinstance(thffile, basestring):
            thf_areacell = ReadAreaSelectRegion(thffile, areaname=thfareaname, box=thfbox, **kwargs)
        else:
            for ii in range(len(thffile)):
                thf_areacell = ReadAreaSelectRegion(thffile[ii], areaname=thfareaname[ii], box=thfbox, **kwargs)
                if thf_areacell is not None:
                    break
    if debug is True:
        dict_debug = {}
        if sst_areacell is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_areacell.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_areacell.shape)
        if thf_areacell is not None:
            dict_debug['axes2'] = '(thf) ' + str([ax.id for ax in thf_areacell.getAxisList()])
            dict_debug['shape2'] = '(thf) ' + str(thf_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfile:
        sst_landmask = ReadLandmaskSelectRegion(sstlandmaskfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    else:
        sst_landmask = ReadLandmaskSelectRegion(sstfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    if thflandmaskfile:
        if isinstance(thflandmaskfile, basestring):
            thf_landmask = ReadAreaSelectRegion(thflandmaskfile, areaname=thflandmaskname, box=thfbox, **kwargs)
        else:
            for ii in range(len(thflandmaskfile)):
                thf_landmask = ReadAreaSelectRegion(thflandmaskfile[ii], areaname=thflandmaskname[ii], box=thfbox,
                                                    **kwargs)
                if thf_landmask is not None:
                    break
    else:
        if isinstance(thffile, basestring):
            thf_landmask = ReadAreaSelectRegion(thffile, areaname=thflandmaskname, box=thfbox, **kwargs)
        else:
            for ii in range(len(thffile)):
                thf_landmask = ReadAreaSelectRegion(thffile[ii], areaname=thflandmaskname[ii], box=thfbox, **kwargs)
                if thf_landmask is not None:
                    break
    if debug is True:
        dict_debug = {}
        if sst_landmask is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_landmask.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_landmask.shape)
        if thf_landmask is not None:
            dict_debug['axes2'] = '(thf) ' + str([ax.id for ax in thf_landmask.getAxisList()])
            dict_debug['shape2'] = '(thf) ' + str(thf_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if sst_landmask is not None:
        sst = ApplyLandmask(sst, sst_landmask, maskland=True, maskocean=False)
        if sst_areacell is None:
            sst_areacell = ArrayOnes(sst_landmask, id='areacell')
        sst_areacell = ApplyLandmaskToArea(sst_areacell, sst_landmask, maskland=True, maskocean=False)
        del sst_landmask
    if thf_landmask is not None:
        thf = ApplyLandmask(thf, thf_landmask, maskland=True, maskocean=False)
        if thf_areacell is None:
            thf_areacell = ArrayOnes(thf_landmask, id='areacell')
        thf_areacell = ApplyLandmaskToArea(thf_areacell, thf_landmask, maskland=True, maskocean=False)
    del thf_landmask

    # Checks if the same time period is used for both variables and if the minimum number of time steps is respected
    sst, thf = CheckTime(sst, thf, metric_name='EnsoAlphaThf', **kwargs)

    # Number of years
    yearN = sst.shape[0] / 12

    # Time period
    actualtimebounds = TimeBounds(sst)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smooths TS, averages horizontally)
    sst, Method = PreProcessTS(sst, Method, areacell=sst_areacell, average='horizontal', compute_anom=True, **kwargs)
    thf, unneeded = PreProcessTS(thf, '', areacell=thf_areacell, average='horizontal', compute_anom=True, **kwargs)
    del sst_areacell, thf_areacell
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(thf) ' + str([ax.id for ax in thf.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(thf) ' + str(thf.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(thf) ' + str(TimeBounds(thf))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Computes the linear regression for all points, for SSTA >=0 and for SSTA<=0
    alpha, alphaPos, alphaNeg = LinearRegressionAndNonlinearity(thf, sst, return_stderr=True)

    # Create output
    alphaMetric = {
        'name': Name, 'value': alpha[0], 'value_error': alpha[1], 'units': Units, 'method': Method,
        'method_nonlinearity': Method_NL, 'nyears': yearN, 'time_frequency': kwargs['frequency'],
        'time_period': actualtimebounds, 'ref': Ref, 'nonlinearity': alphaNeg[0] - alphaPos[0],
        'nonlinearity_error': alphaNeg[1] + alphaPos[1],
    }
    return alphaMetric


def EnsoAmpl(sstfile, sstname, sstareafile, sstareaname, sstlandmaskfile, sstlandmaskname, sstbox, debug=False,
             **kwargs):
    """
    The EnsoAmpl() function computes the standard deviation of 'sstbox' sstA (usually the standard deviation of nino3
    sstA)

    Author:	Eric Guilyardi : Eric.Guilyardi@locean-ipsl.upmc.fr
    Co-author: Yann Planton : yann.planton@locean-ipsl.upmc.fr

    Created on Mon Jan  9 11:05:18 CET 2017

    Inputs:
    ------
    :param sstfile: string
        path_to/filename of the file (NetCDF) of SST
    :param sstname: string
        name of SST variable (tos, ts) in 'sstfile'
    :param sstareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SST
    :param sstareaname: string
        name of areacell variable (areacella, areacello) in 'sstareafile'
    :param sstlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SST
    :param sstlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfile'
    :param sstbox: string
        name of box (nino3') for SST
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return amplMetric: dict
        name, value, value_error, units, method, nyears, time_frequency, time_period, ref

    Method:
    -------
        uses tools from uvcdat library

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO amplitude'
    Units = 'C'
    Method = 'Standard deviation of ' + sstbox + ' sstA'
    Ref = 'Using CDAT regression calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'EnsoAmpl', 10)
        dict_debug = {'file1': '(sst) ' + sstfile, 'var1': '(sst) ' + sstname}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst = ReadSelectRegionCheckUnits(sstfile, sstname, 'temperature', box=sstbox, **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]), 'shape1': '(sst) ' + str(sst.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafile:
        sst_areacell = ReadAreaSelectRegion(sstareafile, areaname=sstareaname, box=sstbox, **kwargs)
    else:
        sst_areacell = ReadAreaSelectRegion(sstfile, areaname=sstareaname, box=sstbox, **kwargs)
    if debug is True:
        if sst_areacell is not None:
            dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst_areacell.getAxisList()]),
                          'shape1': '(sst) ' + str(sst_areacell.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfile:
        sst_landmask = ReadLandmaskSelectRegion(sstlandmaskfile, landmaskname=sstlandmaskname, box=sstbox, **kwargs)
    else:
        sst_landmask = ReadLandmaskSelectRegion(sstfile, landmaskname=sstlandmaskname, box=sstbox, **kwargs)
    if debug is True:
        if sst_landmask is not None:
            dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst_landmask.getAxisList()]),
                          'shape1': '(sst) ' + str(sst_landmask.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if sst_landmask is not None:
        sst = ApplyLandmask(sst, sst_landmask, maskland=True, maskocean=False)
        if sst_areacell is None:
            sst_areacell = ArrayOnes(sst_landmask, id='areacell')
        sst_areacell = ApplyLandmaskToArea(sst_areacell, sst_landmask, maskland=True, maskocean=False)
        del sst_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        if len(sst) < kwargs['min_time_steps']:
            EnsoErrorsWarnings.TooShortTimePeriod('EnsoAmpl', len(sst), kwargs['min_time_steps'], INSPECTstack())

    # Number of years
    yearN = sst.shape[0] / 12

    # Time period
    actualtimebounds = TimeBounds(sst)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    sst, Method = PreProcessTS(sst, Method, areacell=sst_areacell, average='horizontal', compute_anom=True, **kwargs)
    del sst_areacell
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]), 'shape1': '(sst) ' + str(sst.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Computes the standard deviation
    sstStd = float(Std(sst))

    # Standard Error of the Standard Deviation (function of nyears)
    sstStdErr = sstStd / NUMPYsqrt(yearN)

    # Create output
    amplMetric = {
        'name': Name, 'value': sstStd, 'value_error': sstStdErr, 'units': Units, 'method': Method, 'nyears': yearN,
        'time_frequency': kwargs['frequency'], 'time_period': actualtimebounds, 'ref': Ref,
    }
    return amplMetric


def EnsoMu(sstfile, sstname, sstareafile, sstareaname, sstlandmaskfile, sstlandmaskname, sstbox, tauxfile, tauxname,
           tauxareafile, tauxareaname, tauxlandmaskfile, tauxlandmaskname, tauxbox, debug=False, **kwargs):
    """
    The EnsoMu() function computes the regression of 'tauxbox' tauxA (surface downward zonal stress anomalies) over
    'sstbox' sstA (usually the regression of nino4 tauxA over nino3 sstA)

    Author:	Eric Guilyardi : Eric.Guilyardi@locean-ipsl.upmc.fr
    Co-author: Yann Planton : yann.planton@locean-ipsl.upmc.fr

    Created on Mon Jan  9 11:05:18 CET 2017

    Inputs:
    ------
    :param sstfile: string
        path_to/filename of the file (NetCDF) of SST
    :param sstname: string
        name of SST variable (tos, ts) in 'sstfile'
    :param sstareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SST
    :param sstareaname: string
        name of areacell variable (areacella, areacello) in 'sstareafile'
    :param sstlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SST
    :param sstlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfile'
    :param sstbox: string
        name of box (nino3') for SST
    :param tauxfile: string
        path_to/filename of the file (NetCDF) of TAUX
    :param tauxname: string
        name of TAUX variable (taux, tauu) in 'tauxfile'
    :param tauxareafile: string
        path_to/filename of the file (NetCDF) of the areacell for TAUX
    :param tauxareaname: string
        name of areacell variable (areacella, areacello) in 'tauxareafile'
    :param tauxlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for TAUX
    :param tauxlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'tauxlandmaskfile'
    :param tauxbox: string
        name of box (nino4') for TAUX
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return muMetric: dict
        name, value, value_error, units, method, nyears, time_frequency, time_period, ref, nonlinearity,
        nonlinearity_error

    Method:
    -------
        uses tools from uvcdat library

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Bjerknes feedback (mu)'
    Units = '10e-3 N/m2/C'
    Method = 'Regression of ' + tauxbox + ' tauxA over ' + sstbox + ' sstA'
    Method_NL = 'The nonlinearity is the regression computed when sstA<0 minus the regression computed when sstA>0'
    Ref = 'Using CDAT regression calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'EnsoMu', 10)
        dict_debug = {'file1': '(sst) ' + sstfile, 'file2': '(taux) ' + tauxfile, 'var1': '(sst) ' + sstname,
                      'var2': '(taux) ' + tauxname}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst = ReadSelectRegionCheckUnits(sstfile, sstname, 'temperature', box=sstbox, **kwargs)
    taux = ReadSelectRegionCheckUnits(tauxfile, tauxname, 'wind stress', box=tauxbox, **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(thf) ' + str([ax.id for ax in taux.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(thf) ' + str(taux.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(thf) ' + str(TimeBounds(taux))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafile:
        sst_areacell = ReadAreaSelectRegion(sstareafile, areaname=sstareaname, box=sstbox, **kwargs)
    else:
        sst_areacell = ReadAreaSelectRegion(sstfile, areaname=sstareaname, box=sstbox, **kwargs)
    if tauxareafile:
        taux_areacell = ReadAreaSelectRegion(tauxareafile, areaname=tauxareaname, box=tauxbox, **kwargs)
    else:
        taux_areacell = ReadAreaSelectRegion(tauxfile, areaname=tauxareaname, box=tauxbox, **kwargs)
    if debug is True:
        dict_debug = {}
        if sst_areacell is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_areacell.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_areacell.shape)
        if taux_areacell is not None:
            dict_debug['axes2'] = '(taux) ' + str([ax.id for ax in taux_areacell.getAxisList()])
            dict_debug['shape2'] = '(taux) ' + str(taux_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfile:
        sst_landmask = ReadLandmaskSelectRegion(sstlandmaskfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    else:
        sst_landmask = ReadLandmaskSelectRegion(sstfile, landmaskname=sstlandmaskname, box=sstbox,
                                                **kwargs)
    if tauxlandmaskfile:
        taux_landmask = ReadLandmaskSelectRegion(tauxlandmaskfile, landmaskname=tauxlandmaskname, box=tauxbox, **kwargs)
    else:
        taux_landmask = ReadLandmaskSelectRegion(tauxfile, landmaskname=tauxlandmaskname, box=tauxbox, **kwargs)
    if debug is True:
        dict_debug = {}
        if sst_landmask is not None:
            dict_debug['axes1'] = '(sst) ' + str([ax.id for ax in sst_landmask.getAxisList()])
            dict_debug['shape1'] = '(sst) ' + str(sst_landmask.shape)
        if taux_landmask is not None:
            dict_debug['axes2'] = '(taux) ' + str([ax.id for ax in taux_landmask.getAxisList()])
            dict_debug['shape2'] = '(taux) ' + str(taux_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if sst_landmask is not None:
        sst = ApplyLandmask(sst, sst_landmask, maskland=True, maskocean=False)
        if sst_areacell is None:
            sst_areacell = ArrayOnes(sst_landmask, id='areacell')
        sst_areacell = ApplyLandmaskToArea(sst_areacell, sst_landmask, maskland=True, maskocean=False)
        del sst_landmask
    if taux_landmask is not None:
        taux = ApplyLandmask(taux, taux_landmask, maskland=True, maskocean=False)
        if taux_areacell is None:
            taux_areacell = ArrayOnes(taux_landmask, id='areacell')
        taux_areacell = ApplyLandmaskToArea(taux_areacell, taux_landmask, maskland=True, maskocean=False)
    del taux_landmask

    # Checks if the same time period is used for both variables and if the minimum number of time steps is respected
    sst, taux = CheckTime(sst, taux, metric_name='EnsoMu', **kwargs)

    # Number of years
    yearN = sst.shape[0] / 12

    # Time period
    actualtimebounds = TimeBounds(sst)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smooths TS, averages horizontally)
    sst, Method = PreProcessTS(sst, Method, areacell=sst_areacell, average='horizontal', compute_anom=True, **kwargs)
    taux, unneeded = PreProcessTS(taux, '', areacell=taux_areacell, average='horizontal', compute_anom=True, **kwargs)
    del sst_areacell, taux_areacell
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]),
                      'axes2': '(taux) ' + str([ax.id for ax in taux.getAxisList()]),
                      'shape1': '(sst) ' + str(sst.shape), 'shape2': '(taux) ' + str(taux.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst)), 'time2': '(thf) ' + str(TimeBounds(taux))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Computes the linear regression for all points, for SSTA >=0 and for SSTA<=0
    mu, muPos, muNeg = LinearRegressionAndNonlinearity(taux, sst, return_stderr=True)

    # Change units
    mu = [mu[0] * 1e3, mu[1] * 1e3]
    muPos = [muPos[0] * 1e3, muPos[1] * 1e3]
    muNeg = [muNeg[0] * 1e3, muNeg[1] * 1e3]

    # Create output
    muMetric = {
        'name': Name, 'value': mu[0], 'value_error': mu[1], 'units': Units, 'method': Method,
        'method_nonlinearity': Method_NL, 'nyears': yearN, 'time_frequency': kwargs['frequency'],
        'time_period': actualtimebounds, 'ref': Ref, 'nonlinearity': muNeg[0] - muPos[0],
        'nonlinearity_error': muNeg[1] + muPos[1],
    }
    return muMetric


def EnsoPrJjaTel(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                 sstlandmasknamemodel, prfilemodel, prnamemodel, prareafilemodel, prareanamemodel, prlandmaskfilemodel,
                 prlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                 sstlandmasknameobs, prfileobs, prnameobs, prareafileobs, prareanameobs, prlandmaskfileobs,
                 prlandmasknameobs, sstbox, prbox, event_definition, centered_rmse=0, biased_rmse=1, debug=False,
                 **kwargs):
    """
    The EnsoPrJjaTel() function computes precipitations anomalies associated with El Niño and La Niña events in many AR5
        reference regions, then precipitations in JJA are composited for each selected event and the difference
        (El Niño PR - La Niña PR) is computed in each region.
    The first rmse(observations vs model) is the metric.
    The second metric is the number of regions where observations and models agree on the sign of the teleconnection

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param prfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled PR
    :param prnamemodel: string
        name of PRvariable (pr) in 'prfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param prfileobs: string
        path_to/filename of the file (NetCDF) of the observed PR
    :param prnameobs: string
        name of PR variable (pr, precip) in 'prfileobs'
    :param box: string
        name of box (e.g. 'nino3') for SST
    :param event_definition: dict
        dictionary providing the necessary information to detect ENSO events (region_ev, season_ev, threshold)
        e.g., event_definition = {'region_ev': 'nino3', 'season_ev': 'DEC', 'threshold': -0.75}
    :param sstareafilemodel: string, optional
        path_to/filename of the file (NetCDF) of the modeled SST areacell
    :param sstareanamemodel: string, optional
        name of areacell for the SST variable (areacella, areacello,...) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string, optional
        path_to/filename of the file (NetCDF) of the modeled SST landmask
    :param sstlandmasknamemodel: string, optional
        name of landmask for the SST variable (sftlf,...) in 'sstlandmaskfilemodel'
    :param prareafilemodel: string, optional
        path_to/filename of the file (NetCDF) of the modeled PR areacell
    :param prareanamemodel: string, optional
        name of areacell for the PR variable (areacella, areacello,...) in 'prareafilemodel'
    :param prlandmaskfilemodel: string, optional
        path_to/filename of the file (NetCDF) of the modeled PR landmask
    :param prlandmasknamemodel: string, optional
        name of landmask for the PR variable (sftlf,...) in 'prlandmaskfilemodel'
    :param sstareafileobs: string, optional
        path_to/filename of the file (NetCDF) of the observed SST areacell
    :param sstareanameobs: string, optional
        name of areacell for the SST variable (areacella, areacello,...) in 'sstareafileobs'
    :param sstlandmaskfileobs: string, optional
        path_to/filename of the file (NetCDF) of the observed SST landmask
    :param sstlandmasknameobs: string, optional
        name of landmask for the SST variable (sftlf,...) in 'sstlandmaskfileobs'
    :param prareafileobs: string, optional
        path_to/filename of the file (NetCDF) of the observed PR areacell
    :param prareanameobs: string, optional
        name of areacell for the PR variable (areacella, areacello,...) in 'prareafileobs'
    :param prlandmaskfileobs: string, optional
        path_to/filename of the file (NetCDF) of the observed PR landmask
    :param prlandmasknameobs: string, optional
        name of landmask for the PR variable (sftlf,...) in 'prlandmaskfileobs'
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)

    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return EnsoPrTelMetric: dict
        name, value (rms [NinoPr-NinaPr]), value_error, units, method, value2 (sign agreement [NinoPr-NinaPr]),
        value_error2, units2, nyears_model, nyears_observations, nina_model, nino_model, nina_observations,
        nino_observations, time_frequency, time_period_model, time_period_observations, ref, dive_down_diag

    Method:
    -------
        uses tools from uvcdat library

    """
    # setting variables
    region_ev = event_definition['region_ev']
    season_ev = event_definition['season_ev']
    threshold = event_definition['threshold']
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds_model',
                    'time_bounds_obs']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Nino composite minus Nina composite during JJA preceding the events in each region'
    Method = 'Nino events = ' + region_ev + ' sstA > ' + str(threshold) + ', Nina events = ' + region_ev + ' sstA < -'\
             + str(threshold) + ' during ' + season_ev + '; Precipitations associated with El Nino/La Nina' + \
             'events during the preceding JJA are composited and the difference (El Niño PR - La Niña PR) is' + \
             'computed in each region'
    if kwargs['normalization']:
        Units = ''
    else:
        Units = 'mm/day'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # ------------------------------------------------
    # detect events
    # ------------------------------------------------
    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'EnsoPrJjaTel', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files ENSO', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=region_ev,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=region_ev,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)
    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)
    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel,
                                                  box=region_ev, **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=region_ev,
                                                  **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs,
                                                  box=region_ev, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs,
                                                box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)
    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "EnsoPrJjaTel: the modeled time-period is too short: "
                            + str(len(sst_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "EnsoPrJjaTel: the observed time-period is too short: "
                            + str(len(sst_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess sst (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    sst_model, unneeded = PreProcessTS(sst_model, '', areacell=model_areacell, average='horizontal', compute_anom=True,
                                       **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average='horizontal', compute_anom=True,
                                     **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Lists event years
    nina_years_model = DetectEvents(sst_model, season_ev, -threshold, normalization=kwargs['normalization'], nino=False)
    nino_years_model = DetectEvents(sst_model, season_ev, threshold, normalization=kwargs['normalization'], nino=True)
    nina_years_obs = DetectEvents(sst_obs, season_ev, -threshold, normalization=kwargs['normalization'], nino=False)
    nino_years_obs = DetectEvents(sst_obs, season_ev, threshold, normalization=kwargs['normalization'], nino=True)
    del sst_model, sst_obs
    if debug is True:
        dict_debug = {'nina1': '(model) ' + str(nina_years_model), 'nina2': '(obs) ' + str(nina_years_obs),
                      'nino1': '(model) ' + str(nino_years_model), 'nino2': '(obs) ' + str(nino_years_obs)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after DetectEvents', 15, **dict_debug)

    # ------------------------------------------------
    # compute composite
    # ------------------------------------------------
    if debug is True:
        dict_debug = {
            'file1': '(model) ' + prfilemodel, 'file2': '(obs) ' + prfileobs, 'var1': '(model) ' + prnamemodel,
            'var2': '(obs) ' + prnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files Composite', 10, **dict_debug)
    # smoothing is not applied
    if 'smoothing' in kwargs.keys():
        smooth = deepcopy(kwargs['smoothing'])
        kwargs['smoothing'] = False
    if not isinstance(prbox, list):
        prbox = [prbox]
    prbox = sorted(prbox, key=str.lower)
    list_composite_model, list_composite_obs = list(), list()
    for reg in prbox:
        if debug is True:
            EnsoErrorsWarnings.DebugMode('\033[92m', 'region = '+str(reg), 10)
        # Read file and select the right region
        pr_model = ReadSelectRegionCheckUnits(prfilemodel, prnamemodel, 'precipitations', box=reg,
                                              time_bounds=kwargs['time_bounds_model'], **kwargs)
        pr_obs = ReadSelectRegionCheckUnits(prfileobs, prnameobs, 'precipitations', box=reg,
                                            time_bounds=kwargs['time_bounds_obs'], **kwargs)
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                          'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape),
                          'time1': '(model) ' + str(TimeBounds(pr_model)), 'time2': '(obs) ' + str(TimeBounds(pr_obs))}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)
        # Read areacell
        if prareafilemodel:
            model_areacell = ReadAreaSelectRegion(prareafilemodel, areaname=prareanamemodel, box=reg, **kwargs)
        else:
            model_areacell = ReadAreaSelectRegion(prfilemodel, areaname=prareanamemodel, box=reg, **kwargs)
        if prareafileobs:
            obs_areacell = ReadAreaSelectRegion(prareafileobs, areaname=prareanameobs, box=reg, **kwargs)
        else:
            obs_areacell = ReadAreaSelectRegion(prfileobs, areaname=prareanameobs, box=reg, **kwargs)
        if debug is True:
            dict_debug = {}
            if model_areacell is not None:
                dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
                dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
            if obs_areacell is not None:
                dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
                dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)
        # Read if the given region is defined as a land region, an oceanic region, or both
        dict_reg = ReferenceRegions(reg)
        if 'maskland' in dict_reg.keys():
            maskland = dict_reg['maskland']
        else:
            maskland = False
        if 'maskocean' in dict_reg.keys():
            maskocean = dict_reg['maskocean']
        else:
            maskocean = False
        # Read landmask
        if prlandmaskfilemodel:
            model_landmask = ReadLandmaskSelectRegion(prlandmaskfilemodel, landmaskname=prlandmasknamemodel, box=reg,
                                                      **kwargs)
        else:
            model_landmask = ReadLandmaskSelectRegion(prfilemodel, landmaskname=prlandmasknamemodel, box=reg, **kwargs)
        if prlandmaskfileobs:
            obs_landmask = ReadLandmaskSelectRegion(prlandmaskfileobs, landmaskname=prlandmasknameobs, box=reg,
                                                    **kwargs)
        else:
            obs_landmask = ReadLandmaskSelectRegion(prfileobs, landmaskname=prlandmasknameobs, box=reg, **kwargs)
        if debug is True:
            dict_debug = {}
            if model_landmask is not None:
                dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
                dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
            if obs_landmask is not None:
                dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
                dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)
        # Apply landmask
        if model_landmask is not None:
            pr_model = ApplyLandmask(pr_model, model_landmask, maskland=maskland, maskocean=maskocean)
            if model_areacell is None:
                model_areacell = ArrayOnes(model_landmask, id='areacell')
            model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=maskland, maskocean=maskocean)
            del model_landmask
        if obs_landmask is not None:
            pr_obs = ApplyLandmask(pr_obs, obs_landmask, maskland=maskland, maskocean=maskocean)
            if obs_areacell is None:
                obs_areacell = ArrayOnes(obs_landmask, id='areacell')
            obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=maskland, maskocean=maskocean)
            del obs_landmask

        # Preprocess sst (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
        pr_model, Method = PreProcessTS(pr_model, Method, areacell=model_areacell, average='horizontal',
                                        compute_anom=False, **kwargs)
        pr_obs, unneeded = PreProcessTS(pr_obs, '', areacell=obs_areacell, average='horizontal', compute_anom=False,
                                        **kwargs)
        del model_areacell, obs_areacell
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                          'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape),
                          'time1': '(model) ' + str(TimeBounds(pr_model)), 'time2': '(obs) ' + str(TimeBounds(pr_obs))}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

        # Seasonal mean
        pr_model = SeasonalMean(pr_model, 'JJA', compute_anom=False)
        pr_obs = SeasonalMean(pr_obs, 'JJA', compute_anom=False)

        # composites
        composite_nina_model = Composite(pr_model, nina_years_model, kwargs['frequency'])
        composite_nino_model = Composite(pr_model, nino_years_model, kwargs['frequency'])
        composite_nina_obs = Composite(pr_obs, nina_years_obs, kwargs['frequency'])
        composite_nino_obs = Composite(pr_obs, nino_years_obs, kwargs['frequency'])

        # list composites
        list_composite_model.append(float(composite_nino_model-composite_nina_model))
        list_composite_obs.append(float(composite_nino_obs-composite_nina_obs))
    if 'smoothing' in kwargs.keys():
        kwargs['smoothing'] = smooth
        del smooth

    # Computes the root mean square difference
    compositeRmse = RmsAxis(list_composite_model, list_composite_obs, centered=centered_rmse, biased=biased_rmse)

    # Computes the percentage of regions where observations and model agree on the sign of the teleconnection
    signAgreement = sum([1. for vmod,vobs in zip(list_composite_model,list_composite_obs)
                        if NUMPYsign(vmod)==NUMPYsign(vobs)])/len(list_composite_model)

    # Dive down diagnostic
    dive_down_diag = {'model': list_composite_model, 'observations': list_composite_obs, 'axis': prbox}

    # Create output
    EnsoPrTelMetric = {
        'name': Name, 'value': compositeRmse, 'value_error': None, 'units': Units, 'method': Method,
        'value2': signAgreement, 'value_error2': None, 'units2': '%', 'nyears_model': yearN_model,
        'nyears_observations': yearN_obs, 'nina_model': nina_years_model, 'nino_model': nino_years_model,
        'nina_observations': nina_years_obs, 'nino_observations': nino_years_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model': actualtimeboundsmodel, 'time_period_observations': actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return EnsoPrTelMetric


def EnsoSeasonality(sstfile, sstname, sstareafile, sstareaname, sstlandmaskfile, sstlandmaskname, sstbox, debug=False,
                    **kwargs):
    """
    The EnsoSeasonality() function computes ratio between the November-December-January (NDJ) and March-April-May (MAM)
    average standard deviation of 'sstbox' sstA (usually nino3 sstA)

    Inputs:
    ------
    :param sstfile: string
        path_to/filename of the file (NetCDF) of SST
    :param sstname: string
        name of SST variable (tos, ts) in 'sstfile'
    :param sstareafile: string
        path_to/filename of the file (NetCDF) of the areacell for SST
    :param sstareaname: string
        name of areacell variable (areacella, areacello) in 'sstareafile'
    :param sstlandmaskfile: string
        path_to/filename of the file (NetCDF) of the landmask for SST
    :param sstlandmaskname: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfile'
    :param sstbox: string
        name of box (nino3') for SST
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return SeaMetric: dict
        name, value, value_error, units, method, nyears, time_frequency, time_period, ref

    Method:
    -------
        uses tools from uvcdat library

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'ENSO seasonality'
    Units = ''
    Method = 'Ratio between NDJ and MAM standard deviation ' + sstbox + ' sstA'
    Ref = 'Using CDAT std dev calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'EnsoSeasonality', 10)
        dict_debug = {'file1': '(sst) ' + sstfile, 'var1': '(sst) ' + sstname}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst = ReadSelectRegionCheckUnits(sstfile, sstname, 'temperature', box=sstbox, **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]), 'shape1': '(sst) ' + str(sst.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafile:
        sst_areacell = ReadAreaSelectRegion(sstareafile, areaname=sstareaname, box=sstbox, **kwargs)
    else:
        sst_areacell = ReadAreaSelectRegion(sstfile, areaname=sstareaname, box=sstbox, **kwargs)
    if debug is True:
        if sst_areacell is not None:
            dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst_areacell.getAxisList()]),
                          'shape1': '(sst) ' + str(sst_areacell.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfile:
        sst_landmask = ReadLandmaskSelectRegion(sstlandmaskfile, landmaskname=sstlandmaskname, box=sstbox, **kwargs)
    else:
        sst_landmask = ReadLandmaskSelectRegion(sstfile, landmaskname=sstlandmaskname, box=sstbox, **kwargs)
    if debug is True:
        if sst_landmask is not None:
            dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst_landmask.getAxisList()]),
                          'shape1': '(sst) ' + str(sst_landmask.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if sst_landmask is not None:
        sst = ApplyLandmask(sst, sst_landmask, maskland=True, maskocean=False)
        if sst_areacell is None:
            sst_areacell = ArrayOnes(sst_landmask, id='areacell')
        sst_areacell = ApplyLandmaskToArea(sst_areacell, sst_landmask, maskland=True, maskocean=False)
        del sst_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst) < mini:
            EnsoErrorsWarnings.TooShortTimePeriod('EnsoSeasonality', len(sst), mini, INSPECTstack())

    # Number of years
    yearN = sst.shape[0] / 12

    # Time period
    actualtimebounds = TimeBounds(sst)

    # Preprocess sst (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    sst, Method = PreProcessTS(sst, Method, areacell=sst_areacell, average='horizontal', compute_anom=False, **kwargs)
    del sst_areacell
    if debug is True:
        dict_debug = {'axes1': '(sst) ' + str([ax.id for ax in sst.getAxisList()]), 'shape1': '(sst) ' + str(sst.shape),
                      'time1': '(sst) ' + str(TimeBounds(sst))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Seasonal mean
    sst_NDJ = SeasonalMean(sst, 'NDJ', compute_anom=True)
    sst_MAM = SeasonalMean(sst, 'MAM', compute_anom=True)
    if debug is True:
        dict_debug = {'axes1': '(sst_NDJ) ' + str([ax.id for ax in sst_NDJ.getAxisList()]),
                      'shape1': '(sst_NDJ) ' + str(sst_NDJ.shape),
                      'axes2': '(sst_NDJ) ' + str([ax.id for ax in sst_MAM.getAxisList()]),
                      'shape2': '(sst_NDJ) ' + str(sst_MAM.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after SeasonalMean', 15, **dict_debug)

    # Compute std dev and ratio
    sst_NDJ_std = Std(sst_NDJ)
    sst_MAM_std = Std(sst_MAM)
    ratioStd = float(sst_NDJ_std / sst_MAM_std)

    # Standard Error of the Standard Deviation (function of nyears)
    sst_NDJ_std_err = sst_NDJ_std / NUMPYsqrt(yearN - 1)
    sst_MAM_std_err = sst_MAM_std / NUMPYsqrt(yearN)

    # The error (dy) on ratio ('y = x/z'): dy = (z*dx + x*dz) / z2
    ratio_std_err = float((sst_MAM_std * sst_NDJ_std_err + sst_NDJ_std * sst_MAM_std_err) / NUMPYsquare(sst_MAM_std))

    # Create output
    seaMetric = {
        'name': Name, 'value': ratioStd, 'value_error': ratio_std_err, 'units': Units, 'method': Method,
        'nyears': yearN, 'time_frequency': kwargs['frequency'], 'time_period': actualtimebounds, 'ref': Ref,
    }
    return seaMetric


def NinaSstLonRmse(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                   sstlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                   sstlandmasknameobs, box, event_definition, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The NinaSstLonRmse() function computes a zonal composite of La Niña events during the peak of the event
    SSTA averaged in 'region_ev' are normalized / detrended / smoothed (running average) if applicable
        Then SSTA > 'threshold' during 'season' are considered as La Niña events
    Then the zonal SSTA at the peak of the event is composited for each selected event

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param sstareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for SST
    :param sstareanamemodel: string
        name of areacell variable (areacella, areacello) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for SST
    :param sstlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param sstareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for SST
    :param sstareanameobs: string
        name of areacell variable (areacella, areacello) in 'sstareafileobs'
    :param sstlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for SST
    :param sstlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfileobs'
    :param box: string
        name of box ('nino3') for SST
    :param event_definition: dict
        dictionary providing the necessary information to detect ENSO events (region_ev, season_ev, threshold)
        e.g., event_definition = {'region_ev': 'nino3', 'season_ev': 'DEC', 'threshold': -0.75}
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return NinaLonMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, events_model, events_observations,
        time_frequency, time_period_model, time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    """
    # setting variables
    region_ev = event_definition['region_ev']
    season_ev = event_definition['season_ev']
    threshold = event_definition['threshold']
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds_model',
                    'time_bounds_obs']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Nina Composite Time Series'
    lat = ReferenceRegions('equatorial_pacific')['latitude']
    Method = 'Nina events = ' + region_ev + ' sstA > ' + str(threshold) + ' during ' + season_ev + ', zonal SSTA '\
             + '(meridional averaged [' + str(lat[0]) + ' ; ' + str(lat[1]) + ']'
    if kwargs['normalization']:
        Units = ''
    else:
        Units = 'C'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # ------------------------------------------------
    # detect events
    # ------------------------------------------------
    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'NinaSstLonRmse', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=region_ev,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=region_ev,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)
    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)
    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel,
                                                  box=region_ev, **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=region_ev,
                                                  **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=region_ev,
                                                **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)
    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "NinaSstLonRmse: the modeled time-period is too short: "
                            + str(len(sst_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "NinaSstLonRmse: the observed time-period is too short: "
                            + str(len(sst_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess sst (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    sst_model, unneeded = PreProcessTS(sst_model, '', areacell=model_areacell, average='horizontal', compute_anom=True,
                                       **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average='horizontal', compute_anom=True,
                                     **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Lists event years
    event_years_model = DetectEvents(sst_model, season_ev, threshold, normalization=kwargs['normalization'], nino=False)
    event_years_obs = DetectEvents(sst_obs, season_ev, threshold, normalization=kwargs['normalization'], nino=False)
    if debug is True:
        dict_debug = {'nina1': '(model) ' + str(event_years_model), 'nina2': '(obs) ' + str(event_years_obs)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after DetectEvents', 15, **dict_debug)

    # ------------------------------------------------
    # compute composite
    # ------------------------------------------------
    # Read file and select the right region
    if debug is True:
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files Composite', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=box,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=box,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)
    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)
    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=box, **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)
    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # Preprocess sst (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    sst_model, Method = PreProcessTS(sst_model, Method, areacell=model_areacell, average=False, compute_anom=True,
                                     **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average=False, compute_anom=True, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Seasonal mean
    sst_model = SeasonalMean(sst_model, season_ev, compute_anom=False)
    sst_obs = SeasonalMean(sst_obs, season_ev, compute_anom=False)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after SeasonalMean', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        sst_model, sst_obs, Method = TwoVarRegrid(sst_model, sst_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                          'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Meridional average
    sst_model = AverageMeridional(sst_model)
    sst_obs = AverageMeridional(sst_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageMeridional', 15, **dict_debug)

    # composites
    composite_model = Composite(sst_model, event_years_model, kwargs['frequency'])
    composite_obs = Composite(sst_obs, event_years_obs, kwargs['frequency'])
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in composite_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in composite_obs.getAxisList()]),
                      'shape1': '(model) ' + str(composite_model.shape), 'shape2': '(obs) ' + str(composite_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after Composite', 15, **dict_debug)

    # Computes the root mean square difference
    compositeRmse = RmsZonal(composite_model, composite_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(composite_model), 'observations': arrayToList(composite_obs),
                      'axis': list(composite_model.getAxis(0)[:])}

    # Create output
    NinaLonMetric = {
        'name': Name, 'value': compositeRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'events_model': event_years_model,
        'events_observations': event_years_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model': actualtimeboundsmodel, 'time_period_observations': actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return NinaLonMetric


def NinoSstLonRmse(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                   sstlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                   sstlandmasknameobs, box, event_definition, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The NinoSstLonRmse() function computes a zonal composite of El Niño events during the peak of the event
    SSTA averaged in 'region_ev' are normalized / detrended / smoothed (running average) if applicable
        Then SSTA > 'threshold' during 'season' are considered as El Niño events
    Then the zonal SSTA at the peak of the event is composited for each selected event

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param sstareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for SST
    :param sstareanamemodel: string
        name of areacell variable (areacella, areacello) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for SST
    :param sstlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param sstareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for SST
    :param sstareanameobs: string
        name of areacell variable (areacella, areacello) in 'sstareafileobs'
    :param sstlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for SST
    :param sstlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfileobs'
    :param box: string
        name of box ('nino3') for SST
    :param event_definition: dict
        dictionary providing the necessary information to detect ENSO events (region_ev, season_ev, threshold)
        e.g., event_definition = {'region_ev': 'nino3', 'season_ev': 'DEC', 'threshold': 0.75}
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return NinoLonMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, events_model, events_observations,
        time_frequency, time_period_model, time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    """
    # setting variables
    region_ev = event_definition['region_ev']
    season_ev = event_definition['season_ev']
    threshold = event_definition['threshold']
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds_model',
                    'time_bounds_obs']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Nino Composite Time Series'
    lat = ReferenceRegions('equatorial_pacific')['latitude']
    Method = 'Nino events = ' + region_ev + ' sstA > ' + str(threshold) + ' during ' + season_ev + ', zonal SSTA '\
             + '(meridional averaged [' + str(lat[0]) + ' ; ' + str(lat[1]) + ']'
    if kwargs['normalization']:
        Units = ''
    else:
        Units = 'C'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # ------------------------------------------------
    # detect events
    # ------------------------------------------------
    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'NinoSstLonRmse', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=region_ev,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=region_ev,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)
    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)
    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel,
                                                  box=region_ev, **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=region_ev,
                                                  **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=region_ev,
                                                **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)
    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "NinoSstLonRmse: the modeled time-period is too short: "
                            + str(len(sst_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "NinoSstLonRmse: the observed time-period is too short: "
                            + str(len(sst_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess sst (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    sst_model, unneeded = PreProcessTS(sst_model, '', areacell=model_areacell, average='horizontal', compute_anom=True,
                                       **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average='horizontal', compute_anom=True,
                                     **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Lists event years
    event_years_model = DetectEvents(sst_model, season_ev, threshold, normalization=kwargs['normalization'], nino=True)
    event_years_obs = DetectEvents(sst_obs, season_ev, threshold, normalization=kwargs['normalization'], nino=True)
    if debug is True:
        dict_debug = {'nino1': '(model) ' + str(event_years_model), 'nino2': '(obs) ' + str(event_years_obs)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after DetectEvents', 15, **dict_debug)

    # ------------------------------------------------
    # compute composite
    # ------------------------------------------------
    # Read file and select the right region
    if debug is True:
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files Composite', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=box,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=box,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)
    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=box, **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)
    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # Preprocess sst (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    sst_model, Method = PreProcessTS(sst_model, Method, areacell=model_areacell, average=False, compute_anom=True,
                                     **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average=False, compute_anom=True, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Seasonal mean
    sst_model = SeasonalMean(sst_model, season_ev, compute_anom=False)
    sst_obs = SeasonalMean(sst_obs, season_ev, compute_anom=False)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after SeasonalMean', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        sst_model, sst_obs, Method = TwoVarRegrid(sst_model, sst_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                          'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Meridional average
    sst_model = AverageMeridional(sst_model)
    sst_obs = AverageMeridional(sst_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageMeridional', 15, **dict_debug)

    # composites
    composite_model = Composite(sst_model, event_years_model, kwargs['frequency'])
    composite_obs = Composite(sst_obs, event_years_obs, kwargs['frequency'])
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in composite_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in composite_obs.getAxisList()]),
                      'shape1': '(model) ' + str(composite_model.shape), 'shape2': '(obs) ' + str(composite_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after Composite', 15, **dict_debug)

    # Computes the root mean square difference
    compositeRmse = RmsZonal(composite_model, composite_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(composite_model), 'observations': arrayToList(composite_obs),
                      'axis': list(composite_model.getAxis(0)[:])}

    # Create output
    NinoLonMetric = {
        'name': Name, 'value': compositeRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'events_model': event_years_model,
        'events_observations': event_years_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model': actualtimeboundsmodel, 'time_period_observations': actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return NinoLonMetric


def NinaSstTsRmse(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                  sstlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                  sstlandmasknameobs, box, event_definition, nbr_years_window, centered_rmse=0, biased_rmse=1,
                  debug=False, **kwargs):
    """
    The NinaSstTsRmse() function computes a time composite of La Niña events
    SSTA averaged in 'region_ev' are normalized / detrended / smoothed (running average) if applicable
        Then SSTA < 'threshold' during 'season' are considered as La Niña events
        Then a 'nbr_years_window' long time series centered on selected events is composited for each selected event

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param sstareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for SST
    :param sstareanamemodel: string
        name of areacell variable (areacella, areacello) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for SST
    :param sstlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param sstareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for SST
    :param sstareanameobs: string
        name of areacell variable (areacella, areacello) in 'sstareafileobs'
    :param sstlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for SST
    :param sstlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfileobs'
    :param box: string
        name of box ('nino3') for SST
    :param event_definition: dict
        dictionary providing the necessary information to detect ENSO events (region_ev, season_ev, threshold)
        e.g., event_definition = {'region_ev': 'nino3', 'season_ev': 'DEC', 'threshold': -0.75}
    :param nbr_years_window: integer
        number of years used to compute the composite (e.g. 6)
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return NinaTsMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, events_model, events_observations,
        time_frequency, time_period_model, time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    """
    # setting variables
    region_ev = event_definition['region_ev']
    season_ev = event_definition['season_ev']
    threshold = event_definition['threshold']
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds_model',
                    'time_bounds_obs']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Nina Composite Time Series'
    Method = 'Nina events = ' + region_ev + ' sstA < ' + str(threshold) + ' during ' + season_ev + ', time series of '\
             + str(nbr_years_window) + ' years (centered on events)'
    if kwargs['normalization']:
        Units = ''
    else:
        Units = 'C'
    Ref = 'Using CDAT rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'NinaSstTsRmse', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files ENSO', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=region_ev,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=region_ev,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel,
                                                  box=region_ev, **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=region_ev,
                                                  **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=region_ev,
                                                **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "NinaSstTsRmse: the modeled time-period is too short: "
                            + str(len(sst_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "NinaSstTsRmse: the observed time-period is too short: "
                            + str(len(sst_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess sst (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    sst_model, Method = PreProcessTS(sst_model, Method, areacell=model_areacell, average='horizontal',
                                     compute_anom=True, **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average='horizontal', compute_anom=True,
                                     **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Lists event years
    event_years_model = DetectEvents(sst_model, season_ev, threshold, normalization=kwargs['normalization'], nino=False)
    event_years_obs = DetectEvents(sst_obs, season_ev, threshold, normalization=kwargs['normalization'], nino=False)
    if debug is True:
        dict_debug = {'nina1': '(model) ' + str(event_years_model), 'nina2': '(obs) ' + str(event_years_obs)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after DetectEvents', 15, **dict_debug)

    # composites
    composite_model = Composite(sst_model, event_years_model, kwargs['frequency'], nbr_years_window=nbr_years_window)
    composite_obs = Composite(sst_obs, event_years_obs, kwargs['frequency'], nbr_years_window=nbr_years_window)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in composite_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in composite_obs.getAxisList()]),
                      'shape1': '(model) ' + str(composite_model.shape), 'shape2': '(obs) ' + str(composite_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after Composite', 15, **dict_debug)

    # Computes the root mean square difference
    compositeRmse = RmsTemporal(composite_model, composite_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(composite_model), 'observations': arrayToList(composite_obs),
                      'axis': list(composite_model.getAxis(0)[:])}

    # Create output
    NinaTsMetric = {
        'name': Name, 'value': compositeRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'events_model': event_years_model,
        'events_observations': event_years_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model': actualtimeboundsmodel, 'time_period_observations': actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return NinaTsMetric


def NinoSstTsRmse(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                  sstlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                  sstlandmasknameobs, box, event_definition, nbr_years_window, centered_rmse=0, biased_rmse=1,
                  debug=False, **kwargs):
    """
    The NinoSstTsRmse() function computes a time composite of El Niño events
    SSTA averaged in 'box' are normalized / detrended / smoothed (running average) if applicable
        Then SSTA > 'threshold' during 'season' are considered as El Niño events
        Then a 'nbr_years_window' long time series centered on selected events is composited for each selected event

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param sstareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for SST
    :param sstareanamemodel: string
        name of areacell variable (areacella, areacello) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for SST
    :param sstlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param sstareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for SST
    :param sstareanameobs: string
        name of areacell variable (areacella, areacello) in 'sstareafileobs'
    :param sstlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for SST
    :param sstlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfileobs'
    :param box: string
        name of box ('nino3') for SST
    :param event_definition: dict
        dictionary providing the necessary information to detect ENSO events (region_ev, season_ev, threshold)
        e.g., event_definition = {'region_ev': 'nino3', 'season_ev': 'DEC', 'threshold': 0.75}
    :param nbr_years_window: integer
        number of years used to compute the composite (e.g. 6)
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds: tuple, optional
        tuple of the first and last dates to extract from the files (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return NinoTsMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, events_model, events_observations,
        time_frequency, time_period_model, time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    """
    # setting variables
    region_ev = event_definition['region_ev']
    season_ev = event_definition['season_ev']
    threshold = event_definition['threshold']
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'smoothing', 'time_bounds_model',
                    'time_bounds_obs']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'Nino Composite Time Series'
    Method = 'Nino events = ' + region_ev + ' sstA > ' + str(threshold) + ' during ' + season_ev + ', time series of '\
             + str(nbr_years_window) + ' years (centered on events)'
    if kwargs['normalization']:
        Units = ''
    else:
        Units = 'C'
    Ref = 'Using CDAT rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'NinoSstTsRmse', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files ENSO', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=region_ev,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=region_ev,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=region_ev, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel,
                                                  box=region_ev, **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=region_ev,
                                                  **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=region_ev,
                                                **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=region_ev, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "NinoSstTsRmse: the modeled time-period is too short: "
                            + str(len(sst_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "NinoSstTsRmse: the observed time-period is too short: "
                            + str(len(sst_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess sst (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    sst_model, Method = PreProcessTS(sst_model, Method, areacell=model_areacell, average='horizontal',
                                     compute_anom=True, **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', areacell=obs_areacell, average='horizontal', compute_anom=True,
                                     **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # Lists event years
    event_years_model = DetectEvents(sst_model, season_ev, threshold, normalization=kwargs['normalization'], nino=True)
    event_years_obs = DetectEvents(sst_obs, season_ev, threshold, normalization=kwargs['normalization'], nino=True)
    if debug is True:
        dict_debug = {'nino1': '(model) ' + str(event_years_model), 'nino2': '(obs) ' + str(event_years_obs)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after DetectEvents', 15, **dict_debug)

    # composites
    composite_model = Composite(sst_model, event_years_model, kwargs['frequency'], nbr_years_window=nbr_years_window)
    composite_obs = Composite(sst_obs, event_years_obs, kwargs['frequency'], nbr_years_window=nbr_years_window)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in composite_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in composite_obs.getAxisList()]),
                      'shape1': '(model) ' + str(composite_model.shape), 'shape2': '(obs) ' + str(composite_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after Composite', 15, **dict_debug)

    # Computes the root mean square difference
    compositeRmse = RmsTemporal(composite_model, composite_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(composite_model), 'observations': arrayToList(composite_obs),
                      'axis': list(composite_model.getAxis(0)[:])}

    # Create output
    NinoTsMetric = {
        'name': Name, 'value': compositeRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'events_model': event_years_model,
        'events_observations': event_years_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model': actualtimeboundsmodel, 'time_period_observations': actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return NinoTsMetric


def SeasonalPrLatRmse(prfilemodel, prnamemodel, prareafilemodel, prareanamemodel, prlandmaskfilemodel,
                      prlandmasknamemodel, prfileobs, prnameobs, prareafileobs, prareanameobs, prlandmaskfileobs,
                      prlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The SeasonalPrLatRmse() function computes the climatological (12 months) PR (precipitation) meridional (latitude)
    standard deviation root mean square error (RMSE) in a 'box' (usually the nino3.3_LatExt)

    Inputs:
    ------
    :param prfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled PR
    :param prnamemodel: string
        name of PR variable (pr, precip) in 'prfilemodel'
    :param prareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for PR
    :param prareanamemodel: string
        name of areacell variable (areacella, areacello) in 'prareafilemodel'
    :param prlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for PR
    :param prlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfilemodel'
    :param prfileobs: string
        path_to/filename of the file (NetCDF) of the observed PR
    :param prnameobs: string
        name of PR variable (pr, prec) in 'prfileobs'
    :param prareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for PR
    :param prareanameobs: string
        name of areacell variable (areacella, areacello) in 'prareafileobs'
    :param prlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for PR
    :param prlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfileobs'
    :param box: string
        name of box ('nino3.3_LatExt') for PR
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return LatRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'PR meridional seasonality RMSE'
    Units = 'mm/day'
    Method = 'Meridional root mean square error of ' + box + ' climatological pr STD'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'SeasonalPrLatRmse', 10)
        dict_debug = {'file1': '(model) ' + prfilemodel, 'file2': '(obs) ' + prfileobs,
                      'var1': '(model) ' + prnamemodel, 'var2': '(obs) ' + prnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    pr_model = ReadSelectRegionCheckUnits(prfilemodel, prnamemodel, 'precipitations', box=box,
                                          time_bounds=kwargs['time_bounds_model'], **kwargs)
    pr_obs = ReadSelectRegionCheckUnits(prfileobs, prnameobs, 'precipitations', box=box,
                                        time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(pr_model)), 'time2': '(obs) ' + str(TimeBounds(pr_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if prareafilemodel:
        model_areacell = ReadAreaSelectRegion(prareafilemodel, areaname=prareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(prfilemodel, areaname=prareanamemodel, box=box, **kwargs)
    if prareafileobs:
        obs_areacell = ReadAreaSelectRegion(prareafileobs, areaname=prareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(prfileobs, areaname=prareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if prlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(prlandmaskfilemodel, landmaskname=prlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(prfilemodel, landmaskname=prlandmasknamemodel, box=box, **kwargs)
    if prlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(prlandmaskfileobs, landmaskname=prlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(prfileobs, landmaskname=prlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        pr_model = ApplyLandmask(pr_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        pr_obs = ApplyLandmask(pr_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(pr_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "SeasonalPrLatRmse: the modeled time-period is too short: "
                            + str(len(pr_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(pr_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "SeasonalPrLatRmse: the observed time-period is too short: "
                            + str(len(pr_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = pr_model.shape[0] / 12
    yearN_obs = pr_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(pr_model)
    actualtimeboundsobs = TimeBounds(pr_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    pr_model, Method = PreProcessTS(pr_model, Method, compute_sea_cycle=True, **kwargs)
    pr_obs, unneeded = PreProcessTS(pr_obs, '', compute_sea_cycle=True, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # standard deviation computation
    pr_model = Std(pr_model)
    pr_obs = Std(pr_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after Std', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        pr_model, pr_obs, Method = TwoVarRegrid(pr_model, pr_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                          'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Zonal average
    pr_model = AverageZonal(pr_model)
    pr_obs = AverageZonal(pr_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageZonal', 15, **dict_debug)

    # Computes the root mean square difference
    prRmse = RmsMeridional(pr_model, pr_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(pr_model), 'observations': arrayToList(pr_obs),
                      'axis': list(pr_model.getAxis(0)[:])}

    # Create output
    LatRmseMetric = {
        'name': Name, 'value': prRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model': actualtimeboundsmodel, 'time_period_observations': actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return LatRmseMetric


def SeasonalPrLonRmse(prfilemodel, prnamemodel, prareafilemodel, prareanamemodel, prlandmaskfilemodel,
                      prlandmasknamemodel, prfileobs, prnameobs, prareafileobs, prareanameobs, prlandmaskfileobs,
                      prlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The SeasonalPrLonRmse() function computes the climatological (12 months) PR (precipitation) zonal (longitude)
    standard deviation root mean square error (RMSE) in a 'box' (usually the Equatorial Pacific)

    Inputs:
    ------
     :param prfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled PR
    :param prnamemodel: string
        name of PR variable (pr, precip) in 'prfilemodel'
    :param prareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for PR
    :param prareanamemodel: string
        name of areacell variable (areacella, areacello) in 'prareafilemodel'
    :param prlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for PR
    :param prlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfilemodel'
    :param prfileobs: string
        path_to/filename of the file (NetCDF) of the observed PR
    :param prnameobs: string
        name of PR variable (pr, prec) in 'prfileobs'
    :param prareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for PR
    :param prareanameobs: string
        name of areacell variable (areacella, areacello) in 'prareafileobs'
    :param prlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for PR
    :param prlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'prlandmaskfileobs'
    :param box: string
        name of box ('equatorial_pacific') for PR
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed PR file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return LonRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'PR zonal seasonality RMSE'
    Units = 'mm/day'
    Method = 'Zonal root mean square error of ' + box + ' climatological pr STD'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'SeasonalPrLonRmse', 10)
        dict_debug = {'file1': '(model) ' + prfilemodel, 'file2': '(obs) ' + prfileobs,
                      'var1': '(model) ' + prnamemodel, 'var2': '(obs) ' + prnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    pr_model = ReadSelectRegionCheckUnits(prfilemodel, prnamemodel, 'precipitations', box=box,
                                          time_bounds=kwargs['time_bounds_model'], **kwargs)
    pr_obs = ReadSelectRegionCheckUnits(prfileobs, prnameobs, 'precipitations', box=box,
                                        time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(pr_model)), 'time2': '(obs) ' + str(TimeBounds(pr_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if prareafilemodel:
        model_areacell = ReadAreaSelectRegion(prareafilemodel, areaname=prareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(prfilemodel, areaname=prareanamemodel, box=box, **kwargs)
    if prareafileobs:
        obs_areacell = ReadAreaSelectRegion(prareafileobs, areaname=prareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(prfileobs, areaname=prareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if prlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(prlandmaskfilemodel, landmaskname=prlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(prfilemodel, landmaskname=prlandmasknamemodel, box=box, **kwargs)
    if prlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(prlandmaskfileobs, landmaskname=prlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(prfileobs, landmaskname=prlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        pr_model = ApplyLandmask(pr_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        pr_obs = ApplyLandmask(pr_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(pr_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "SeasonalPrLonRmse: the modeled time-period is too short: "
                            + str(len(pr_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(pr_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "SeasonalPrLonRmse: the observed time-period is too short: "
                            + str(len(pr_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = pr_model.shape[0] / 12
    yearN_obs = pr_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(pr_model)
    actualtimeboundsobs = TimeBounds(pr_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    pr_model, Method = PreProcessTS(pr_model, Method, compute_sea_cycle=True, **kwargs)
    pr_obs, unneeded = PreProcessTS(pr_obs, '', compute_sea_cycle=True, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # standard deviation computation
    pr_model = Std(pr_model)
    pr_obs = Std(pr_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after Std', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        pr_model, pr_obs, Method = TwoVarRegrid(pr_model, pr_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                          'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Meridional average
    pr_model = AverageMeridional(pr_model)
    pr_obs = AverageMeridional(pr_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in pr_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in pr_obs.getAxisList()]),
                      'shape1': '(model) ' + str(pr_model.shape), 'shape2': '(obs) ' + str(pr_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageMeridional', 15, **dict_debug)

    # Computes the root mean square difference
    prRmse = RmsZonal(pr_model, pr_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(pr_model), 'observations': arrayToList(pr_obs),
                      'axis': list(pr_model.getAxis(0)[:])}

    # Create output
    LonRmseMetric = {
        'name': Name, 'value': prRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model': actualtimeboundsmodel, 'time_period_observations': actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return LonRmseMetric


def SeasonalSstLatRmse(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                       sstlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                       sstlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The SeasonalSstLatRmse() function computes the climatological (12 months) SST meridional (latitude) standard
    deviation root mean square error (RMSE) in a 'box' (usually the nino3.3_LatExt)

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param sstareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for SST
    :param sstareanamemodel: string
        name of areacell variable (areacella, areacello) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for SST
    :param sstlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param sstareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for SST
    :param sstareanameobs: string
        name of areacell variable (areacella, areacello) in 'sstareafileobs'
    :param sstlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for SST
    :param sstlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfileobs'
    :param box: string
        name of box ('nino3.3_LatExt') for SST
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return LatRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try: kwargs[arg]
        except: kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'SST meridional seasonality RMSE'
    Units = 'C'
    Method = 'Meridional root mean square error of ' + box + ' climatological sst STD'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'SeasonalSstLatRmse', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=box,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=box,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=box, **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "SeasonalSstLatRmse: the modeled time-period is too short: "
                            + str(len(sst_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "SeasonalSstLatRmse: the observed time-period is too short: "
                            + str(len(sst_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    sst_model, Method = PreProcessTS(sst_model, Method, compute_sea_cycle=True, **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', compute_sea_cycle=True, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # standard deviation computation
    sst_model = Std(sst_model)
    sst_obs = Std(sst_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after Std', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        sst_model, sst_obs, Method = TwoVarRegrid(sst_model, sst_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                          'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Zonal average
    sst_model = AverageZonal(sst_model)
    sst_obs = AverageZonal(sst_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageZonal', 15, **dict_debug)

    # Computes the root mean square difference
    sstRmse = RmsMeridional(sst_model, sst_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(sst_model), 'observations': arrayToList(sst_obs),
                      'axis': list(sst_model.getAxis(0)[:])}

    # Create output
    LatRmseMetric = {
        'name': Name, 'value': sstRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model':actualtimeboundsmodel, 'time_period_observations':actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return LatRmseMetric


def SeasonalSstLonRmse(sstfilemodel, sstnamemodel, sstareafilemodel, sstareanamemodel, sstlandmaskfilemodel,
                       sstlandmasknamemodel, sstfileobs, sstnameobs, sstareafileobs, sstareanameobs, sstlandmaskfileobs,
                       sstlandmasknameobs, box, centered_rmse=0, biased_rmse=1, debug=False, **kwargs):
    """
    The SeasonalSstLonRmse() function computes the climatological (12 months) SST zonal (longitude) standard
    deviation root mean square error (RMSE) in a 'box' (usually the Equatorial Pacific)

    Inputs:
    ------
    :param sstfilemodel: string
        path_to/filename of the file (NetCDF) of the modeled SST
    :param sstnamemodel: string
        name of SST variable (tos, ts) in 'sstfilemodel'
    :param sstareafilemodel: string
        path_to/filename of the file (NetCDF) of the model areacell for SST
    :param sstareanamemodel: string
        name of areacell variable (areacella, areacello) in 'sstareafilemodel'
    :param sstlandmaskfilemodel: string
        path_to/filename of the file (NetCDF) of the model landmask for SST
    :param sstlandmasknamemodel: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfilemodel'
    :param sstfileobs: string
        path_to/filename of the file (NetCDF) of the observed SST
    :param sstnameobs: string
        name of SST variable (tos, ts) in 'sstfileobs'
    :param sstareafileobs: string
        path_to/filename of the file (NetCDF) of the observations areacell for SST
    :param sstareanameobs: string
        name of areacell variable (areacella, areacello) in 'sstareafileobs'
    :param sstlandmaskfileobs: string
        path_to/filename of the file (NetCDF) of the observations landmask for SST
    :param sstlandmasknameobs: string
        name of landmask variable (sftlf, lsmask, landmask) in 'sstlandmaskfileobs'
    :param box: string
        name of box ('equatorial_pacific') for SST
    :param centered_rmse: int, optional
        default value = 0 returns uncentered statistic (same as None). To remove the mean first (i.e centered statistic)
        set to 1. NOTE: Most other statistic functions return a centered statistic by default
    :param biased_rmse: int, optional
        default value = 1 returns biased statistic (number of elements along given axis)
        If want to compute an unbiased variance pass anything but 1 (number of elements along given axis minus 1)
    :param debug: bolean, optional
        default value = False debug mode not activated
        If want to activate the debug mode set it to True (prints regularly to see the progress of the calculation)
    usual kwargs:
    :param detrending: dict, optional
        see EnsoUvcdatToolsLib.Detrend for options
        the aim if to specify if the trend must be removed
        detrending method can be specified
        default value is False
    :param frequency: string, optional
        time frequency of the datasets
        e.g., frequency='monthly'
        default value is None
    :param min_time_steps: int, optional
        minimum number of time steps for the metric to make sens
        e.g., for 30 years of monthly data mintimesteps=360
        default value is None
    :param normalization: boolean, optional
        True to normalize by the standard deviation (needs the frequency to be defined), if you don't want it pass
        anything but true
        default value is False
    :param regridding: dict, optional
        see EnsoUvcdatToolsLib.TwoVarRegrid and EnsoUvcdatToolsLib.Regrid for options
        the aim if to specify if the model is regridded toward the observations or vice versa, of if both model and
        observations are regridded toward another grid
        interpolation tool and method can be specified
        default value is False
    :param smoothing: dict, optional
        see EnsoUvcdatToolsLib.Smoothing for options
        the aim if to specify if variables are smoothed (running mean)
        smoothing axis, window and method can be specified
        default value is False
    :param time_bounds_model: tuple, optional
        tuple of the first and last dates to extract from the modeled SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None
    :param time_bounds_obs: tuple, optional
        tuple of the first and last dates to extract from the observed SST file (strings)
        e.g., time_bounds=('1979-01-01T00:00:00', '2017-01-01T00:00:00')
        default value is None

    Output:
    ------
    :return LonRmseMetric: dict
        name, value, value_error, units, method, nyears_model, nyears_observations, time_frequency, time_period_model,
        time_period_observations, ref

    Method:
    -------
        uses tools from uvcdat library

    Notes:
    -----
        TODO: add error calculation to rmse (function of nyears)

    """
    # test given kwargs
    needed_kwarg = ['detrending', 'frequency', 'min_time_steps', 'normalization', 'regridding', 'smoothing',
                    'time_bounds_model', 'time_bounds_obs']
    for arg in needed_kwarg:
        try:
            kwargs[arg]
        except:
            kwargs[arg] = DefaultArgValues(arg)

    # Define metric attributes
    Name = 'SST zonal seasonality RMSE'
    Units = 'C'
    Method = 'Zonal root mean square error of ' + box + ' climatological sst STD'
    Ref = 'Using CDAT regridding and rms (uncentered and biased) calculation'

    # Read file and select the right region
    if debug is True:
        EnsoErrorsWarnings.DebugMode('\033[92m', 'SeasonalSstLonRmse', 10)
        dict_debug = {'file1': '(model) ' + sstfilemodel, 'file2': '(obs) ' + sstfileobs,
                      'var1': '(model) ' + sstnamemodel, 'var2': '(obs) ' + sstnameobs}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'Files', 10, **dict_debug)
    sst_model = ReadSelectRegionCheckUnits(sstfilemodel, sstnamemodel, 'temperature', box=box,
                                           time_bounds=kwargs['time_bounds_model'], **kwargs)
    sst_obs = ReadSelectRegionCheckUnits(sstfileobs, sstnameobs, 'temperature', box=box,
                                         time_bounds=kwargs['time_bounds_obs'], **kwargs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape),
                      'time1': '(model) ' + str(TimeBounds(sst_model)), 'time2': '(obs) ' + str(TimeBounds(sst_obs))}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadSelectRegionCheckUnits', 15, **dict_debug)

    # Read areacell
    if sstareafilemodel:
        model_areacell = ReadAreaSelectRegion(sstareafilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    else:
        model_areacell = ReadAreaSelectRegion(sstfilemodel, areaname=sstareanamemodel, box=box, **kwargs)
    if sstareafileobs:
        obs_areacell = ReadAreaSelectRegion(sstareafileobs, areaname=sstareanameobs, box=box, **kwargs)
    else:
        obs_areacell = ReadAreaSelectRegion(sstfileobs, areaname=sstareanameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_areacell is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_areacell.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_areacell.shape)
        if obs_areacell is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_areacell.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_areacell.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadAreaSelectRegion', 15, **dict_debug)

    # Read landmask
    if sstlandmaskfilemodel:
        model_landmask = ReadLandmaskSelectRegion(sstlandmaskfilemodel, landmaskname=sstlandmasknamemodel, box=box,
                                                  **kwargs)
    else:
        model_landmask = ReadLandmaskSelectRegion(sstfilemodel, landmaskname=sstlandmasknamemodel, box=box, **kwargs)
    if sstlandmaskfileobs:
        obs_landmask = ReadLandmaskSelectRegion(sstlandmaskfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    else:
        obs_landmask = ReadLandmaskSelectRegion(sstfileobs, landmaskname=sstlandmasknameobs, box=box, **kwargs)
    if debug is True:
        dict_debug = {}
        if model_landmask is not None:
            dict_debug['axes1'] = '(model) ' + str([ax.id for ax in model_landmask.getAxisList()])
            dict_debug['shape1'] = '(model) ' + str(model_landmask.shape)
        if obs_landmask is not None:
            dict_debug['axes2'] = '(obs) ' + str([ax.id for ax in obs_landmask.getAxisList()])
            dict_debug['shape2'] = '(obs) ' + str(obs_landmask.shape)
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after ReadLandmaskSelectRegion', 15, **dict_debug)

    # Apply landmask
    if model_landmask is not None:
        sst_model = ApplyLandmask(sst_model, model_landmask, maskland=True, maskocean=False)
        if model_areacell is None:
            model_areacell = ArrayOnes(model_landmask, id='areacell')
        model_areacell = ApplyLandmaskToArea(model_areacell, model_landmask, maskland=True, maskocean=False)
        del model_landmask
    if obs_landmask is not None:
        sst_obs = ApplyLandmask(sst_obs, obs_landmask, maskland=True, maskocean=False)
        if obs_areacell is None:
            obs_areacell = ArrayOnes(obs_landmask, id='areacell')
        obs_areacell = ApplyLandmaskToArea(obs_areacell, obs_landmask, maskland=True, maskocean=False)
        del obs_landmask

    # checks if the time-period fulfills the minimum length criterion
    if isinstance(kwargs['min_time_steps'], int):
        mini = kwargs['min_time_steps']
        if len(sst_model) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "SeasonalSstLonRmse: the modeled time-period is too short: "
                            + str(len(sst_model)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)
        if len(sst_obs) < mini:
            list_strings = ["ERROR " + EnsoErrorsWarnings.MessageFormating(INSPECTstack()) + ": too short time-period",
                            str().ljust(5) + "SeasonalSstLonRmse: the observed time-period is too short: "
                            + str(len(sst_obs)) + " (minimum time-period: " + str(mini) + ")"]
            EnsoErrorsWarnings.MyError(list_strings)

    # Number of years
    yearN_model = sst_model.shape[0] / 12
    yearN_obs = sst_obs.shape[0] / 12

    # Time period
    actualtimeboundsmodel = TimeBounds(sst_model)
    actualtimeboundsobs = TimeBounds(sst_obs)

    # Preprocess variables (computes anomalies, normalizes, detrends TS, smoothes TS, averages horizontally)
    # here only the detrending (if applicable) and time averaging are performed
    sst_model, Method = PreProcessTS(sst_model, Method, compute_sea_cycle=True, **kwargs)
    sst_obs, unneeded = PreProcessTS(sst_obs, '', compute_sea_cycle=True, **kwargs)
    del model_areacell, obs_areacell
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after PreProcessTS', 15, **dict_debug)

    # standard deviation computation
    sst_model = Std(sst_model)
    sst_obs = Std(sst_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after Std', 15, **dict_debug)

    # Regridding
    if isinstance(kwargs['regridding'], dict):
        known_args = {'model_orand_obs', 'newgrid', 'missing', 'order', 'mask', 'newgrid_name', 'regridder',
                      'regridTool', 'regridMethod'}
        extra_args = set(kwargs['regridding']) - known_args
        if extra_args:
            EnsoErrorsWarnings.UnknownKeyArg(extra_args, INSPECTstack())
        sst_model, sst_obs, Method = TwoVarRegrid(sst_model, sst_obs, Method, region=box, **kwargs['regridding'])
        if debug is True:
            dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                          'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                          'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
            EnsoErrorsWarnings.DebugMode('\033[92m', 'after TwoVarRegrid', 15, **dict_debug)

    # Meridional average
    sst_model = AverageMeridional(sst_model)
    sst_obs = AverageMeridional(sst_obs)
    if debug is True:
        dict_debug = {'axes1': '(model) ' + str([ax.id for ax in sst_model.getAxisList()]),
                      'axes2': '(obs) ' + str([ax.id for ax in sst_obs.getAxisList()]),
                      'shape1': '(model) ' + str(sst_model.shape), 'shape2': '(obs) ' + str(sst_obs.shape)}
        EnsoErrorsWarnings.DebugMode('\033[92m', 'after AverageMeridional', 15, **dict_debug)

    # Computes the root mean square difference
    sstRmse = RmsZonal(sst_model, sst_obs, centered=centered_rmse, biased=biased_rmse)

    # Dive down diagnostic
    dive_down_diag = {'model': arrayToList(sst_model), 'observations': arrayToList(sst_obs),
                      'axis': list(sst_model.getAxis(0)[:])}

    # Create output
    LonRmseMetric = {
        'name': Name, 'value': sstRmse, 'value_error': None, 'units': Units, 'method': Method,
        'nyears_model': yearN_model, 'nyears_observations': yearN_obs, 'time_frequency': kwargs['frequency'],
        'time_period_model': actualtimeboundsmodel, 'time_period_observations': actualtimeboundsobs, 'ref': Ref,
        'dive_down_diag': dive_down_diag,
    }
    return LonRmseMetric
# ---------------------------------------------------------------------------------------------------------------------#




