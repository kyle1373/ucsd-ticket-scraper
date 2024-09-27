import supabaseAdmin from "@lib/supabaseAdmin";
import { NextRequest } from "next/server";
import { formatISO, subDays } from "date-fns";
import Link from "next/link";

type Ticket = {
  citation_id: number;
  status: string;
  device_num: number;
  issue_date: string;
  license_plate: string;
  balance: string;
  location: string;
  created_at: string;
};

// Revalidate the data every 5 seconds (or use ISR if needed)
export const revalidate = 5;

// The server-side component
export default async function HomePage({
  searchParams,
}: {
  searchParams: { search?: string; deviceNum?: string };
}) {
  function convertToPDTandFormat(dateString: string): string {
    const date = new Date(dateString);

    // Convert date to PDT timezone
    const options: Intl.DateTimeFormatOptions = {
      timeZone: "America/Los_Angeles",
      year: "2-digit",
      month: "2-digit",
      day: "2-digit",
    };

    // Format the date as MM/DD/YY
    return new Intl.DateTimeFormat("en-US", options).format(date);
  }

  const searchQuery = searchParams.search?.trim() || ""; // Get the search query from URL params
  const deviceNumQuery = searchParams.deviceNum?.trim() || ""; // Get the device number query from URL params

  const dateAfterString = "2024-09-16T23:12:40.708043+00";
  // Prepare the base Supabase query for both regular and paid tickets
  let query = supabaseAdmin.from("tickets").select("*");
  let paidQuery = null; // Initialize to null and set conditionally

  let isLast24HoursQuery = false; // To keep track of if we're querying the last 24 hours
  let totalFees = 0; // Variable to accumulate the total fees

  // If there is a search query or device number query, apply ILIKE filter and the specific created_at filter
  if (searchQuery || deviceNumQuery) {
    if (searchQuery) {
      query = query.ilike("location", `%${searchQuery}%`);
    }
    if (deviceNumQuery) {
      query = query.eq("device_num", `${deviceNumQuery}`);
      // Only include error tickets if deviceNum is present and no search query
      // paidQuery = supabaseAdmin
      //   .from("error_tickets")
      //   .select("*")
      //   .eq("device_num", `${deviceNumQuery}`)
      //   .gt("created_at", "2024-09-16T23:12:40.708043+00")
      //   .limit(100);
    }
    query = query.gt("created_at", dateAfterString).limit(1000);
  } else {
    // If no search query, pull all tickets from the last 24 hours
    const last24Hours = formatISO(subDays(new Date(), 1));
    query = query.gt("created_at", dateAfterString);
    // paidQuery = supabaseAdmin
    //   .from("error_tickets")
    //   .select("*")
    //   .gt("created_at", last24Hours);
    isLast24HoursQuery = true; // Mark that we are querying for the last 24 hours
  }

  // Apply common ordering for both scenarios
  query = query
    .order("created_at", { ascending: false, nullsFirst: false })
    .order("citation_id", { ascending: false, nullsFirst: false })
    .order("issue_date", { ascending: false, nullsFirst: false });

  // Fetch data from both queries (if paidQuery is defined)
  const [ticketResult, paidTicketResult] = await Promise.all([
    query,
    paidQuery ? paidQuery : Promise.resolve({ data: [], error: null }), // Fallback to empty array if no paidQuery
  ]);

  const { data: tickets, error: ticketError } = ticketResult;
  const { data: paidTickets, error: paidError } = paidTicketResult;

  if (ticketError || paidError) {
    console.error("Error fetching tickets:", ticketError || paidError);
    return <div>Failed to load tickets.</div>;
  }

  // Map paid tickets to the Ticket type and mark them as paid
  const mappedPaidTickets = paidTickets?.map((data) => ({
    citation_id: data.citation_id,
    issue_date: convertToPDTandFormat(data.created_at),
    device_num: data.device_num,
    status: "PAID",
    license_plate: "*******",
    balance: "$80.00",
    location: data.location || "UNKNOWN",
    created_at: data.created_at,
  }));

  // Combine regular tickets and paid tickets into one array
  let combinedTickets = tickets || [];
  if (mappedPaidTickets) {
    combinedTickets = [...combinedTickets, ...mappedPaidTickets];
  }

  // Sort the combined tickets by created_at in descending order
  combinedTickets.sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  // Parse balance and sum up the fees if there is no search query or device number query
  if (!searchQuery && !deviceNumQuery && combinedTickets) {
    totalFees = combinedTickets.reduce((sum, ticket) => {
      const parsedBalance = parseFloat(
        ticket.balance.replace(/[^0-9.-]+/g, "")
      ); // Remove $ symbol and parse as float
      return sum + (isNaN(parsedBalance) ? 0 : parsedBalance); // Add to sum, skip NaN
    }, 0);
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-4">UCSD Tickets</h1>
      <h1 className="text-base font-bold text-neutral-700 mb-4">
        This website no longer updates in real time and is just a 7 day archive
        because UCSD shut it down
      </h1>
      <h1 className="text-base font-bold text-neutral-700 mb-4">
        <Link
          className="underline text-blue-500 hover:text-blue-600"
          href={
            "https://kylewade.dev/blog/reverse-engineering-ucsd-parking-ticket-system"
          }
        >
          Read the blogpost here
        </Link>
      </h1>
      {/* Search Form */}
      <form
        method="GET"
        action="/"
        className="mb-4 flex flex-wrap space-y-2 md:space-y-0 md:space-x-2"
      >
        <input
          type="text"
          name="search" // This will append `?search=value` to the URL
          placeholder="Search location"
          defaultValue={searchQuery} // Show the current search query in the input
          className="px-4 py-2 border border-gray-300 rounded-lg w-full md:w-auto"
        />
        <input
          type="text"
          name="deviceNum" // This will append `?deviceNum=value` to the URL
          placeholder="Search device number"
          defaultValue={deviceNumQuery} // Show the current device number query in the input
          className="px-4 py-2 border border-gray-300 rounded-lg w-full md:w-auto"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-500 text-white rounded-lg w-full md:w-auto text-center"
        >
          Search
        </button>
        {/* Clear search button */}
        {(searchQuery || deviceNumQuery) && (
          <a
            href="/" // Navigates back to the root URL, clearing the search query
            className="px-4 py-2 bg-gray-500 text-white rounded-lg w-full md:w-auto text-center"
          >
            Clear Search
          </a>
        )}
      </form>

      {/* Conditionally display ticket count if querying the last 24 hours */}
      {!searchQuery && !deviceNumQuery && isLast24HoursQuery && (
        <p className="text-gray-600 mb-4">
          {combinedTickets.length} tickets ($
          {totalFees.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
          ) from 9/16/2024 - 9/23/2024
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200">
          <thead className="bg-gray-200">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Issue Date
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                License Plate
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Fee
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Location
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Device #
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Detected
              </th>
            </tr>
          </thead>
          <tbody>
            {combinedTickets?.map((ticket: Ticket) => (
              <tr key={ticket.citation_id} className="border-t">
                <td className="px-4 py-2 whitespace-nowrap">
                  {new Date(ticket.issue_date).toLocaleDateString()}
                </td>
                <td className="px-4 py-2 whitespace-nowrap">
                  {ticket.license_plate}
                </td>
                <td className="px-4 py-2 whitespace-nowrap">
                  {ticket.balance}
                </td>
                <td className="px-4 py-2 whitespace-nowrap">
                  {ticket.location}
                </td>
                <td className="px-4 py-2 whitespace-nowrap">
                  {ticket.device_num}
                </td>
                <td className="px-4 py-2 whitespace-nowrap">
                  {new Intl.DateTimeFormat("en-US", {
                    timeZone: "America/Los_Angeles",
                    year: "numeric",
                    month: "2-digit", // Ensure 2-digit month (MM)
                    day: "2-digit", // Ensure 2-digit day (DD)
                    hour: "numeric",
                    minute: "numeric",
                    second: "numeric",
                    hour12: true, // Use 12-hour format
                  }).format(new Date(ticket.created_at))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Disclaimer */}
      <footer className="mt-8 text-center text-gray-600 text-sm">
        <p>
          This website is not affiliated with UC San Diego and is for
          educational and research purposes only.
        </p>
      </footer>
    </div>
  );
}
