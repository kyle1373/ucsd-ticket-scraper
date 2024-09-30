import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz
from services.helpers import parse_citation_number

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL or SERVICE_ROLE_KEY not defined")

supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

def convert_pdt_to_utc(issue_date: str) -> str:
    """This functionc converts PDT timezone to UTC"""
    # Parse the date string (assuming the format is MM/DD/YYYY)
    local_date = datetime.strptime(issue_date, "%m/%d/%Y")
    
    # Set the timezone to Pacific Daylight Time (PDT)
    pdt_timezone = pytz.timezone('America/Los_Angeles')
    local_date_pdt = pdt_timezone.localize(local_date)
    
    # Convert the PDT time to UTC
    utc_date = local_date_pdt.astimezone(pytz.UTC)
    
    # Return the UTC date in ISO format
    return utc_date.isoformat()

def check_ticket_exists(citation_id: int):
    """
    This function checks if a ticket exists in the database
    """
    response = supabase.table("tickets").select("*").eq("citation_id", citation_id).execute()
    return response.data if response.data and len(response.data) > 0 else None


def insert_ticket(citation_id: int, status: str, issue_date: str, license_plate: str, balance: str, location: str, just_scraped: bool = False):
    """
    This function inserts a valid ticket into the database
    """
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
        "created_at": created_at,
    }

    # Insert or update the ticket in the table
    response = supabase.table("tickets").upsert(data).execute()
    return response


def insert_error_ticket(citation_id: int, error_message: str, should_try_again: bool):
    """
    This function inserts an error ticket, which is a ticket that threw an error when we tried to scrape it. This error could be that the ticket was paid for already or it could be any other unhandled error.
    """
    parsed_citation = parse_citation_number(citation_id)

    data = {
        "citation_id": citation_id,
        "error_message": error_message,
        "should_try_again": should_try_again,
        "region_num": parsed_citation["region_num"],
        "device_num": parsed_citation["device_num"],
    }

    response = supabase.table("error_tickets").upsert(data).execute()

    return response
