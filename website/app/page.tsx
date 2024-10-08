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

// Revalidate cache every 60 seconds (or use ISR if needed)
export const revalidate = 60;

export default async function HomePage({
  searchParams,
}: {
  searchParams: { search?: string; deviceNum?: string };
}) {
  const searchQuery = searchParams.search?.trim() || ""; // Get the search query from URL params
  const deviceNumQuery = searchParams.deviceNum?.trim() || ""; // Get the device number query from URL params

  const dateAfterString = "2024-09-16T23:12:40.708043+00"; // Get tickets only after this date by default

  let query = supabaseAdmin.from("tickets").select("*");

  let totalFees = 0; // Variable to accumulate the total fees

  query = query.gt("created_at", dateAfterString).limit(1000);

  if (searchQuery) {
    query = query.ilike("location", `%${searchQuery}%`);
  }
  if (deviceNumQuery) {
    query = query.eq("device_num", `${deviceNumQuery}`);
  }

  query = query
    .order("created_at", { ascending: false, nullsFirst: false })
    .order("citation_id", { ascending: false, nullsFirst: false })
    .order("issue_date", { ascending: false, nullsFirst: false });

  const ticketResult = await query; // Execute query

  const { data: tickets, error: ticketError } = ticketResult;

  if (ticketError) {
    console.error("Error fetching tickets:", ticketError);
    return <div>Failed to load tickets.</div>;
  }

  // Parse balance and sum up the fees if there is no search query or device number query
  if (!searchQuery && !deviceNumQuery && tickets) {
    totalFees = tickets.reduce((sum, ticket) => {
      const parsedBalance = parseFloat(
        ticket.balance.replace(/[^0-9.-]+/g, "")
      ); // Remove $ symbol and parse as float
      return sum + (isNaN(parsedBalance) ? 0 : parsedBalance);
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
          name="search"
          placeholder="Search location"
          defaultValue={searchQuery}
          className="px-4 py-2 border border-gray-300 rounded-lg w-full md:w-auto"
        />
        <input
          type="text"
          name="deviceNum"
          placeholder="Search device number"
          defaultValue={deviceNumQuery}
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
            href="/"
            className="px-4 py-2 bg-gray-500 text-white rounded-lg w-full md:w-auto text-center"
          >
            Clear Search
          </a>
        )}
      </form>

      {/* Conditionally display ticket count if querying the last 24 hours */}
      {!searchQuery && !deviceNumQuery && (
        <p className="text-gray-600 mb-4">
          {tickets.length} tickets ($
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
            {tickets?.map((ticket: Ticket) => (
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
                    month: "2-digit",
                    day: "2-digit",
                    hour: "numeric",
                    minute: "numeric",
                    second: "numeric",
                    hour12: true,
                  }).format(new Date(ticket.created_at))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <footer className="mt-8 text-center text-gray-600 text-sm">
        <p>
          This website is not affiliated with UC San Diego and is for
          educational and research purposes only.
        </p>
      </footer>
    </div>
  );
}
