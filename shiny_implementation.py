### To run this, type the following in terminal: shiny run shiny_implementation.py --reload
## For the windows users: python -m shiny run shiny_implementation.py --reload

# Import libraries for UI, reactive programming, and data handling
from shiny.express import ui, input, render, output 
from shiny.types import FileInfo
from shiny import reactive
from shiny.render import DataGrid
from faicons import icon_svg as icon
from htmltools import tags
from datetime import datetime
import pandas as pd

import GS_Classes as gsc # Custum classes for Gale Shapley allocation
import GS_Functions as gsf # Helper functions for Gale Shapley
from outline import gale_shapley_main # Completed Gale Shapley assignment function

# Create page title
ui.page_opts(title='NACSB Bus Assignment')

# Start a Shiny ui.card to hold all input information
with ui.card():
    ui.card_header('Input Files Here')

    # Driver preferences CSV upload
    with ui.div(style="display: inline-grid;"
            "grid-auto-flow: column;"
            "grid-auto-columns: min-content;"
            "align-items: center;"
            "gap: 0.25rem;"):
        ui.input_file("driver_prefs", "Input Driver Preferences", accept=['.csv'], multiple=False, width="375px") # Input button
        
        # Create the popup with data schema
        with ui.popover(title='Driver Preferences CSV Data Structure', placement='left' ):
            icon("circle-info")
            ui.HTML("""
                Required Columns: (Example input)<br/>
                'Id': (123456)<br/>
                '1': (11)<br/>
                '2': (12)<br/>
                etc
                """)
            
    # Static routes csv upload
    with ui.div(style="display: inline-grid;"
            "grid-auto-flow: column;"
            "grid-auto-columns: min-content;"
            "align-items: center;"
            "gap: 0.25rem;"):
        ui.input_file("driver_routes", "Input Static Routes", accept=['.csv'], multiple=False, width="375px") # Input button

        # Create the popup with data schema
        with ui.popover(title='Static Routes CSV Data Structure', placement='auto' ):
            icon("circle-info")
            ui.HTML("""
          Required Columns: (Example input)<br/>
          'Route identifier': (471936)<br/>
          'Days of the week': (MTWRF)<br/>
          'Depot departure time': (6:00 AM)<br/>
          'Depot return time': (9:29 AM)
        """)
    
    # Charter routes csv upload
    with ui.div(style="display: inline-grid;"
            "grid-auto-flow: column;"
            "grid-auto-columns: min-content;"
            "align-items: center;"
            "gap: 0.25rem;"):
        ui.input_file("charter_routes", "Input Charter Routes", accept=['.csv'], multiple=False, width="375px") # Input button

        # Create the popup with data schema
        with ui.popover(title='Charter Routes CSV Data Structure', placement='auto' ):
            icon("circle-info")
            ui.HTML("""
                    Required Columns: (Example input)<br/> 
                    'Buses': (1)<br/>
                    'Trip Number': (1)<br/>
                    'P/U Time': (18:30:00)<br/>
                    'Return Time': (23:30:00)<br/>
                    'Trip Date': (10/26/2024)
                    """)

    # Driver seniority routes csv upload
    with ui.div(style="display: inline-grid;"
            "grid-auto-flow: column;"
            "grid-auto-columns: min-content;"
            "align-items: center;"
            "gap: 0.25rem;"):
        ui.input_file("seniority_nums", "Input Seniority Numbers", accept=['.csv'], multiple=False, width="375px") # Input button

        # Create the popup with data schema
        with ui.popover(title='Seniority Numbers CSV Data Structure', placement='auto' ):
            icon("circle-info")
            ui.HTML("""
                    Required Columns: (Example input)<br/> 
                    'FullName': (Adam Smith)<br/>
                    'DriverID': (123456)<br/>
                    'SeniorityNumber': (1)
                    """)

    # Optional Force Reject Allocations csv upload
    with ui.div(style="display: inline-grid;"
            "grid-auto-flow: column;"
            "grid-auto-columns: min-content;"
            "align-items: center;"
            "gap: 0.25rem;"):
        ui.input_file("force_rejections", "Input Force-Rejection Assignments (Not Required)", accept=['.csv'], multiple=False, width="375px") # Input button

        # Create the popup with data schema
        with ui.popover(title='Force-Rejections Data Structure', placement='auto' ):
            icon("circle-info")
            ui.HTML("""
                    Required Columns: (Example input)<br/> 
                    'DriverID': (123456)<br/>
                    'RouteID': (50)
                    """)

    # Numerical inputs
    ui.input_numeric("max_hours", "Input maximum hours", value=40, min=0, step=1) # Input maximum hours each driver can work
    ui.input_numeric("padding", "Input time padding (minutes to cut off from route end time)", value = 30, min = 0, step = 1) # Input time padding, set value is 30
    ui.input_numeric("seniority", "Input Seniority Number from last allocation (not last seniority number + 1)", value = 0, step = 1) # Input last seniority number

    # Button that lets us run the Gale Shapley with our uploaded data
    ui.input_action_button("gs_run", "Run Driver Assignments")
    
    # Store status messages as reactive.Value so we can set and dispplay them later
    status_msg = reactive.Value("")
    status_msg2 = reactive.Value("")

    # Create a render.text function that displays the status messages assigned above (they're blank to begin with)
    @render.text
    def status_text():
        return status_msg.get()

# Create another ui.card for the outputs
with ui.card():
    ui.card_header('Output Table - Press Column Header to Sort')

    # Reactive storage for Dataframes to be displayed later
    stored_diagnostic_df=reactive.Value(None)
    stored_bid_assignments = reactive.Value(None)
    stored_charter_unassigned = reactive.Value(None)

    # Create a dataframe render
    @render.data_frame 
    @reactive.event(input.gs_run) # This sets the below function to run only when the "Run Driver Assignemnts" button is clicked
    def run_gale_shapley():
        """
        Executes when the Run button is clicked:
        1. Validates uploads and required columns
        2. Reads each CSV into a DataFrame
        3. Runs the Gale-Shapley matching algorithm
        4. Prepares DataFrames for display and download
        """

        # Makes sure all four required files are uploaded
        if not all([input.driver_prefs(), 
                    input.driver_routes(),
                    input.charter_routes(),
                    input.seniority_nums()]):
            status_msg.set('Please upload all four required files')
            return

        status_msg.set('Running Gale Shapley')

        # Read and validate driver preferences, we don't check for specific columns here though, as the data is taken right from the Microsoft Form.
        try:
            prefs_csv = input.driver_prefs()[0]
            prefs_path=prefs_csv['datapath']
            prefs_df=pd.read_csv(prefs_path)
        except:
            status_msg.set("Driver Bids file is not a csv!")
            return

        # Read and validate static routes
        try:
            routes_csv = input.driver_routes()[0]
            routes_path=routes_csv['datapath']
            routes_df=pd.read_csv(routes_path)
        except:
            # Check that error catch works
            status_msg.set("Driver Routes file is not a csv!")
            return
        
        # Check that required columns are in the static route csv
        try:
            req_columns = set(["Route identifier", 'Days of the week', 'Depot departure time', 'Depot return time'])
            missing = req_columns - set(routes_df.columns)
            if missing:
                status_msg.set(f"File for Driver Static Routes is missing columns: {', '.join(missing)}")
                return
        except:
            status_msg.set("Driver Static Routes csv does not have the correct columns")

        # Read and validate charter routes
        try:
            charters_csv = input.charter_routes()[0]
            charters_path=charters_csv['datapath']
            charters_df=pd.read_csv(charters_path)
        except:
            try:
                # Tries a different encoding. Likely causes an issue with the code breaking
                charters_df = pd.read_csv(charters_path, encoding = "ISO-8859-1")
            except:
                status_msg.set("Charter List file is not a csv!")
                return
            
        # Make sure required columns are in charter route csv
        try:
            req_columns = set(["Buses", "Trip Number", "P/U Time", "Return Time"])
            missing = req_columns - set(charters_df.columns)
            if missing:
                status_msg.set(f"File for Charter List is missing columns: {', '.join(missing)}")
                return
        except:
            status_msg.set("Driver Static Routes csv does not have the correct columns")

        # Read and validate seniority numbers
        try:
            seniority_csv = input.seniority_nums()[0]
            seniority_path=seniority_csv['datapath']
            seniority_df=pd.read_csv(seniority_path)
        except:
            status_msg.set("Seniority List file is not a csv!")
            return
        
        # Ensure required columns are in seniority list csv
        try:
            req_columns = set(['FullName', 'DriverID', 'SeniorityNumber'])
            missing = req_columns - set(seniority_df.columns)
            if missing:
                status_msg.set(f"File for Seniority List is missing columns: {', '.join(missing)}")
                return
        except:
            status_msg.set("Seniority list csv does not have the correct columns")

        # Read force-reject csv file
        if input.force_rejections():
            force_reject_csv=input.force_rejections()[0]
            force_reject_path=force_reject_csv['datapath']
            force_reject_df=pd.read_csv(force_reject_path)

            # Make it so all entries are ints, not strings
            force_reject_df['DriverID'] = force_reject_df['DriverID'].astype(int)
            force_reject_df['RouteID']  = force_reject_df['RouteID'].astype(int)

            # Use itertuples to construct the force-rejection df
            force_reject_list=list(
                force_reject_df[['DriverID','RouteID']].itertuples(index=False, name=None)
            )
        else:
            force_reject_list=None
        

        status_msg.set('Passed csvs')

        # Execute core gale-shapley algorithm
        all_drivers, bids_assigned, charters, unassigned_charters, driver_matches, last_empl = gale_shapley_main(routes_df, seniority_df, charters_df,
                                                               prefs_df, force_reject_tuples=force_reject_list, max_hours=int(input.max_hours()),
                                                               anti_padding=int(input.padding()), sen_num=int(input.seniority()))
        if all_drivers is None:
            status_msg.set(charters)

        # Create diagnostic sheet
        diagnostic_df=gsf.diagnostics_sheet(all_drivers)
        stored_diagnostic_df.set(diagnostic_df)

        status_msg.set('Algorithm completed, creating table')

        # Prepare the main assignment table
        rows = []
        for route, driver_row in bids_assigned.items():
            for i in range(len(driver_row)):
                # Driver details
                driver=driver_row[i]
                driver_name=seniority_df[seniority_df['SeniorityNumber']==driver.SeniorityNumber]['FullName'].item()
                driver_id=seniority_df[seniority_df['SeniorityNumber']==driver.SeniorityNumber]['DriverID'].item()
                # Route details
                charter_pickup=charters_df[charters_df['Trip Number']==route.ID]['P/U Time'].item().time()
                charter_return=charters_df[charters_df['Trip Number']==route.ID]['Return Time'].item().time()
                charter_date=charters_df[charters_df['Trip Number']==route.ID]['Trip Date'].item()
                charter_location=charters_df[charters_df['Trip Number']==route.ID]['Pick Up Location'].item()
                charter_destination=charters_df[charters_df['Trip Number']==route.ID]['Destination'].item()

                route_id_assignment = str(route.ID)+str(chr(ord('`')+(route.AssignedDrivers.index(driver.ID)+1))).upper()
                if len(route.AssignedDrivers) < 2:
                    route_id_assignment = route.ID
                
                # Append the dictionary onto our rows list
                rows.append({
                "Driver Name": driver_name,
                "Seniority Number": driver.SeniorityNumber,
                "Driver ID": driver_id,
                "Route ID": route_id_assignment,
                "Route Pickup Location": charter_location,
                "Route Destination": charter_destination,
                "Charter Date": charter_date,
                "Pick Up Time": charter_pickup,
                "Return Time": charter_return
                })
        
        # Turn rows into a Dataframe, and sort by seniority number
        output_df = pd.DataFrame(rows).sort_values(by='Seniority Number')
        stored_bid_assignments.set(output_df)

        # Create the dataframe for unassigned charters and display it
        charter_rows = []
        for charter in unassigned_charters:
            drivers = [driver_matches[driver].Name for driver in charter.AssignedDrivers]
            charter_rows.append({
                "Charter ID": charter.ID,
                "Charter Left Unassigned": charter.capacity,
                "Charter Drivers Assigned": ", ".join(drivers)
            })
        stored_charter_unassigned.set(pd.DataFrame(charter_rows))

        # Find the last seniority number to be assigned a route
        status_msg.set('Allocation Process Done!')
        last_id = None
        if last_empl is not None:
            last_id = driver_matches[last_empl].SeniorityNumber
        status_msg2.set('The last employee assigned is seniority number: '+str(last_id))

        # Returns a "Datagrid", Shinys way of displaying tables
        return DataGrid(
            output_df,
            height=800,
            summary=True
            )
    
    # Show the unassigned charters that we created in the previous function
    @render.data_frame
    @reactive.event(input.gs_run)
    def show_dataframe():
        return DataGrid(
            stored_charter_unassigned.get(),height = 400, summary = True
        )

    # Create custom naming conventions for .csv files
    y=datetime.now().year
    m=datetime.now().month
    d=datetime.now().day
    
    # Create the downloadable csv for charter assignments
    @render.download(label="Download Charter Assignments Sheet",
                     filename=f"{y}_{m}_{d}_Charter_Assignments.csv")
    def download_charters():
        downloadable_diagnostic = stored_bid_assignments.get()
        if downloadable_diagnostic is None:
            yield ""
        else:
           yield downloadable_diagnostic.to_csv(index=False)
    
    # Create the downloadable csv for unassigned Charters
    @render.download(label="Download Unassigned Charter Details Sheet",
                     filename=f"{y}_{m}_{d}_Charter_Unassigned.csv")
    def download_unassigned():
        downloadable_diagnostic = stored_charter_unassigned.get()
        if downloadable_diagnostic is None:
            yield ""
        else:
           yield downloadable_diagnostic.to_csv(index=False)
    
    # Create the downloadable csv for Diagnostic Sheet
    @render.download(label="Download Diagnostic Sheet",
                     filename=f"{y}_{m}_{d}_diagnostic_sheet.csv")
    def download_csv():
        downloadable_diagnostic=stored_diagnostic_df.get()
        if downloadable_diagnostic is None:
            yield ""
        else:
           yield downloadable_diagnostic.to_csv(index=False)

    # Display the last seniority number
    @render.text
    def status_text2():
        return status_msg2.get()
