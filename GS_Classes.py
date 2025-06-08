import datetime
import pandas as pd

class Driver:
    """Drivers have Standard Routes, Bids, and Rejected Routes and traits"""
    def __init__(self, OriginalBids=[], ID = 0, Hours=0):
        self.Routes = []  # all routes they currently run at a given point in the program
        self.OriginalBids = OriginalBids # save all bids, can use for debugging
        self.ActiveBids = []  # charter bids that have not been rejected
        self.BidStatus = {} # dictionary of rejection reasons
        self.ID = ID # Driver ID
        self.Hours = Hours # Works worked
        self.Trained = False # Flag if the driver has not had training for SpEd
        self.SeniorityNumber = None # Seniority Number
        self.Name = None # Driver Name displayed on tables
        self.ForceRejectedBids = [] # List of bids we force pre-processing to omit
    def populate_identification(self, driver_data):
        """driver_data is a Series of data in the following order: name, ID, seniority number"""
        self.Name = driver_data.FullName
        self.ID = driver_data.DriverID
        try:
            test = float(driver_data.SeniorityNumber) + 1
        except:
            return "Seniority List contains a seniority number that is not a number"
        self.SeniorityNumber = driver_data.SeniorityNumber
        return


class Route:
    """Routes have specific days, start time and end time. There are traits like required training and equipment"""
    def __init__(self, ID = 0, capacity = 0, hours=0):
        self.ActiveTimes = []
        self.Hours = hours
        self.ID = ID
        self.RequiresTraining = False
        self.equipment = False
        # Number of drivers for a route
        self.capacity = capacity

        # If we need to delineate between there and back, might want to use:
        # self.num_bus_there = 0
        # self.num_bus_back = 0
        # self.size_there = 0
        # self.size_back = 0
        self.DropPick = False  # whether a route is one leg of a combined drop and pick route
        self.Lunch = False  # whether there's lunch during the route
        self.Standard = False  # whether the route is a standard (school) route or a charter
        self.AssignedDrivers = []





