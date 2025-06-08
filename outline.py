import algos.deferred_acceptance as def_ac
import GS_Classes as gsc
import GS_Functions as gsf
import pandas as pd

def gale_shapley_main(route_list, seniority, charters, bid_list, force_reject_tuples=None, max_hours=40, anti_padding = 30, sen_num = 0):
    """Route List, Seniority, Charters, Bid_List: Dataframe of Routes, Seniority List, Charters, Bids from pandas
    force_reject_tuples: Optional Dataframe of Force Rejections
    max_hours: Maximum Hours Drivers can work
    anti-padding: Take minutes off the start and end of routes (ie a route from 8:00 to 10:00 am with 30 minutes padding becomes 8:30 to 9:30 am)
    sen_num: Seniority Number of the last allocation, this is not the person you start with, it is the person you end with
    
    Returns: drivers list object, assigned bids, all charters, unassigned charters, id:driver dict, and last employee"""
    # Read data
    std_routes, std_routes_to_drivers, all_drivers, driver_matches = gsf.initialize(route_list, seniority, anti_padding)
    # Check if route list input correctly
    if isinstance(driver_matches, str):
        return None, None, driver_matches, None, None, None
    # Check charters read correctly
    try:
        charter_routes, charter_id_to_routes = gsf.read_charters_routes(charters)
    except:
        return None, None, "Charter Routes P/U and Dropoff are not read as datetime variables. Ensure they are all datetime variables not things like TBD, TBA, or text in Excel type formatting", None, None, None
    # Check Seniority list input correctly
    try:
        seniority_list = seniority["SeniorityNumber"].astype(str).to_list()
        if sen_num != 0:
            seniority_list = seniority_list[sen_num:] + seniority_list[:sen_num]
    except:
        return None, None, "Issue occured when reading Seniority List. Check if the SeniorityNumber column is corrected named as SeniorityNumber (not something like Seniority_Number or Senioritynumber)", None, None, None

    # Create route preferences (seniority list preference)
    route_prefs = {(route,route.capacity):seniority_list for route in charter_routes}
    driver_id = [d.ID for d in all_drivers]
    
    # Read charters
        # No errors here, assuming the charter list is the Microsoft Forms (aka no changes to the form)
    gsf.read_charter_bids(driver_matches, bid_list, charter_id_to_routes)

    # Remove bad bids
    gsf.pre_processing(all_drivers, max_hours, driver_matches, charter_id_to_routes, force_reject_tuples,)
    bids = [d.ActiveBids for d in all_drivers]

    # Load the driver bids
    bid_preferences = {k:v for (k,v) in zip(driver_id, bids)}

    # Helpful variables
    iteration = 0
    bids_assigned = {}
    old_routes = []
    last_empl = None
    # Start gale-shapley algo
    # Iterations set to less than 8 because drivers can only take 7 routes (technically yes there's an extra iteration included)
    while iteration < 8 and len(route_prefs.keys()) > 0:
        iteration+=1
        # Deferred Acceptance call, get back the matches and route assignments
        matches, new_routes, empl_assigned = def_ac.da(bid_preferences, route_prefs)
        if empl_assigned is not None:
            last_empl = empl_assigned
        # We don't use this for loop tbh
        for driver in matches.keys():
            if isinstance(matches[driver], gsc.Route):
                matches[driver].AssignedDrivers.append(driver)

        # post processing update variables
        bids_assigned, route_prefs = gsf.post_processing(all_drivers, new_routes, driver_matches, 
                                                         iteration, bids_assigned, route_prefs, max_hours)
        bids = [d.ActiveBids for d in all_drivers]
        bid_preferences = {k:v for (k,v) in zip(driver_id, bids)}

        # End iterations loop
        if set(old_routes) == set(route_prefs.keys()):
            break
        old_routes = list(route_prefs.keys())
    # Find all unassigned charters
    unassigned_charters = []
    for charter in charter_routes:
        if charter.capacity > 0:
            unassigned_charters.append(charter)
    # Return drivers list object, assigned bids, all charters, unassigned charters, id:driver dict, and last employee
    return all_drivers, bids_assigned, charter_routes, unassigned_charters, driver_matches, last_empl
    