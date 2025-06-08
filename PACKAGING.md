## Building the Executable
## (NOTE: SCRIPTS MUST BE PACKAGED ON A WINDOWS MACHINE)

To build the executable from the spec file, ensure that you are operating under the correct working directory. 
We reccommend creating a new folder on a local machine that houses run_shiny.py, shiny_implementation.py, 
GS_Classes.py, GS_Functions.py, outline.py, and the algos package (which contains deferred_acceptance.py). 
Then, open a command line at this folder, and run the following statement:

```bash
pyinstaller run_shiny.spec
