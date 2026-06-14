from MARIADB_CREDS import DB_CONFIG
from mariadb import connect
from models.RentalHistory import RentalHistory
from models.Waitlist import Waitlist
from models.Item import Item
from models.Rental import Rental
from models.Customer import Customer
from datetime import date, timedelta


conn = connect(user=DB_CONFIG["username"], password=DB_CONFIG["password"], host=DB_CONFIG["host"],
               database=DB_CONFIG["database"], port=DB_CONFIG["port"])


cur = conn.cursor()

#HELPER FUNCTIONS:

def _row_to_item(row) -> Item:
    #Converts a database row (Item columns) into objects of the Item model
    item_id, product_name, brand, category, manufact, current_price, start_year, num_owned = row
    return Item(item_id=item_id.strip() if item_id else "",
                product_name=product_name.strip() if product_name else "",
                brand=brand.strip() if brand else "",
                category=category.strip() if category else "",
                manufact=manufact.strip() if manufact else "",
                current_price=float(current_price) if current_price is not None else 0.0,
                start_year=int(start_year) if start_year is not None else 0,
                num_owned=int(num_owned) if num_owned is not None else 0,
                )

def _row_to_customer(row) -> Customer:
    #Converts a database row (Customer columns) into objects of the Customer model
    customer_id, name, street_number, street_name, city, state, zip_code, email = row
    street_num = (street_number or "").strip()
    street_n = (street_name or "").strip()
    city_ = (city or "").strip()
    state_ = (state or "").strip()
    zip_ = (zip_code or "").strip()
    address = f"{street_num} {street_n}, {city_}, {state_} {zip_}".strip()
    return Customer(customer_id=customer_id.strip() if customer_id else "",
                    name=(name or "").strip(),
                    address=address,
                    email=(email or "").strip(),
    )

def _row_to_rental(row) -> Rental:
    #Converts a database row (rental columns) into objects of the Rental model
    item_id, customer_id, rental_date, due_date = row
    return Rental(
        item_id=item_id.strip() if item_id else "",
        customer_id=customer_id.strip() if customer_id else "",
        rental_date=str(rental_date),
        due_date=str(due_date),
    )

def _row_to_rental_history(row) -> RentalHistory:
    #Convert a database row (rental history columns) into a RentalHistory model object
    item_id, customer_id, rental_date, due_date, return_date = row
    return RentalHistory(
        item_id=item_id.strip() if item_id else "",
        customer_id=customer_id.strip() if customer_id else "",
        rental_date=str(rental_date),
        due_date=str(due_date),
        return_date=str(return_date),
    )

def _row_to_waitlist(row) -> Waitlist:
    #Convert a database row (waitlist columns) into a Waitlist model object
    item_id, customer_id, place_in_line = row
    return Waitlist(
        item_id=item_id.strip() if item_id else "",
        customer_id=customer_id.strip() if customer_id else "",
        place_in_line=int(place_in_line),
    )

def add_item(new_item: Item = None):
    """
    new_item - An Item object containing a new item to be inserted into the DB in the item table.
        new_item and its attributes will never be None.
    """
    #Generate the next surrogate key:
    cur.execute("SELECT COALESCE(MAX(i_item_sk), 0) + 1 FROM item")
    new_sk = cur.fetchone()[0]

    #recommended start_date using new item start year:
    start_date = f"{new_item.start_year}-01-01"
    cur.execute(
        """INSERT INTO item
        (i_item_sk, i_item_id, i_rec_start_date, i_product_name, i_brand, i_class, i_category, i_manufact, i_current_price, i_num_owned)
        VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
        """,
        (new_sk, new_item.item_id, start_date, new_item.product_name, new_item.brand, new_item.category, new_item.manufact, new_item.current_price, new_item.num_owned),
    )


def add_customer(new_customer: Customer = None):
    """
    new_customer - A Customer object containing a new customer to be inserted into the DB in the customer table.
        new_customer and its attributes will never be None.
    """
    #Expected: "123 Main St, Springfield, IL 62701"
    try:
        street_part, city_part, state_zip = [p.strip() for p in new_customer.address.split(",", 2)]
        street_tokens = street_part.split(" ", 1)
        ca_street_number = street_tokens[0] if len(street_tokens) > 0 else ""
        ca_street_name = street_tokens[1] if len(street_tokens) > 1 else ""
        ca_city = city_part.strip()
        state_zip_tokens = state_zip.strip().split(" ", 1)
        ca_state = state_zip_tokens[0] if len(state_zip_tokens) > 0 else ""
        ca_zip = state_zip_tokens[1] if len(state_zip_tokens) > 1 else ""
    except Exception:
        ca_street_number = ""
        ca_street_name = new_customer.address
        ca_city = ""
        ca_state = ""
        ca_zip = ""
    #Generate new address surrogate key:
    cur.execute("SELECT COALESCE(MAX(ca_address_sk), 0) + 1 FROM customer_address")
    new_address_sk = cur.fetchone()[0]
    cur.execute("""INSERT INTO customer_address (ca_address_sk, ca_street_number, ca_street_name, ca_city, ca_state, ca_zip)
    VALUES (?, ?, ?, ?, ?, ?)""",
                (new_address_sk, ca_street_number, ca_street_name, ca_city, ca_state, ca_zip),
    )

    name_parts = new_customer.name.split(" ", 1)
    first_name = name_parts[0] if len(name_parts) > 0 else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    #Generate new customer surrogate key:
    cur.execute("SELECT COALESCE(MAX(c_customer_sk), 0) + 1 FROM customer")
    new_customer_sk = cur.fetchone()[0]
    cur.execute("""INSERT INTO customer (c_customer_sk, c_customer_id, c_first_name, c_last_name, c_email_address, c_current_addr_sk)
    VALUES (?, ?, ?, ?, ?, ?)""",
                (new_customer_sk, new_customer.customer_id, first_name, last_name, new_customer.email, new_address_sk,
            ),
    )
def edit_customer(original_customer_id: str = None, new_customer: Customer = None):
    """
    original_customer_id - A string containing the customer id for the customer to be edited.
    new_customer - A Customer object containing attributes to update. If an attribute is None, it should not be altered.
    """
    #fetch customer's surrogate key and address key
    cur.execute("SELECT c_customer_sk, c_current_addr_sk FROM Customer WHERE c_customer_id = ?", (original_customer_id, ), )
    row = cur.fetchone()
    if row is None:
        return     #Customer not found
    cust_sk, addr_sk = row

    customer_updates = []
    customer_params = []
    if new_customer.customer_id is not None:
        customer_updates.append("c_customer_id = ?")
        customer_params.append(new_customer.customer_id)
    if new_customer.name is not None:
        name_parts = new_customer.name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        customer_updates.append("c_first_name = ?")
        customer_params.append(first_name)
        customer_updates.append("c_last_name = ?")
        customer_params.append(last_name)
    if new_customer.email is not None:
        customer_updates.append("c_email_address = ?")
        customer_params.append(new_customer.email)
    if customer_updates:
        customer_params.append(cust_sk)
        cur.execute(f"UPDATE customer SET {', '.join(customer_updates)} WHERE c_customer_sk = ?", customer_params, )

    #Update address if not None:
    if new_customer.address is not None:
        try:
            street_part, city_part, state_zip = [p.strip() for p in new_customer.address.split(",", 2)]
            street_tokens = street_part.split(" ", 1)
            ca_street_number = street_tokens[0] if len(street_tokens) > 0 else ""
            ca_street_name = street_tokens[1] if len(street_tokens) > 1 else ""
            ca_city = city_part.strip()
            state_zip_tokens = state_zip.strip().split(" ", 1)
            ca_state = state_zip_tokens[0] if len(state_zip_tokens) > 0 else ""
            ca_zip = state_zip_tokens[1] if len(state_zip_tokens) > 1 else ""
        except Exception:
            ca_street_number = ""
            ca_street_name = new_customer.address
            ca_city = ""
            ca_state = ""
            ca_zip = ""
        cur.execute("UPDATE customer_address SET ca_street_number = ?, ca_street_name = ?, ca_city = ?, ca_state = ?, ca_zip = ? WHERE ca_address_sk = ?",
                    (ca_street_number, ca_street_name, ca_city, ca_state, ca_zip, addr_sk),
            )




def rent_item(item_id: str = None, customer_id: str = None):
    """
    item_id - A string containing the Item ID for the item being rented.
    customer_id - A string containing the customer id of the customer renting the item.
    """
    today = date.today()
    due_date = today + timedelta(days=14)
    cur.execute("INSERT INTO rental (item_id, customer_id, rental_date, due_date) VALUES (?, ?, ?, ?)",
                (item_id, customer_id, today, due_date),
    )

def waitlist_customer(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's new place in line.
    """
    new_place = line_length(item_id) + 1
    cur.execute("INSERT INTO Waitlist (item_id, customer_id, place_in_line) VALUES (?, ?, ?)",
                (item_id, customer_id, new_place),
    )
    return new_place

def update_waitlist(item_id: str = None):
    """
    Removes person at position 1 and shifts everyone else down by 1.
    """
    #Deletes first entry:
    cur.execute("DELETE FROM Waitlist WHERE item_id = ? AND place_in_line = 1", (item_id,),
    )

    #Shift up by one position (decrementing):
    cur.execute("UPDATE Waitlist SET place_in_line = place_in_line - 1 WHERE item_id = ?", (item_id,),
    )



def return_item(item_id: str = None, customer_id: str = None):
    """
    Moves a rental from rental to rental_history with return_date = today.
    """
    #Fetch current rental record:
    cur.execute("SELECT item_id, customer_id, rental_date, due_date FROM Rental WHERE item_id = ? AND customer_id = ?",
                (item_id, customer_id),
        )
    row = cur.fetchone()
    if row is None:
        return #Rental not found
    r_item_id, r_customer_id, r_rental_date, r_due_date = row
    return_date = date.today()

    #Insert into rental history:
    cur.execute("""INSERT INTO rental_history (item_id, customer_id, rental_date, due_date, return_date)
    VALUES (?, ?, ?, ?, ?)""",
                (r_item_id, r_customer_id, r_rental_date, r_due_date, return_date),
    )

    #Now remove from rental:
    cur.execute("DELETE FROM rental WHERE item_id = ? AND customer_id = ?", (item_id, customer_id), )

def grant_extension(item_id: str = None, customer_id: str = None):
    """
    Adds 14 days to the due_date.
    """
    query="""
    UPDATE rental
    SET due_date = due_date + INTERVAL 14 DAY
    WHERE item_id = ? AND customer_id = ?
    """
    cur.execute(query, (item_id, customer_id))


def get_filtered_items(filter_attributes: Item = None,
                       use_patterns: bool = False,
                       min_price: float = -1,
                       max_price: float = -1,
                       min_start_year: int = -1,
                       max_start_year: int = -1) -> list[Item]:
    """
    Returns a list of Item objects matching the filters.
    """
    query = """SELECT i_item_id, 
                i_product_name,
                i_brand,
                i_category,
                i_manufact,
                i_current_price,
                YEAR(i_rec_start_date) AS start_year,
                i_num_owned FROM Item WHERE 1=1"""
    params = []
    oper = "LIKE" if use_patterns else "="

    #String attribute filters:
    if filter_attributes.item_id is not None:
        query += f" AND i_item_id {oper} ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.product_name is not None:
        query += f" AND i_product_name {oper} ?"
        params.append(filter_attributes.product_name)
    if filter_attributes.brand is not None:
        query += f" AND i_brand {oper} ?"
        params.append(filter_attributes.brand)
    if filter_attributes.category is not None:
        query += f" AND i_category {oper} ?"
        params.append(filter_attributes.category)
    if filter_attributes.manufact is not None:
        query += f" AND i_manufact {oper} ?"
        params.append(filter_attributes.manufact)

    #num_owned filter:
    if filter_attributes.num_owned != -1:
        query += " AND i_num_owned = ?"
        params.append(filter_attributes.num_owned)

    #price filters:
    if min_price != -1:
        query += " AND i_current_price >= ?"
        params.append(min_price)
    if max_price != -1:
        query += " AND i_current_price <= ?"
        params.append(max_price)
    if filter_attributes.current_price != -1 and min_price == -1 and max_price == -1:
        query += " AND i_current_price = ?"
        params.append(filter_attributes.current_price)

    #Start year filters:
    if min_start_year != -1:
        query += " AND YEAR(i_rec_start_date) >= ?"
        params.append(min_start_year)
    if max_start_year != -1:
        query += " AND YEAR(i_rec_start_date) <= ?"
        params.append(max_start_year)
    if filter_attributes.start_year != -1 and min_start_year == -1 and max_start_year == -1:
        query += " AND YEAR(i_rec_start_date) = ?"
        params.append(filter_attributes.start_year)

    cur.execute(query, params)
    return [_row_to_item(row) for row in cur.fetchall()]


def get_filtered_customers(filter_attributes: Customer = None, use_patterns: bool = False) -> list[Customer]:
    """
    Returns a list of Customer objects matching the filters.
    """
    query = """SELECT c.c_customer_id, CONCAT(TRIM(c.c_first_name), ' ', TRIM(c.c_last_name)) AS name,
    ca.ca_street_number, ca.ca_street_name, ca.ca_city, ca.ca_state, ca.ca_zip, c.c_email_address
    FROM Customer c LEFT JOIN customer_address ca ON c.c_current_addr_sk = ca.ca_address_sk 
    WHERE 1=1"""
    params = []
    oper = "LIKE" if use_patterns else "="

    #Filter the strings:
    if filter_attributes.customer_id is not None:
        query += f" AND c.c_customer_id {oper} ?"
        params.append(filter_attributes.customer_id)
    if filter_attributes.name is not None:
        query += f" AND CONCAT(TRIM(c.c_first_name), ' ', TRIM(c.c_last_name)) {oper} ?"
        params.append(filter_attributes.name)
    if filter_attributes.email is not None:
        query += f" AND c.c_email_address {oper} ?"
        params.append(filter_attributes.email)
    if filter_attributes.address is not None:
        full_address = ("CONCAT(TRIM(ca.ca_street_number), ' ', TRIM(ca.ca_street_name), ', ', TRIM(ca.ca_city), ', ', TRIM(ca.ca_state), ' ', TRIM(ca.ca_zip))")
        query += f" AND {full_address} {oper} ?"
        params.append(filter_attributes.address)
    cur.execute(query, params)
    return [_row_to_customer(row) for row in cur.fetchall()]


def get_filtered_rentals(filter_attributes: Rental = None,
                         min_rental_date: str = None,
                         max_rental_date: str = None,
                         min_due_date: str = None,
                         max_due_date: str = None) -> list[Rental]:
    """
    Returns a list of Rental objects matching the filters.
    """
    query = "SELECT item_id, customer_id, rental_date, due_date FROM Rental WHERE 1=1"
    params = []
    if filter_attributes.item_id is not None:
        query += " AND item_id = ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.customer_id is not None:
        query += " AND customer_id = ?"
        params.append(filter_attributes.customer_id)

    #Exact date filters when no range given:
    if filter_attributes.rental_date is not None and min_rental_date is None and max_rental_date is None:
        query += " AND rental_date = ?"
        params.append(filter_attributes.rental_date)
    if filter_attributes.due_date is not None and min_due_date is None and max_due_date is None:
        query += " AND due_date = ?"
        params.append(filter_attributes.due_date)

    #Filters with rental date range:
    if min_rental_date is not None:
        query += " AND rental_date >= ?"
        params.append(min_rental_date)
    if max_rental_date is not None:
        query += " AND rental_date <= ?"
        params.append(max_rental_date)

    #filters of due date range:
    if min_due_date is not None:
        query += " AND due_date >= ?"
        params.append(min_due_date)
    if max_due_date is not None:
        query += " AND due_date <= ?"
        params.append(max_due_date)

    cur.execute(query, params)
    return [_row_to_rental(row) for row in cur.fetchall()]

def get_filtered_rental_histories(filter_attributes: RentalHistory = None,
                                  min_rental_date: str = None,
                                  max_rental_date: str = None,
                                  min_due_date: str = None,
                                  max_due_date: str = None,
                                  min_return_date: str = None,
                                  max_return_date: str = None) -> list[RentalHistory]:
    """
    Returns a list of RentalHistory objects matching the filters.
    """
    query = "SELECT item_id, customer_id, rental_date, due_date, return_date FROM rental_history WHERE 1=1"
    params = []
    if filter_attributes.item_id is not None:
        query += " AND item_id = ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.customer_id is not None:
        query += " AND customer_id = ?"
        params.append(filter_attributes.customer_id)

    #Exact date filters:
    if filter_attributes.rental_date is not None and min_rental_date is None and max_rental_date is None:
        query += " AND rental_date = ?"
        params.append(filter_attributes.rental_date)
    if filter_attributes.due_date  is not None and min_due_date is None and max_due_date is None:
        query += " AND due_date = ?"
        params.append(filter_attributes.due_date)
    if filter_attributes.return_date is not None and min_return_date is None and max_return_date is None:
        query += " AND return_date = ?"
        params.append(filter_attributes.return_date)

    #rental date range filters:
    if min_rental_date is not None:
        query += " AND rental_date >= ?"
        params.append(min_rental_date)
    if max_rental_date is not None:
        query += " AND rental_date <= ?"
        params.append(max_rental_date)

    #due date range filters:
    if min_due_date is not None:
        query += " AND due_date >= ?"
        params.append(min_due_date)
    if max_due_date is not None:
        query += " AND due_date <= ?"
        params.append(max_due_date)

    #return date range filters:
    if min_return_date is not None:
        query += " AND return_date >= ?"
        params.append(min_return_date)
    if max_return_date is not None:
        query += " AND return_date <= ?"
        params.append(max_return_date)
    cur.execute(query, params)
    return [_row_to_rental_history(row) for row in cur.fetchall()]

def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:
    """
    Returns a list of Waitlist objects matching the filters.
    """
    query = "SELECT item_id, customer_id, place_in_line FROM Waitlist WHERE 1=1"
    params = []
    if filter_attributes.item_id is not None:
        query += " AND item_id = ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.customer_id is not None:
        query += " AND customer_id = ?"
        params.append(filter_attributes.customer_id)

    #Exact place in line filters when no range is given:
    if filter_attributes.place_in_line != -1 and min_place_in_line == -1 and max_place_in_line == -1:
        query += " AND place_in_line = ?"
        params.append(filter_attributes.place_in_line)

    #place in linge range filters:
    if min_place_in_line != -1:
        query += " AND place_in_line >= ?"
        params.append(min_place_in_line)
    if max_place_in_line != -1:
        query += " AND place_in_line <= ?"
        params.append(max_place_in_line)
    cur.execute(query, params)
    return [_row_to_waitlist(row) for row in cur.fetchall()]

def number_in_stock(item_id: str = None) -> int:
    """
    Returns num_owned - active rentals. Returns -1 if item doesn't exist.
    """
    #First find the number of copies owned in the store:
    cur.execute("SELECT i_num_owned FROM item WHERE i_item_id = ?", (item_id,))
    row = cur.fetchone()
    if row is None:
        return -1
    num_owned = int(row[0])

    #Then find the number of copies that are being rented:
    cur.execute("SELECT COUNT(*) FROM rental WHERE item_id = ?", (item_id,))
    rented_num = int(cur.fetchone()[0])

    #Now return available copies in the store:
    return num_owned - rented_num




def place_in_line(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's place_in_line, or -1 if not on waitlist.
    """
    cur.execute("SELECT place_in_line FROM Waitlist WHERE item_id = ? AND customer_id = ?", (item_id, customer_id), )
    row = cur.fetchone()
    return int(row[0]) if row is not None else -1


def line_length(item_id: str = None) -> int:
    """
    Returns how many people are on the waitlist for this item.
    """
    cur.execute("SELECT COUNT(*) FROM Waitlist WHERE item_id = ?", (item_id,))
    row = cur.fetchone()
    return int(row[0]) if row is not None else 0


def save_changes():
    """
    Commits all changes made to the db.
    """
    conn.commit()


def close_connection():
    """
    Closes the cursor and connection.
    """
    cur.close()
    conn.close()

