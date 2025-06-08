from datetime import datetime, timedelta
import GS_Classes as gsc
import pandas as pd

dow_to_day = {'U': 0, 'M': 1, 'T': 2, 'W': 3, 'R': 4, 'F': 5,
              'S': 6}
inv_dow_to_day = {v: k for k, v in dow_to_day.items()}


def route_conflicts(route, all_intervals):
    """
    Helper function for route_time_conflicts()
    Check whether any time interval in a Route conflicts with any time interval in the current assigned Routes
    """
    if route.ActiveTimes is list:
        intervals = route.ActiveTimes
    else:
        intervals = [route.ActiveTimes]
    return any(all_intervals.overlaps(iv).any() for iv in intervals)


def route_time_conflicts(driver):
    """
    Removes invalid bids based on time conflicts with already assigned Routes
    """
    valid_bids = []
    all_route_intrv_list = []
    if not driver.Routes:
        # print('empty')
        return 0
    for r in driver.Routes:
        all_route_intrv_list.extend(r.ActiveTimes)
    all_route_interval = pd.IntervalIndex(all_route_intrv_list)
    for bid in driver.ActiveBids:
        # print(bid.ActiveTimes)
        if not route_conflicts(bid, all_route_interval):
            valid_bids.append(bid)
        else:
            driver.BidStatus[bid.ID] = 'Time Conflict'
    driver.ActiveBids = valid_bids


def add_force_rejects(driver_id, route_id, driver_id_to_driver_object, charter_id_to_route_object):
    """
    Input: Driver ID and Route ID, driver ID to object dictionary, charter route ID to object dictionary
    Output: None but adds force rejected bids to attribute and removes them from ActiveBids
    """
    driver = driver_id_to_driver_object[driver_id]
    ob = driver.OriginalBids.copy()  # For some reason OriginalBids gets overwritten somewhere so this stops that
    driver.ForceRejectedBids.append(charter_id_to_route_object[route_id])
    driver.ActiveBids.remove(charter_id_to_route_object[route_id])
    driver.BidStatus[route_id] = 'Force Rejected'
    driver.OriginalBids = ob


def hour_limits(driver, max_hrs):
    """
    Removes invalid bids based on hour limits given a Driver and a limit on hours (set globally in frontend)
    """
    valid_bids = []
    for bid in driver.ActiveBids:
        if driver.Hours + bid.Hours <= max_hrs:
            valid_bids.append(bid)
        else:
            driver.BidStatus[bid.ID] = 'Hour Limit Exceeded'
    driver.ActiveBids = valid_bids


def qualifications(driver):
    """
    Checks if Driver does not have SpEd training.
    If Driver does not, it removes any bids for that do require SpEd training.
    Not currently used
    """
    training = driver.Trained
    valid_bids = []
    for route in driver.ActiveBids:
        if not route.RequiresTraining:
            valid_bids.append(route)
        elif route.RequiresTraining and training:
            valid_bids.append(route)
        else:
            driver.BidStatus[route.ID] = 'Not SpEd trained'
    driver.ActiveBids = valid_bids


def pre_processing(driver_list, max_hrs, driver_id_to_driver_object, charter_id_to_route_object, force_reject_tuples=None):
    """
    Input: List of Driver, maximum hours per week a driver can work, tuples of driver ID,
            route ID force rejects, driver ID to object dictionary, charter route ID to object dictionary
    Output: None but calls all pre-processing subcomponents
    """
    if force_reject_tuples is not None:
        for driver_ID, route_ID in force_reject_tuples:
            add_force_rejects(driver_ID, route_ID, driver_id_to_driver_object, charter_id_to_route_object)
    for driver in driver_list:
        route_time_conflicts(driver)
        hour_limits(driver, max_hrs)
        # qualifications(driver)


def create_time_intervals(route_data, padding):
    """
    Input: route_data, row from the current format of Bytecurve export and padding parameter (set globally in frontend)
    Output: Returns a list of all times that the route is active, for all days of the week
    Times are encoded as timedeltas relative to the start of the week (Sunday-Saturday)
    EX: Monday noon is 1 day 12 hours
    """
    # converts exported DOW codes to numbers for timedelta
    # U = Sunday, update based on actual Bytecurve DOW codes if needed
    intrvs = []
    hours = []
    dep = route_data['DepartureTime']
    dep_abs = datetime.strptime(dep, "%I:%M %p").strftime('%H:%M')
    dep_t = pd.to_datetime(dep_abs, format='%H:%M')

    ret = route_data['ReturnTime']
    ret_abs = datetime.strptime(ret, "%I:%M %p").strftime('%H:%M')
    ret_t = pd.to_datetime(ret_abs, format='%H:%M')

    for char in route_data['DOW']:
        start = pd.Timedelta(days=dow_to_day[char]) + pd.to_timedelta(dep_t.hour, unit='h') + pd.to_timedelta(
            dep_t.minute, unit='m')
        end = pd.Timedelta(days=dow_to_day[char]) + pd.to_timedelta(ret_t.hour, unit='h') + pd.to_timedelta(
            ret_t.minute, unit='m')
        hours.append(pd.Interval(start, end, closed='both').length.seconds / 3600)

        pad_start = start + pd.Timedelta(minutes = int(padding))
        pad_end = end - pd.Timedelta(minutes=int(padding))
        if pad_start < pad_end:
            intrvs.append(pd.Interval(pad_start, pad_end, closed = 'both'))
        else:  # handle if route time is too short to pad properly
            mid = start + (end - start)/2
            intrvs.append(pd.Interval(mid, mid + pd.Timedelta(minutes = 1), closed='both'))
    return intrvs, sum(hours)


def read_standard_routes(data, padding):
    """
    Helper for initialize()
    Input: Bytecurve standard routes export
    Output: List of all standard routes, dictionary mapping standard route IDs to driver IDs
    """
    standard_routes = []
    standard_routes_to_drivers = dict()
    data_clean = data[['Employee', 'Days of the week', 'Depot departure time', 'Depot return time']]
    data_clean.reset_index(inplace=True)
    data_clean.columns = ['RouteID', 'DriverID', 'DOW', 'DepartureTime', 'ReturnTime']
    for _, row in data_clean.iterrows():
        tmp = gsc.Route(ID=row.RouteID)
        tmp.Standard = True
        intrvs, hours = create_time_intervals(row, padding)
        tmp.ActiveTimes = intrvs
        tmp.Hours = hours
        standard_routes.append(tmp)
        standard_routes_to_drivers[row.RouteID] = row.DriverID
    return standard_routes, standard_routes_to_drivers


def read_seniority_data(data):
    """
    Helper for initialize()
    Input: Seniority DataFrame in specified format (see templates)
    Output: List of all drivers, dictionary mapping driver IDs to Driver objects
    """
    drivers = []
    id_to_drivers = dict()
    for _, row in data.iterrows():
        tmp = gsc.Driver()
        val = tmp.populate_identification(row)
        if val:
            return None, val
        drivers.append(tmp)
        id_to_drivers[row.DriverID] = tmp
    return drivers, id_to_drivers


def assign_standard_routes_to_drivers(routes, id_to_drivers, routes_to_drivers):
    """
    Helper for initialize()
    Input: List of routes, dictionary mapping driver IDs to Driver objects, dictionary mapping route IDs to driver IDs
    Output: None but adds routes to corresponding Driver's Routes attribute
    """
    for route in routes:
        driver_id = routes_to_drivers[route.ID]
        driver = id_to_drivers[driver_id]
        driver.Routes.append(route)
        driver.Hours += route.Hours


def initialize(standard_routes_data, seniority_data, padding):
    """
    Input: Standard Routes data, seniority data
    Output: List of all standard routes, dictionary mapping standard route IDs to drivers,
        List of all drivers, dictionary mapping driver IDs to Driver objects
    """
    #try:
    std_routes, std_routes_to_drivers = read_standard_routes(standard_routes_data, padding)
    #except Exception as e:
    #    return (None, None, None,"Bytecurve import for standard routes does not match expected input data types. P/U and Dropoff columns need to be datetime in Excel. "
    #    "Check columns are consistent.")
    drivers, id_to_drivers = read_seniority_data(seniority_data)
    #if drivers is None:
    #    return None,None,None,"Seniority List contains a seniority number that is not a number"
    #try:
    assign_standard_routes_to_drivers(std_routes, id_to_drivers, std_routes_to_drivers)
    #except Exception as e:
    #    return None, None, None, "Some unknown issue occured while reading static routes and/or seniority list"
    return std_routes, std_routes_to_drivers, drivers, id_to_drivers


def get_charter_interval(row):
    """
    Helper function for read_charters()
    Input: Takes in a charter (row) from the charter data (see template for format)
    Output: Returns an interval corresponding to the active time of the trip and the hours of the trip
    """
    start = (pd.Timedelta(days=dow_to_day[row['Trip DOW']]) + pd.to_timedelta(row['P/U Time'].hour, unit='h')
             + pd.to_timedelta(row['P/U Time'].minute, unit='m'))
    end = (pd.Timedelta(days=dow_to_day[row['Trip DOW']]) + pd.to_timedelta(row['Return Time'].hour, unit='h')
           + pd.to_timedelta(row['Return Time'].minute, unit='m'))
    if start >= end:  # correction for overnights
        end = (pd.Timedelta(days=dow_to_day[row['Trip DOW']] + 1) + pd.to_timedelta(row['Return Time'].hour, unit='h')
               + pd.to_timedelta(row['Return Time'].minute, unit='m'))
    return pd.Interval(start, end, closed='both'), pd.Interval(start, end, closed='both').length.seconds / 3600


def dow_converter(dow):
    """
    Helper function for DOW conversion
    """
    return dow + 1 if dow + 1 < 7 else 0


def read_charters_routes(charter_data):
    """
    Input: Reads charters (rows) from the charter data (see template for format)
    Output: Returns a list of Route objects with charter information filled in
        and a dictionary mapping the route ID to the Route object
    """
    charter_id_to_routes = dict()
    charter_data['P/U Time'] = charter_data['P/U Time'].apply(lambda x: pd.to_datetime(x, format='%H:%M:%S'))
    charter_data['Return Time'] = charter_data['Return Time'].apply(
        lambda x: pd.to_datetime(x, format='%H:%M:%S'))
    charter_data['Trip DOW'] = charter_data['Trip Date'].apply(
        lambda x: inv_dow_to_day[dow_converter(pd.Timestamp(x).dayofweek)])

    charter_routes = []
    for ind, row in charter_data.iterrows():
        tmp = gsc.Route()
        tmp.capacity = row.Buses
        tmp.ID = row['Trip Number']
        charter_id_to_routes[tmp.ID] = tmp
        time, hours = get_charter_interval(row)
        tmp.Hours = hours
        tmp.ActiveTimes = time
        charter_routes.append(tmp)
    return charter_routes, charter_id_to_routes


def read_charter_bids(id_to_drivers, form_data, charter_id_to_routes):
    """
    Input: Takes in the driver ID to Driver dict, the form DataFrame and the charter ID to charter Route dict
    Output: Assigns the bids in order to each Driver object
    """
    for ind, row in form_data.iterrows():
        tmp = id_to_drivers[row.Id]
        pref = row[-50:].dropna().to_list()  # 50 is hardcoded based off the number of bid spots in the intake form
        pref_route_objects = [charter_id_to_routes[r] for r in pref]
        tmp.OriginalBids = pref_route_objects
        tmp.ActiveBids = pref_route_objects


def assigned_bids(new_routes, driver_matches, iteration, bids_assigned, route_prefs):
    """
    Add routes to the driver's current routes
    new_routes: dictionary of routes that have been assigned in GS iteration
    driver_matches: dictionary of driver id to driver objects
    iteration: number of iterations
    bids_assigned: dictionary of drivers and route assignments
    route_prefs: dictionary of (routes, capacity): seniority list
    """
    removed_bids = []
    for key in list(new_routes.keys()):
        if isinstance(new_routes[key], gsc.Route):
            route = new_routes[key]
            # Add the route to the driver, add the driver got the match, set the driver to not have that bid left
            driver_matches[key].Routes.append(new_routes[key])
            driver_matches[key].Hours+= new_routes[key].Hours
            driver_matches[key].BidStatus[new_routes[key].ID] = f"Received Bid on iteration {iteration}"
            driver_matches[key].ActiveBids.remove(new_routes[key])
            # Handle assigned routes
            if route.capacity == 1:
                removed_bids.append(new_routes[key])
                if route in bids_assigned.keys():
                    bids_assigned[route].append(driver_matches[key])
                else:
                    bids_assigned[route] = [driver_matches[key]]
                route_prefs.pop((route, route.capacity))
                route.capacity = 0
            else:
                if route in bids_assigned.keys():
                    bids_assigned[route].append(driver_matches[key])
                else:
                    bids_assigned[route] = [driver_matches[key]]
                route_prefs[(route, route.capacity - 1)] = route_prefs.pop((route, route.capacity))
                route.capacity -= 1
    return bids_assigned, route_prefs, removed_bids


def taken_bids(all_drivers, removed_bids, iteration, max_hours):
    """
    Remove bids that drivers can no longer take
    all_drivers: list of all drivers
    removed_bids: list of the bids fulfilled in the cycle
    iteration: number in the iteration cycle"""
    for driver in all_drivers:
        revised_bids = []
        for route in driver.ActiveBids:
            if route in removed_bids:
                driver.BidStatus[route.ID] = f'Route already assigned on iteration {iteration}'
                #driver.ActiveBids.remove(route)
            else:
                revised_bids.append(route)
        driver.ActiveBids = revised_bids
        hour_limits(driver, max_hours)

def remove_same_day(new_routes, driver_matches):
    """
    Remove bids that occur on the same day
    new_routes: dictionary of routes that have been assigned in GS iteration
    driver_matches: dictionary of driver id to driver objects"""
    for key in list(new_routes.keys()):
        if isinstance(new_routes[key], gsc.Route):
            route = new_routes[key]
            route_day = route.ActiveTimes.left.components[0]
            revised_bids = []
            for bid in driver_matches[key].ActiveBids:
                if bid.ActiveTimes.left.components[0] == route_day:
                    # Do not uncomment or delete it the next line. We don't why keeping this uncommented makes this run correctly.
                    #if bid.ID not in driver_matches[key].BidStatus:
                        driver_matches[key].BidStatus[bid.ID] = f"Already received bid on same day"
                else:
                    revised_bids.append(bid)
            driver_matches[key].ActiveBids = revised_bids


def post_processing(all_drivers, new_routes, driver_matches, iteration, bids_assigned, route_prefs, max_hours):
    """
    Removes bids on days that a driver has a charter already assigned and removes already assigned routes
    """
    bids_assigned, route_prefs, removed_bids = assigned_bids(new_routes, driver_matches, iteration, bids_assigned,
                                                             route_prefs)
    taken_bids(all_drivers, removed_bids, iteration, max_hours)
    remove_same_day(new_routes, driver_matches)
    return bids_assigned, route_prefs


def diagnostics_sheet(drivers):
    """
    Returns diagnostic sheet (DataFrame of all Drivers, bids and the outcome of each bid)
    """
    results = []
    for driver in drivers:
        # print(driver.BidStatus)
        # print(driver.Hours)
        for bid in driver.OriginalBids:
            # try/except is critical
            try:
                z = driver.BidStatus[bid.ID]
            except:
                z = 5
            arr = [driver.Name, driver.ID, bid.ID, bid.ActiveTimes.left, bid.ActiveTimes.right, z]
            results.append(arr)

    res_df = pd.DataFrame(results, columns=['DriverName','DriverID', 'RouteID', 'TimeStart', 'TimeEnd', 'Status'])
    return res_df

