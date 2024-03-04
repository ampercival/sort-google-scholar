"""
This code creates a database with a list of publications data from Google 
Scholar.
The data acquired from GS is Title, Citations, Links and Rank.
It is useful for finding relevant papers by sorting by the number of citations
This example will look for the top 100 papers related to the keyword, 
so that you can rank them by the number of citations

As output this program will plot the number of citations in the Y axis and the 
rank of the result in the X axis. It also, optionally, export the database to
a .csv file.


"""

# Standard library imports
import argparse
import datetime
import os
import requests
from time import sleep
import warnings
import webbrowser

# Third-party libraries
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import pandas as pd
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, Toplevel
from tkinter.ttk import Scrollbar, Treeview


#Initialize the webdriver (used if needed)
global driver
driver = None

# Default Parameters
KEYWORD = 'machine learning' # Default argument if command line is empty
NRESULTS = 100 # Fetch 100 articles
CSVPATH = './results' # Current folder
SAVECSV = True
SORTBY = 'Citations'
PLOT_RESULTS = False
now = datetime.datetime.now()
ENDYEAR = now.year # Current year
DEBUG=False # debug mode
MAX_CSV_FNAME = 255

# Websession Parameters
GSCHOLAR_URL = 'https://scholar.google.com/scholar?start={}&q={}&hl=en&as_sdt=0,5'
YEAR_RANGE = '' #&as_ylo={start_year}&as_yhi={end_year}'
#GSCHOLAR_URL_YEAR = GSCHOLAR_URL+YEAR_RANGE
STARTYEAR_URL = '&as_ylo={}'
ENDYEAR_URL = '&as_yhi={}'
ROBOT_KW=['unusual traffic from your computer network', 'not a robot']

def get_citations(content):
    out = 0
    for char in range(0,len(content)):
        if content[char:char+9] == 'Cited by ':
            init = char+9
            for end in range(init+1,init+6):
                if content[end] == '<':
                    break
            out = content[init:end]
    return int(out)

def get_year(content):
    for char in range(0,len(content)):
        if content[char] == '-':
            out = content[char-5:char-1]
    if not out.isdigit():
        out = 0
    return int(out)

def setup_driver():
    try:        
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
                     
    except Exception as e:
        print(e)
        print("Please install Selenium and chrome webdriver for manual checking of captchas")

    print('Loading webdriver...\n')
    
    service = Service()
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=service, options=options)
       
    return driver

def get_author(content):
    for char in range(0,len(content)):
        if content[char] == '-':
            out = content[2:char-1]
            break
    return out
  
def get_content_with_selenium(url):
    
    global driver
    
    if driver is None:
        driver = setup_driver()
    
    driver.get(url)
    captcha_txt = None
    captcha_el = None
    
    
    #print(f"The element is: {captcha_el}")
    
    # Get element from page
    try:
        captcha_el = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.ID, "gs_captcha_f")))
    except:
        print(f"No Captcha element found.")
    
    #print(f"The element is: {captcha_el}")
    
    if captcha_el is not None:
        captcha_txt = captcha_el.text
   
        
    if captcha_txt is not None and any(kw in captcha_txt for kw in ROBOT_KW):
        raw_input("Solve captcha manually and press enter here to continue...")
    
    el = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH,"/html/body")))
    c = el.get_attribute('innerHTML')
        
    return c.encode('utf-8')


def main(keyword, nresults, save_csv, csvpath, sortby, plot_results, start_year, end_year, debug, display_results):
   
    global driver
   
    # Create main URL based on command line arguments
    if start_year:
        GSCHOLAR_MAIN_URL = GSCHOLAR_URL + STARTYEAR_URL.format(start_year)
    else:
        GSCHOLAR_MAIN_URL = GSCHOLAR_URL

    if end_year != now.year:
        GSCHOLAR_MAIN_URL = GSCHOLAR_MAIN_URL + ENDYEAR_URL.format(end_year)

    if debug:
        GSCHOLAR_MAIN_URL='https://web.archive.org/web/20210314203256/'+GSCHOLAR_URL

    # Start new session
    session = requests.Session()
    #headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

    # Variables
    links = []
    title = []
    citations = []
    year = []
    author = []
    venue = []
    publisher = []
    rank = [0]

    # Get content from nresults URLs
    for n in range(0, nresults, 10):
        #if start_year is None:
        url = GSCHOLAR_MAIN_URL.format(str(n), keyword.replace(' ','+'))
        if debug:
            print("Opening URL:", url)
        #else:
        #    url=GSCHOLAR_URL_YEAR.format(str(n), keyword.replace(' ','+'), start_year=start_year, end_year=end_year)
        
        # print("Opening URL:", url)

        print("Loading next {} results".format(n+10))
        page = session.get(url)#, headers=headers)
        c = page.content
        
        #pyperclip.copy(c.decode('ISO-8859-1'))
        #raw_input("Copied C")
               
        if any(kw in c.decode('ISO-8859-1') for kw in ROBOT_KW):
            print("Robot checking detected, handling with selenium (if installed)")
            try:
                # print(f"I went here when n = {n}")
                c = get_content_with_selenium(url)
            except Exception as e:
                print("No success. The following error was raised:")
                print(e)

        # Create parser
        soup = BeautifulSoup(c, 'html.parser', from_encoding='utf-8')

        # Get stuff
        mydivs = soup.findAll("div", { "class" : "gs_or" })

        for div in mydivs:
            try:
                links.append(div.find('h3').find('a').get('href'))
            except: # catch *all* exceptions
                links.append('Look manually at: '+url)

            try:
                title.append(div.find('h3').find('a').text)
            except:
                title.append('Could not catch title')

            try:
                citations.append(get_citations(str(div.format_string)))
            except:
                warnings.warn("Number of citations not found for {}. Appending 0".format(title[-1]))
                citations.append(0)

            try:
                year.append(get_year(div.find('div',{'class' : 'gs_a'}).text))
            except:
                warnings.warn("Year not found for {}, appending 0".format(title[-1]))
                year.append(0)

            try:
                author.append(get_author(div.find('div',{'class' : 'gs_a'}).text))
            except:
                author.append("Author not found")

            try:
                publisher.append(div.find('div',{'class' : 'gs_a'}).text.split("-")[-1])
            except:
                publisher.append("Publisher not found")

            try:
                venue.append(" ".join(div.find('div',{'class' : 'gs_a'}).text.split("-")[-2].split(",")[:-1]))
            except:
                venue.append("Venue not fount")

            rank.append(rank[-1]+1)

        # Delay 
        sleep(0.5)
    
    if driver is not None:
        driver.close()
        driver = None
    
    # Create a dataset and sort by the number of citations
    data = pd.DataFrame(list(zip(author, title, citations, year, publisher, venue, links)), index = rank[1:],
                        columns=['Author', 'Title', 'Citations', 'Year', 'Publisher', 'Venue', 'Source'])
    data.index.name = 'Rank'

    # Add columns with number of citations per year
    data['cit/year']=data['Citations']/(end_year + 1 - data['Year'])
    data['cit/year']=data['cit/year'].round(0).astype(int)

    # Sort by the selected columns, if exists
    try:
        data_ranked = data.sort_values(by=sortby, ascending=False)
    except Exception as e:
        print('Column name to be sorted not found. Sorting by the number of citations...')
        data_ranked = data.sort_values(by=sortby, ascending=False)
        print(e)

    # Print data
    print(data_ranked)

    # Plot by citation number
    if plot_results:
        plt.plot(rank[1:],citations,'*')
        plt.ylabel('Number of Citations')
        plt.xlabel('Rank of the keyword on Google Scholar')
        plt.title('Keyword: '+keyword)
        plt.show()

    # Save results
    if save_csv:
        fpath_csv = os.path.join(csvpath, keyword.replace(' ','_')+'.csv')
        fpath_csv = fpath_csv[:MAX_CSV_FNAME]
        data_ranked.to_csv(fpath_csv, encoding='utf-8')
        
    # Display the results if the checkbox is checked
    if display_results:
        display_dataframe(data_ranked)


def display_dataframe(df):
    # Create a new tkinter window
    new_window = Toplevel(root)
    new_window.title("Results Table")

    # Create a Treeview widget
    tree = Treeview(new_window, columns=list(df.columns), show="headings")
    tree.pack(side="left", fill="both", expand=True)

    # Add a vertical scrollbar
    scrollbar = Scrollbar(new_window, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    # Add the column names to the Treeview
    for col in df.columns:
        tree.heading(col, text=col, command=lambda _col=col: treeview_sort_column(tree, _col, False))
        tree.column(col, width=100)

    # Add the rows to the Treeview
    for index, row in df.iterrows():
        # Insert the row
        iid = tree.insert("", "end", values=list(row))

    # Bind click event to open hyperlink
    tree.bind("<Button-1>", lambda event: on_treeview_click(event, tree))

    new_window.mainloop()

    
def treeview_sort_column(tv, col, reverse):
    """Sort tree contents when a column header is clicked on."""
    # List of numeric columns
    numeric_cols = ["Citations", "Year", "cit/year"]

    # Grab values to sort
    if col in numeric_cols:
        # Convert values to integers for sorting
        data = [(int(tv.set(child, col)), child) for child in tv.get_children('')]
    else:
        data = [(tv.set(child, col), child) for child in tv.get_children('')]

    # Reorder data
    data.sort(reverse=reverse)

    for idx, (val, child) in enumerate(data):
        tv.move(child, '', idx)

    # Reverse sort next time
    tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))

def on_treeview_click(event, tree):
    # Check which row and column was clicked
    row = tree.identify_row(event.y)
    col = tree.identify_column(event.x)

    # Get the corresponding column number for the "Source" column. 
    # If you know the exact column position, you can hard-code it. 
    # For example, if it's the third column, you can use "#3".
    source_col_num = "#" + str(tree["columns"].index("Source") + 1)
    
    # If the "Source" column was clicked and there's a link, open it
    if col == source_col_num:
        item = tree.item(row, 'values')
        link = item[tree["columns"].index("Source")]
        if link:
            webbrowser.open(link)


# UI functions
def run_script():
    # Retrieve values from the UI
    keyword = keyword_entry.get()
    nresults = int(nresults_entry.get())
    csvpath = csvpath_entry.get()
    save_csv = savecsv_var.get()
    sortby = sortby_combobox.get()
    plot_results = plotresults_var.get()
    display_results = displayresults_var.get()
    
    # Retrieve start year and end year, convert to int or set default values
    start_year = int(startyear_entry.get()) if startyear_entry.get() else None
    end_year = int(endyear_entry.get()) if endyear_entry.get() else datetime.datetime.now().year
    
    debug = debug_var.get()

    # Call the main function with the retrieved values
    main(keyword, nresults, save_csv, csvpath, sortby, plot_results, start_year, end_year, debug, display_results)

def exit_application():
    root.destroy()
    
    
def load_results():
    # Open a file dialog and get the selected file's path
    filepath = filedialog.askopenfilename(title="Select a CSV file", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    
    # If a file is selected
    if filepath:
        try:
            # Load the CSV data into a dataframe
            df = pd.read_csv(filepath, index_col=0)
            
            # Display the dataframe
            display_dataframe(df)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while loading the CSV file:\n{e}")


# Create the UI
root = tk.Tk()
root.title("Google Scholar Scraper")
root.geometry("600x400")  # Adjust the window size

# Create frames for better organization
input_frame = ttk.LabelFrame(root, text="Input Parameters", padding=(10, 5))
input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

output_frame = ttk.LabelFrame(root, text="Output Options", padding=(10, 5))
output_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

button_frame = ttk.Frame(root, padding=(10, 5))
button_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="ns")

# Keyword
ttk.Label(input_frame, text="Keyword:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
keyword_entry = ttk.Entry(input_frame)
keyword_entry.insert(0, KEYWORD)  # Default value
keyword_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

# Sort By
ttk.Label(input_frame, text="Sort By:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
sortby_combobox = ttk.Combobox(input_frame, values=["Citations", "cit/year"])
sortby_combobox.set(SORTBY)  # Default value
sortby_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

# Number of Results
ttk.Label(input_frame, text="Number of Results:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
nresults_entry = ttk.Entry(input_frame)
nresults_entry.insert(0, NRESULTS)  # Default value
nresults_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

# Start and End Year
ttk.Label(input_frame, text="Start Year:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
startyear_entry = ttk.Entry(input_frame)
startyear_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

ttk.Label(input_frame, text="End Year:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
endyear_entry = ttk.Entry(input_frame)
endyear_entry.insert(0, ENDYEAR)  # Default value
endyear_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

# Debug Mode
debug_var = tk.BooleanVar(value=DEBUG)  # Default value
debug_check = ttk.Checkbutton(input_frame, text="Debug Mode", variable=debug_var)
debug_check.grid(row=5, column=0, columnspan=2, pady=5)

# CSV Path
ttk.Label(output_frame, text="CSV Path:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
csvpath_entry = ttk.Entry(output_frame)
csvpath_entry.insert(0, CSVPATH)  # Default value
csvpath_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

# Save CSV
savecsv_var = tk.BooleanVar(value=SAVECSV)  # Default value
savecsv_check = ttk.Checkbutton(output_frame, text="Save CSV", variable=savecsv_var)
savecsv_check.grid(row=1, column=0, columnspan=2, pady=5)

# Plot Results
plotresults_var = tk.BooleanVar(value=PLOT_RESULTS)  # Default value
plotresults_check = ttk.Checkbutton(output_frame, text="Plot Results", variable=plotresults_var)
plotresults_check.grid(row=2, column=0, columnspan=2, pady=5)

# Display Results
displayresults_var = tk.BooleanVar(value=True)  # Default value
displayresults_check = ttk.Checkbutton(output_frame, text="Display Results", variable=displayresults_var)
displayresults_check.grid(row=3, column=0, columnspan=2, pady=5)

# Button to run the script
run_button = ttk.Button(button_frame, text="Run Script", command=run_script)
run_button.pack(pady=20)

# Load Previous Results
load_button = ttk.Button(button_frame, text="Load Results", command=load_results)
load_button.pack(pady=20)

# Exit Button
exit_button = ttk.Button(button_frame, text="Exit", command=exit_application)
exit_button.pack(pady=20)

root.mainloop()
