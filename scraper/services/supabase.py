import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz
from services.helpers import parse_citation_number

load_dotenv()

# Load Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL or SERVICE_ROLE_KEY not defined")

# Initialize the Supabase client
supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)


# Function to parse date to UTC timestamptz
def parse_to_utc(issue_date: str) -> str:
    # Parse the date string (assuming the format is MM/DD/YYYY)
    local_date = datetime.strptime(issue_date, "%m/%d/%Y")

    # Set timezone to UTC (because we want the same date in UTC, regardless of local timezone)
    local_date = local_date.replace(tzinfo=pytz.UTC)

    # Convert to UTC ISO format
    return local_date.isoformat()

# Function to parse date to PDT timestamp
def parse_to_pdt(issue_date: str) -> str:
    # Parse the date string (assuming the format is MM/DD/YYYY)
    local_date = datetime.strptime(issue_date, "%m/%d/%Y")

    # Set timezone to Pacific Daylight Time (PDT)
    pdt_timezone = pytz.timezone('America/Los_Angeles')
    local_date = pdt_timezone.localize(local_date)

    # Convert to PDT ISO format
    return local_date.isoformat()

# Function to convert a PDT date to UTC
def convert_pdt_to_utc(issue_date: str) -> str:
    # Parse the date string (assuming the format is MM/DD/YYYY)
    local_date = datetime.strptime(issue_date, "%m/%d/%Y")
    
    # Set the timezone to Pacific Daylight Time (PDT)
    pdt_timezone = pytz.timezone('America/Los_Angeles')
    local_date_pdt = pdt_timezone.localize(local_date)
    
    # Convert the PDT time to UTC
    utc_date = local_date_pdt.astimezone(pytz.UTC)
    
    # Return the UTC date in ISO format
    return utc_date.isoformat()

# Check if ticket exists in 'tickets' table by citation_id
def check_ticket_exists(citation_id: int):
    response = supabase.table("tickets").select("*").eq("citation_id", citation_id).execute()
    return response.data if response.data and len(response.data) > 0 else None

# Insert ticket with adjusted created_at logic
# Insert ticket with adjusted created_at logic
def insert_ticket(citation_id: int, status: str, issue_date: str, license_plate: str, balance: str, location: str, just_scraped: bool = False):
    issue_date_utc = convert_pdt_to_utc(issue_date)
    parsed_citation = parse_citation_number(citation_id)
    
    # Check if ticket already exists
    existing_ticket = check_ticket_exists(citation_id)
    
    if existing_ticket:
        # If ticket exists, use its existing created_at value
        created_at = existing_ticket[0]['created_at']
    else:
        current_time_utc = datetime.now(pytz.UTC)
        time_difference = current_time_utc - datetime.fromisoformat(issue_date_utc)

        if time_difference > timedelta(hours=36):
            # If the current time and the issue time are greater than 36 hours apart, set created_at to issue_date_utc
            created_at = issue_date_utc
        else:
            # Otherwise, set created_at to current time
            created_at = current_time_utc.isoformat()

    # Data to insert into tickets table
    data = {
        "citation_id": citation_id,
        "status": status,
        "issue_date": issue_date,  # Use PDT formatted date
        "license_plate": license_plate,
        "balance": balance,
        "location": location,
        "region_num": parsed_citation["region_num"],
        "device_num": parsed_citation["device_num"],
        "created_at": created_at,  # Use the computed created_at value
    }

    # Insert or update the ticket in the table
    response = supabase.table("tickets").upsert(data).execute()
    return response



# Function to get ticket by citation_id
def get_ticket(citation_id: int):
    # Query the "tickets" table
    response = (
        supabase.table("tickets").select("*").eq("citation_id", citation_id).execute()
    )

    # Check if we got a result from the tickets table
    if response.data and len(response.data) > 0:
        return response.data[0]  # Return the first result if found in tickets

    # If not found in "tickets", query the "error_tickets" table
    response = (
        supabase.table("error_tickets")
        .select("*")
        .eq("citation_id", citation_id)
        .execute()
    )

    # Check if we got a result from the error_tickets table
    if response.data and len(response.data) > 0:
        return response.data[0]  # Return the first result if found in error_tickets

    # If not found in either table, return None
    return None


# Function to insert error ticket
def insert_error_ticket(citation_id: int, error_message: str, should_try_again: bool):
    parsed_citation = parse_citation_number(citation_id)

    # Data you want to insert
    data = {
        "citation_id": citation_id,
        "error_message": error_message,
        "should_try_again": should_try_again,
        "region_num": parsed_citation["region_num"],
        "device_num": parsed_citation["device_num"],
    }

    # Specify the table name and insert the data
    response = supabase.table("error_tickets").upsert(data).execute()

    # Check the response
    return response
