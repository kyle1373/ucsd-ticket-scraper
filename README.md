![image](https://github.com/user-attachments/assets/dd7b91e4-9cc5-497c-a1b8-eacbdfe8cd02)

Read the blogpost for the full documented writeup: https://kylewade.dev/blog/reverse-engineering-ucsd-parking-ticket-system  

# What is this?

This is a scraping program which took advantage of a loophole with the **University of California, San Diego's (UCSD)** parking ticket system. By reverse engineering how citation numbers in parking tickets were calculated, a user is able to look up new parking tickets in UCSD's system via webscraping new predicted citation numbers. This resulted in a website which tracked the locations of tickets being issued on campus in real time, resulting in **$56,900** in parking tickets being scraped in 7 days. Eventually, UCSD was notified of this exploit and patched it in their system. However, there are other universities which are vulnerable to this webscraping technique (see the writeup above at the very end).

![image](https://github.com/user-attachments/assets/6510bc84-ff3b-4d73-9f9d-c57195c0d253)

This codebase contains 3 folders:

`/database` contains the PostgreSQL database schema, which can be self hosted via Supabase  
`/scraper` contains the webscraping program which scrapes parking tickets from UCSD's system using Selenium Chromedriver (can be extended to other universities)  
`/website` contains the Next.js website which is used to display parking tickets stored in the database  

If you have any questions, feel free to submit an issue here, and I will happily respond :)
