TPC-DS Item Rental Management System
A command-line Item Rental Management System built on MariaDB and populated with the TPC-DS benchmark dataset. Implemented the full database query layer in db_handler.py, connecting the CLI application to five tables which includes item, customer, rental, rental_history, 
and waitlist to support end-to-end rental workflows.

Key features include:
- Adding and editing items and customer records
- Renting and returning items with availability checks
- Granting rental extensions and managing waitlists
- Filtered search across inventory and customer data

All database interactions use parameterized SQL queries to prevent injection, with joins and aggregations to ensure accurate results. Query output is mapped to Python model objects for clean, consistent display in the CLI.
