import json
import concurrent.futures
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from services.grafana import push_logs_to_loki
from services.supabase import insert_error_ticket, insert_ticket
from services.webdriver import get_webdriver
from dotenv import load_dotenv

load_dotenv()

DO_LOGGING = True

LATEST_CITATIONS_FILE = 'latest_citations.json'

print("Pulling from", LATEST_CITATIONS_FILE)

def log_to_loki(level: str, message: str, extra_info: dict = None):
    stream = {
        "service": "ucsd-ticket-scraper",
        "job": "scrape-new-citations",
        "level": level
    }
    messages = [message]
    if extra_info:
        messages.append(json.dumps(extra_info))
    push_logs_to_loki(stream, messages)

# Function to check for an error message
def check_for_error_message(driver):
    try:
        error_message_element = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "message"))
        )
        return error_message_element.text
    except TimeoutException:
        return None


def check_for_error_validation_message(driver):
    try:
        error_message_element = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "validation-summary-errors"))
        )
        return error_message_element.text
    except TimeoutException:
        return None


# Function to check for a redirection
def check_for_redirect(driver):
    try:
        WebDriverWait(driver, 3).until(EC.url_contains("/Account/Citations/Results"))
        return True
    except TimeoutException:
        return False


def extract_citation_details(driver, citation_id):
    try:
        # Wait until the table containing the citation details appears
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "citations-list-table"))
        )

        # Find all the rows in the citation table
        rows = driver.find_elements(
            By.XPATH, "//table[@id='citations-list-table']//tbody//tr"
        )

        # List to hold citation data for each row
        citations_data = []

        for row in rows:
            # Extract the citation details from each column in the row
            citation_number = row.find_element(By.XPATH, "./td[1]").text
            status = row.find_element(By.XPATH, "./td[2]").text
            balance = row.find_element(By.XPATH, "./td[3]").text
            issue_date = row.find_element(By.XPATH, "./td[4]").text
            license_plate = row.find_element(By.XPATH, "./td[5]").text
            location = row.find_element(By.XPATH, "./td[6]").text

            # Store citation data into a dictionary
            citation_data = {
                "citation_number": citation_number,
                "status": status,
                "balance": balance,
                "issue_date": issue_date,
                "license_plate": license_plate,
                "location": location,
                "just_scraped": str(citation_id) == str(citation_number),
            }

            # Append the dictionary to the citations_data list
            citations_data.append(citation_data)

        log_to_loki("info", f"Citation details extracted for citation ID {citation_id}", {"citations_data": citations_data})
        return citations_data  # Return the list of dictionaries

    except TimeoutException:
        log_to_loki("error", f"Timeout occurred while extracting citation details for citation ID {citation_id}")
        return None
    except NoSuchElementException:
        log_to_loki("error", f"No such element found while extracting citation details for citation ID {citation_id}")
        return None


def get_citation_status_with_driver(citation_id, driver):
    log_to_loki("info", f"Getting citation details for {citation_id}")

    try:
        # Navigate to the URL
        driver.get("https://ucsd-transportation.t2hosted.com/Account/Portal")

        # Wait for the citation input field to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "citationSearchBox"))
        )

        # Enter the citation ID
        citation_input = driver.find_element(By.ID, "citationSearchBox")
        citation_input.clear()
        citation_input.send_keys(citation_id)

        # Click the search button
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[@type='submit' and contains(text(), 'Search Citations')]",
                )
            )
        )
        search_button.click()

        # Run checks for redirection or errors
        with concurrent.futures.ThreadPoolExecutor() as executor:
            error_check = executor.submit(check_for_error_message, driver)
            redirect_check = executor.submit(check_for_redirect, driver)
            unavailable_check = executor.submit(
                check_for_error_validation_message, driver
            )

            # Wait for either result to return
            done, _ = concurrent.futures.wait(
                [error_check, redirect_check, unavailable_check],
                return_when=concurrent.futures.FIRST_COMPLETED,
            )

            for future in done:
                result = future.result()
                if result == True:
                    # If redirection is detected, extract citation details
                    return extract_citation_details(driver, citation_id)
                elif isinstance(result, str):
                    return f"Error message found: {result}"

        return "No result found."

    except TimeoutException:
        log_to_loki("error", f"Timeout occurred while fetching citation data for citation ID {citation_id}")
        return "Timeout occurred while fetching citation data"


# Citation status checker and Supabase integration function
def handle_citation_with_driver(citation_id, driver):
    start_time = time.time()  # Start time for logging

    # Fetch the citation status from the UCSD portal
    citation_status = get_citation_status_with_driver(citation_id, driver)

    # Log the result and time taken
    end_time = time.time()
    time_taken = end_time - start_time
    if DO_LOGGING:
        log_to_loki("info", f"Citation ID: {citation_id} | Time Taken: {time_taken:.2f} seconds | Result: {citation_status}")


    # Handle different outcomes from the citation status
    if isinstance(citation_status, list):
        # Loop through all citation records in the list and insert each one
        for citation in citation_status:
            try:
                response = insert_ticket(
                    citation_id=citation.get("citation_number", None),
                    status=citation.get("status", None),
                    issue_date=citation.get("issue_date", None),
                    license_plate=citation.get("license_plate", None),
                    balance=citation.get("balance", None),
                    location=citation.get("location", None),
                    just_scraped=citation.get("just_scraped", False)  # Pass the just_scraped flag

                )
                if DO_LOGGING:
                    log_to_loki("info", f"Citation ID {citation.get('citation_number')} data inserted/updated in tickets successfully.")

            except Exception as e:
                if DO_LOGGING:
                    log_to_loki("error", 
                        f"Error inserting/updating tickets for citation ID {citation.get('citation_number')}: {e}"
                    )
                return False  # Failed insertion
        return True  # Success: all citations were inserted

    elif "Error message found" in citation_status:
        # Insert into "error_tickets" based on error content
        try:
            if (
                "Your search did not match any unpaid citations" in citation_status
                or "No results found" in citation_status
            ):
                response = insert_error_ticket(
                    citation_id, citation_status, should_try_again=True
                )
                if DO_LOGGING:
                    log_to_loki("warning",
                        f"Error: Citation ID {citation_id} either appealed or something else."
                    )
                return True  # Citation exists but errored. Try again later and move on

            elif (
                "The citation you entered does not match any citations in the system"
                in citation_status
            ):
                if DO_LOGGING:
                    log_to_loki("info", f"Citation ID {citation_id} does not exist.")
                    
                return False  # Citation does not exist. Do not insert and do not move on

            elif (
                "The citation you entered has already been paid"
                in citation_status
            ):
                response = insert_error_ticket(
                    citation_id, citation_status, should_try_again=False
                )
                
                if DO_LOGGING:
                    log_to_loki("warning", f"Citation ID {citation_id} has already been paid.")
                
                return True  # Citation has already been paid. Move on and do not try again
            
            else:
                response = insert_error_ticket(
                    citation_id, citation_status, should_try_again=True
                )
                if DO_LOGGING:
                    log_to_loki("warning",
                        f"Error: Citation ID {citation_id} gave an unhandled citation status: {citation_status}."
                    )
                return False  # Some unhandled citation error. Try again and do not move on
        except Exception as e:
            if DO_LOGGING:
                log_to_loki("error", 
                    f"Error inserting into error_tickets for citation ID {citation_id}: {e}"
                )
            return False  # Error handling failed

    response = insert_error_ticket(
        citation_id, "Some unknown error occurred", should_try_again=True
    )
    if DO_LOGGING:
        log_to_loki("warning",
            f"Error: Citation ID {citation_id} gave an unhandled citation status."
        )
    return False  # Unexpected response

def load_latest_citations():
    """Load the latest citations from the JSON file."""
    with open(LATEST_CITATIONS_FILE, "r") as json_file:
        return json.load(json_file)


def save_latest_citations(latest_citations):
    """Save the updated latest citations to the JSON file."""
    with open(LATEST_CITATIONS_FILE, "w") as json_file:
        json.dump(latest_citations, json_file, indent=4)


def scrape_new_citations(driver):
    """Continuously check for new citations on each device and process them."""
    latest_citations = (
        load_latest_citations()
    )  # Load the latest citations from the file

    max_retries = 3  # Maximum number of retries
    retry_count = 0

    while retry_count < max_retries:
        try:
            for device, citation_id in latest_citations.items():
                next_citation_id = (
                    citation_id + 1
                )  # Start with the next citation number

                while True:
                    # Handle the citation and check if it was successfully inserted
                    citation_handled = handle_citation_with_driver(
                        next_citation_id, driver
                    )

                    if citation_handled:
                        log_to_loki("info",
                            f"New citation found and handled for {device}: {next_citation_id}"
                        )

                        # Update the latest citation ID for this device
                        latest_citations[device] = next_citation_id

                        # Save the updated citation data back to the JSON file
                        save_latest_citations(latest_citations)

                        # Log the new citation
                        if DO_LOGGING:
                            log_to_loki("info",
                                f"Processed new citation for {device}: {next_citation_id}"
                            )

                        # Increment to try the next citation immediately
                        next_citation_id += 1
                    else:
                        log_to_loki("info",
                            f"No more new citations for {device}. Last known: {next_citation_id - 1}"
                        )
                        break  # Exit the while loop when no new citation is found

                # Sleep for a few seconds to avoid overwhelming the server with requests
                time.sleep(0.3)

            # Exit loop if no issues occur
            break

        except Exception as e:
            log_to_loki("error", f"Error in scrape_new_citations: {e}")

            retry_count += 1
            if retry_count < max_retries:
                log_to_loki("info", f"Retrying ({retry_count}/{max_retries})...")
                driver.quit()  # Quit the current driver instance
                driver = get_webdriver()  # Restart a new WebDriver instance
            else:
                log_to_loki("error", "Max retries exceeded in scrape_new_citations. Exiting process.")
                break
    
    log_to_loki("info", "Restarting chromedriver to prevent memory leaks...")
    driver.quit()  # Quit the current driver instance
    driver = get_webdriver()  # Restart a new WebDriver instance
    
    return driver
    

def run_scrape_new_citations_thread(driver):
    """Run scrape_new_citations function in a separate thread."""
    while True:
        try:
            driver = scrape_new_citations(driver)  # Update the driver
        except Exception as e:
            if DO_LOGGING:
                log_to_loki("error", f"Error in scrape_new_citations: {e}")
        time.sleep(1)  # Sleep for a short while to avoid high CPU usage
    
# Call the function to start the threads
driver = get_webdriver()  # Get WebDriver instance for scraping

log_to_loki("info", "Starting to get new citations")

run_scrape_new_citations_thread(driver)